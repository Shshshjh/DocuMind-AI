import os
import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

async def generate_answer(question: str, passages: list[dict]) -> tuple[str, str]:
    if not passages:
        return "No relevant text was found in this document.", "retrieval"
    context = "\n\n".join(f"[Page {p['page']}] {p['text']}" for p in passages)
    prompt = ("Answer using ONLY the passages below. If they lack the answer, say you do not know. "
              "Cite the source page numbers.\n\n" + context + "\n\nQuestion: " + question)
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(f"{OLLAMA_URL}/api/generate", json={"model":OLLAMA_MODEL,"prompt":prompt,"stream":False})
            response.raise_for_status()
        answer = response.json().get("response", "").strip()
        if answer:
            return answer, "ollama"
    except (httpx.HTTPError, ValueError):
        pass
    # Do not fabricate answers when local LLM is not available.
    return "Qwen/Ollama is unavailable. Relevant passages are provided below; no generated answer was produced.", "retrieval"
