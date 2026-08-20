# Segovia Legal Clinic — Offline Multilingual Legal RAG

A **fully offline** AI legal assistant built at the [IE University AI Lab](https://www.ie.edu/) for the **Segovia Penitentiary Centre**. Inmates ask questions about penitentiary law in **Arabic, English, French, or Spanish** and receive answers grounded *strictly* in the Spanish legal corpus — or an explicit, honest refusal when the documents don't support an answer.

Everything runs on local hardware (Raspberry Pi + mini-PC) with **no internet connection** after setup — a hard requirement of the deployment environment.

> This repository contains the retrieval and inference services. Actual legal PDFs, generated vector stores, and audit logs are intentionally not committed.

---

## Why this is hard

In a prison legal-information setting, a confident wrong answer is worse than no answer. The system is built around one principle: **the model can only speak from the source law, and must refuse otherwise.** That constraint — plus the offline requirement and four query languages against a Spanish-only corpus — drives every design decision below.

## Architecture

Two independently deployable FastAPI services with a formal contract between them:

```
  user question (ar / en / fr / es)
            │
            ▼
 ┌──────────────────────────┐
 │  Inference Engine         │   safety pre-filter → prompt assembly →
 │  (FastAPI microservice)   │   local LLM → post-processing → disclaimer
 └───────────┬──────────────┘
             │  POST /retrieve   (retrieval–inference contract)
             ▼
 ┌──────────────────────────┐
 │  Retrieval Layer          │   multilingual-e5 embeddings (local)
 │  (FastAPI microservice)   │   → ChromaDB semantic search
 │                           │   → BM25 / RRF hybrid re-ranking
 │                           │   → confidence gate → grounded context
 └───────────┬──────────────┘
             ▼
      ChromaDB  (single multilingual collection, metadata-partitioned by language)
```

The two layers talk over a versioned JSON contract (`docs/retrieval_inference_contract.md`). Retrieval returns **context, never final advice**; a hard `can_answer` / `inference_must_refuse` flag tells the inference layer when it is forbidden to speak.

## What makes it work

**One multilingual collection, not four systems.** Spanish is the single legal source corpus. `multilingual-e5` embeddings are cross-lingual, so an Arabic or French question retrieves the Spanish source law directly — no translation of the legal text, so nothing gets lost or distorted in translation. The four languages are metadata partitions inside one ChromaDB collection.

**A structurally enforced answerability gate.** Context is only released when `best_distance ≤ 0.19` **and** at least **2 supporting chunks** clear the threshold. Below that, retrieval returns *zero* chunks — so the inference layer physically has nothing to answer from and cannot fall back on the model's general legal training. The two-chunk minimum is deliberate: dropping it to one makes unrelated questions look answerable, which is unsafe for legal text.

**Hybrid ranking that re-orders but never admits.** Semantic search is fused with BM25/RRF and a small offline multilingual legal-term map, so exact references — `Artículo 47`, `Article 47`, `المادة ٤٧` — rank the right Spanish chunks cleanly. Crucially, keyword signal can improve *ordering* but is **never allowed to bypass the confidence gate** and turn weak semantic support into an answer. Arabic-Indic digits (`٤٧`) are normalised to ASCII article numbers during ingestion.

**A dedicated safety layer.** Before retrieval, the inference engine screens for requests it must never assist — escape, hiding or introducing contraband, weapon-making, harming others, breaking centre rules — and returns a calm, localised refusal in the user's language that redirects them toward legitimate legal questions.

**Full source traceability.** Every chunk carries `doc_type`, `file_name`, `page`, and a `document_version` (SHA-256-derived) so answers can cite readable sources like *"Artículo 47 — Comunicaciones telefónicas (p. 28)"* and every deployed answer is auditable back to an exact source version.

## Evaluation

A **33-case evaluation set** spans **10 legal categories** (ingreso, sanciones, permisos, extranjería, clasificación, legal articles, …) and **all four query languages**, including deliberate **negative cases** — off-topic and unsafe questions the system must *refuse* rather than answer. Coverage minimums (cases per category, per language, and negative cases) are themselves checked by a test so the eval set can't silently degrade. A separate calibration script sweeps the confidence threshold against this set.

## Engineering

- **Two-service architecture** with a documented handoff contract and integration checklist.
- **CI** (GitHub Actions) running the retrieval and inference test suites — unit tests across embedding, ingestion, retrieval, prompt-contract, safety/policy, and end-to-end integration.
- **Observability**: OpenTelemetry spans exported to a local **Arize Phoenix** instance for on-site tracing without any external service.
- **Offline-first deployment**: one online step caches the embedding model; everything else runs air-gapped. Documented pull-and-run flow for Raspberry Pi + mini-PC, with `Makefile` targets and an offline-warmup check.
- **Privacy by default**: audit logging stores a query *hash*, not raw text; raw-query logging is off unless explicitly enabled with sign-off.
- **Containerised** (Docker Compose) with legal PDFs mounted, never baked into the image.

## Tech stack

**Retrieval** — Python · FastAPI · LlamaIndex · ChromaDB · sentence-transformers (`multilingual-e5-small`) · BM25/RRF
**Inference** — Python · FastAPI · local LLM client · multilingual safety + templating layer
**Infra & Ops** — Docker Compose · GitHub Actions CI · OpenTelemetry + Arize Phoenix · Raspberry Pi / mini-PC offline deployment

## Repository layout

```
app/                     retrieval layer — ingestion, embedding, retrieval, audit, metrics
inference_engine/        inference layer — safety, prompt, LLM client, post-processing
config/                  document-type + legal-citation configuration
data/evaluation/         33-case multilingual retrieval evaluation set
scripts/                 ingestion/retrieval validation, evaluation, calibration, model download
docs/                    retrieval–inference contract, integration + hardware deployment guides
tests/ · inference_engine/tests/   CI test suites
```

*Built at the IE University AI Lab. This is applied, deployed infrastructure, not a demo — but it is not a substitute for legal review: lawyers approve the disclaimers and answer style before pilot use.*
