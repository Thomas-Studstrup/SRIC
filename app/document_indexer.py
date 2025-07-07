import os
from langchain.document_loaders import PyPDFLoader, Docx2txtLoader, UnstructuredEmailLoader, UnstructuredExcelLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb

DATA_DIR = "data"
CHROMA_DIR = "chroma"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Initialiser embedding-model og vector store
embedder = SentenceTransformer(EMBEDDING_MODEL)
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = chroma_client.get_or_create_collection(name="documents")

# Tekst-splitter til chunking
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

# Funktion til at hente loader baseret på filtype
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

# Indlæs og indexér alle filer i hele mappestrukturen
for root, _, files in os.walk(DATA_DIR):
    for filename in files:
        filepath = os.path.join(root, filename)
        loader = get_loader(filepath)

        if loader:
            try:
                docs = loader.load()
                chunks = text_splitter.split_documents(docs)
                for i, chunk in enumerate(chunks):
                    text = chunk.page_content
                    embedding = embedder.encode([text])[0].tolist()
                    collection.add(
                        documents=[text],
                        embeddings=[embedding],
                        metadatas=[{"source": filepath}],
                        ids=[f"{filepath}_{i}"]
                    )
                print(f"[OK] Indexed: {filepath}")
            except Exception as e:
                print(f"[SKIPPED] {filepath}: {e}")
        else:
            print(f"[IGNORED] {filepath} – ukendt filtype")
