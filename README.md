# Documento — backend

Django + DRF API that indexes uploaded files (md, txt, csv, json, pdf) through a
RAG pipeline and answers questions about them. Built to *learn* RAG: every
pipeline stage is a plain function you can call, and retrieval is exposed
separately from generation so you can see what the LLM is given.

Read [LEARNING.md](LEARNING.md) for the concepts, stage by stage.

## Stack

- Python 3.12, [uv](https://docs.astral.sh/uv/), Django 5.2, DRF, SimpleJWT, drf-spectacular
- PostgreSQL 16 + [pgvector](https://github.com/pgvector/pgvector) (chunks + embeddings live in a Django model)
- LangChain core + text-splitters; provider packages are optional extras
- Local embeddings by default via [fastembed](https://github.com/qdrant/fastembed) (ONNX, no API key)
- Code style: [HackSoft Django Styleguide](https://github.com/HackSoftware/Django-Styleguide)
  (services / selectors / one `APIView` per action with nested `InputSerializer` / `OutputSerializer`)

## Setup

```bash
cp .env.example .env            # then edit; add ANTHROPIC_API_KEY (or switch LLM_MODEL)
uv sync --extra anthropic       # or --extra openai / --extra ollama
docker compose up -d --wait     # pgvector Postgres on localhost:5433
uv run manage.py migrate
uv run manage.py runserver
```

Swagger UI: http://localhost:8000/api/docs/ — Admin: http://localhost:8000/admin/
(`uv run manage.py createsuperuser`).

## Try it

```bash
# sign up + token
curl -s -X POST localhost:8000/api/v1/users/ -H 'Content-Type: application/json' \
  -d '{"email":"ada@example.com","password":"password123"}'
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/token/ -H 'Content-Type: application/json' \
  -d '{"email":"ada@example.com","password":"password123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access"])')

# upload (runs LOAD -> CHUNK -> EMBED -> STORE synchronously)
curl -s -X POST localhost:8000/api/v1/documents/upload/ -H "Authorization: Bearer $TOKEN" -F file=@../README.md

# what did the splitter produce?
curl -s localhost:8000/api/v1/documents/<id>/chunks/ -H "Authorization: Bearer $TOKEN"

# retrieval only: which chunks would the LLM see, and how similar are they?
curl -s -X POST localhost:8000/api/v1/search/ -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"question":"what does documento do?","top_k":3}'

# full RAG: answer with [n] citations + the matching sources
curl -s -X POST localhost:8000/api/v1/ask/ -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"question":"what does documento do?"}'
```

## API (`/api/v1/`, JWT bearer, everything scoped to the caller)

| Method | Path | API class |
|---|---|---|
| POST | `users/` | `UserCreateApi` |
| GET | `users/me/` | `UserMeApi` |
| POST | `auth/token/`, `auth/token/refresh/` | `TokenObtainApi`, `TokenRefreshApi` |
| POST | `documents/upload/` (multipart `file`, optional `title`) | `DocumentCreateApi` |
| GET | `documents/?status=&mime_type=&q=&limit=&offset=` | `DocumentListApi` |
| GET | `documents/<id>/` | `DocumentDetailApi` |
| DELETE | `documents/<id>/delete/` | `DocumentDeleteApi` |
| POST | `documents/<id>/reindex/` | `DocumentReindexApi` |
| GET | `documents/<id>/chunks/` | `DocumentChunkListApi` |
| POST | `search/` `{question, top_k?, document_ids?}` | `ChunkSearchApi` |
| POST | `ask/` `{question, top_k?, document_ids?}` | `QuestionAnswerApi` |
| GET | `queries/` | `QueryLogListApi` |

Errors always look like `{"message": "...", "extra": {...}}`; validation errors
put field errors under `extra.fields`.

## Switching providers

Everything is resolved from `.env` by `apps/rag/providers.py`:

| Setting | Values |
|---|---|
| `LLM_MODEL` | `anthropic:claude-opus-5`, `openai:gpt-4.1`, `ollama:llama3.1`, … (LangChain `init_chat_model`) |
| `LLM_BASE_URL` / `LLM_API_KEY` | optional; route an `openai:` model through a gateway, e.g. OpenRouter: `LLM_MODEL=openai:anthropic/claude-sonnet-4.5`, `LLM_BASE_URL=https://openrouter.ai/api/v1`, `LLM_API_KEY=sk-or-...` |
| `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` | `fastembed` / `BAAI/bge-small-en-v1.5` (default, local), `openai` / `text-embedding-3-small`, `ollama` / `nomic-embed-text`, `huggingface` / … |
| `EMBEDDING_DIM` | must equal the embedding model's output size (384 for bge-small, 1536 for text-embedding-3-small) |

Changing the embedding model means the stored vectors are stale: update
`EMBEDDING_DIM` → `makemigrations && migrate` → `uv run manage.py reindex`.
The first `embeddings_get()` call verifies the dimension and refuses to run on a mismatch.

## Tests

```bash
DJANGO_SETTINGS_MODULE=config.django.test uv run manage.py test apps
```

Services and selectors are tested against the database; the embedding model and
the LLM are replaced with `langchain_core` fakes, so the suite runs offline.

## Layout

```
config/            env.py, django/{base,local,production,test}.py, settings/{jwt,rag}.py, urls.py
apps/common/       BaseModel, model_update
apps/core/         ApplicationError, exception handler, pagination, inline_serializer
apps/users/        BaseUser (email login), user_create, UserCreateApi / UserMeApi
apps/authentication/  SimpleJWT token APIs
apps/documents/    Document + Chunk (the vector store), document_* services/selectors, Document* APIs
apps/rag/
  providers.py     embeddings_get() / llm_get() — the only place a provider is named
  services/        loaders.py (LOAD) chunking.py (CHUNK) indexing.py (EMBED+STORE) answering.py (AUGMENT+GENERATE)
  selectors.py     chunk_search (RETRIEVE, cosine distance in SQL)
  retriever.py     DjangoChunkRetriever — LangChain BaseRetriever over the selector
  management/commands/reindex.py
```
