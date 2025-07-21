from sentence_transformers import SentenceTransformer
import torch

def load_embedder(model_size: str = "large") -> SentenceTransformer:
    """
    Dynamically load a SentenceTransformer embedder based on model_size.
    Supported sizes:
        - "large": BAAI/bge-large-en-v1.5
        - "small": BAAI/bge-small-en-v1.5
    Uses CUDA if available, else CPU.
    """
    model_map = {
        "large": "BAAI/bge-large-en-v1.5",
        "small": "BAAI/bge-small-en-v1.5"
    }
    model_name = model_map.get(model_size, model_map["large"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading embedder: {model_name} on device: {device}")
    return SentenceTransformer(model_name, device=device)
