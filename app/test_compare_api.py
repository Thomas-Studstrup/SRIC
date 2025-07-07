#!/usr/bin/env python3
"""
Test API endpoint for sammenligning
"""

import requests
import json

def test_compare_endpoint():
    """Test /ask endpoint med sammenligning spørgsmål"""
    
    base_url = "http://localhost:8000"
    
    test_cases = [
        {
            "name": "Betingelser sammenligning",
            "message": "Sammenlign betingelser mellem Tryg og Topdanmark for rejseforsikring"
        },
        {
            "name": "Generel sammenligning", 
            "message": "Hvad er forskellen på rejseafbestillingsforsikring?"
        },
        {
            "name": "Selskab sammenligning",
            "message": "Sammenlign Tryg og Topdanmark som forsikringsselskaber"
        },
        {
            "name": "Spørgeskema vurdering",
            "message": "Vurder om dette spørgeskema lever op til kravene for rejseforsikring"
        },
        {
            "name": "Police sammenligning",
            "message": "Sammenlign forskellige forsikringspolicer for rejse"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n=== TEST {i}: {test_case['name']} ===")
        print(f"Spørgsmål: {test_case['message']}")
        
        try:
            response = requests.post(
                f"{base_url}/ask",
                json={"message": test_case['message']},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("Svar:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print(f"Fejl: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"Request fejl: {e}")
        except Exception as e:
            print(f"Generel fejl: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    print("🌐 Testing sammenligning API endpoints...")
    test_compare_endpoint()
    print("\n🌐 API test afsluttet!")
