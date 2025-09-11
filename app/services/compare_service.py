import re
from typing import Dict, List, Any, Optional
from vector_store import retrieve_similar_chunks
from mistral_local import generate_answer

# ------------------------------------------------------------
# Offentlig API
# ------------------------------------------------------------

def compare(question: str) -> dict:
    """
    Én dynamisk indgang: klassificér -> hent -> byg kontekst -> prompt -> LLM -> post-proc -> svar
    Kompatibel returstruktur.
    """
    print(f"🔶 compare_service: Starter pipeline for: '{question}'")

    try:
        comparison_type = _classify_type_llm_first(question)
        print(f"🔶 compare_service: Type valgt: {comparison_type}")

        profile = TYPE_PROFILES.get(comparison_type, TYPE_PROFILES["general_comparison"])

        # 1) Retrieval
        top_k = profile.get("top_k", 6)
        print(f"🔶 compare_service: Retrieval top_k={top_k}")
        results = retrieve_similar_chunks(question, top_k=top_k)
        documents_list = results.get("documents", [[]]) if results else [[]]
        documents = documents_list[0] if documents_list and len(documents_list) > 0 else []

        # 2) Tidlig exit hvis intet at sammenligne
        if not documents:
            msg = profile.get("no_docs_msg", "Ingen relevante dokumenter fundet.")
            return _build_response(
                subtype=comparison_type,
                question=question,
                result=msg,
                documents=[],
                meta={"classifier": "llm", "reason": "no_documents"}
            )

        # 3) Pre-filter (hurtig relevans)
        pre_filtered = _pre_filter_relevant_docs(question, documents)
        print(f"🔶 compare_service: Efter pre-filter: {len(pre_filtered)} dokumenter")

        # 4) Kontekst
        context = _build_comparison_context(
            pre_filtered,
            comparison_type=comparison_type,
            max_docs=profile.get("context_max_docs", 5),
            doc_snippet_len=profile.get("doc_snippet_len", 400),
            max_total_len=profile.get("max_total_len", 3000)
        )
        print(f"🔶 compare_service: Kontekst længde: {len(context)}")

        # 5) Prompt (base + typeblok + tvungen dansk + konklusion)
        prompt = _build_prompt(question, context, profile)
        print(f"🔶 compare_service: Prompt længde: {len(prompt)}")

        # 6) LLM
        llm_out = generate_answer(question, prompt)

        # 7) Post-processing (kun hvis nødvendigt)
        if len(llm_out) > 800:  # konservativ gate
            cleaned = _remove_repetitive_content(llm_out)
            fixed = _fix_incomplete_answer(cleaned)
            final_answer = fixed.strip()
        else:
            final_answer = _fix_incomplete_answer(llm_out.strip())

        # 8) Svar
        return _build_response(
            subtype=comparison_type,
            question=question,
            result=final_answer,
            documents=pre_filtered,
            context=context,
            meta={"classifier": "llm", "profile": comparison_type}
        )

    except Exception as e:
        print(f"🔴 compare_service: Fejl: {e}")
        return {
            "type": "compare",
            "subtype": "general_comparison",
            "question": question,
            "error": {
                "code": "COMPARE_PIPELINE_ERROR",
                "message": "Der opstod en teknisk fejl under behandlingen.",
                "debug": str(e)
            },
            "answer": "Der opstod en teknisk fejl ved behandling af din forespørgsel.",
            "result": "Der opstod en teknisk fejl ved behandling af din forespørgsel.",
            "sources_count": 0,
            "source_docs": []
        }

# ------------------------------------------------------------
# Typeprofiler (nem udvidelse)
# ------------------------------------------------------------

