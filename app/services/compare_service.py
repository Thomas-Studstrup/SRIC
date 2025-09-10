import re
from typing import Dict, List, Any, Optional
from vector_store import retrieve_similar_chunks
from mistral_local import generate_answer

def handle_comparison(question: str) -> dict:
    """
    Hovedfunktion til at håndtere forskellige typer af sammenligninger.
    
    Args:
        question: Brugerens spørgsmål/anmodning om sammenligning
        
    Returns:
        Dict med sammenligning resultater
    """
    print(f"🔶 compare_service: Starter sammenligning for: '{question}'")
    
    # Klassificer typen af sammenligning
    comparison_type = _classify_comparison_type(question)
    print(f"🔶 compare_service: Sammenligning type: {comparison_type}")
    
    try:
        if comparison_type == "terms_comparison":
            return _compare_terms_and_conditions(question)
        elif comparison_type == "questionnaire_assessment":
            return _assess_questionnaire_against_requirements(question)
        elif comparison_type == "policy_comparison":
            return _compare_policies(question)
        elif comparison_type == "company_comparison":
            return _compare_companies(question)
        else:
            return _general_comparison(question)
    except Exception as e:
        print(f"🔴 compare_service: Fejl ved sammenligning: {e}")
        return {
            "type": "compare", 
            "error": f"Fejl ved sammenligning: {str(e)}",
            "question": question,
            "answer": "Der opstod en teknisk fejl ved behandling af din sammenligning. Prøv venligst igen."
        }

def _classify_comparison_type(question: str) -> str:
    """Klassificer typen af sammenligning baseret på spørgsmålet."""
    q = question.lower()
    
    print(f"🔶 compare_service: Klassificerer type for: '{q}'")
    
    # Betingelser sammenligning
    if any(word in q for word in ["betingelser", "vilkår", "terms", "conditions"]):
        if any(word in q for word in ["sammenlign", "forskel", "difference", "compare"]):
            return "terms_comparison"
    
    # Spørgeskema vurdering
    if any(word in q for word in ["spørgeskema", "questionnaire", "survey", "form"]):
        if any(word in q for word in ["krav", "requirements", "lever op til", "passer", "match"]):
            return "questionnaire_assessment"
    
    # Police sammenligning
    if any(word in q for word in ["police", "policy", "forsikring", "insurance"]):
        return "policy_comparison"
    
    # Selskab sammenligning
    if any(word in q for word in ["selskab", "company", "firma", "tryg", "topdanmark", "cna", "hdi"]):
        return "company_comparison"
    
    return "general_comparison"

def _compare_terms_and_conditions(question: str) -> dict:
    """Sammenlign betingelser mellem forskellige selskaber eller produkter."""
    print(f"🔶 compare_service: Sammenligner betingelser")
    
    # Hent relevante betingelser fra vector store
    results = retrieve_similar_chunks(question, k=10)
    documents_list = results.get("documents", [[]]) if results else [[]]
    documents = documents_list[0] if documents_list is not None and len(documents_list) > 0 else []
    
    if not documents:
        return {
            "type": "compare",
            "subtype": "terms_comparison",
            "result": "Ingen relevante betingelser fundet til sammenligning.",
            "question": question
        }
    
    # Byg kontekst for sammenligning
    context = _build_comparison_context(documents, "betingelser")
    
    # Generer sammenligning med LLM
    comparison_prompt = f"""
Du skal lave en detaljeret sammenligning af betingelser baseret på følgende kontekst.

Kontekst:
{context}

Spørgsmål: {question}

Lav en struktureret sammenligning der inkluderer:
1. Hovedforskelle mellem betingelserne
2. Fordele og ulemper for hver option
3. Anbefaling baseret på forskellige scenarier
4. Vigtige punkter at være opmærksom på

Sammenligning:"""
    
    comparison_result = generate_answer(question, comparison_prompt)
    
    return {
        "type": "compare",
        "subtype": "terms_comparison",
        "question": question,
        "result": comparison_result,
        "sources_count": len(documents),
        "context_preview": context[:200] + "..." if len(context) > 200 else context
    }

