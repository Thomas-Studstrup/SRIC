from services.compare_service import handle_comparison

async def handle(question: str):
    print(f"🟤 compare_controller: Modtog question: '{question}'")
    
    try:
        result = handle_comparison(question)
        print(f"🟤 compare_controller: handle_comparison returnerede")
        print(f"🟤 compare_controller: Result type: {type(result)}")
        print(f"🟤 compare_controller: Result keys: {result.keys() if isinstance(result, dict) else 'Not dict'}")
        
        if isinstance(result, dict):
            if "answer" in result:
                print(f"🟤 compare_controller: answer længde: {len(result['answer'])} karakterer")
                print(f"🟤 compare_controller: answer preview: {result['answer'][:200]}...")
            if "result" in result:
                print(f"🟤 compare_controller: result længde: {len(result['result'])} karakterer")
                print(f"🟤 compare_controller: result preview: {result['result'][:200]}...")
        
        print(f"🟤 compare_controller: Returnerer result")
        return result
    except Exception as e:
        print(f"🔴 compare_controller: Fejl: {e}")
        return {
            "type": "compare",
            "error": f"Fejl ved sammenligning: {str(e)}",
            "question": question
        }
