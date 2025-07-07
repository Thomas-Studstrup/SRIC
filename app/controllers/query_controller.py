async def handle(question: str) -> dict:
    """Håndterer generelle spørgsmål som ikke er sammenligninger."""
    print(f"🟢 query_controller: Modtog question: '{question}'")
    
    try:
        from services.query_service import handle_query as service_handle_query
        
        print(f"🟢 query_controller: Dirigerer til query_service")
        result = await service_handle_query(question)
        
        print(f"🟢 query_controller: Query service returnerede")
        print(f"🟢 query_controller: Result type: {type(result)}")
        print(f"🟢 query_controller: Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict) and "answer" in result:
            print(f"🟢 query_controller: Answer længde: {len(result['answer'])} karakterer")
            print(f"🟢 query_controller: Answer preview: {result['answer'][:100]}...")
        
        # Ensure proper structure for return
        return {
            "type": "query",
            "question": question,
            "answer": result.get("answer", "Ingen svar tilgængeligt") if isinstance(result, dict) else str(result),
            "sources_count": len(result.get("documents", [])) if isinstance(result, dict) else 0
        }
        
    except Exception as e:
        print(f"🔴 query_controller: Fejl ved håndtering af query: {e}")
        return {
            "type": "query",
            "question": question,
            "answer": "Der opstod en fejl ved behandling af dit spørgsmål. Prøv venligst igen.",
            "sources_count": 0
        }