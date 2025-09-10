import os
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions
from config import PERSIST_DIR, CHROMA_COLLECTION_NAME

# Initialiser model og client
model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path=PERSIST_DIR)
collection = client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)

def retrieve_similar_chunks(query: str, top_k: int = 5):
    print(f"🔷 vector_store: Søger efter chunks for query: '{query}'")
    print(f"🔷 vector_store: top_k={top_k}")
    
    try:
        embedding = model.encode(query).tolist() # type: ignore
        print(f"🔷 vector_store: Embedding oprettet (dimension: {len(embedding)})")
        
        # Include distances in the query to get relevance scores
        results = collection.query(
            query_embeddings=[embedding], 
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )
        print(f"🔷 vector_store: Collection query udført")
        print(f"🔷 vector_store: Results type: {type(results)}")
        print(f"🔷 vector_store: Results keys: {results.keys() if results else 'None'}")
        
        if results and 'documents' in results:
            docs = results['documents']
            distances = results.get('distances', [[]])
            print(f"🔷 vector_store: Documents struktur: {type(docs)}")
            print(f"🔷 vector_store: Antal document grupper: {len(docs) if docs is not None else 0}")
            if docs is not None and len(docs) > 0:
                print(f"🔷 vector_store: Antal dokumenter i første gruppe: {len(docs[0])}")
                print(f"🔷 vector_store: Distances: {distances[0] if distances is not None and len(distances) > 0 and len(distances[0]) > 0 else 'Ingen distances'}")
                if len(docs[0]) > 0:
                    print(f"🔷 vector_store: Første dokument (100 chars): {docs[0][0][:100]}...")
        
        return results
    except Exception as e:
        print(f"🔴 vector_store: Fejl i retrieve_similar_chunks: {e}")
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

def embed_and_store(text: str, metadata: dict):
    if not text.strip():
        return
    chunks = chunk_text(text)
    embeddings = model.encode(chunks).tolist() # type: ignore
    for i, emb in enumerate(embeddings):
        doc_id = f"{metadata.get('filename','doc')}-{i}"
        collection.add(
            documents=[chunks[i]],
            embeddings=[emb],
            ids=[doc_id],
            metadatas=[metadata]
        )

def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks
