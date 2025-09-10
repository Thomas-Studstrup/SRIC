from typing import List, Tuple, Optional
import re
import numpy as np
from sentence_transformers import CrossEncoder
from vector_store import retrieve_similar_chunks
from mistral_local import generate_answer
from utils.rag_service_utils import clean_document_content, safe_extract_results


def _normalize_threshold_float(value, *, default_enabled: Optional[float] = None) -> Tuple[Optional[float], bool]:
    """
    Konverter en mulig liste/array/None til (float|None, enabled_flag).
    - Hvis value er None eller tom ([], np.array([])), returneres (None, False) => tærskel er deaktiveret.
    - Hvis value kan reduceres til én skalar, returneres (float(v), True).
    - Hvis value er en vektor med flere værdier, bruges første element defensivt.
    - Hvis value ikke kan parses, falder vi tilbage til deaktiveret, medmindre default_enabled er sat.
    """
    if value is None:
        return (default_enabled, False if default_enabled is None else True)

    try:
        arr = np.asarray(value)
        # Tomt => deaktiver
        if arr.size == 0:
            return (default_enabled, False if default_enabled is None else True)
        # Skalar
        if arr.shape == () or arr.size == 1:
            return (float(arr.reshape(-1)[0]), True)
        # Flere værdier: tag første element
        return (float(arr.reshape(-1)[0]), True)
    except Exception:
        try:
            return (float(value), True)
        except Exception:
            return (default_enabled, False if default_enabled is None else True)


def get_relevant_documents(question: str, top_k: int = 8, relevance_threshold=0.5) -> List[dict]:
    # Normalisér threshold *før* logging og brug
    norm_threshold, threshold_enabled = _normalize_threshold_float(relevance_threshold, default_enabled=None)

    print(f"\U0001F50D Søger efter dokumenter for: '{question}'")
    if threshold_enabled:
        print(f"\U0001F50D Top_k: {top_k}, relevance_threshold: {norm_threshold}")
    else:
        # Bevidst: tom/None betyder "ingen filtrering på tærskel"
        print(f"\U0001F50D Top_k: {top_k}, relevance_threshold: (deaktiveret)")

    # Ekstraher policenumre
    policy_numbers = re.findall(r'(?:police\s*nr\.?\s*|policy\s*no\.?)\s*(\d+)', question.lower())
    if policy_numbers:
        print(f"\U0001F50D Fandt policenumre i spørgsmål: {policy_numbers}")
        enhanced_question = f"{question} policenummer {' '.join(policy_numbers)}"
        print(f"\U0001F50D Forbedret søgning: '{enhanced_question}'")
        results = retrieve_similar_chunks(enhanced_question, top_k=top_k)
    else:
        results = retrieve_similar_chunks(question, top_k=top_k)

    documents, metadatas, distances = safe_extract_results(results)

    if not documents:
        print("\u26A0\ufe0f Ingen dokumenter fundet")
        return []

    # Step 3: Reranking med CrossEncoder
    print(f"\U0001F501 Reranking {len(documents)} dokumenter med cross-encoder")
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    rerank_input = [(question, doc) for doc in documents]
    rerank_scores = reranker.predict(rerank_input)
    # Gør robust mod NumPy-typer senere i koden
    rerank_scores = np.asarray(rerank_scores).astype(float).reshape(-1).tolist()

    combined = list(zip(documents, metadatas, distances, rerank_scores))
    combined.sort(key=lambda x: x[3], reverse=True)

    all_docs: List[dict] = []
    filtered_docs: List[dict] = []

    for i, (doc, meta, dist, score) in enumerate(combined):
        relevance_score = float(score)
        cleaned_content = clean_document_content(doc)

        print(f"\U0001F4C4 Dokument {i+1}: distance={dist}, rerank_score={score:.3f}")
        preview = (cleaned_content or "")[:150]
        print(f"\U0001F4C4 Dokument {i+1} preview: {preview}...")

        if policy_numbers:
            lc = (cleaned_content or "").lower()
            for policy_num in policy_numbers:
                if policy_num in lc:
                    relevance_score += 0.5
                    print(f"\U0001F3AF Dokument {i+1} indeholder policenummer {policy_num}, boost til relevance: {relevance_score:.3f}")

        if len((cleaned_content or "").strip()) < 50:
            print(f"⚠️ Dokument {i+1} for kort efter rensning, springer over")
            continue

        doc_info = {
            "content": cleaned_content,
            "metadata": meta,
            "relevance_score": relevance_score,
            "distance": dist
        }

        all_docs.append(doc_info)

        if threshold_enabled and norm_threshold is not None:
            if relevance_score >= norm_threshold:
                filtered_docs.append(doc_info)
                print(f"✅ Dokument {i+1} inkluderet (relevance: {relevance_score:.3f})")
            else:
                print(f"❌ Dokument {i+1} filtreret ud (relevance: {relevance_score:.3f} < {norm_threshold})")
        else:
            # Ingen tærskel => inkluder alle (vi beholder stadig fallback nedenfor for sikkerhed)
            filtered_docs.append(doc_info)
            print(f"✅ Dokument {i+1} inkluderet (tærskel deaktiveret, relevance: {relevance_score:.3f})")

    # Fallback: hvis intet slap igennem (kan ske ved hård tærskel)
    if not filtered_docs and all_docs:
        all_docs.sort(key=lambda x: x['relevance_score'], reverse=True)
        filtered_docs = all_docs[:3]
        print(f"🔄 Fallback: Inkluderer de {len(filtered_docs)} bedste dokumenter")
        for j, doc in enumerate(filtered_docs):
            print(f"🔄 Fallback dokument {j+1}: relevance={doc['relevance_score']:.3f}")

    print(f"✅ Fandt {len(filtered_docs)} relevante dokumenter (filteret fra {len(documents)})")
    return filtered_docs