def _assess_questionnaire_against_requirements(question: str) -> dict:
    """Vurder om spørgeskemaer lever op til krav og hvilke betingelser de passer til."""
    print(f"🔶 compare_service: Vurderer spørgeskema mod krav")
    
    # Hent relevante dokumenter (både spørgeskemaer og krav)
    results = retrieve_similar_chunks(question, k=8)
    documents_list = results.get("documents", [[]]) if results else [[]]
    documents = documents_list[0] if documents_list is not None and len(documents_list) > 0 else []
    
    if not documents:
        return {
            "type": "compare",
            "subtype": "questionnaire_assessment", 
            "result": "Ingen relevante dokumenter fundet til vurdering.",
            "question": question
        }
    
    context = _build_comparison_context(documents, "spørgeskema_vurdering")
    
    assessment_prompt = f"""
Du skal vurdere spørgeskemaer mod krav og betingelser baseret på følgende kontekst.

Kontekst:
{context}

Spørgsmål: {question}

Lav en struktureret vurdering der inkluderer:
1. Hvilke krav spørgeskemaet opfylder
2. Hvilke krav der ikke opfyldes
3. Hvilke betingelser/produkter der passer bedst
4. Anbefalinger til forbedringer
5. Risiko-vurdering

Vurdering:"""
    
    assessment_result = generate_answer(question, assessment_prompt)
    
    return {
        "type": "compare",
        "subtype": "questionnaire_assessment",
        "question": question,
        "result": assessment_result,
        "sources_count": len(documents)
    }

def _compare_policies(question: str) -> dict:
    """Sammenlign forsikringspolicer."""
    print(f"🔶 compare_service: Sammenligner policer")
    
    results = retrieve_similar_chunks(question, k=8)
    documents_list = results.get("documents", [[]]) if results else [[]]
    documents = documents_list[0] if documents_list is not None and len(documents_list) > 0 else []
    
    if not documents:
        return {
            "type": "compare",
            "subtype": "policy_comparison",
            "result": "Ingen relevante policer fundet til sammenligning.",
            "question": question
        }
    
    context = _build_comparison_context(documents, "policer")
    
    policy_prompt = f"""
Du skal sammenligne forsikringspolicer baseret på følgende kontekst.

Kontekst:
{context}

Spørgsmål: {question}

Lav en struktureret sammenligning der inkluderer:
1. Dækning og omfattning
2. Præmier og priser
3. Selvrisiko og begrænsninger
4. Særlige fordele og ulemper
5. Målgruppe og egnethed

Sammenligning:"""
    
    policy_result = generate_answer(question, policy_prompt)
    
    return {
        "type": "compare",
        "subtype": "policy_comparison",
        "question": question,
        "result": policy_result,
        "sources_count": len(documents)
    }

def _compare_companies(question: str) -> dict:
    """Sammenlign forsikringsselskaber."""
    print(f"🔶 compare_service: Sammenligner selskaber")
    
    # Reduceret antal dokumenter for hastighed
    results = retrieve_similar_chunks(question, k=6)  # Reduceret fra 10
    documents_list = results.get("documents", [[]]) if results else [[]]
    documents = documents_list[0] if documents_list is not None and len(documents_list) > 0 else []
    
    if not documents:
        return {
            "type": "compare",
            "subtype": "company_comparison",
            "answer": "Ingen relevante selskabsoplysninger fundet til sammenligning.",
            "result": "Ingen relevante selskabsoplysninger fundet til sammenligning.",
            "question": question,
            "sources_count": 0
        }
    
    # Pre-filter dokumenter
    relevant_docs = _pre_filter_relevant_docs(question, documents)
    print(f"🔶 compare_service: Efter pre-filtering: {len(relevant_docs)} selskabsdokumenter")
    
    context = _build_comparison_context(relevant_docs, "selskaber")
    
    # Kortere prompt for hurtigere processing
    company_prompt = f"""Sammenlign disse forsikringsselskaber kort:

{context}

Spørgsmål: {question}

Lav en kort sammenligning:
1. Hovedforskelle mellem selskaberne
2. Produkter og priser
3. Konklusion

Svar:"""
    
    print(f"🔶 compare_service: Kalder generate_answer for selskaber...")
    
    import time
    start_time = time.time()
    
    company_result = generate_answer(question, company_prompt)
    
    end_time = time.time()
    print(f"🔶 compare_service: Selskab LLM tog {end_time - start_time:.2f} sekunder")
    
    # Clean up repetitive content
    cleaned_result = _remove_repetitive_content(company_result)
    print(f"🔶 compare_service: Selskab sammenligning efter cleaning - længde: {len(cleaned_result)} karakterer")
    
    return {
        "type": "compare",
        "subtype": "company_comparison",
        "question": question,
        "answer": cleaned_result,
        "result": cleaned_result,
        "sources_count": len(relevant_docs)
    }

