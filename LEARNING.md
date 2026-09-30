# Learning RAG through Documento

RAG = **Retrieval-Augmented Generation**. An LLM only knows what was in its
training data and what you put in the prompt. RAG is the discipline of
*finding the right text to put in the prompt* — automatically, from your own
documents — so the model answers from evidence instead of memory.

There are two pipelines, and they must agree with each other:

```
INDEXING (write path, runs once per document)
  file ──► LOAD ──► CHUNK ──► EMBED ──► STORE
                                         │  pgvector column on documents_chunk
QUERYING (read path, runs once per question)
  question ─► EMBED ─► RETRIEVE ─► AUGMENT ─► GENERATE ─► answer + citations
```

The word "agree" matters: the **same embedding model** must be used on both
sides, or the vectors live in different spaces and similarity is meaningless.

Each section below: the concept, where it lives in this codebase, the knobs,
and what to try. Fill in *Notes* as you experiment.

---

## 1. LOAD — `apps/rag/services/loaders.py`

**Concept.** Get plain text out of the file, preserving anything you'll want
to cite later (page numbers, section headers). Output is a list of LangChain
`Document(page_content, metadata)` — the lingua franca of every later stage.

**Here.** PDFs become one `Document` per page (`metadata["page"]`) via `pypdf`;
text formats become one `Document`. Empty output raises `ApplicationError`
(a scanned PDF has no text layer — OCR is a separate problem).

**Try.** Upload a PDF, then `GET /documents/<id>/chunks/` and look for `page`
in metadata. Upload an image-only PDF and watch the document land in
`status=failed` with a readable `error`.

**Notes.**

---

## 2. CHUNK — `apps/rag/services/chunking.py`

**Concept.** Embedding models have a small input window (bge-small: 512
tokens) and, more importantly, *retrieval works on focused passages*. A
whole chapter embeds to a mushy average; a paragraph embeds to a point.
Chunks overlap so a sentence cut at a boundary still appears intact somewhere.

**Here.** `RecursiveCharacterTextSplitter` tries `\n\n` → `\n` → `. ` → ` `
before hard-cutting. Markdown is pre-split on headings so chunks never straddle
sections and carry `h1/h2/h3` in metadata (compare `chunks/` output for a `.md`
vs a `.txt` copy of the same text).

**Knobs.** `CHUNK_SIZE`, `CHUNK_OVERLAP` in `.env` (characters, not tokens).

**Try.** Set `CHUNK_SIZE=200`, `uv run manage.py reindex`, re-run the same
`/search/` — scores and passages change. Then `CHUNK_SIZE=2000`. Which gives
answers that quote the right sentence? Which gives more context to the LLM?
There is no universally right value; this is the first thing to tune in any
RAG system.

**Notes.**

---

## 3. EMBED — `apps/rag/providers.py`

**Concept.** An embedding model maps text to a fixed-length vector such that
*semantically similar texts have nearby vectors*. "Where do chunks live?" and
"Chunks are stored in Postgres" share almost no words but embed close together.
Similarity is measured by **cosine similarity** (angle between vectors):
1.0 = same direction, 0 = unrelated, negative = opposed.

**Here.** `embeddings_get()` returns a LangChain `Embeddings` object — two
methods, `embed_documents(texts)` and `embed_query(text)` — regardless of
provider. The default `FastEmbedEmbeddings` adapter is ~15 lines: that's the
whole interface. bge models get a query prefix (see `embed_query`) because they
were trained with asymmetric query/passage inputs.

**The dimension footgun.** The vector column is `vector(384)`. Switch to
`text-embedding-3-small` (1536-dim) without migrating and inserts fail; switch
and migrate but don't reindex and old vectors are silently incomparable to new
queries. `embeddings_get()` checks the dimension on first use;
`Document.embedding_model` records what indexed each document so you can spot
stale ones.

**Try.** `uv run python -c` a quick script: embed three sentences, compute
cosine similarities by hand (`numpy.dot` on normalized vectors), see the numbers
match what `/search/` reports.

**Notes.**

---

## 4. STORE — `apps/documents/models.py` (`Chunk`)

**Concept.** A "vector store" is just a table with a vector column and an
index that makes nearest-neighbour search fast. Postgres + pgvector does this
inside the same database as everything else, so ownership filtering, joins and
transactions are ordinary SQL.

**Here.** `Chunk.embedding = VectorField(dimensions=EMBEDDING_DIM)` plus an
`HnswIndex(... vector_cosine_ops)`. HNSW = a graph-based **approximate**
nearest-neighbour index: sub-linear search at the cost of possibly missing a
true neighbour (recall < 100%). `m` and `ef_construction` trade build
time/memory for recall. Storing is a `bulk_create` inside `transaction.atomic()`
in `apps/rag/services/indexing.py`, replacing old chunks so reindex is safe.

