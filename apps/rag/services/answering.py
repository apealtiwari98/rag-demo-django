"""
AUGMENT + GENERATE: the last two stages of a RAG query.

    question -> retriever -> numbered context -> prompt -> LLM -> answer

The LLM is told to use only the supplied context and to cite passages as
[n]; the API returns the matching sources so citations are verifiable.
"""

import time
from uuid import UUID

from django.conf import settings
from langchain_core.documents import Document as LCDocument
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from apps.rag.models import QueryLog
from apps.rag.providers import llm_get
from apps.rag.retriever import DjangoChunkRetriever
from apps.users.models import BaseUser

SYSTEM_PROMPT = """\
You answer questions about the user's documents.

Rules:
- Use ONLY the numbered context passages below. Do not use outside knowledge.
- Cite the passages you rely on with their number in square brackets, e.g. [2].
- If the context does not contain the answer, say you don't know and do not guess.
- Be concise.
"""

HUMAN_PROMPT = """\
Context passages:
{context}

Question: {question}
"""

NO_CONTEXT_ANSWER = "I couldn't find anything relevant in your indexed documents."

prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", HUMAN_PROMPT)])


def context_format(docs: list[LCDocument]) -> str:
    blocks = []

    for number, doc in enumerate(docs, start=1):
        source = doc.metadata.get("document_title", "")
        page = doc.metadata.get("page")
        location = f"{source}, page {page}" if page else source
        blocks.append(f"[{number}] ({location})\n{doc.page_content}")

    return "\n\n".join(blocks)


def sources_format(docs: list[LCDocument]) -> list[dict]:
    return [
        {
            "n": number,
            "chunk_id": doc.metadata["chunk_id"],
            "document_id": doc.metadata["document_id"],
            "document_title": doc.metadata["document_title"],
            "index": doc.metadata["index"],
            "page": doc.metadata.get("page"),
            "score": round(doc.metadata["score"], 4),
        }
        for number, doc in enumerate(docs, start=1)
    ]


def question_answer(
    *,
    user: BaseUser,
    question: str,
    top_k: int,
    document_ids: list[UUID] | None = None,
) -> QueryLog:
    started = time.perf_counter()

    retriever = DjangoChunkRetriever(user=user, top_k=top_k, document_ids=document_ids)
    docs = retriever.invoke(question)

    if docs:
        # LCEL: prompt | llm | parser. Each `|` pipes one Runnable into the next.
        chain = prompt | llm_get() | StrOutputParser()
        answer = chain.invoke({"context": context_format(docs), "question": question})
    else:
        answer = NO_CONTEXT_ANSWER

    latency_ms = int((time.perf_counter() - started) * 1000)

    query_log = QueryLog(
        user=user,
        question=question,
        answer=answer,
        sources=sources_format(docs),
        llm_model=settings.LLM_MODEL,
        embedding_model=f"{settings.EMBEDDING_PROVIDER}:{settings.EMBEDDING_MODEL}",
        top_k=top_k,
        latency_ms=latency_ms,
    )
    query_log.full_clean()
    query_log.save()

    return query_log
