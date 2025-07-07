from llm_service import ask_llm

def handle_analysis(question: str) -> dict:
    response = ask_llm(f"Analysér følgende tekst: {question}")
    return {"type": "analyse", "result": response}
