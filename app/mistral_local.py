from llama_cpp import Llama
import time
from functools import wraps
import hashlib
from functools import lru_cache
# Initialiser lokal Mistral model
llm = Llama(
    # model_path="./models/mistral.q4_K_M.gguf",  # Ret hvis din sti er anderledes
    model_path="./models/mistral-7b-instruct-v0.2.Q5_K_M.gguf",  # Ret hvis din sti er anderledes
    n_ctx=10000,
    n_threads=8,
    verbose=False
)

def timing_decorator(func):
    """Decorator til at måle funktions performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"🕐 {func.__name__} tog {end_time - start_time:.2f} sekunder")
        return result
    return wrapper

# Simple cache for frequently asked questions
_question_cache = {}

def get_cached_answer(question: str, context_hash: str) -> str:
    """Check hvis vi har cached svar til lignende spørgsmål."""
    cache_key = f"{question[:50]}_{context_hash[:10]}"  # Short cache key
    cached = _question_cache.get(cache_key)
    return cached if cached is not None else ""

def cache_answer(question: str, context_hash: str, answer: str):
    """Cache svar for fremtidige forespørgsler."""
    cache_key = f"{question[:50]}_{context_hash[:10]}"
    _question_cache[cache_key] = answer
    
    # Begræns cache størrelse
    if len(_question_cache) > 100:
        # Fjern ældste entries
        keys_to_remove = list(_question_cache.keys())[:20]
        for key in keys_to_remove:
            del _question_cache[key]

def _validate_context_and_question(question: str, context: str) -> tuple[bool, str]:
    """Validerer om spørgsmål og kontekst er tilstrækkelige til at give et meningsfuldt svar for alle typer spørgsmål."""
    
    question_lower = question.lower().strip()
    
    # Basic length check
    if len(question_lower) < 5:
        return False, "Dit spørgsmål er for kort. Vær mere specifik."
    
    # Check for overly vague questions
    vague_patterns = [
        "hej", "hallo", "hvad", "hvem", "hvor", "hvornår", "hvorfor",
        "hvad med", "fortæl om", "generelt", "alt om", "kan du", "vil du"
    ]
    
    # Single word vague questions
    if question_lower in vague_patterns[:7]:
        return False, "Dit spørgsmål er for vagt. Stil et specifikt spørgsmål om forsikring."
    
    # Vague phrase starters
    if any(question_lower.startswith(phrase) for phrase in vague_patterns[7:]):
        # Allow if it contains insurance/comparison terms
        insurance_comparison_terms = [
            "forsikring", "sammenlign", "forskelle", "police", "dækning", 
            "betingelser", "topdanmark", "tryg", "cna", "hdi"
        ]
        if not any(term in question_lower for term in insurance_comparison_terms):
            return False, "Dit spørgsmål er for vagt. Vær mere specifik om forsikring eller sammenligning."
    
    # Check for insurance-related content in question
    insurance_keywords = [
        "forsikring", "police", "dækning", "præmie", "selvrisiko", 
        "betingelser", "erstatning", "skade", "topdanmark", "tryg", "cna", "hdi",
        "sammenlign", "forskelle", "selskab", "vilkår"
    ]
    
    has_insurance_terms = any(keyword in question_lower for keyword in insurance_keywords)
    
    if not has_insurance_terms:
        return False, "Dit spørgsmål skal relatere til forsikring. Nævn forsikringsselskaber, policer eller forsikringstyper."
    
    # Check context quality (if provided)
    if context and len(context.strip()) > 0:
        if len(context.strip()) < 50:
            return False, "Der er ikke nok kontekst tilgængelig til at besvare spørgsmålet."
        
        # Check if context contains insurance-related content
        context_lower = context.lower()
        context_has_insurance = any(keyword in context_lower for keyword in insurance_keywords)
        
        if not context_has_insurance:
            return False, "Konteksten indeholder ikke relevante forsikringsoplysninger."
    
    return True, ""

def _validate_answer_quality(answer: str, question: str) -> tuple[bool, str]:
    """Validerer om det genererede svar er af tilstrækkelig kvalitet - nu mere tilladende for korte, præcise svar."""
    
    # Meget mere tilladende længde check - acceptér korte, præcise svar
    if not answer or len(answer.strip()) < 8:
        return False, "Svaret er for kort eller tomt."
    
    answer_lower = answer.lower()
    
    # Check for explicit "I don't know" responses from LLM
    uncertainty_indicators = [
        "jeg ved ikke", "kan ikke besvare", "ikke tilgængelig information",
        "mangler data", "ingen information", "ikke muligt", "ved ikke",
        "kan ikke svare", "ikke sikkert", "usikker"
    ]
    
    if any(indicator in answer_lower for indicator in uncertainty_indicators):
        return False, "LLM indikerede selv usikkerhed eller manglende information."
    
    # Check for meaningless repetition - kun for længere svar
    words = answer.split()
    if len(words) > 50:  # Kun check repetition for længere svar
        unique_words = set(words)
        repetition_ratio = len(unique_words) / len(words)
        if repetition_ratio < 0.15:  # Endnu mere tilladende
            return False, "Svaret indeholder for mange gentagelser."
    
    # Check for repeated phrases/sentences - kun for meget lange svar
    sentences = [s.strip() for s in answer.split('.') if len(s.strip()) > 20]
    if len(sentences) > 12:  # Kun check for meget lange svar
        unique_sentences = set(sentences)
        sentence_repetition = len(unique_sentences) / len(sentences)
        if sentence_repetition < 0.3:  # Meget tilladende
            return False, "Svaret indeholder for mange gentagede sætninger."
    
    # For comparison questions - mere tilladende check
    question_lower = question.lower()
    
    if any(term in question_lower for term in ["sammenlign", "forskelle", "difference", "versus", "vs"]):
        comparison_indicators = [
            "forskelle", "ligheder", "versus", "vs", "modsat", "sammenlignet",
            "derimod", "hvorimod", "til forskel", "forskellige", "bedre", "værre"
        ]
        
        # Kun check for sammenligning hvis svaret er længere end 20 ord
        if len(words) > 20 and not any(indicator in answer_lower for indicator in comparison_indicators):
            return False, "Svaret adresserer ikke den ønskede sammenligning."
    
    # For simple spørgsmål som "hvem er kunden", acceptér svar uden forsikringstermer
    simple_question_patterns = [
        "hvem er", "hvad er", "hvor", "hvilken", "hvornår", "kunde", "police nr"
    ]
    is_simple_question = any(pattern in question_lower for pattern in simple_question_patterns)
    
    if not is_simple_question:
        # Kun kræv forsikringstermer for komplekse spørgsmål
        insurance_response_terms = [
            "forsikring", "police", "dækning", "præmie", "selvrisiko",
            "betingelser", "erstatning", "skade", "vilkår", "kunde", "kundenummer"
        ]
        
        if not any(term in answer_lower for term in insurance_response_terms):
            return False, "Svaret indeholder ikke relevante forsikringsoplysninger."
    
    # Check for generic/templated responses - kun for længere svar
    if len(words) > 30:  # Kun check generisk indhold for længere svar
        generic_phrases = [
            "det afhænger af", "det kan variere", "kontakt din forsikring",
            "læs betingelserne", "det er vigtigt at", "husk at tjekke"
        ]
        
        generic_count = sum(1 for phrase in generic_phrases if phrase in answer_lower)
        if generic_count >= 4 and len(words) < 80:  # Endnu mere tilladende
            return False, "Svaret er for generisk og giver ikke specifik information."
    
    # Additional check for extremely repetitive patterns - kun for meget lange svar
    if len(words) > 100:
        company_mentions = answer_lower.count("hdi") + answer_lower.count("pidl0919")
        if company_mentions > 20:  # Meget højere threshold
            return False, "Svaret indeholder for mange gentagelser af samme information."
    
    return True, ""

def _clean_context_for_llm(context: str) -> str:
    """Clean context text to remove template pollution and improve LLM performance"""
    if not context:
        return context
    
    import re
    
    # Remove excessive whitespace and normalize line breaks
    context = re.sub(r'\n\s*\n\s*\n+', '\n\n', context)  # Max double line breaks
    context = re.sub(r'[ \t]+', ' ', context)  # Normalize spaces
    
    # Remove template artifacts that pollute LLM responses
    artifacts_to_remove = [
        r'PIDL\d+',  # Policy/document IDs
        r'Dokument \d+:',  # Document headers added by our system
        r'^\d+\.\s*$',  # Standalone numbered lines
        r'^\*\s*$',  # Standalone bullet points
        r'^\-\s*$',  # Standalone dashes
        r'^\s*-+\s*$',  # Lines with just dashes
        r'^\s*=+\s*$',  # Lines with just equals signs
        r'^\s*\*+\s*$',  # Lines with just asterisks
        r'Side \d+ af \d+',  # Page numbers
        r'Version:.*',  # Version info
        r'Dato:.*',  # Date info
    ]
    
    for pattern in artifacts_to_remove:
        context = re.sub(pattern, '', context, flags=re.MULTILINE)
    
    # Remove repetitive content that often appears in templates
    # Find and remove patterns that repeat more than 3 times
    lines = context.split('\n')
    seen_lines = {}
    filtered_lines = []
    
    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            filtered_lines.append(line)
            continue
            
        # Normalize line for comparison (remove extra spaces, punctuation)
        normalized = re.sub(r'[^\w\s]', '', clean_line.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Skip if we've seen this line too many times
        seen_lines[normalized] = seen_lines.get(normalized, 0) + 1
        if seen_lines[normalized] <= 3:  # Allow up to 3 repetitions
            filtered_lines.append(line)
    
    context = '\n'.join(filtered_lines)
    
    # Final cleanup
    context = re.sub(r'\n\s*\n\s*\n+', '\n\n', context)  # Remove excessive line breaks
    context = context.strip()
    
    # Limit context length to prevent overwhelming the LLM
    if len(context) > 8000:  # Reasonable limit for context
        # Try to cut at a sentence boundary
        context = context[:8000]
        last_period = context.rfind('.')
        if last_period > 6000:  # If we find a period reasonably close to the end
            context = context[:last_period + 1]
    
    return context

@timing_decorator
def generate_answer(question: str, context: str) -> str:
    print(f"🗭 mistral_local: generate_answer kaldt")
    print(f"🗭 mistral_local: Question: {question}")
    print(f"🗭 mistral_local: Context længde: {len(context)} karakterer")

    # Validér input (du kan genaktivere validering hvis ønsket)
    if not context.strip() or not question.strip():
        return "Manglende kontekst eller spørgsmål."

    # Rens kontekst (kan tilpasses)
    MAX_CONTEXT_LENGTH = 8000
    cleaned_context = context.strip()
    if len(cleaned_context) > MAX_CONTEXT_LENGTH:
        print(f"🗭 mistral_local: Kontekst for lang ({len(cleaned_context)}). Forkorter til {MAX_CONTEXT_LENGTH} tegn.")
        cleaned_context = cleaned_context[:MAX_CONTEXT_LENGTH] + "\n... (kontekst forkortet)"


    prompt = f"""Kontekst:
{cleaned_context}

