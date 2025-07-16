import os
import uuid
import torch
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredEmailLoader,
    UnstructuredExcelLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb

# === Konfiguration ===
DATA_DIR = "data"
CHROMA_DIR = "chroma"
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# === Initialisering ===
embedder = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = chroma_client.get_or_create_collection(name="documents")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

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
            chunks = text_splitter.split_documents(docs)

            texts = [chunk.page_content.strip() for chunk in chunks if chunk.page_content.strip()]
            if not texts:
                print(f"[SKIPPED] {filepath} – ingen brugbare tekst-chunks")
                continue

            document_id = str(uuid.uuid4())  # Unik ID for dokumentet
            passages = [f"passage: {text}" for text in texts]

            # Embed i batch
            raw_embeddings = embedder.encode(passages, normalize_embeddings=True, batch_size=32)
            embeddings = [e.tolist() if isinstance(e, torch.Tensor) else e for e in raw_embeddings]

            ids = [f"{document_id}_{i}" for i in range(len(texts))]
            metadatas = [{
                "document_id": document_id,
                "source_path": filepath,
                "filename": filename,
                "chunk_index": i
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