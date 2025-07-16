import re
from typing import List, Tuple
from services.context_analyzer import requires_context
from services.rag_service import get_relevant_documents, generate_answer_with_sources
from services.compare_service import handle_comparison

def build_conversation_context(messages: List[dict], max_context: int = 5) -> str:
    """Byg kontekst fra tidligere beskeder"""
    if not messages:
        return ""

    recent_messages = messages[-max_context:]
    context_parts = []
    for msg in recent_messages:
        if msg["role"] == "user":
            context_parts.append(f"Bruger: {msg['content']}")
        elif msg["role"] == "assistant":
            context_parts.append(f"Assistant: {msg['content']}")

    return "\n".join(context_parts)

def detect_comparison_query(question: str) -> bool:
    """Detect if question is asking for comparison"""
    comparison_patterns = [
        r'\bsammenlign\b', r'\bforskel\b', r'\blighed\b',
        r'\bvs\.?\b', r'\bversus\b', r'\bkontra\b',
        r'\bhvilken.*bedre\b', r'\bhvad er.*bedst\b'
    ]
    question_lower = question.lower()
    return any(re.search(p, question_lower) for p in comparison_patterns)

def process_contextual_query(question: str, conversation_history: List[dict], relevance_threshold: float = 0.6) -> Tuple[str, List[str]]:
    """Behandl spørgsmål med intelligent kontekst detektion og specialiseret handling"""
    print(f"\U0001F9E0 Analyserer spørgsmål: '{question}'")
    is_comparison = detect_comparison_query(question)
    conversation_context = build_conversation_context(conversation_history)
    needs_context = requires_context(question)

    if needs_context and conversation_context.strip():
        print("✅ Spørgsmål kræver kontekst - inkluderer chat historik")
        context_policy_numbers = re.findall(r'(?:police\s*nr\.?\s*|policy\s*no\.?)(\d+)', conversation_context.lower())
        current_policy_numbers = re.findall(r'(?:police\s*nr\.?\s*|policy\s*no\.?)(\d+)', question.lower())

        if current_policy_numbers:
            contextual_question = f"{question}"
        elif any(word in question.lower() for word in ["på", "ikke", "den", "det", "kunden"]):
            question_numbers = re.findall(r'\b(\d{4})\b', question)
            if question_numbers:
                contextual_question = f"Hvem er kunden på police nr {question_numbers[0]}?"
            else:
                contextual_question = f"""
Samtale historik:
{conversation_context}

Nyt spørgsmål: {question}

Besvar det nye spørgsmål, og tag hensyn til tidligere samtale hvis relevant. 
Hvis spørgsmålet refererer til noget fra tidligere (som \"den\", \"det\", \"kunden\" osv.), 
brug informationen fra samtale historikken.
"""
        else:
            contextual_question = f"""
Samtale historik:
{conversation_context}

Nyt spørgsmål: {question}

Besvar det nye spørgsmål, og tag hensyn til tidligere samtale hvis relevant. 
Hvis spørgsmålet refererer til noget fra tidligere (som \"den\", \"det\", \"kunden\" osv.), 
brug informationen fra samtale historikken.
"""
    else:
        if not needs_context:
            print("\U0001F3AF Selvstændigt spørgsmål - ignorerer chat historik")
        else:
            print("⚠️ Spørgsmål ville kræve kontekst, men ingen historik tilgængelig")
        contextual_question = question

    print(f"\U0001F916 Processeret spørgsmål: '{contextual_question}'")

    if is_comparison:
        print("\U0001F50D Sammenligning detekteret - bruger compare_service.handle_comparison")
        result_dict = handle_comparison(contextual_question)
        source_docs = result_dict.get("source_docs", [])
        sources = [
            f"Kilde {i+1}: {doc[:80]}... ({metadata.get('source', 'ukendt kilde')})"
            for i, (doc, metadata) in enumerate(
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
