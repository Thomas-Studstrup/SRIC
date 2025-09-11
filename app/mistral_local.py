from llama_cpp import Llama
import time
from functools import wraps
import hashlib
from config import LLM_MODEL_PATH

llm = Llama(
    model_path=LLM_MODEL_PATH,
    n_ctx=32768,
    n_threads=6,
    n_gpu_layers=20,
    n_batch=32,
    use_mmap=True,
    use_mlock=True
)


def clean_llm_output(text: str) -> str:
    """Samlet cleaning-funktion for LLM output: fjerner gentagelser, retter formatering og trunkerer."""
    import re
    if not text or len(text) < 50:
        return text.strip()

    # Fix basic formatting
    text = re.sub(r'(\d+\.)\s*([A-ZÆØÅ])', r'\n\1 \2', text)
    text = re.sub(r'(\*\s*[^*]+?)\s*(\*\s*)', r'\1\n\2', text)
    text = re.sub(r'([a-zæøå])\s*(\*\s*[A-ZÆØÅ])', r'\1.\n\2', text)
    text = re.sub(r'([a-zæøå])\s*(\d+\.\s*[A-ZÆØÅ])', r'\1.\n\2', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    text = text.strip()

    # Remove duplicate consecutive lines
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

    # Remove duplicate paragraphs
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

    # Remove repetitive bullet points
    bullet_patterns = [r'^\s*-\s+', r'^\s*\*\s+', r'^\s*\d+\.\s+']
    lines = result.split('\n')
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
    result = '\n'.join(cleaned)

    # Truncate at obvious repetition
    sentences = result.split('.')
    if len(sentences) > 10:
        sentence_counts = {}
        for i, sentence in enumerate(sentences):
            sentence_clean = re.sub(r'\s+', ' ', sentence.strip().lower())
            if len(sentence_clean) > 20:
                if sentence_clean in sentence_counts:
                    if i > 5:
                        result = '.'.join(sentences[:i]) + '.'
                        break
                sentence_counts[sentence_clean] = i
    return result.strip()

def timing_decorator(func):
    """Decorator to measure execution time of a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"⏱ {func.__name__} took {end_time - start_time:.3f} seconds")
        return result
    return wrapper

@timing_decorator
def generate_answer(question: str, context: str) -> str:
    print(f"🗭 mistral_local: generate_answer kaldt")
    print(f"🗭 mistral_local: Question: {question}")
    print(f"🗭 mistral_local: Context længde: {len(context)} karakterer")

    # Validér input (du kan genaktivere validering hvis ønsket)
    if not context.strip() or not question.strip():
        return "Manglende kontekst eller spørgsmål."

    # Rens kontekst (kan tilpasses)
    MAX_CONTEXT_LENGTH = 15000
    cleaned_context = context.strip()
    if len(cleaned_context) > MAX_CONTEXT_LENGTH:
        print(f"🗭 mistral_local: Kontekst for lang ({len(cleaned_context)}). Forkorter til {MAX_CONTEXT_LENGTH} tegn.")
        cleaned_context = cleaned_context[:MAX_CONTEXT_LENGTH] + "\n... (kontekst forkortet)"


    from config import BASE_PROMPT
    prompt = f"""{BASE_PROMPT}

Kontekst:
{cleaned_context}

Spørgsmål: {question}
"""

    print(f"🗭 mistral_local: Total prompt længde: {len(prompt)} tegn")

    print(f"🗭 mistral_local: Prompt preview:\n{prompt[:500]}\n---")


    try:
        from config import get_max_tokens
        output = llm(
            prompt=prompt,
            max_tokens=get_max_tokens("mistral_local_default"),
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
