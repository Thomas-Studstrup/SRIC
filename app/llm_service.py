from llama_cpp import Llama

MODEL_PATH = "./models/mistral.q4_K_M.gguf"

llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,
    n_threads=6,
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
