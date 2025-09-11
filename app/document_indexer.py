import os
import uuid
import torch
from nltk.tokenize import sent_tokenize
import chromadb
from utils.file_reader import extract_text_from_file
from config import PERSIST_DIR, CHROMA_COLLECTION_NAME, EMBEDDER
from sentence_transformers import SentenceTransformer
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredEmailLoader,
    UnstructuredExcelLoader
)

DATA_DIR = "data"

embedder = SentenceTransformer(EMBEDDER)  # [NYT] Dynamisk embedder
chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)
collection = chroma_client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)

# [NYT] Semantisk chunking-funktion
from config import get_max_tokens
def semantic_chunk(text, max_tokens=None):
    if max_tokens is None:
        max_tokens = get_max_tokens("document_indexer_chunk", 500)
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


# === Indexér alle filer kun ved direkte kørsel ===
if __name__ == "__main__":
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
                texts = []
                for doc in docs:
                    content = getattr(doc, "page_content", str(doc)).strip()
                    if not content:
                        continue
                    for chunk in semantic_chunk(content):
                        if chunk.strip():
                            texts.append(chunk.strip())
                # Fallback hvis ingen brugbare tekst-chunks
                if not texts:
                    print(f"[FALLBACK] {filepath} – prøver file_reader util")
                    raw_content = extract_text_from_file(filepath)
                    texts = [chunk.strip() for chunk in semantic_chunk(raw_content) if chunk.strip()]
                    if not texts:
                        print(f"[SKIPPED] {filepath} – ingen brugbare tekst-chunks selv med fallback")
                        continue

                document_id = str(uuid.uuid4())
                passages = [f"passage: {text}" for text in texts]
                raw_embeddings = embedder.encode(passages, normalize_embeddings=True, batch_size=32)
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
                    embeddings=embeddings, #type: ignore
                    metadatas=metadatas, #type: ignore
                    ids=ids
                )
                print(f"[OK] Indexed: {filepath} ({len(texts)} chunks) – doc_id={document_id} – filename={filename}")
            except Exception as e:
                print(f"[ERROR] {filepath}: {e}")

# Helper: Hent alle chunks fra et dokument-id
def get_all_chunks_for_document(document_id: str):
    all_docs = collection.get(include=["documents", "metadatas"])
    docs = all_docs.get("documents") or [[]]
    metas = all_docs.get("metadatas") or [[]]
    if not isinstance(docs, list) or (len(docs) > 0 and not isinstance(docs[0], list)):
        docs = [docs]
    if not isinstance(metas, list) or (len(metas) > 0 and not isinstance(metas[0], list)):
        metas = [metas]
    chunks = []
    for doc, meta in zip(docs[0], metas[0]):
        if isinstance(meta, dict) and meta.get("document_id") == document_id:
            chunks.append(doc)
    return chunks