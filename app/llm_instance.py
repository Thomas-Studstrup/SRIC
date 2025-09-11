from llama_cpp import Llama
from config import LLM_MODEL_PATH

# Juster parametre her centralt
llm = Llama(
    model_path=LLM_MODEL_PATH,
    n_ctx=4096,         # Sæt lavere for mindre RAM/VRAM
    n_threads=6,
    n_gpu_layers=10,    # Sæt lavere hvis du har lidt VRAM
    n_batch=32,
    use_mmap=True,
    use_mlock=True
)