def generate_answer_with_sources(question: str, documents: List[dict], min_source_relevance=0.6) -> Tuple[str, List[str]]:
    if not documents:
        return "Ingen relevante dokumenter blev fundet.", []

    # Normaliser kilde-tærskel for at undgå samme faldgrube
    norm_min_src, src_thr_enabled = _normalize_threshold_float(min_source_relevance, default_enabled=0.6)
    if not src_thr_enabled or norm_min_src is None:
        # Hvis brugeren forsøger at deaktivere den, accepterer vi alle kilder
        norm_min_src = -float("inf")

    context_parts: List[str] = []
    potential_sources = []

    for i, doc in enumerate(documents):
        content = doc.get('content') or ""
        context_parts.append(content)
        meta = doc.get("metadata", {}) or {}
        score = float(doc.get("relevance_score", 0.0) or 0.0)
        src = meta.get("source", f"Dokument {i+1}")
        potential_sources.append({
            'source': src,
            'relevance_score': score,
            'distance': doc.get('distance', 1.0)
        })

    context = "\n\n".join(context_parts)
    print(f"\U0001F916 Genererer svar med {len(context_parts)} dokumenter i kontekst")
    print(f"\U0001F916 Total kontekst længde: {len(context)} karakterer")

    answer = generate_answer(question, context)

    relevant_sources: List[str] = []
    for s in potential_sources:
        if float(s['relevance_score']) >= norm_min_src:
            if s['source'] not in relevant_sources:
                relevant_sources.append(s['source'])
                print(f"📋 Inkluderer kilde: {s['source']} (relevance: {s['relevance_score']:.3f})")
        else:
            print(f"📋 Filtrerer kilde: {s['source']} (relevance: {s['relevance_score']:.3f} < {norm_min_src})")

    print(f"✅ Returnerer svar med {len(relevant_sources)} kilder (filteret fra {len(potential_sources)})")
    return answer, relevant_sources
