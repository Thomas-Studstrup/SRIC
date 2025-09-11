# Fælles base-instruktioner til LLM-prompts
BASE_PROMPT = (
	"Du er en dansk forsikringsanalytiker. "
	"Skriv KUN på dansk. "
	"Svar kun på det spørgsmål, brugeren stillede; tilføj ikke egne spørgsmål eller Q&A. "
	"Hold dig til konteksten; vær tydelig ved ekstrapolation. "
	"Brug korte afsnit og punktopstilling når relevant. "
)
import os

# Hvor embeddings og dokumenter gemmes
PERSIST_DIR = "./chroma"

# Navn på ChromaDB collection
CHROMA_COLLECTION_NAME = "documents"

# Størrelse af embedder-model:
EMBEDDER = "BAAI/bge-small-en-v1.5"
# EMBEDDER = "BAAI/bge-large-en-v1.5"

LLM_MODEL_PATH = "./models/mistral-7b-instruct-v0.2.Q5_K_S.gguf"

# Token-konfiguration
SECRET_KEY = "din_super_hemmelige_nøgle"  # Udskift med en sikker nøgle i produktion
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# --- Dynamisk max_tokens styring ---
MAX_TOKENS_CONFIG = {
	"llm_service": 10000,
	"mistral_local_default": 1000,
	"mistral_local_fallback": 200,
	"document_indexer_chunk": 500,
}

def get_max_tokens(name: str, default: int = 1000) -> int:
	"""
	Returnerer max_tokens for et givet navn, eller default hvis ikke fundet.
	"""
	return MAX_TOKENS_CONFIG.get(name, default)