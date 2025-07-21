import os
import uuid
import torch
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredEmailLoader,
    UnstructuredExcelLoader
)
# [NYT] Importer dynamisk embedder-switch og semantisk chunking
from embedding_model import load_embedder
from nltk.tokenize import sent_tokenize
import chromadb

# === Konfiguration ===
DATA_DIR = "data"
CHROMA_DIR = "chroma"
# [NYT] Skift nemt embedder-størrelse her:
EMBEDDER_SIZE = "small"  # "small" eller "large"

# === Initialisering ===
embedder = load_embedder(model_size=EMBEDDER_SIZE)  # [NYT] Dynamisk embedder
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
# [NYT] Skiftet collection-navn for BGE-small
COLLECTION_NAME = "documents-BGE-small"
collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

# [NYT] Semantisk chunking-funktion
def semantic_chunk(text, max_tokens=500):
    """
    Splitter tekst i sætninger og samler dem til chunks på ca. 400–600 tokens.
    Splitter aldrig midt i en sætning.
    Returnerer en liste af tekst-chunks (strings).
    """
    sentences = sent_tokenize(text)
    chunks = []
    current_chunk = []
    current_tokens = 0
    for sentence in sentences:
        tokens = len(sentence.split())
        if current_tokens + tokens > max_tokens and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_tokens = 0
        current_chunk.append(sentence)
        current_tokens += tokens
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

# === Loader baseret på filtype ===
def get_loader(filepath):
    if filepath.endswith(".pdf"):
        return PyPDFLoader(filepath)
    elif filepath.endswith(".docx"):
        return Docx2txtLoader(filepath)
    elif filepath.endswith(".eml"):
        return UnstructuredEmailLoader(filepath)
    elif filepath.endswith(".xlsx"):
        return UnstructuredExcelLoader(filepath)
    else:
        return None

# === Indexér alle filer ===
for root, _, files in os.walk(DATA_DIR):
    for filename in files:
        if filename.startswith("~$"):
            continue  # Midlertidige filer ignoreres

        filepath = os.path.join(root, filename)
        loader = get_loader(filepath)

        if not loader:
            print(f"[IGNORED] {filepath} – ukendt filtype")
            continue

        try:
            docs = loader.load()
            # [NYT] Semantisk chunking erstatter RecursiveCharacterTextSplitter
            texts = []
            for doc in docs:
                # Hvis doc har .page_content (LangChain), brug den
                content = getattr(doc, "page_content", str(doc)).strip()
                if not content:
                    continue
                for chunk in semantic_chunk(content, max_tokens=500):
                    if chunk.strip():
                        texts.append(chunk.strip())
            if not texts:
                print(f"[SKIPPED] {filepath} – ingen brugbare tekst-chunks")
                continue

            document_id = str(uuid.uuid4())  # Unik ID for dokumentet
            passages = [f"passage: {text}" for text in texts]

            # Embed i batch
            raw_embeddings = embedder.encode(passages, normalize_embeddings=True, batch_size=32)
            # Sikrer at embeddings er en liste af float-lister
            embeddings = [list(map(float, e)) for e in raw_embeddings]

            ids = [f"{document_id}_{i}" for i in range(len(texts))]
            metadatas = [{
                "document_id": str(document_id),
                "source_path": str(filepath),
                "filename": str(filename),
                "chunk_index": int(i)
            } for i in range(len(texts))]

            collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )

            print(f"[OK] Indexed: {filepath} ({len(texts)} chunks) – doc_id={document_id}")

        except Exception as e:
            print(f"[SKIPPED] {filepath}: {e}")