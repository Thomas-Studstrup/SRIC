#!/usr/bin/env python3
"""
Demo script for at vise sammenligning funktionalitet
"""

from services.ask_classifier import classify_question

def demo_classification():
    """Demonstrer klassificering af forskellige spørgsmål"""
    
    print("🎯 DEMO: Sammenligning Klassificering\n")
    
    test_questions = [
        "Sammenlign betingelser mellem Tryg og Topdanmark",
        "Hvad er forskellen på rejseforsikring?",
        "Tryg vs Topdanmark - hvilken er bedst?",
        "Vurder om dette spørgeskema lever op til kravene",
        "Sammenlign forsikringspolicer",
        "Hvad dækker rejseforsikring?",
        "Analyser markedet for bilforsikring",
        "Hvilken forsikring er bedst for mig?",
        "Fordele og ulemper ved forskellige selskaber",
        "Kan du anbefale en forsikring?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        classification = classify_question(question)
        print(f"{i:2d}. '{question}'")
        print(f"    → Klassificeret som: {classification}")
        print()
    
    print("🎯 Demo afsluttet!")

if __name__ == "__main__":
    demo_classification()
