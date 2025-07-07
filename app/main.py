import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from routes.ask_router import router as ask_router
from routes.auth_routes import router as auth_router
from routes.chat_routes import router as chat_router

app = FastAPI()

# ⏱ Middleware til timing af requests
@app.middleware("http")
async def add_request_timing(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    print(f"⏱ {request.method} {request.url.path} tog {duration:.3f} sekunder")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inkluder dine routers
app.include_router(ask_router, prefix="/ask")
app.include_router(auth_router)  # auth_router har allerede prefix="/auth"
app.include_router(chat_router)

# Root-endpoint
@app.get("/")
def root():
    return {"message": "API kører"}
