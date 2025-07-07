#!/usr/bin/env python3
"""
Test script for sammenligning funktionalitet
"""

import asyncio
from services.compare_service import handle_comparison
from controllers.compare_controller import handle

async def test_comparison_functionality():
    """Test forskellige typer af sammenligninger"""
    
    print("🧪 Testing sammenligning funktionalitet...\n")
    
    # Test 1: Betingelser sammenligning
    print("=== TEST 1: Betingelser sammenligning ===")
    question1 = "Sammenlign betingelser mellem Tryg og Topdanmark for rejseforsikring"
    result1 = await handle(question1)
    print(f"Spørgsmål: {question1}")
    print(f"Resultat: {result1}")
    print()
    
    # Test 2: Generel sammenligning
    print("=== TEST 2: Generel sammenligning ===")
    question2 = "Hvad er forskellen på rejseafbestillingsforsikring mellem forskellige selskaber?"
    result2 = await handle(question2)
    print(f"Spørgsmål: {question2}")
    print(f"Resultat: {result2}")
    print()
    
    # Test 3: Selskab sammenligning
    print("=== TEST 3: Selskab sammenligning ===")
    question3 = "Sammenlign Tryg og Topdanmark som forsikringsselskaber"
    result3 = await handle(question3)
    print(f"Spørgsmål: {question3}")
    print(f"Resultat: {result3}")
    print()
    
    # Test 4: Spørgeskema vurdering
    print("=== TEST 4: Spørgeskema vurdering ===")
    question4 = "Vurder om dette spørgeskema lever op til kravene for rejseforsikring"
    result4 = await handle(question4)
    print(f"Spørgsmål: {question4}")
    print(f"Resultat: {result4}")
    print()
    
    # Test 5: Police sammenligning
    print("=== TEST 5: Police sammenligning ===")
    question5 = "Sammenlign forskellige forsikringspolicer for rejse"
    result5 = await handle(question5)
    print(f"Spørgsmål: {question5}")
    print(f"Resultat: {result5}")
    print()
    
    print("🧪 Test afsluttet!")

if __name__ == "__main__":
    asyncio.run(test_comparison_functionality())
