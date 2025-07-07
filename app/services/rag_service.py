from typing import List, Tuple
import json
import re
from vector_store import retrieve_similar_chunks
from mistral_local import generate_answer

def clean_document_content(content: str) -> str:
    """Clean document content from template artifacts and formatting issues"""
    if not content:
        return content
    
    # Remove common template artifacts
    content = re.sub(r'PIDL\d+', '', content)  # Remove policy IDs that pollute context
    content = re.sub(r'^\d+\.\s*$', '', content, flags=re.MULTILINE)  # Remove standalone numbers
    content = re.sub(r'^\*\s*$', '', content, flags=re.MULTILINE)  # Remove standalone bullets
    content = re.sub(r'^\-\s*$', '', content, flags=re.MULTILINE)  # Remove standalone dashes
    
    # Remove excessive whitespace and empty lines
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Max 2 consecutive newlines
    content = re.sub(r'[ \t]+', ' ', content)  # Normalize spaces
    
    # Remove repeated phrases that often appear in templates
    content = re.sub(r'(.*?)\1{3,}', r'\1', content)  # Remove text repeated 4+ times
    
    # Remove common template headers/footers
    template_patterns = [
        r'^\s*-+\s*$',  # Lines with just dashes
        r'^\s*=+\s*$',  # Lines with just equals
        r'^\s*\*+\s*$',  # Lines with just asterisks
        r'^\s*##+\s*$',  # Lines with just hashes
        r'^\s*Side \d+ af \d+\s*$',  # Page numbers
        r'^\s*Dato:.*$',  # Date lines
        r'^\s*Version:.*$',  # Version lines
    ]
    
    for pattern in template_patterns:
        content = re.sub(pattern, '', content, flags=re.MULTILINE)
    
    # Clean up the result
    content = '\n'.join(line.strip() for line in content.split('\n') if line.strip())
    
    return content.strip()

def get_relevant_documents(question: str, top_k: int = 15, relevance_threshold: float = 0.3) -> List[dict]:
    """Hent relevante dokumenter baseret på spørgsmål og filtrer efter relevance score"""
    print(f"🔍 Søger efter dokumenter for: '{question}'")
    print(f"🔍 Top_k: {top_k}, relevance_threshold: {relevance_threshold}")
    
    # Extract specific policy numbers from the question to improve search
    import re
    policy_numbers = re.findall(r'(?:police\s*nr\.?\s*|policy\s*no\.?\s*)(\d+)', question.lower())
    if policy_numbers:
        print(f"🔍 Fandt policenumre i spørgsmål: {policy_numbers}")
        # Enhance the search query with specific policy numbers
        enhanced_question = f"{question} policenummer {' '.join(policy_numbers)}"
        print(f"🔍 Forbedret søgning: '{enhanced_question}'")
        results = retrieve_similar_chunks(enhanced_question, top_k=top_k)
    else:
        results = retrieve_similar_chunks(question, top_k=top_k)
    
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    
    if not documents:
        print("⚠️ Ingen dokumenter fundet")
        return []
    
    # Process all documents and collect them with scores
    all_docs = []
    filtered_docs = []
    
    for i, doc in enumerate(documents):
        distance = distances[i] if i < len(distances) else 1.0
        relevance_score = 1.0 - distance  # Convert distance to relevance (0-1)
        metadata = metadatas[i] if i < len(metadatas) else {}
        cleaned_content = clean_document_content(doc)
        
        print(f"📄 Dokument {i+1}: distance={distance:.3f}, relevance={relevance_score:.3f}")
        print(f"📄 Dokument {i+1} preview: {cleaned_content[:150]}...")
        
        # If we have specific policy numbers, boost relevance for exact matches
        if policy_numbers:
            for policy_num in policy_numbers:
                if policy_num in cleaned_content.lower():
                    relevance_score += 0.3  # Boost relevance for exact policy number match
                    print(f"🎯 Dokument {i+1} indeholder policenummer {policy_num}, boost til relevance: {relevance_score:.3f}")
        
        # Skip documents that become too short after cleaning
        if len(cleaned_content.strip()) < 50:
            print(f"⚠️ Dokument {i+1} for kort efter rensning, springer over")
            continue
        
        doc_info = {
            "content": cleaned_content,
            "metadata": metadata,
            "relevance_score": relevance_score,
            "distance": distance
        }
        
        all_docs.append(doc_info)
        
        # Check if document meets the relevance threshold
        if relevance_score >= relevance_threshold:
            filtered_docs.append(doc_info)
            print(f"✅ Dokument {i+1} inkluderet (relevance: {relevance_score:.3f})")
        else:
            print(f"❌ Dokument {i+1} filtreret ud (relevance: {relevance_score:.3f} < {relevance_threshold})")
    
    # Fallback: If no documents meet the threshold, include the best documents
    if not filtered_docs and all_docs:
        # Sort by relevance and take the top 3
        all_docs.sort(key=lambda x: x['relevance_score'], reverse=True)
        filtered_docs = all_docs[:3]
        print(f"🔄 Fallback: Inkluderer de {len(filtered_docs)} bedste dokumenter")
        for i, doc in enumerate(filtered_docs):
            print(f"🔄 Fallback dokument {i+1}: relevance={doc['relevance_score']:.3f}")
    
    print(f"✅ Fandt {len(filtered_docs)} relevante dokumenter (filteret fra {len(documents)})")
    return filtered_docs