TYPE_PROFILES: Dict[str, Dict[str, Any]] = {
    "terms_comparison": {
        "keywords": ["betingelser", "vilkår", "terms", "conditions", "sammenlign", "forskel"],
        "top_k": 10,
        "context_max_docs": 5,
        "doc_snippet_len": 400,
        "max_total_len": 3000,
        "no_docs_msg": "Ingen relevante betingelser fundet til sammenligning.",
        "sections": [
            "Hovedforskelle mellem betingelserne",
            "Fordele og ulemper for hver option",
            "Anbefaling pr. scenarie",
            "Vigtige opmærksomhedspunkter"
        ]
    },
    "questionnaire_assessment": {
        "keywords": ["spørgeskema", "questionnaire", "survey", "form", "krav", "requirements"],
        "top_k": 8,
        "no_docs_msg": "Ingen relevante dokumenter fundet til vurdering.",
        "sections": [
            "Opfyldte krav",
            "Manglende krav",
            "Match til betingelser/produkter",
            "Anbefalede forbedringer",
            "Risikovurdering"
        ]
    },
    "policy_comparison": {
        "keywords": ["police", "policy", "forsikring", "insurance"],
        "top_k": 8,
        "no_docs_msg": "Ingen relevante policer fundet til sammenligning.",
        "sections": [
            "Dækning og omfang",
            "Præmier/priser",
            "Selvrisiko og begrænsninger",
            "Særlige fordele/ulemper",
            "Målgruppe og egnethed"
        ]
    },
    "general_comparison": {
        "keywords": [],
        "top_k": 4,
        "no_docs_msg": "Ingen relevante dokumenter fundet til sammenligning.",
        "sections": [
            "Hovedelementer/dækning",
            "Nøgleforskelle",
            "Konklusion"
        ]
    }
}

# ------------------------------------------------------------
# Klassifikation
# ------------------------------------------------------------

def _classify_type_llm_first(question: str) -> str:
    """
    LLM-klassifikation (dansk), returnerer en nøgle fra TYPE_PROFILES.
    Fejler LLM-kaldet, bruges en simpel regex-baseret heuristik som nødudvej.
    """
    try:
        label_prompt = (
            "Du er en klassifikator for forsikringsforespørgsler. "
            "Returnér KUN én af følgende etiketter (præcis streng): "
            f"{', '.join(TYPE_PROFILES.keys())}.\n\n"
            "Beslut ud fra teksten, hvad brugeren vil: \n"
            f"\"{question}\"\n\n"
            "Svar kun med selve etiketten, intet andet."
        )
        raw = generate_answer(question, label_prompt).strip().lower()
        # normalisér
        raw = re.sub(r'[^a-z_]', '', raw)
        if raw in TYPE_PROFILES:
            return raw
        # map små variationer
        if "terms" in raw or "vilk" in raw or "beting" in raw:
            return "terms_comparison"
        if "questionnaire" in raw or "survey" in raw or "sporgeskema" in raw:
            return "questionnaire_assessment"
        if "policy" in raw or "police" in raw or "insurance" in raw:
            return "policy_comparison"
        return "general_comparison"
    except Exception as e:
        print(f"⚠️ LLM-klassifikation fejlede, bruger heuristik: {e}")
        return _classify_comparison_type_regex(question)

def _classify_comparison_type_regex(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["betingelser", "vilkår", "terms", "conditions"]) and any(
        w in q for w in ["sammenlign", "forskel", "difference", "compare"]
    ):
        return "terms_comparison"
    if any(w in q for w in ["spørgeskema", "questionnaire", "survey", "form"]) and any(
        w in q for w in ["krav", "requirements", "lever op til", "passer", "match"]
    ):
        return "questionnaire_assessment"
    if any(w in q for w in ["police", "policy", "forsikring", "insurance"]):
        return "policy_comparison"
    return "general_comparison"

# ------------------------------------------------------------
# Promptbygning
# ------------------------------------------------------------

from config import BASE_PROMPT

def _build_prompt(question: str, context: str, profile: Dict[str, Any]) -> str:
    # Byg struktureret sektion
    sections = profile.get("sections", [])
    structure = "\n".join(f"{i+1}. {title}" for i, title in enumerate(sections)) or "1. Analyse\n2. Nøgleforskelle\n3. Konklusion"

    prompt = f"""{BASE_PROMPT}

Kontekst (uddrag fra relevante dokumenter):
{context}

Brugerens spørgsmål:
{question}

Lav en struktureret besvarelse med følgende overskrifter:
{structure}

Krav:
- Hold dig til konteksten hvor det er muligt; vær eksplicit når du ekstrapolerer.
- Brug bullet points, hvor det øger klarheden.
- Angiv antagelser, hvis nødvendige.
- Skriv altid en klar KONKLUSION til sidst.
"""
    return prompt

# ------------------------------------------------------------
# Responsbygning
# ------------------------------------------------------------

