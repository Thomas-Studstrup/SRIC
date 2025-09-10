from typing import List, Tuple
import json
import re
from vector_store import retrieve_similar_chunks
from mistral_local import generate_answer
from services.context_analyzer import requires_context, analyze_question_context

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

def get_relevant_documents(question: str, top_k: int = 8, relevance_threshold: float = 0.5) -> List[dict]:
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
    
    documents, metadatas, distances = safe_extract_results(results)
    
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
                    relevance_score += 0.5  # Boost relevance for exact policy number match
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
    """Behandl spørgsmål med intelligent kontekst detektion og specialiseret handling"""
    
    print(f"🧠 Analyserer spørgsmål: '{question}'")
    
    # Check if this is a comparison query
    is_comparison = detect_comparison_query(question)
    
    # Byg kontekst fra tidligere samtale
    conversation_context = build_conversation_context(conversation_history)
    
    # Intelligent kontekst detektion
    needs_context = requires_context(question)
    
    if needs_context and conversation_context.strip():
        print("✅ Spørgsmål kræver kontekst - inkluderer chat historik")
        
        # Extract policy numbers or other specific references from conversation history
        import re
        context_policy_numbers = re.findall(r'(?:police\s*nr\.?\s*|policy\s*no\.?\s*)(\d+)', conversation_context.lower())
        
        # Enhanced contextual question construction
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
        if not needs_context:
            print("🎯 Selvstændigt spørgsmål - ignorerer chat historik")
        else:
            print("⚠️ Spørgsmål ville kræve kontekst, men ingen historik tilgængelig")
        contextual_question = question
    
    print(f"🤖 Processeret spørgsmål: '{contextual_question}'")
    
    # Use specialized handling for comparison queries
    if is_comparison:
        print("🔍 Sammenligning detekteret - bruger specialiseret handling")
        documents = get_comparison_documents(contextual_question, relevance_threshold=relevance_threshold)
        answer, sources = generate_comparison_answer_with_sources(contextual_question, documents)
    else:
        # Regular document retrieval and answer generation
        documents = get_relevant_documents(contextual_question, relevance_threshold=relevance_threshold)
        answer, sources = generate_answer_with_sources(contextual_question, documents)
    
    return answer, sources

def detect_comparison_query(question: str) -> bool:
    """Detect if question is asking for comparison"""
    comparison_patterns = [
        r'\bsammenlign\b', r'\bforskel\b', r'\blighed\b',
        r'\bvs\.?\b', r'\bversus\b', r'\bkontra\b',
        r'\bhvilken.*bedre\b', r'\bhvad er.*bedst\b'
    ]
    
    question_lower = question.lower()
    for pattern in comparison_patterns:
        if re.search(pattern, question_lower):
            return True
    return False

def get_comparison_documents(question: str, top_k: int = 12, relevance_threshold: float = 0.1) -> List[dict]:
    """Get documents specifically for comparison queries with lower threshold and more documents"""
    print(f"🔍 Sammenligning søgning: '{question}'")
    print(f"🔍 Top_k: {top_k}, relevance_threshold: {relevance_threshold}")
    
    # Extract company names for targeted search
    import re
    companies = re.findall(r'\b(tryg|topdanmark|cna|hdi)\b', question.lower())
    if companies:
        print(f"🔍 Fandt selskaber: {companies}")
        # Enhance search to find documents from specific companies
        enhanced_question = f"{question} {' '.join(companies)}"
        print(f"🔍 Forbedret sammenligning søgning: '{enhanced_question}'")
        results = retrieve_similar_chunks(enhanced_question, top_k=top_k)
    else:
        results = retrieve_similar_chunks(question, top_k=top_k)
    
    documents, metadatas, distances = safe_extract_results(results)
    
    if not documents:
        print("⚠️ Ingen dokumenter fundet til sammenligning")
        return []
    
    # Process all documents and collect them with scores
    all_docs = []
    filtered_docs = []
    company_docs = {company: [] for company in ['tryg', 'topdanmark', 'cna', 'hdi']}
    
    for i, doc in enumerate(documents):
        distance = distances[i] if i < len(distances) else 1.0
        relevance_score = 1.0 - distance
        metadata = metadatas[i] if i < len(metadatas) else {}
        cleaned_content = clean_document_content(doc)
        
        print(f"📄 Sammenligning dok {i+1}: distance={distance:.3f}, relevance={relevance_score:.3f}")
        
        # Boost relevance for company matches
        for company in companies:
            source_str = str(metadata.get('source', ''))
            if company in cleaned_content.lower() or company in source_str.lower():
                relevance_score += 0.2
                print(f"🎯 Dok {i+1} indeholder {company}, boost til relevance: {relevance_score:.3f}")
        
        # Skip documents that become too short after cleaning
        if len(cleaned_content.strip()) < 50:
            print(f"⚠️ Dok {i+1} for kort efter rensning, springer over")
            continue
        
        doc_info = {
            "content": cleaned_content,
            "metadata": metadata,
            "relevance_score": relevance_score,
            "distance": distance
        }
        
        all_docs.append(doc_info)
        
        # Categorize by company for balanced comparison
        source = str(metadata.get('source', '')).lower()
        for company in ['tryg', 'topdanmark', 'cna', 'hdi']:
            if company in cleaned_content.lower() or company in source:
                company_docs[company].append(doc_info)
                break
        
        # Include documents that meet the relevance threshold
        if relevance_score >= relevance_threshold:
            filtered_docs.append(doc_info)
            print(f"✅ Sammenligning dok {i+1} inkluderet (relevance: {relevance_score:.3f})")
        else:
            print(f"❌ Sammenligning dok {i+1} filtreret ud (relevance: {relevance_score:.3f} < {relevance_threshold})")
    
    # Ensure we have documents from multiple sources for comparison
    if len(filtered_docs) < 5 and all_docs:
        print(f"🔄 For få dokumenter til sammenligning, tilføjer flere")
        # Sort by relevance and ensure diversity
        all_docs.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Try to get at least 2 documents per company if available
        balanced_docs = []
        for company in companies:
            company_list = company_docs.get(company, [])
            if company_list:
                balanced_docs.extend(company_list[:3])  # Top 3 per company
        
        # Fill remaining slots with best documents
        remaining_slots = max(8 - len(balanced_docs), 0)
        for doc in all_docs:
            if doc not in balanced_docs and len(balanced_docs) < 8:
                balanced_docs.append(doc)
        
        filtered_docs = balanced_docs[:8]  # Limit to 8 total
        print(f"🔄 Balanceret sammenligning: {len(filtered_docs)} dokumenter")
    
    print(f"✅ Fandt {len(filtered_docs)} dokumenter til sammenligning")
    return filtered_docs

