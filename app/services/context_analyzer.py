import re
from typing import List, Dict

def requires_context(question: str) -> bool:
    """
    Analyserer om et spørgsmål kræver chat kontekst baseret på:
    - Pronomer der refererer til tidligere samtale
    - Spørgeord der antyder opfølgning
    - Korte spørgsmål uden specifik information
    """
    
    question_lower = question.lower().strip()
    
    # Refererende pronomer på dansk
    context_indicators = [
        # Pronomer
        r'\bden\b', r'\bdet\b', r'\bde\b', r'\bdenne\b', r'\bdette\b',
        r'\bham\b', r'\bhende\b', r'\bdem\b',
        
        # Opfølgende spørgeord
        r'^hvad med\b', r'^og\b', r'^men\b', r'^så\b',
        r'\bhvad dækker den\b', r'\bhvad koster det\b',
        r'\bhvor meget\b.*\bdet\b', r'\bhvornår\b.*\bden\b',
        
        # Kritik og opfølgning på tidligere svar
        r'\bvær mere\b', r'\bmer kritisk\b', r'\bgrundiger\b', r'\bbedre\b',
        r'\bdetaljer\b', r'\bforskelle\b', r'\bspecifik\b',
        r'\bdet er ikke\b', r'\bforkert\b', r'\bmangler\b',
        r'\buden\b.*\bspecifik\b', r'\bfor kort\b', r'\bfor overfladisk\b',
        
        # Sammenligningsmæssige opfølgninger
        r'^sammenlign\b(?!.*\bmilli\b)(?!.*\bnr\.?\s*\d+)(?!.*\b[A-ZÆØÅ][a-zæøå]+)',
        r'\bforskel\b(?!.*mellem.*\bog\b)', r'\blighed\b(?!.*mellem.*\bog\b)',
        
        # Uspecifikke referencer
        r'\bpolice?n\b.*\buden\b.*\bnummer\b',  # "policen" uden nummer
        r'\bkunden\b.*\buden\b.*\bnavn\b',      # "kunden" uden navn
        r'\bforsikringen\b.*\buden\b.*\btype\b', # "forsikringen" uden type
    ]
    
    # Tjek for kontekst indikatorer
    for pattern in context_indicators:
        if re.search(pattern, question_lower):
            print(f"🧠 Kontekst indikator fundet: {pattern}")
            return True
    
    # Korte spørgsmål (under 30 tegn) er ofte opfølgningsspørgsmål
    if len(question.strip()) < 30:
        # Men ikke hvis de indeholder specifikke numre/navne
        if not re.search(r'\b\d{4}\b', question):  # 4-cifret nummer (policenr)
            if not re.search(r'\b[A-ZÆØÅ][a-zæøå]+ [A-ZÆØÅ][a-zæøå]+\b', question):  # Fuldt navn
                print(f"🧠 Kort spørgsmål uden specifik info: '{question}'")
                return True
    
    return False

def analyze_question_context(question: str, previous_messages: List[Dict]) -> Dict:
    """
    Analyserer om spørgsmålet kræver kontekst og returnerer analyse
    """
    needs_context = requires_context(question)
    
    analysis = {
        "needs_context": needs_context,
        "question": question,
        "context_indicators": [],
        "recommendation": ""
    }
    
    if needs_context:
        analysis["recommendation"] = "Inkluder chat historik for bedre forståelse"
        
        # Find specifikke indikatorer
        question_lower = question.lower()
        if re.search(r'\bden\b|\bdet\b', question_lower):
            analysis["context_indicators"].append("Refererende pronomen")
        if len(question.strip()) < 30:
            analysis["context_indicators"].append("Kort spørgsmål")
        if re.search(r'^hvad med|^og |^men |^så ', question_lower):
            analysis["context_indicators"].append("Opfølgende spørgeord")
        if re.search(r'\bvær mere\b|\bmer kritisk\b', question_lower):
            analysis["context_indicators"].append("Kritik af tidligere svar")
    else:
        analysis["recommendation"] = "Spørgsmål er selvstændigt, ingen kontekst nødvendig"
    
    return analysis
    
    return analysis