def _build_response(
    subtype: str,
    question: str,
    result: str,
    documents: List[str],
    context: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> dict:
    ctx_preview = (context[:200] + "...") if context and len(context) > 200 else (context or "")
    resp = {
        "type": "compare",
        "subtype": subtype,
        "question": question,
        "answer": result,  # backward compat
        "result": result,
        "sources_count": len(documents),
        "context_preview": ctx_preview,
        "source_docs": documents,
    }
    if meta:
        resp["meta"] = meta
    return resp

# ------------------------------------------------------------
# Kontekstbygning (optimeret)
# ------------------------------------------------------------

def _build_comparison_context(
    documents: List[str],
    comparison_type: str,
    max_docs: int = 5,
    doc_snippet_len: int = 400,
    max_total_len: int = 3000
) -> str:
    print(f"🔶 compare_service: Bygger kontekst for '{comparison_type}'")
    if not documents:
        return ""

    context_parts = []
    total_length = 0

    for i, doc in enumerate(documents[:max_docs]):
        snippet = doc.strip()[:doc_snippet_len]
        entry = f"--- Dokument {i+1} ---\n{snippet}\n"
        if total_length + len(entry) <= max_total_len:
            context_parts.append(entry)
            total_length += len(entry)
        else:
            print(f"⚠️ Dokument {i+1} udeladt (kontekstcap {max_total_len})")
            break

    context = "\n".join(context_parts)
    print(f"🔶 compare_service: Kontekst længde {len(context)}, dokumenter brugt {len(context_parts)}")
    return context

# ------------------------------------------------------------
# Pre-filter (hurtig heuristik)
# ------------------------------------------------------------

def _pre_filter_relevant_docs(question: str, documents: List[str]) -> List[str]:
    print(f"🔶 compare_service: Pre-filtering {len(documents)} dokumenter")
    q = question.lower()
    keywords = []

    ids = re.findall(r'(pidl\d+|[\d\-]+)', q)
    keywords.extend(ids)

    common_keywords = ["forsikring", "ansvar", "betingelser", "police", "professionelt", "diverse", "dækning", "selvrisiko", "præmie"]
    for w in common_keywords:
        if w in q:
            keywords.append(w)

    if not keywords:
        return documents[:3]

    scored = []
    for doc in documents:
        dl = doc.lower()
        score = sum(dl.count(k) for k in keywords)
        if len(doc) < 2000:
            score += 1
        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [d for s, d in scored[:3]]
    print(f"🔶 compare_service: Pre-filter reducerede til {len(top)}")
    return top

# ------------------------------------------------------------
# Post-processing (valgfrit, men nyttigt)
# ------------------------------------------------------------

def _remove_repetitive_content(text: str) -> str:
    if not text or len(text) < 100:
        return text
    lines = text.split('\n')
    cleaned_lines, prev, rep = [], "", 0
    for line in lines:
        ls = line.strip()
        if ls == prev.strip():
            rep += 1
            if rep <= 2:
                cleaned_lines.append(line)
        else:
            rep = 0
            cleaned_lines.append(line)
        prev = line

    text_cleaned = '\n'.join(cleaned_lines)
    paragraphs = text_cleaned.split('\n\n')
    unique, seen = [], set()
    for p in paragraphs:
        norm = ' '.join(p.split())
        if norm and len(norm) > 20:
            if norm not in seen:
                unique.append(p)
                seen.add(norm)
        else:
            unique.append(p)
    result = '\n\n'.join(unique)
    return _clean_repetitive_lists(result).strip()

def _clean_repetitive_lists(text: str) -> str:
    bullet_patterns = [r'^\s*-\s+', r'^\s*\*\s+', r'^\s*\d+\.\s+']
    lines = text.split('\n')
    cleaned, items, in_list = [], set(), False
    for line in lines:
        is_bullet = any(re.match(p, line) for p in bullet_patterns)
        if is_bullet:
            content = re.sub(r'^\s*[-*\d\.]\s*', '', line).strip()
            if content not in items and len(content) > 5:
                items.add(content)
                cleaned.append(line)
                in_list = True
        else:
            if in_list:
                items.clear()
                in_list = False
            cleaned.append(line)
    return '\n'.join(cleaned)

def _fix_incomplete_answer(answer: str) -> str:
    if not answer:
        return answer
    if re.search(r'\d+\.\s*$', answer.strip()):
        answer = re.sub(r'\d+\.\s*$', '', answer.strip())
    if answer and not answer.strip().endswith(('.', '!', '?')):
        answer = answer.strip() + '.'
    return answer
