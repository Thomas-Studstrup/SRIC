from services.analyse_service import handle_analysis

async def handle(question: str):
    return handle_analysis(question)
