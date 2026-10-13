"""Simple local retrieval: TF-IDF, no external API or model download required."""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def split_text(text: str, chunk_chars: int = 900, overlap: int = 130) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + chunk_chars//2, end)
            if boundary > start:
                end = boundary
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks

def retrieve(query: str, records: list[dict], top_k: int = 3) -> list[dict]:
    if not records:
        return []
    texts = [r["text"] for r in records]
    tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1,2))
    matrix = tfidf.fit_transform(texts)
    q = tfidf.transform([query])
    similarities = cosine_similarity(q, matrix).ravel()
    ranked = similarities.argsort()[::-1][:top_k]
    return [{**records[int(i)], "score": round(float(similarities[i]),4)} for i in ranked if similarities[i] > 0]
