from typing import List, Tuple, Dict, Any
import re

def clean_document_content(content: str) -> str:
    """
    Fjerner støj, overflødigt whitespace og skabelon-artefakter fra dokumenttekst.
    """
    if not content:
        return ""
    # Fjern gentagne tomme linjer
    content = re.sub(r'\n\s*\n+', '\n\n', content)
    # Fjern linjer med kun specialtegn eller tal
    content = re.sub(r'^[-=*_~\d\s]+$', '', content, flags=re.MULTILINE)
    # Fjern skabelon-artefakter (fx "Dokument X:", "Side X af Y", "Version:", "Dato:")
    content = re.sub(r'Dokument \d+:', '', content)
    content = re.sub(r'Side \d+ af \d+', '', content)
    content = re.sub(r'Version:.*', '', content)
    content = re.sub(r'Dato:.*', '', content)
    # Fjern overflødige mellemrum
    content = re.sub(r'[ \t]+', ' ', content)
    # Trim start og slut
    content = content.strip()
    return content

def safe_extract_results(results: Dict[str, Any]) -> Tuple[List[str], List[dict], List[float]]:
    """
    Udtrækker dokumenter, metadata og afstande fra ChromaDB resultater på robust vis.
    Returnerer altid tre lister (strings, dicts, floats).
    """
    documents = []
    metadatas = []
    distances = []
    if not results:
        return documents, metadatas, distances
    docs = results.get('documents', [[]])
    metas = results.get('metadatas', [[]])
    dists = results.get('distances', [[]])
    # Pak ud hvis lister af lister
    if isinstance(docs, list) and len(docs) > 0 and isinstance(docs[0], list):
        docs = docs[0]
    if isinstance(metas, list) and len(metas) > 0 and isinstance(metas[0], list):
        metas = metas[0]
    if isinstance(dists, list) and len(dists) > 0 and isinstance(dists[0], list):
        dists = dists[0]
    # Sikr typer
    documents = [str(d) for d in docs]
    metadatas = [m if isinstance(m, dict) else {} for m in metas]
    distances = [float(d) if isinstance(d, (float, int)) else 1.0 for d in dists]
    return documents, metadatas, distances
