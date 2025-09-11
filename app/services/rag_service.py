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

    # Find alle dokument_id'er for relevante chunks
    document_ids = set()
    filenames = {}
    for meta in metadatas:
        if isinstance(meta, dict):
            doc_id = meta.get("document_id")
            filename = meta.get("filename")
            if doc_id:
                document_ids.add(doc_id)
                if filename:
                    filenames[doc_id] = filename

    # Hent alle chunks for hvert dokument og saml dem
    from document_indexer import get_all_chunks_for_document
    filtered_docs: List[dict] = []
    for doc_id in document_ids:
        chunks = get_all_chunks_for_document(doc_id)
        full_content = "\n\n".join([clean_document_content(chunk) for chunk in chunks])
        meta = {"document_id": doc_id, "filename": filenames.get(doc_id, "ukendt")}
        doc_info = {
            "content": full_content,
            "metadata": meta,
            "relevance_score": 1.0,  # Kan evt. beregnes som max af relevante chunks
            "distance": None
        }
        filtered_docs.append(doc_info)
        print(f"✅ Inkluderer hele dokumentet: {filenames.get(doc_id, 'ukendt')}")

    print(f"✅ Fandt {len(filtered_docs)} relevante dokumenter (samlet fra chunks)")
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
        # Brug filnavn som kilde hvis muligt
        src = meta.get("filename") or meta.get("source") or f"Dokument {i+1}"
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