def _general_comparison(question: str) -> dict:
    """Generel sammenligning når typen ikke kan identificeres specifikt."""
    print(f"🔶 compare_service: Generel sammenligning")
    
    # Reduceret fra k=8 til k=4 for bedre performance
    results = retrieve_similar_chunks(question, k=4)
    print(f"🔶 compare_service: retrieve_similar_chunks returnerede: {type(results)}")
    print(f"🔶 compare_service: retrieve_similar_chunks keys: {results.keys() if results else 'None'}")
    
    documents_list = results.get("documents", [[]]) if results else [[]]
    documents = documents_list[0] if documents_list is not None and len(documents_list) > 0 else []
    
    print(f"🔶 compare_service: Antal dokumenter fundet: {len(documents)}")
    
    if not documents:
        return {
            "type": "compare",
            "subtype": "general_comparison",
            "answer": "Ingen relevante dokumenter fundet til sammenligning.",
            "result": "Ingen relevante dokumenter fundet til sammenligning.",
            "question": question,
            "sources_count": 0
        }
    
    # Pre-filter dokumenter for relevans
    relevant_docs = _pre_filter_relevant_docs(question, documents)
    print(f"🔶 compare_service: Efter pre-filtering: {len(relevant_docs)} dokumenter")
    
    # Log de første par dokumenter for at se hvad vi arbejder med
    for i, doc in enumerate(relevant_docs[:2]):  # Kun top 2 for hastighed
        print(f"🔶 compare_service: Dokument {i+1} preview: {doc[:100]}...")
    
    context = _build_comparison_context(relevant_docs, "generel")
    print(f"🔶 compare_service: Context bygget, længde: {len(context)} karakterer")
    print(f"🔶 compare_service: Context preview: {context[:200]}...")
    
    # Kort og fokuseret prompt for hurtigere processing med specifik struktur
    general_prompt = f"""Sammenlign disse forsikringsbetingelser kort og præcist:

{context}

Spørgsmål: {question}

Lav en komplet sammenligning med følgende struktur:
1. Hovedelementer - hvad dækker hver forsikring
2. Nøgleforskelle - hovedforskelle mellem dem
3. Konklusion - hvilken er bedst og hvornår

Skriv punkt 3 komplet og afslut ikke før alle 3 punkter er færdige.

Svar:"""

    print(f"🔶 compare_service: Prompt længde: {len(general_prompt)} karakterer")
    print(f"🔶 compare_service: Kalder generate_answer...")
    
    import time
    start_time = time.time()
    
    general_result = generate_answer(question, general_prompt)
    
    end_time = time.time()
    print(f"🔶 compare_service: LLM tog {end_time - start_time:.2f} sekunder")
    print(f"🔶 compare_service: LLM svar modtaget!")
    print(f"🔶 compare_service: Svar type: {type(general_result)}")
    print(f"🔶 compare_service: Svar længde: {len(general_result)} karakterer")
    print(f"🔶 compare_service: Svar preview: {general_result[:200]}...")
    
    # Clean up repetitive content and fix incomplete answers
    cleaned_result = _remove_repetitive_content(general_result)
    fixed_result = _fix_incomplete_answer(cleaned_result)
    print(f"🔶 compare_service: Efter cleaning og fixing - længde: {len(fixed_result)} karakterer")
    
    return {
        "type": "compare",
        "subtype": "general_comparison",
        "question": question,
        "answer": fixed_result,
        "result": fixed_result,
        "sources_count": len(relevant_docs)
    }

def _build_comparison_context(documents: List[str], comparison_type: str) -> str:
    """Byg kontekst optimeret til sammenligning."""
    print(f"🔶 compare_service: Bygger kontekst for {comparison_type}")
    
    if not documents:
        return ""
    
    # Organisér dokumenter for bedre sammenligning
    context_parts = []
    
    for i, doc in enumerate(documents):
        # Kortere dokumenter for hastighed - kun de første 800 karakterer
        doc_excerpt = doc[:800] + "..." if len(doc) > 800 else doc
        context_parts.append(f"--- Dokument {i+1} ---\n{doc_excerpt}\n")
    
    context = "\n".join(context_parts)
    
    # Kraftigt reduceret kontekst størrelse for hastighed
    max_context_length = 2000  # Reduceret fra 4000 for hurtigere processing
    if len(context) > max_context_length:
        context = context[:max_context_length] + "\n... (kontekst forkortet for hastighed)"
    
    return context

