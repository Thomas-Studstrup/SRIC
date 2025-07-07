from vector_store import retrieve_similar_chunks
from mistral_local import generate_answer

async def handle_query(question: str):
    print(f"🟢 query_service: Starter behandling af question: '{question}'")
    
    print("🟢 query_service: Kalder retrieve_similar_chunks...")
    results = retrieve_similar_chunks(question)
    print(f"🟢 query_service: retrieve_similar_chunks returnerede: {results}")
    print(f"🟢 query_service: Type af results: {type(results)}")
    
    documents = results.get("documents", [[]])[0] # type: ignore
    print(f"🟢 query_service: Ekstraherede documents: {documents}")
    print(f"🟢 query_service: Antal dokumenter: {len(documents) if documents else 0}")

    if not documents:
        print("🔴 query_service: Ingen dokumenter fundet!")
        return {"answer": "Ingen relevante dokumenter blev fundet."}

    context = "\n\n".join(documents)
    print(f"🟢 query_service: Opbygget context (første 200 chars): {context[:200]}...")
    
    print("🟢 query_service: Kalder generate_answer...")
    answer = generate_answer(question, context)
    print(f"🟢 query_service: generate_answer returnerede: {answer}")
    print(f"🟢 query_service: Type af answer: {type(answer)}")
    
    final_result = {"question": question, "answer": answer}
    print(f"🟢 query_service: Final result: {final_result}")
    return final_result