def generate_answer_with_sources(question: str, documents: List[dict], min_source_relevance: float = 0.3) -> Tuple[str, List[str]]:
    """Generer svar baseret på dokumenter og returner kun virkelig relevante kilder"""
    if not documents:
        return "Ingen relevante dokumenter blev fundet.", []
    
    # Byg kontekst fra dokumenter - kun inkluder indhold, ikke metadataa
    context_parts = []
    potential_sources = []
    
    for i, doc in enumerate(documents):
        # Add clean content to context without document numbers or metadata pollution
        context_parts.append(doc['content'])
        
        # Collect source information with relevance scores
        metadata = doc.get('metadata', {})
        relevance_score = doc.get('relevance_score', 0.0)
        source = metadata.get('source', f'Dokument {i+1}')
        
        potential_sources.append({
            'source': source,
            'relevance_score': relevance_score,
            'distance': doc.get('distance', 1.0)
        })
    
    # Create clean context without "Dokument X:" prefixes that pollute the LLM prompt
    context = "\n\n".join(context_parts)
    
    print(f"🤖 Genererer svar med {len(context_parts)} dokumenter i kontekst")
    print(f"🤖 Total kontekst længde: {len(context)} karakterer")
    
    # Generer svar
    answer = generate_answer(question, context)
    
    # Only include sources that are highly relevant to avoid showing irrelevant sources
    relevant_sources = []
    for source_info in potential_sources:
        if source_info['relevance_score'] >= min_source_relevance:
            if source_info['source'] not in relevant_sources:
                relevant_sources.append(source_info['source'])
                print(f"📋 Inkluderer kilde: {source_info['source']} (relevance: {source_info['relevance_score']:.3f})")
        else:
            print(f"📋 Filtrerer kilde: {source_info['source']} (relevance: {source_info['relevance_score']:.3f} < {min_source_relevance})")
    
    print(f"✅ Returnerer svar med {len(relevant_sources)} kilder (filteret fra {len(potential_sources)})")
    
    return answer, relevant_sources

def build_conversation_context(messages: List[dict], max_context: int = 5) -> str:
    """Byg kontekst fra tidligere beskeder"""
    if not messages:
        return ""
    
    # Tag de sidste N beskeder for kontekst
    recent_messages = messages[-max_context:]
    context_parts = []
    
    for msg in recent_messages:
        if msg["role"] == "user":
            context_parts.append(f"Bruger: {msg['content']}")
        elif msg["role"] == "assistant":
            context_parts.append(f"Assistant: {msg['content']}")
    
    return "\n".join(context_parts)

def process_contextual_query(question: str, conversation_history: List[dict], relevance_threshold: float = 0.3) -> Tuple[str, List[str]]:
    """Behandl spørgsmål med samtale-kontekst og filtrer kilder efter relevance"""
    
    # Byg kontekst fra tidligere samtale
    conversation_context = build_conversation_context(conversation_history)
    
    # Extract policy numbers or other specific references from conversation history
    import re
    context_policy_numbers = []
    if conversation_context:
        context_policy_numbers = re.findall(r'(?:police\s*nr\.?\s*|policy\s*no\.?\s*)(\d+)', conversation_context.lower())
    
    # Enhanced contextual question construction
    if conversation_context:
        # Check if current question has specific policy numbers
        current_policy_numbers = re.findall(r'(?:police\s*nr\.?\s*|policy\s*no\.?\s*)(\d+)', question.lower())
        
        # If current question has policy numbers, use them directly
        if current_policy_numbers:
            contextual_question = f"{question}"
            print(f"🎯 Direkte policenummer i spørgsmål: {current_policy_numbers}")
        # If current question refers to context (e.g., "på 1001 ikke på 1005")
        elif any(word in question.lower() for word in ["på", "ikke", "den", "det", "kunden"]):
            # Extract any numbers from the current question that might be policy numbers
            question_numbers = re.findall(r'\b(\d{4})\b', question)
            if question_numbers:
                contextual_question = f"Hvem er kunden på police nr {question_numbers[0]}?"
                print(f"🎯 Udvundet policenummer fra kontekst: {question_numbers[0]}")
            else:
                contextual_question = f"""
Samtale historik:
{conversation_context}

Nyt spørgsmål: {question}

Besvar det nye spørgsmål, og tag hensyn til tidligere samtale hvis relevant. 
Hvis spørgsmålet refererer til noget fra tidligere (som "den", "det", "kunden" osv.), 
brug informationen fra samtale historikken.
"""
        else:
            contextual_question = f"""
Samtale historik:
{conversation_context}

Nyt spørgsmål: {question}

Besvar det nye spørgsmål, og tag hensyn til tidligere samtale hvis relevant. 
Hvis spørgsmålet refererer til noget fra tidligere (som "den", "det", "kunden" osv.), 
brug informationen fra samtale historikken.
"""
    else:
        contextual_question = question
    
    print(f"🤖 Processeret spørgsmål: '{contextual_question}'")
    
    # Hent relevante dokumenter med filtering
    documents = get_relevant_documents(contextual_question, relevance_threshold=relevance_threshold)
    
    # Generer svar med kun virkelig relevante kilder
    answer, sources = generate_answer_with_sources(contextual_question, documents)
    
    return answer, sources
