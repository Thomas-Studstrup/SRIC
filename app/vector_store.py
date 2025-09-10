from typing import Optional
import os
import re
from sentence_transformers import SentenceTransformer
import chromadb
from config import PERSIST_DIR, CHROMA_COLLECTION_NAME, EMBEDDER

# Initialiser model og client
model = SentenceTransformer(EMBEDDER)
client = chromadb.PersistentClient(path=PERSIST_DIR)
collection = client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)

def find_chunks_with_exact_match(object_strings: list[str]):
    results = []
    all_docs = collection.get(include=['documents', 'metadatas'])
    docs = all_docs.get('documents', [[]])
    metas = all_docs.get('metadatas', [[]])
    if docs and metas and len(docs) > 0:
        for doc, meta in zip(docs[0], metas[0]):
            for obj in object_strings:
                if obj and obj.strip() and obj.strip() in doc:
                    results.append({'document': doc, 'metadata': meta})
                    break
    return results



def retrieve_similar_chunks(query: str, top_k: int = 5, required_title: Optional[str] = None, object_strings: Optional[list[str]] = None):
    RELEVANCE_THRESHOLD = 0.6
    if object_strings is None:
        object_strings = re.findall(r'(policenummer\s*\d+|nr\s*\d+)', query.lower())

    print(f"🔷 vector_store: Søger efter chunks for query: '{query}'")
    print(f"🔷 vector_store: top_k={top_k}")

    try:
        # Robust: konverter altid til flad python-liste af floats
        embedding = model.encode(query)
        # Hvis det er numpy/tensor, brug .tolist(), ellers brug som er
        if hasattr(embedding, 'tolist'):
            embedding = embedding.tolist()
        # Hvis det er 2D (fx [[...]]), tag første element
        if isinstance(embedding, list) and len(embedding) > 0 and isinstance(embedding[0], (list, tuple)):
            embedding = list(embedding[0])
        # Sikr at det nu er en flad liste af floats
        embedding = [float(x) for x in embedding]
        print(f"🔷 vector_store: Embedding oprettet (dimension: {len(embedding)})")

        results = collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )
        print(f"🔷 vector_store: Collection query udført")

        docs = results.get('documents') or [[]]
        metas = results.get('metadatas') or [[]]
        distances = results.get('distances') or [[]]

        # Sikr at docs/metas/distances er lister af lister
        if not isinstance(docs, list) or (len(docs) > 0 and not isinstance(docs[0], list)):
            docs = [docs]
        if not isinstance(metas, list) or (len(metas) > 0 and not isinstance(metas[0], list)):
            metas = [metas]
        if not isinstance(distances, list) or (len(distances) > 0 and not isinstance(distances[0], list)):
            distances = [distances]

        filtered_docs = [[]]
        filtered_metas = [[]]
        filtered_distances = [[]]

        if docs and distances and len(docs) > 0 and len(distances) > 0:
            for doc, meta, dist in zip(docs[0], metas[0], distances[0]):
                # Hvis dist er en liste, tag første element, ellers brug som float
                dist_val = None
                if isinstance(dist, list):
                    if len(dist) > 0:
                        dist_val = dist[0]
                else:
                    dist_val = dist
                if dist_val is not None and isinstance(dist_val, (float, int)) and dist_val <= RELEVANCE_THRESHOLD:
                    filtered_docs[0].append(doc)
                    filtered_metas[0].append(meta)
                    filtered_distances[0].append(dist)

        if required_title and metas and len(metas) > 0:
            required_title_lower = str(required_title).lower()
            for doc, meta, dist in zip(docs[0], metas[0], distances[0]):
                title_val = meta.get('title', '') if isinstance(meta, dict) else str(meta)
                if isinstance(title_val, str) and title_val.lower() == required_title_lower:
                    if doc not in filtered_docs[0]:
                        filtered_docs[0].append(doc)
                        filtered_metas[0].append(meta)
                        filtered_distances[0].append(dist)

        if object_strings:
            all_docs = collection.get(include=['documents', 'metadatas'])
            docs_all = all_docs.get('documents') or [[]]
            metas_all = all_docs.get('metadatas') or [[]]
            if not isinstance(docs_all, list) or (len(docs_all) > 0 and not isinstance(docs_all[0], list)):
                docs_all = [docs_all]
            if not isinstance(metas_all, list) or (len(metas_all) > 0 and not isinstance(metas_all[0], list)):
                metas_all = [metas_all]
            if docs_all and metas_all and len(docs_all) > 0:
                for doc, meta in zip(docs_all[0], metas_all[0]):
                    for obj in object_strings:
                        if obj and obj.strip() and obj.strip() in doc:
                            if doc not in filtered_docs[0]:
                                filtered_docs[0].append(doc)
                                filtered_metas[0].append(meta)
                                filtered_distances[0].append(None)
                            break

        # 🔁 Step 2 – Tilføj alle chunks fra samme dokument
        if filtered_metas and len(filtered_metas[0]) > 0:
            matched_doc_ids = set()
            for meta in filtered_metas[0]:
                if isinstance(meta, dict):
                    doc_id = meta.get('document_id')
                    if doc_id:
                        matched_doc_ids.add(doc_id)

            if matched_doc_ids:
                all_docs = collection.get(include=["documents", "metadatas"])
                docs_all = all_docs.get("documents") or [[]]
                metas_all = all_docs.get("metadatas") or [[]]
                if not isinstance(docs_all, list) or (len(docs_all) > 0 and not isinstance(docs_all[0], list)):
                    docs_all = [docs_all]
                if not isinstance(metas_all, list) or (len(metas_all) > 0 and not isinstance(metas_all[0], list)):
                    metas_all = [metas_all]
                for doc, meta in zip(docs_all[0], metas_all[0]):
                    doc_id = meta.get("document_id") if isinstance(meta, dict) else None
                    if doc_id in matched_doc_ids and doc not in filtered_docs[0]:
                        filtered_docs[0].append(doc)
                        filtered_metas[0].append(meta)
                        filtered_distances[0].append(None)

        results['documents'] = filtered_docs
        results['metadatas'] = filtered_metas
        results['distances'] = filtered_distances

        return results

    except Exception as e:
        print(f"🔴 vector_store: Fejl i retrieve_similar_chunks: {e}")
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

def embed_and_store(text: str, metadata: dict):
    if not text.strip():
        return
    chunks = chunk_text(text)
    embeddings = model.encode(chunks)
    # Hvis numpy array, konverter til liste
    if hasattr(embeddings, 'tolist'):
        embeddings = embeddings.tolist()
    # Hvis kun ét chunk, pak ind i liste
    if isinstance(embeddings, list) and len(embeddings) > 0 and not isinstance(embeddings[0], (list, tuple)):
        embeddings = [embeddings]
    for i, emb in enumerate(embeddings):
        # Konverter til flad python-liste af floats
        if hasattr(emb, 'tolist'):
            emb = emb.tolist()
        emb = list(emb)
        emb = [float(x) for x in emb]
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
