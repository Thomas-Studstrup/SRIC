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