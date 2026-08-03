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
| Embeddings | [sentence-transformers](https://www.sbert.net/) (`all-MiniLM-L6-v2`, `BAAI/bge-base-en-v1.5`) |
| Document parsing | `python-docx`, `pdfplumber` |
| RAG evaluation | [RAGAS](https://docs.ragas.io/) with an LLM judge |

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

## RAG Quality Evaluation

A core part of this project is a **systematic evaluation and tuning of the RAG pipeline**, rather than picking retrieval settings arbitrarily. The evaluation script lives at `evaluation/evaluate.py` and uses the **[RAGAS](https://docs.ragas.io/)** framework to score answer quality along 4 standard metrics:

| Metric | Meaning |
|---|---|
| **faithfulness** | Whether the answer stays grounded in the retrieved context (no hallucinated facts outside the context). |
| **answer_relevancy** | Whether the answer is actually on-topic and relevant to the question asked. |
| **context_recall** | Whether the retrieved context covers all the information needed to answer correctly. |
| **llm_context_precision_with_reference** | Of the retrieved chunks, what fraction are actually useful/relevant to the query. |

Judge model used for this round of experiments: **Gemma3:4B**.

### Variants Tested

The goal was to study the effect of three main parameters on RAG quality: **top_k** (number of retrieved chunks), **chunking strategy** (chunk size & overlap), and the **embedding model**.

| # | Configuration | Embedding | faithfulness | answer_relevancy | context_recall | context_precision |
|---|---|---|---|---|---|---|
| 1 | top_k = 3 | all-MiniLM-L6-v2 | 0.7908 | 0.5814 | 0.8685 | 0.6341 |
| 2 | top_k = 5 | all-MiniLM-L6-v2 | 0.8874 | 0.7126 | 0.9184 | 0.6284 |
| 3 | top_k = 10 | all-MiniLM-L6-v2 | 0.8937 | 0.5805 | **0.9849** | 0.5672 |
| 4 | top_k = 5, chunk 100 words / overlap 20 words | all-MiniLM-L6-v2 | 0.8644 | 0.5589 | 0.9329 | 0.6410 |
| 5 | top_k = 5, chunk 100 words / overlap 20 words | BAAI/bge-base-en-v1.5 (768d) | **0.9305** | 0.6964 | 0.9273 | 0.6690 |
| 6 | top_k = 20 → reranked down to top_k = 5, chunk 100 words / overlap 20 words | BAAI/bge-base-en-v1.5 (768d) | 0.9079 | 0.6490 | 0.9185 | **0.7102** |

### Analysis & Observations

- **Effect of top_k (configs 1 → 3, same MiniLM embedding):** increasing top_k from 3 to 5 improves nearly every metric — faithfulness rises from 0.79 to 0.89, and context_recall rises from 0.87 to 0.92. This makes sense: pulling in more chunks reduces the chance of missing needed information.
- **Too large a top_k introduces noise:** pushing top_k further to 10 drives context_recall to nearly its maximum (0.9849), but answer_relevancy drops sharply to 0.58 and context_precision drops to 0.57 — the lowest across all runs. A likely explanation is that as more chunks are retrieved, the proportion of irrelevant ("noisy") chunks in the context grows, making it harder for the LLM to synthesize a focused answer even though the needed information is technically present.
- **Smaller chunks with overlap (configs 2 → 4):** switching to 100-word chunks with 20-word overlap at the same top_k = 5 slightly improves context_recall (0.918 → 0.933) and context_precision (0.628 → 0.641), but answer_relevancy drops (0.713 → 0.559) — suggesting that smaller chunks improve retrieval coverage but can fragment the context in a way that hurts the LLM's ability to stay on-topic.
- **Effect of the embedding model (configs 4 → 5):** with the same chunking strategy and top_k, switching from `all-MiniLM-L6-v2` (384 dimensions) to `BAAI/bge-base-en-v1.5` (768 dimensions) clearly improves faithfulness (0.864 → 0.9305 — the highest across all runs) and context_precision (0.641 → 0.669), while answer_relevancy also rises significantly (0.559 → 0.696). This is strong evidence that embedding quality has a large impact on the whole RAG pipeline, not just on retrieval in isolation.
- **Adding reranking (configs 5 → 6):** retrieving broadly (top_k = 20) and then reranking down to the best 5 chunks achieves the **highest context_precision across all runs (0.7102)** — as expected, since reranking is designed to filter out weakly relevant chunks. However, faithfulness and answer_relevancy are slightly lower than config 5 (no reranking), showing a trade-off between context accuracy and the stability of the final answer.

### Preliminary Conclusions

- **Configuration 5** (top_k = 5, 100-word chunks / 20-word overlap, `bge-base-en-v1.5` embedding) offers the best overall balance, with the highest faithfulness and solid scores on every other metric.
- **Configuration 6** (with reranking) is preferable when the priority is maximizing context precision, at the cost of a slight drop in answer faithfulness.
- top_k should not be increased indefinitely just to chase recall — it needs to be balanced against answer_relevancy and context_precision, since a noisy context directly hurts the quality of the final answer.
- The embedding model matters more than initially expected; upgrading from MiniLM (384d) to bge-base (768d) produced a clear improvement on almost every metric.

> Possible next steps: testing additional judge models to check the stability of the evaluation results, trying intermediate top_k values (7, 8) with the `bge-base` embedding, and evaluating the effect of larger chunk sizes (200–300 words) combined with reranking.

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
- Evaluation currently uses a single judge model (Gemma3:4B) — additional judges should be tried to verify the stability of the results.

## Link demo on Render.com
https://nlp-server-zr2m.onrender.com

## License