Spørgsmål: {question}

Svar på dansk:
"""

    print(f"🗭 mistral_local: Total prompt længde: {len(prompt)} tegn")

    print(f"🗭 mistral_local: Prompt preview:\n{prompt[:500]}\n---")


    try:
        output = llm(
            prompt=prompt,
            max_tokens=600,
            temperature=0.2,
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.2,
            echo=False
        )

        if isinstance(output, dict) and "choices" in output:
            text = output["choices"][0].get("text", "").strip()
            return text if text else "Model genererede ikke noget svar."
        else:
            return "Uventet outputformat fra LLM."

    except Exception as e:
        import traceback
        print("Fejl i generate_answer:", e)
        print(traceback.format_exc())
        return f"Der opstod en fejl under generering af svar: {e}"


def test_llm_simple():
    """Test LLM med super simpelt prompt"""
    print(f"🟦 mistral_local: Tester LLM med simpelt prompt...")
    
    try:
        response = llm(
            prompt="Hvad er 2+2?",
            max_tokens=10,
            temperature=0.1,
            echo=False
        )
        
        print(f"🟦 mistral_local: Test response: {response}")
        
        if isinstance(response, dict) and "choices" in response and len(response["choices"]) > 0:
            text = response["choices"][0]["text"].strip()
            print(f"🟦 mistral_local: Test answer: '{text}'")
            return text
        else:
            return "Test fejlede - ingen choices"
    except Exception as e:
        print(f"🔴 mistral_local: Test fejlede: {e}")
        return f"Test fejl: {str(e)}"

def _clean_repetitive_sentences(text: str) -> str:
    """Clean repetitive sentences and fix formatting issues in LLM output."""
    if not text or len(text) < 100:
        return text
    
    # First fix basic formatting issues
    text = _fix_basic_formatting(text)
    
    # Split into sentences more robustly
    import re
    # Split on periods, but also on bullet points and obvious sentence breaks
    sentences = re.split(r'[.!?]\s*(?=[A-ZÆØÅ]|[\*\-\d])', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
    
    # Remove duplicate sentences (case insensitive and normalized)
    seen_sentences = set()
    cleaned_sentences = []
    
    for sentence in sentences:
        # Normalize sentence for comparison
        normalized = re.sub(r'\s+', ' ', sentence.lower().strip())
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
        
        # Check if this sentence is too similar to previous ones
        is_duplicate = False
        for seen_norm in seen_sentences:
            # If 75% of words are the same, consider it a duplicate
            words1 = set(normalized.split())
            words2 = set(seen_norm.split())
            if len(words1) > 3 and len(words2) > 3:
                overlap = len(words1.intersection(words2))
                similarity = overlap / max(len(words1), len(words2))
                if similarity > 0.75:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            seen_sentences.add(normalized)
            cleaned_sentences.append(sentence)
    
    return '. '.join(cleaned_sentences) + '.' if cleaned_sentences else text

def _fix_basic_formatting(text: str) -> str:
    """Fix basic formatting issues in LLM output."""
    import re
    
    # Add line breaks before numbered points
    text = re.sub(r'(\d+\.)\s*([A-ZÆØÅ])', r'\n\1 \2', text)
    
    # Add line breaks before bullet points that are smashed together
    text = re.sub(r'(\*\s*[^*]+?)\s*(\*\s*)', r'\1\n\2', text)
    
    # Fix missing periods before bullets
    text = re.sub(r'([a-zæøå])\s*(\*\s*[A-ZÆØÅ])', r'\1.\n\2', text)
    
    # Fix missing periods before numbered items
    text = re.sub(r'([a-zæøå])\s*(\d+\.\s*[A-ZÆØÅ])', r'\1.\n\2', text)
    
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Clean up multiple newlines
    text = re.sub(r'\n+', '\n', text)
    
    return text.strip()

def _generate_fallback_answer(question: str, context: str, original_error: str) -> str:
    """Generate a cleaner fallback answer when the original fails validation."""
    print(f"🟡 mistral_local: Genererer fallback svar pga: {original_error}")
    
    try:
        # Simpler, more direct prompt to avoid repetition
        fallback_prompt = f"""Baseret på denne information:
{context[:800]}