def _remove_repetitive_content(text: str) -> str:
    """Remove repetitive lines and sections from LLM output."""
    if not text or len(text) < 100:
        return text
    
    # Split into lines
    lines = text.split('\n')
    
    # Remove duplicate consecutive lines
    cleaned_lines = []
    prev_line = ""
    repetition_count = 0
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip empty lines or very short lines when they repeat
        if line_stripped == prev_line.strip():
            repetition_count += 1
            # Only allow up to 2 consecutive identical lines
            if repetition_count <= 2:
                cleaned_lines.append(line)
        else:
            repetition_count = 0
            cleaned_lines.append(line)
        
        prev_line = line
    
    # Look for repeating sections (paragraphs or bullet points)
    text_cleaned = '\n'.join(cleaned_lines)
    
    # Split into paragraphs
    paragraphs = text_cleaned.split('\n\n')
    unique_paragraphs = []
    seen_paragraphs = set()
    
    for paragraph in paragraphs:
        # Normalize paragraph for comparison (remove extra whitespace)
        normalized = ' '.join(paragraph.split())
        
        # Skip if we've seen this paragraph before (or a very similar one)
        if normalized and len(normalized) > 20:
            # Check if this paragraph is very similar to any we've seen
            is_duplicate = False
            for seen in seen_paragraphs:
                # If paragraphs are very similar (>80% overlap), consider it a duplicate
                if len(normalized) > 50 and len(seen) > 50:
                    similarity = len(set(normalized.split()) & set(seen.split())) / len(set(normalized.split()) | set(seen.split()))
                    if similarity > 0.8:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_paragraphs.append(paragraph)
                seen_paragraphs.add(normalized)
        else:
            # Keep short paragraphs (they're usually headers or transitions)
            unique_paragraphs.append(paragraph)
    
    result = '\n\n'.join(unique_paragraphs)
    
    # Additional cleanup: remove sections that repeat the same bullet points
    result = _clean_repetitive_lists(result)
    
    return result.strip()


def _clean_repetitive_lists(text: str) -> str:
    """Clean up repetitive bullet point lists."""
    import re
    
    # Look for bullet point patterns
    bullet_patterns = [r'^\s*-\s+', r'^\s*\*\s+', r'^\s*\d+\.\s+']
    
    lines = text.split('\n')
    cleaned_lines = []
    current_list_items = set()
    in_list = False
    
    for line in lines:
        is_bullet = any(re.match(pattern, line) for pattern in bullet_patterns)
        
        if is_bullet:
            # Extract the content after the bullet
            content = re.sub(r'^\s*[-*\d\.]\s*', '', line).strip()
            
            # If we haven't seen this content before in the current list
            if content not in current_list_items and len(content) > 5:
                current_list_items.add(content)
                cleaned_lines.append(line)
                in_list = True
            # Skip duplicate bullet points
        else:
            # Not a bullet point, reset list tracking
            if in_list:
                current_list_items.clear()
                in_list = False
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def _pre_filter_relevant_docs(question: str, documents: List[str]) -> List[str]:
    """Quick filtering før expensive LLM processing."""
    print(f"🔶 compare_service: Pre-filtering {len(documents)} dokumenter")
    
    # Udtræk nøgleord fra spørgsmålet
    question_lower = question.lower()
    keywords = []
    
    # Specifik forsikrings-id detection
    import re
    ids = re.findall(r'(pidl\d+|[\d\-]+)', question_lower)
    keywords.extend(ids)
    
    # Almindelige forsikrings nøgleord
    common_keywords = ["forsikring", "ansvar", "betingelser", "police", "professionelt", "diverse"]
    for word in common_keywords:
        if word in question_lower:
            keywords.append(word)
    
    print(f"🔶 compare_service: Nøgleord: {keywords}")
    
    if not keywords:
        # Hvis ingen specifikke nøgleord, returner top 3 dokumenter
        return documents[:3]
    
    # Score dokumenter baseret på nøgleord matches
    scored_docs = []
    for doc in documents:
        doc_lower = doc.lower()
        score = 0
        
        for keyword in keywords:
            if keyword in doc_lower:
                score += doc_lower.count(keyword)
        
        # Prioriter kortere dokumenter (ofte mere fokuserede)
        if len(doc) < 2000:
            score += 1
            
        scored_docs.append((score, doc))
    
    # Sorter efter score og returner top dokumenter
    scored_docs.sort(key=lambda x: x[0], reverse=True)
    relevant_docs = [doc for score, doc in scored_docs[:3]]  # Top 3 dokumenter
    
    print(f"🔶 compare_service: Pre-filtering reduceret til {len(relevant_docs)} dokumenter")
    return relevant_docs

def _fix_incomplete_answer(answer: str) -> str:
    """Fix incomplete answers that end abruptly."""
    if not answer:
        return answer
    
    # Check if answer ends with just a number and period (like "3.")
    import re
    if re.search(r'\d+\.\s*$', answer.strip()):
        print(f"🔶 compare_service: Detekteret ufuldstændig svar (ender med nummer)")
        # Remove the incomplete numbered point
        answer = re.sub(r'\d+\.\s*$', '', answer.strip())
    
    # If answer doesn't end with period, add one
    if answer and not answer.strip().endswith('.'):
        answer = answer.strip() + '.'
    
    return answer
