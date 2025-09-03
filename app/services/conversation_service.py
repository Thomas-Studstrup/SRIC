import re
from typing import List, Tuple
from services.rag_service import get_relevant_documents, generate_answer_with_sources
from services.compare_service import handle_comparison


def detect_comparison_query(question: str) -> bool:
    """Detect if question is asking for comparison"""
    comparison_patterns = [
        r'\bsammenlign\b', r'\bforskel\b', r'\blighed\b',
        r'\bvs\.?\b', r'\bversus\b', r'\bkontra\b',
        r'\bhvilken.*bedre\b', r'\bhvad er.*bedst\b'
    ]
    question_lower = question.lower()
    return any(re.search(p, question_lower) for p in comparison_patterns)

def process_contextual_query(question: str, relevance_threshold: float = 0.6) -> Tuple[str, List[str]]:
    """Behandl spørgsmål med intelligent kontekst detektion og specialiseret handling"""
    print(f"\U0001F9E0 Analyserer spørgsmål: '{question}'")
    is_comparison = detect_comparison_query(question)
    contextual_question = question  # Brug kun det aktuelle spørgsmål
    print(f"\U0001F916 Processeret spørgsmål: '{contextual_question}'")

    if is_comparison:
        print("\U0001F50D Sammenligning detekteret - bruger compare_service.handle_comparison")
        result_dict = handle_comparison(contextual_question)
        source_docs = result_dict.get("source_docs", [])
        
        sources = [
            f"Kilde {i+1}: {doc[:80]}... ({metadata.get('filename', 'ukendt kilde')})" for i, (doc, metadata) in enumerate(
                zip(
                    source_docs,
                    [d.get('metadata', {}) if isinstance(d, dict) else {} for d in source_docs]
                )
            )
        ]
        return result_dict.get("result", "Ingen resultat returneret."), sources
    else:
        documents = get_relevant_documents(contextual_question, relevance_threshold=relevance_threshold)
        return generate_answer_with_sources(contextual_question, documents)