Besvar kort og præcist: {question}

Svar (max 3 linjer):"""
        
        fallback_response = llm(
            fallback_prompt,
            max_tokens=200,  # Much shorter to avoid repetition
            temperature=0.3,
            repeat_penalty=1.5,  # Higher repeat penalty
            stop=["Spørgsmål:", "Baseret på", "\n\n\n"],
            echo=False
        )
        
        if isinstance(fallback_response, dict) and "choices" in fallback_response:
            fallback_text = fallback_response["choices"][0]["text"].strip()
            
            # Quick validation of fallback
            if len(fallback_text) > 30 and "forsikring" in fallback_text.lower():
                print(f"🟢 mistral_local: Fallback lykkedes")
                return fallback_text
        
    except Exception as e:
        print(f"🔴 mistral_local: Fallback fejlede: {e}")
    
    # If fallback fails, return a helpful error message
    return "Jeg kan ikke give et detaljeret svar på dette spørgsmål lige nu. Prøv at omformulere spørgsmålet eller vær mere specifik om hvad du vil sammenligne."

def _detect_and_fix_repetition(text: str) -> str:
    """Detect and fix repetitive content in LLM output."""
    if not text or len(text) < 100:
        return text
    
    # Split into lines
    lines = text.split('\n')
    
    # Look for consecutive identical lines
    cleaned_lines = []
    prev_line = ""
    repetition_count = 0
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        if line_stripped == prev_line.strip() and len(line_stripped) > 10:
            repetition_count += 1
            # If we see more than 2 identical lines, stop here
            if repetition_count > 2:
                print(f"🟦 mistral_local: Repetition detected at line {i}, stopping")
                break
            cleaned_lines.append(line)
        else:
            repetition_count = 0
            cleaned_lines.append(line)
        
        prev_line = line
    
    # Check for repeating bullet point patterns
    result = '\n'.join(cleaned_lines)
    
    # Look for patterns like "* PIDL0919 - 470-15-04 diverse..." repeating
    import re
    
    # Find all bullet points with the same pattern
    bullet_pattern = r'^\s*\*\s+PIDL0919.*?er en specialforsikring.*?$'
    matches = re.findall(bullet_pattern, result, re.MULTILINE)
    
    if len(matches) > 3:
        print(f"🟦 mistral_local: Found {len(matches)} repetitive bullet points, truncating")
        # Find where the repetition starts and cut there
        lines = result.split('\n')
        for i, line in enumerate(lines):
            if re.match(bullet_pattern, line):
                # Look ahead to see if this pattern repeats
                count = 0
                for j in range(i, min(len(lines), i + 10)):
                    if re.match(bullet_pattern, lines[j]):
                        count += 1
                
                # If we find 3+ similar bullet points, cut at the first one
                if count >= 3:
                    print(f"🟦 mistral_local: Cutting at line {i} due to repetitive pattern")
                    result = '\n'.join(lines[:i])
                    break
    
    return result.strip()

def _aggressive_repetition_cleanup(text: str) -> str:
    """Aggressiv cleanup af repetitive indhold i LLM output."""
    if not text or len(text) < 50:
        return text
    
    import re
    
    # Fjern gentagne punktummer med samme mønster
    lines = text.split('\n')
    cleaned_lines = []
    seen_patterns = set()
    
    for line in lines:
        line_stripped = line.strip()
        
        # Tjek for punktum mønstre
        if line_stripped.startswith('*'):
            # Ekstraher kerne mønster (ignorér specifikke detaljer)
            pattern = re.sub(r'\d+', 'X', line_stripped)  # Erstat tal med X
            pattern = re.sub(r'[A-Z]{2,}', 'XXX', pattern)  # Erstat koder med XXX
            
            if pattern in seen_patterns and len(seen_patterns) > 2:
                # Spring denne linje over hvis vi har set dette mønster for mange gange
                continue
            seen_patterns.add(pattern)
        
        cleaned_lines.append(line)
    
    result = '\n'.join(cleaned_lines)
    
    # Fjern gentagne sætninger
    words = result.split()
    if len(words) > 50:
        # Kig efter sætninger der gentages for ofte
        phrase_counts = {}
        for i in range(len(words) - 2):
            phrase = ' '.join(words[i:i+3])  # 3-ords sætninger
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        
        # Hvis nogen sætning vises mere end 5 gange, er det sandsynligvis gentaget
        for phrase, count in phrase_counts.items():
            if count > 5 and len(phrase) > 15:
                # Erstat overdreven gentagelse
                result = result.replace(phrase, phrase, count - 3)  # Behold kun 3 forekomster
    
    # Truncate ved åbenlyse gentagelsespunkter
    sentences = result.split('.')
    if len(sentences) > 10:
        # Kig efter den samme sætning der vises flere gange
        sentence_counts = {}
        for i, sentence in enumerate(sentences):
            sentence_clean = re.sub(r'\s+', ' ', sentence.strip().lower())
            if len(sentence_clean) > 20:
                if sentence_clean in sentence_counts:
                    # Hvis vi ser den samme sætning igen efter position 5, så afskær
                    if i > 5:
                        result = '.'.join(sentences[:i]) + '.'
                        break
                sentence_counts[sentence_clean] = i
    
    return result.strip()

# Kør test ved import
print(f"🟦 mistral_local: Kører LLM test...")
test_result = test_llm_simple()
print(f"🟦 mistral_local: LLM test resultat: '{test_result}'")
