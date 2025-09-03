from typing import List, Tuple
import re
from sentence_transformers import CrossEncoder
from vector_store import retrieve_similar_chunks
from mistral_local import generate_answer
from utils.rag_service_utils import clean_document_content, safe_extract_results

def get_relevant_documents(question: str, top_k: int = 8, relevance_threshold: float = 0.5) -> List[dict]:
    print(f"\U0001F50D Søger efter dokumenter for: '{question}'")
    print(f"\U0001F50D Top_k: {top_k}, relevance_threshold: {relevance_threshold}")

    # Ekstraher policenumre
    policy_numbers = re.findall(r'(?:police\s*nr\.?\s*|policy\s*no\.?)(\d+)', question.lower())
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

    combined = list(zip(documents, metadatas, distances, rerank_scores))
    combined.sort(key=lambda x: x[3], reverse=True)

    all_docs = []
    filtered_docs = []

    for i, (doc, meta, dist, score) in enumerate(combined):
        relevance_score = score
        cleaned_content = clean_document_content(doc)

        print(f"\U0001F4C4 Dokument {i+1}: distance={dist}, rerank_score={score:.3f}")
        print(f"\U0001F4C4 Dokument {i+1} preview: {cleaned_content[:150]}...")

        if policy_numbers:
            for policy_num in policy_numbers:
                if policy_num in cleaned_content.lower():
                    relevance_score += 0.5
                    print(f"\U0001F3AF Dokument {i+1} indeholder policenummer {policy_num}, boost til relevance: {relevance_score:.3f}")

        if len(cleaned_content.strip()) < 50:
            print(f"⚠️ Dokument {i+1} for kort efter rensning, springer over")
            continue

        doc_info = {
            "content": cleaned_content,
            "metadata": meta,
            "relevance_score": relevance_score,
            "distance": dist
        }

        all_docs.append(doc_info)

        if relevance_score >= relevance_threshold:
            filtered_docs.append(doc_info)
            print(f"✅ Dokument {i+1} inkluderet (relevance: {relevance_score:.3f})")
        else:
            print(f"❌ Dokument {i+1} filtreret ud (relevance: {relevance_score:.3f} < {relevance_threshold})")

    if not filtered_docs and all_docs:
        all_docs.sort(key=lambda x: x['relevance_score'], reverse=True)
        filtered_docs = all_docs[:3]
        print(f"🔄 Fallback: Inkluderer de {len(filtered_docs)} bedste dokumenter")
        for i, doc in enumerate(filtered_docs):
            print(f"🔄 Fallback dokument {i+1}: relevance={doc['relevance_score']:.3f}")

    print(f"✅ Fandt {len(filtered_docs)} relevante dokumenter (filteret fra {len(documents)})")
    return filtered_docs

def generate_answer_with_sources(question: str, documents: List[dict], min_source_relevance: float = 0.6) -> Tuple[str, List[str]]:
    if not documents:
        return "Ingen relevante dokumenter blev fundet.", []

    context_parts = []
    potential_sources = []

    for i, doc in enumerate(documents):
        context_parts.append(doc['content'])
        meta = doc.get("metadata", {})
        score = doc.get("relevance_score", 0.0)
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

    relevant_sources = []
    for s in potential_sources:
        if s['relevance_score'] >= min_source_relevance:
            if s['source'] not in relevant_sources:
                relevant_sources.append(s['source'])
                print(f"📋 Inkluderer kilde: {s['source']} (relevance: {s['relevance_score']:.3f})")
        else:
            print(f"📋 Filtrerer kilde: {s['source']} (relevance: {s['relevance_score']:.3f} < {min_source_relevance})")

    print(f"✅ Returnerer svar med {len(relevant_sources)} kilder (filteret fra {len(potential_sources)})")
    return answer, relevant_sources
