# NLP Server

A **FastAPI backend service** that provides NLP / RAG (Retrieval-Augmented Generation) capabilities — document upload & indexing, semantic search, LLM-powered question answering, and simple task generation.

This service is designed to run as a **standalone API backend** for another web application (frontend or another repo of the author). It exposes REST endpoints that a client app can call to upload documents, ask questions grounded in those documents, and generate task lists from natural-language descriptions.

## Features

- **Document upload & indexing** — Fetches files from MinIO object storage, extracts text (`.pdf`, `.docx`, `.txt`), splits it into overlapping chunks, embeds each chunk, and stores the vectors in Qdrant.
- **RAG chat** — Given a query and a set of document IDs, retrieves the most relevant chunks from Qdrant and asks an LLM (via Groq) to answer using that context, returning a strict JSON response.
- **Task generation** — Breaks a free-text description into a short list of actionable tasks using an LLM.
- **Caching** — Redis is used to cache LLM responses (RAG answers and generated tasks) to reduce latency and API usage.
- **API key rotation** — The RAG service can automatically rotate between multiple Groq API keys when a daily quota / rate limit is hit.
- **Request logging & tracing** — Middleware attaches a request ID to every request and logs method, path, status code, and duration.

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Vector database | [Qdrant](https://qdrant.tech/) |
| Object storage | [MinIO](https://min.io/) |
| Cache | [Redis](https://redis.io/) |
| LLM provider | [Groq](https://groq.com/) (OpenAI-compatible API, `llama-3.1-8b-instant`) |
| Embeddings | [sentence-transformers](https://www.sbert.net/) (`all-MiniLM-L6-v2`) |
| Document parsing | `python-docx`, `pdfplumber` |

## Project Structure

```
app/
├── api/routers/           # FastAPI route definitions
│   ├── task_router.py     # POST /generate-task
│   ├── upload_router.py   # POST /upload
│   └── rag_route.py       # POST /rag-chat
├── controllers/           # Thin controllers connecting routers to services
├── core/                  # Shared clients & config (Qdrant, MinIO, logger, env)
├── loaders/                # File parsers (docx, pdf, txt)
├── middleware/             # Request-ID and logging middleware
├── schemas/                 # Pydantic request/response models
├── services/
│   ├── llm_service.py           # LLM calls, key rotation, Redis caching (RAG)
│   ├── task_service.py          # LLM calls & caching (task generation)
│   ├── rag_services/            # Query normalization, vector search, RAG orchestration
│   └── upload_services/         # Chunking, embedding, upload pipeline
├── utils/                  # Small helpers (file type detection, etc.)
└── main.py                 # FastAPI app entrypoint

evaluation/
├── evaluate.py             # Evaluation script for RAG quality
└── llamaIndex.py           # LlamaIndex-based comparison/experiments
```

## Prerequisites

You'll need the following services running locally (or reachable) before starting the server:

- **Qdrant** — vector database, default `127.0.0.1:6333`
- **Redis** — cache, default `127.0.0.1:6379`
- **MinIO** — object storage, default `localhost:9000` (uploaded files must already exist in a MinIO bucket)
- **Groq API key(s)** — for LLM access

> Note: connection settings for Qdrant, Redis, and MinIO are currently hardcoded to `localhost`/`127.0.0.1` in `app/core/`. If you deploy these services elsewhere, update the corresponding files (`app/core/qdrant.py`, `app/core/minio.py`, `app/services/llm_service.py`, `app/services/task_service.py`) or refactor them to read from environment variables.

## Installation

```bash
git clone https://github.com/huyhd2334/NLP_Server.git
cd NLP_Server

python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate

pip install fastapi uvicorn python-dotenv openai redis \
            qdrant-client minio sentence-transformers \
            python-docx pdfplumber
```

> This repository does not yet include a `requirements.txt`. The list above covers the packages imported across the codebase — consider generating and committing one (`pip freeze > requirements.txt`) for reproducible installs.

## Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_primary_groq_key
GROQ_API_KEY_2=your_backup_key_2   # optional, used for key rotation
GROQ_API_KEY_3=your_backup_key_3   # optional, used for key rotation
```

## Running the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

## API Endpoints

### `GET /`
Health check.
```json
{ "message": "AI Task System Running" }
```

### `POST /upload`
Loads a file from MinIO, extracts and chunks its text, generates embeddings, and stores them in Qdrant.

**Request body:**
```json
{
  "bucket_name": "my-bucket",
  "object_name": "report.pdf",
  "file_id": "unique-file-id"
}
```

**Response:**
```json
{ "success": true }
```

### `POST /rag-chat`
Answers a question using RAG over previously uploaded documents.

**Request body:**
```json
{
  "query": "What is the summary of the report?",
  "documents": ["unique-file-id"]
}
```

**Response:**
```json
{
  "success": true,
  "response": {
    "answer": "...",
    "sources": []
  }
}
```

### `POST /generate-task`
Breaks a natural-language description into a short list of tasks (max 4).

**Request body:**
```json
{ "description": "Plan a product launch for next month" }
```

**Headers (optional):** `Authorization`, `X-User-Id`, `X-User-Name`

**Response:**
```json
{
  "success": true,
  "tasks": ["task 1", "task 2", "task 3"]
}
```

## Integrating with a Frontend / Other Repo

Since this server is meant to act as a backend for another web project, a typical integration flow looks like:

1. Your frontend uploads a file to MinIO (directly or via your own backend) and calls `POST /upload` with the bucket/object name and a `file_id`.
2. Your frontend calls `POST /rag-chat` with a user's question and the relevant `file_id`(s) to get a grounded answer.
3. Optionally, `POST /generate-task` can be used anywhere in your app that needs to turn a text description into a task list.

CORS is not yet configured in `app/main.py`; if your frontend runs on a different origin, add `fastapi.middleware.cors.CORSMiddleware` before deploying.

## Known Issues / TODO

- `README.md` and `docker_compose.yml` are currently empty — a Docker Compose setup (Qdrant + Redis + MinIO + this API) would simplify local development and deployment.
- No `requirements.txt` / dependency lockfile yet.
- Qdrant, Redis, and MinIO hosts/ports are hardcoded rather than read from `.env`.
- `app/core/logger.py` has a bug (`logging.setLogger` should be `logging.getLogger`) that will raise an error if imported.
- `app/middleware/*` is defined but not yet wired into the FastAPI app in `main.py`.
- CORS middleware is not configured.

## License

No license file is currently included in this repository. Add one (e.g. MIT) if you intend to share or open-source this project.
