"""
Knobs for the RAG pipeline. Everything here is provider-agnostic: the LLM and
the embedding model are resolved at runtime by `apps.rag.providers`.
"""

from config.env import env

# Generation: LangChain `init_chat_model` string, "<provider>:<model>".
LLM_MODEL = env("LLM_MODEL", default="anthropic:claude-opus-5")
# Optional overrides for OpenAI-compatible gateways (OpenRouter, LiteLLM, vLLM, ...).
# Leave empty to use the provider's own endpoint and its usual env var
# (ANTHROPIC_API_KEY / OPENAI_API_KEY).
LLM_BASE_URL = env("LLM_BASE_URL", default="")
LLM_API_KEY = env("LLM_API_KEY", default="")

# Indexing/retrieval embeddings.
EMBEDDING_PROVIDER = env("EMBEDDING_PROVIDER", default="fastembed")
EMBEDDING_MODEL = env("EMBEDDING_MODEL", default="BAAI/bge-small-en-v1.5")
# The pgvector column is fixed-size; this MUST match the model's output dimension.
EMBEDDING_DIM = env.int("EMBEDDING_DIM", default=384)

# Chunking
CHUNK_SIZE = env.int("CHUNK_SIZE", default=800)
CHUNK_OVERLAP = env.int("CHUNK_OVERLAP", default=100)

# Retrieval
TOP_K = env.int("TOP_K", default=5)
TOP_K_MAX = 20

# Upload constraints
DOCUMENT_MAX_SIZE_BYTES = env.int("DOCUMENT_MAX_SIZE_BYTES", default=10 * 1024 * 1024)
DOCUMENT_ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "application/pdf",
}
# Extension fallback used when the client sends a generic mime type.
DOCUMENT_EXTENSION_MIME_TYPES = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".pdf": "application/pdf",
}
