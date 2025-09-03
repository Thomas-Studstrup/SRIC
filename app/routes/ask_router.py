from fastapi import APIRouter, Request
from pydantic import BaseModel
from services.ask_classifier import classify_question
from controllers import query_controller, compare_controller, analyse_controller

router = APIRouter()

class QuestionRequest(BaseModel):
    question: str

@router.post("/")
async def ask_router(request: Request):
    print("🟡 Backend: ask_router modtog request")
    
    body = await request.json()
    print(f"🟡 Backend: Request body: {body}")
    print(f"🟡 Backend: Type af body: {type(body)}")
    
    question = body.get("question", "")
    message = body.get("message", "")
    
    print(f"🟡 Backend: question fra body: '{question}'")
    print(f"🟡 Backend: message fra body: '{message}'")
    
    # Brug message hvis question er tom
    final_question = question if question else message
    print(f"🟡 Backend: Final question/message: '{final_question}'")
    
    if not final_question:
        print("🔴 Backend: Ingen question eller message fundet!")
        return {"error": "No question or message provided"}
    
    qtype = classify_question(final_question)
    print(f"🟡 Backend: Classified question type: '{qtype}'")

    if qtype == "query":
        print("🟡 Backend: Dirigerer til query_controller")
        result = await query_controller.handle(final_question)
        print(f"🟡 Backend: Query controller returnerede: {result}")
        return result
    elif qtype == "compare":
        print("🟡 Backend: Dirigerer til compare_controller")
        result = await compare_controller.handle(final_question)
        print(f"🟡 Backend: Compare controller returnerede: {result}")
        return result
    elif qtype == "analyse":
        print("🟡 Backend: Dirigerer til analyse_controller")
        result = await analyse_controller.handle(final_question)
        print(f"🟡 Backend: Analyse controller returnerede: {result}")
        return result
    else:
        print(f"🔴 Backend: Unknown question type: {qtype}")
        return {"error": "Unknown question type"}

@router.post("/analyze")
async def analyze_question(request: QuestionRequest):
    """Debug endpoint til at analysere om spørgsmål kræver kontekst"""
    
    analysis = analyze_question_context(request.question, [])
    
    return {
        "question": request.question,
        "analysis": analysis,
        "recommendation": analysis["recommendation"]
    }
