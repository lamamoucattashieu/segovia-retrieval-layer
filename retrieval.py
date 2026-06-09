from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb

BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = BASE_DIR / "storage" / "chroma"
COLLECTION_NAME = "legal_clinic_kb"
MODEL_NAME = "intfloat/multilingual-e5-small"

CACHE_DIR = BASE_DIR / "hf_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["TRANSFORMERS_CACHE"] = str(CACHE_DIR)
os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(CACHE_DIR)

from sentence_transformers import SentenceTransformer

DEFAULT_TOP_K = 5
MAX_TOP_K = 10

ANSWER_DISTANCE_THRESHOLD = 0.20
WEAK_DISTANCE_THRESHOLD = 0.24
MIN_SUPPORTING_CHUNKS = 2


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_collection(COLLECTION_NAME)


def collection_info() -> dict[str, Any]:
    collection = get_collection()
    return {
        "collection_name": COLLECTION_NAME,
        "count": collection.count(),
        "chroma_path": str(CHROMA_PATH),
        "embedding_model": MODEL_NAME,
    }


def _result_item(result: dict[str, Any], index: int) -> dict[str, Any]:
    metadata = result["metadatas"][0][index] or {}
    distance = float(result["distances"][0][index])

    return {
        "text": clean_text(result["documents"][0][index]),
        "distance": distance,
        "doc_id": metadata.get("doc_id"),
        "doc_type": metadata.get("doc_type"),
        "language": metadata.get("language"),
        "source_language": metadata.get("source_language"),
        "file_name": metadata.get("file_name"),
        "page": metadata.get("page"),
        "canonical_doc_id": metadata.get("canonical_doc_id"),
        "translation_status": metadata.get("translation_status"),
    }


def retrieve(query: str, top_k: int = DEFAULT_TOP_K, include_debug: bool = False) -> dict[str, Any]:
    query = query.strip()

    if not query:
        return {
            "status": "invalid_query",
            "can_answer": False,
            "confidence": "none",
            "message": "Query cannot be empty.",
            "results": [],
        }

    top_k = max(1, min(top_k, MAX_TOP_K))

    collection = get_collection()
    collection_count = collection.count()

    if collection_count == 0:
        return {
            "status": "empty_collection",
            "can_answer": False,
            "confidence": "none",
            "message": "The Chroma collection is empty. Add the Chroma DB or run ingestion first.",
            "results": [],
        }

    search_k = min(max(top_k, MIN_SUPPORTING_CHUNKS), collection_count)

    query_embedding = get_embedder().encode(
        [f"query: {query}"],
        normalize_embeddings=True,
    ).tolist()[0]

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=search_k,
        include=["documents", "metadatas", "distances"],
    )

    distances = [float(distance) for distance in result["distances"][0]]
    candidates = [_result_item(result, index) for index in range(len(distances))]

    if not distances:
        return {
            "status": "insufficient_context",
            "can_answer": False,
            "confidence": "insufficient",
            "message": "No relevant legal context was found.",
            "results": [],
        }

    best_distance = distances[0]
    supporting_chunks = sum(
        1 for distance in distances if distance <= ANSWER_DISTANCE_THRESHOLD
    )

    can_answer = (
        best_distance <= ANSWER_DISTANCE_THRESHOLD
        and supporting_chunks >= MIN_SUPPORTING_CHUNKS
    )

    if can_answer:
        status = "success"
        confidence = "strong"
        message = "Relevant legal context found."
        results = candidates[:top_k]
    elif best_distance <= WEAK_DISTANCE_THRESHOLD:
        status = "low_confidence"
        confidence = "weak"
        message = "Some related context was found, but not enough to answer safely."
        results = []
    else:
        status = "insufficient_context"
        confidence = "insufficient"
        message = "No reliable support was found in the legal documents."
        results = []

    response = {
        "status": status,
        "can_answer": can_answer,
        "confidence": confidence,
        "message": message,
        "query": query,
        "top_k": top_k,
        "best_distance": best_distance,
        "supporting_chunks": supporting_chunks,
        "thresholds": {
            "answer_distance": ANSWER_DISTANCE_THRESHOLD,
            "weak_distance": WEAK_DISTANCE_THRESHOLD,
            "min_supporting_chunks": MIN_SUPPORTING_CHUNKS,
        },
        "results": results,
    }

    if include_debug:
        response["debug_candidates"] = candidates

    return response

