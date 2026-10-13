# DocuMind — Python Backend + Document Q&A

A FastAPI REST API for authenticated PDF upload, local text extraction, passage retrieval, and optional source-grounded question answering using **Qwen via local Ollama**. It can run without a paid API and never invents a model answer when the LLM is offline.

## Requirements
Python 3.11–3.13 recommended; dependencies in `requirements.txt`. Local Ollama is optional.

## Run locally
```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Visit http://localhost:8000/docs for interactive API docs.

Alternatively, `docker compose up --build` serves the app at port 8000.

## Enable generative Q&A using local Qwen (optional)
Install Ollama, then:
```bash
ollama pull qwen2.5:3b
ollama serve
```
Ollama may already run as a service; if so you don't need the second command. Set `OLLAMA_URL` and `OLLAMA_MODEL` if you use a different server/model. Responses include source passages and page numbers. The local retrieval system is **TF-IDF**, not vector embeddings; model-generated answers are optional.

## Test manually
1. `POST /auth/register` with `{"email":"demo@example.com","password":"password123"}`; copy token.
2. Use **Authorize** in Swagger with the token.
3. `POST /documents` with PDF file.
4. `POST /documents/{id}/ask` with `{"question":"What is the document about?","top_k":3}`.
5. `GET /documents` to list your files, or `DELETE /documents/{id}` to delete one.

## Tests
```bash
pytest -q
```

## Honest limitations / upgrade ideas
- This MVP processes text-based PDFs synchronously; large-scale background jobs and OCR are **not** included.
- Document retrieval is currently TF-IDF (not embeddings or pgvector). Upgrade to sentence-transformer embeddings and pgvector after the MVP is working.
- The default datastore is SQLite for zero-config development. PostgreSQL can be used by setting `DATABASE_URL` and installing a Postgres driver.
- No production-ready rate limits, migrations, adversarial-PDF isolation, per-user quotas, or load-test results yet. Uploaded files are read in memory with 10 MB/100-page limits; extracted text stays in the DB.
- RAG answers are not guaranteed factual; always inspect source passages. Qwen must be run with Ollama locally.
- Set a secure `JWT_SECRET` and use HTTPS before deployment.