**Try.** `psql postgres://documento:documento@localhost:5433/documento` then
`EXPLAIN ANALYZE SELECT id FROM documents_chunk ORDER BY embedding <=> '[...]' LIMIT 5;`
(`<=>` is cosine distance). With few rows Postgres may skip the index —
`SET enable_seqscan = off;` to force it and compare.

**Notes.**

---

## 5. RETRIEVE — `apps/rag/selectors.py` (`chunk_search`)

**Concept.** Embed the question with the *same* model, then fetch the k
chunks with the smallest cosine distance. `top_k` is a budget: more chunks =
more chance the answer is present, but more noise and more tokens for the LLM.

**Here.** One ORM query:
`Chunk.objects.filter(document__owner=user).annotate(distance=CosineDistance("embedding", vec)).order_by("distance")[:k]`.
Ownership is in the same `WHERE` clause — a selector concern, never a view's.
`score = 1 - distance`. `DjangoChunkRetriever` wraps the selector as a LangChain
`BaseRetriever` so it composes with LCEL like any off-the-shelf store.

**Try.** `/search/` is retrieval with no LLM — use it constantly. Ask a
question whose answer you know is in a document; is the right chunk in the top
3? If not, the LLM *cannot* answer correctly no matter how good it is. This is
the single most useful debugging habit in RAG: **check retrieval before blaming
generation.**

**Limits you'll hit.** Pure vector search is bad at exact tokens (IDs, error
codes, rare names) — that's what hybrid search (Postgres full-text + vectors,
fused by rank) fixes. And the top-k by cosine is a coarse ranking; a
cross-encoder **reranker** over the top-20 usually improves the top-5. Both are
Phase 5 extensions.

**Notes.**

---

## 6. AUGMENT + GENERATE — `apps/rag/services/answering.py`

**Concept.** Build a prompt = instructions + numbered context passages +
question, and ask the LLM. The instructions do real work: *only use the
context*, *cite [n]*, *say "I don't know"*. Citations aren't decoration — they
let you verify the answer against `sources`, which is how you detect
hallucination.

**Here.** `prompt | llm_get() | StrOutputParser()` is LCEL — each `|` pipes a
Runnable into the next. `context_format` produces the `[n] (title, page)`
blocks; the API returns the same numbering in `sources` with chunk ids and
scores. Every question is written to `QueryLog`, which is your evaluation
dataset in waiting. `LLM_MODEL` is a `"provider:model"` string resolved by
LangChain's `init_chat_model`, so swapping vendors is an env change.

**Try.**
- Ask something *not* in your documents. Does it say it doesn't know, or does
  it make something up? Tighten `SYSTEM_PROMPT` and compare.
- Ask the same question with `top_k=1` and `top_k=10`.
- Switch `LLM_MODEL` to another provider and confirm the request is unchanged.
- Read `/queries/` after a session: which questions retrieved low-scoring
  sources? Those are your weak spots (chunking? missing document? phrasing?).

**Notes.**

---

## What went wrong while building (keep adding)

- **Circular import**: `selectors` imported the embeddings factory from the
  `services` package, whose `__init__` imported `answering` → `retriever` →
  `selectors`. Fix: the provider factories are infrastructure, not domain
  services — they moved to `apps/rag/providers.py`.
- **`langchain-community` is sunset**: instead of importing its
  `FastEmbedEmbeddings`, a 15-line adapter implements `Embeddings` directly.
  Less dependency, and it shows how small the interface is.
- **Mime types lie**: `.md` arrives as `text/plain` or `application/octet-stream`
  depending on the client, so a known extension wins over the header
  (`document_mime_detect`).
- **Indexing failures must not 500 the upload**: `document_index` catches,
  records `status=failed` + `error`, and returns; `reindex` retries. The DB
  write is inside a savepoint so a failed insert doesn't poison the request
  transaction (`ATOMIC_REQUESTS=True`).

## Glossary

- **Embedding** — fixed-length vector representing text meaning.
- **Cosine similarity / distance** — angle-based closeness; pgvector `<=>` is distance = 1 − similarity.
- **ANN / HNSW** — approximate nearest-neighbour search and pgvector's graph index for it.
- **Chunk** — the unit that gets embedded and retrieved.
- **top-k** — number of chunks retrieved per question.
- **Grounding** — answering only from retrieved evidence; **hallucination** is its failure.
- **LCEL** — LangChain Expression Language: composing Runnables with `|`.
- **Hybrid search** — vector + keyword (BM25/full-text) results fused together.
- **Reranker** — a second, more expensive model that re-orders the retrieved candidates.
