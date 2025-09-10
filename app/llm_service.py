from llama_cpp import Llama
from config import LLM_MODEL_PATH

llm = Llama(
    model_path=LLM_MODEL_PATH,
    n_ctx=32768,
    n_threads=6,
    n_gpu_layers=20,
    n_batch=32,
    use_mmap=True,
    use_mlock=True
)

def ask_llm(prompt: str) -> str:
    response = llm(
        prompt=f"<s>[INST] {prompt} [/INST]",
        max_tokens=10000,  # Øget fra 512 til 10000 for længere svar
        temperature=0.7,
        stop=["</s>"]
    )
    return response["choices"][0]["text"].strip()
