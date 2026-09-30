"""
Provider adapters (embeddings + chat model).

Provider-agnostic factories. Everything else in the pipeline only ever sees
LangChain's `Embeddings` / `BaseChatModel` interfaces, so swapping providers
is a settings change.
"""

from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from langchain.chat_models import init_chat_model
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from config.env import BASE_DIR


class FastEmbedEmbeddings(Embeddings):
    """
    Minimal LangChain adapter over `fastembed` (local ONNX models, no API key,
    no torch). Implementing `Embeddings` is just these two methods.
    """

    def __init__(self, *, model_name: str):
        from fastembed import TextEmbedding

        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name, cache_dir=str(BASE_DIR / "local_cache"))

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        # bge models get better retrieval when queries carry this prefix.
        prefix = "Represent this sentence for searching relevant passages: " if "bge" in self.model_name else ""
        return next(self._model.query_embed(prefix + text)).tolist()


def _embeddings_build(*, provider: str, model_name: str) -> Embeddings:
    if provider == "fastembed":
        return FastEmbedEmbeddings(model_name=model_name)

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=model_name)

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=model_name)

    if provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=model_name)

    raise ImproperlyConfigured(f"Unknown EMBEDDING_PROVIDER '{provider}'.")


@lru_cache(maxsize=1)
def embeddings_get() -> Embeddings:
    """
    Process-wide singleton (loading a local model is slow). On first use it
    verifies the model's output size matches the pgvector column — the classic
    RAG footgun when someone changes EMBEDDING_MODEL without reindexing.
    """
    try:
        embeddings = _embeddings_build(provider=settings.EMBEDDING_PROVIDER, model_name=settings.EMBEDDING_MODEL)
    except ImportError as exc:
        raise ImproperlyConfigured(
            f"EMBEDDING_PROVIDER='{settings.EMBEDDING_PROVIDER}' needs an extra package: "
            f"uv sync --extra {settings.EMBEDDING_PROVIDER}"
        ) from exc

    dimension = len(embeddings.embed_query("dimension check"))

    if dimension != settings.EMBEDDING_DIM:
        raise ImproperlyConfigured(
            f"EMBEDDING_MODEL '{settings.EMBEDDING_MODEL}' produces {dimension}-dim vectors but "
            f"EMBEDDING_DIM={settings.EMBEDDING_DIM}. Update EMBEDDING_DIM, migrate, and run `manage.py reindex`."
        )

    return embeddings


@lru_cache(maxsize=1)
def llm_get() -> BaseChatModel:
    """
    `init_chat_model("<provider>:<model>")` resolves the provider package and
    its API key from the environment (ANTHROPIC_API_KEY, OPENAI_API_KEY, ...).

    LLM_BASE_URL / LLM_API_KEY point an OpenAI-compatible provider at a gateway
    such as OpenRouter: LLM_MODEL="openai:anthropic/claude-sonnet-4.5",
    LLM_BASE_URL="https://openrouter.ai/api/v1", LLM_API_KEY="sk-or-...".
    """
    kwargs = {}
    if settings.LLM_BASE_URL:
        kwargs["base_url"] = settings.LLM_BASE_URL
    if settings.LLM_API_KEY:
        kwargs["api_key"] = settings.LLM_API_KEY

    try:
        return init_chat_model(settings.LLM_MODEL, **kwargs)
    except ImportError as exc:
        provider = settings.LLM_MODEL.split(":", 1)[0]
        raise ImproperlyConfigured(f"LLM_MODEL='{settings.LLM_MODEL}' needs: uv sync --extra {provider}") from exc
