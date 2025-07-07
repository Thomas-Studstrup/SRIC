import os

# Hvor embeddings og dokumenter gemmes
PERSIST_DIR = "./chroma"

# Navn på ChromaDB collection
CHROMA_COLLECTION_NAME = "documents"

# Token-konfiguration
SECRET_KEY = "din_super_hemmelige_nøgle"  # Udskift med en sikker nøgle i produktion
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30