def generate_comparison_answer_with_sources(question: str, documents: List[dict], min_source_relevance: float = 0.2) -> Tuple[str, List[str]]:
    """Generate specialized comparison answer with detailed analysis"""
    if not documents:
        return "Ingen relevante dokumenter blev fundet til sammenligning.", []
    
    # Build context with focus on comparison
    context_parts = []
    potential_sources = []
    company_info = {}
    
    for i, doc in enumerate(documents):
        content = doc['content']
        metadata = doc.get('metadata', {})
        relevance_score = doc.get('relevance_score', 0.0)
        source = str(metadata.get('source', f'Dokument {i+1}'))
        
        # Categorize content by company
        content_lower = content.lower()
        for company in ['tryg', 'topdanmark', 'cna', 'hdi']:
            if company in content_lower or company in source.lower():
                if company not in company_info:
                    company_info[company] = []
                company_info[company].append(content)
                break
        
        context_parts.append(content)
        potential_sources.append({
            'source': source,
            'relevance_score': relevance_score,
            'distance': doc.get('distance', 1.0)
        })
    
    # Create specialized comparison context
    comparison_context = "\n\n".join(context_parts)
    
    # Enhanced comparison prompt
    comparison_prompt = f"""Baseret på følgende dokumenter, lav en detaljeret sammenligning:

{comparison_context}

Spørgsmål: {question}

Giv et grundigt svar der:
1. Identificerer specifikke forskelle mellem selskaberne/produkterne
2. Nævner ligheder hvis relevante
3. Fremhæver vigtige detaljer som dækning, vilkår, priser
4. Bruger konkrete eksempler fra dokumenterne
5. Giver en objektiv analyse uden at anbefale

Fokuser på faktiske forskelle og vær specifik i din sammenligning."""
    
    print(f"🤖 Genererer sammenligning med {len(context_parts)} dokumenter")
    print(f"🤖 Selskaber identificeret: {list(company_info.keys())}")
    
    # Generate answer with specialized prompt
    answer = generate_answer(comparison_prompt, "")  # Empty context since prompt contains everything
    
    # Include more sources for comparison to show breadth of analysis
    relevant_sources = []
    for source_info in potential_sources:
        if source_info['relevance_score'] >= min_source_relevance:
            if source_info['source'] not in relevant_sources:
                relevant_sources.append(source_info['source'])
                print(f"📋 Inkluderer sammenligning kilde: {source_info['source']} (relevance: {source_info['relevance_score']:.3f})")
    
    print(f"✅ Sammenligning svar med {len(relevant_sources)} kilder")
    return answer, relevant_sources

def safe_extract_results(results):
    """Safely extract documents, metadatas, and distances from vector search results"""
    documents = []
    metadatas = []
    distances = []
    
    if results and isinstance(results, dict):
        documents_list = results.get("documents", [[]])
        metadatas_list = results.get("metadatas", [[]])
        distances_list = results.get("distances", [[]])
        
        if documents_list is not None and len(documents_list) > 0:
            documents = documents_list[0]
        if metadatas_list is not None and len(metadatas_list) > 0:
            metadatas = metadatas_list[0]
        if distances_list is not None and len(distances_list) > 0:
            distances = distances_list[0]
    
    return documents, metadatas, distances
