from pathlib import Path
import json
import os

import chromadb
from sentence_transformers import SentenceTransformer
from deep_translator import GoogleTranslator

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "sample_chunks.json"
CHROMA_PATH = BASE_DIR / "chroma_store"
COLLECTION_NAME = "prison_docs"

# Keep the cache inside the project so Windows permissions do not block it
CACHE_DIR = BASE_DIR / "hf_cache"
CACHE_DIR.mkdir(exist_ok=True)
os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["TRANSFORMERS_CACHE"] = str(CACHE_DIR)
os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(CACHE_DIR)

MODEL_NAME = "intfloat/multilingual-e5-small"

embedder = SentenceTransformer(MODEL_NAME)
client = chromadb.PersistentClient(path=str(CHROMA_PATH))
collection = client.get_or_create_collection(name=COLLECTION_NAME)


def translate_to_spanish(text: str) -> str:
    try:
        return GoogleTranslator(source="auto", target="es").translate(text)
    except Exception:
        return text


def seed_demo_data() -> None:
    if collection.count() > 0:
        return

    chunks = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    ids = [item["id"] for item in chunks]
    docs = [f"passage: {item['text']}" for item in chunks]
    metas = [
        {
            "language": item["language"],
            "page": item["page"],
            "source": item["source"],
        }
        for item in chunks
    ]
    embeddings = embedder.encode(docs, normalize_embeddings=True).tolist()

    collection.add(
        ids=ids,
        documents=docs,
        metadatas=metas,
        embeddings=embeddings,
    )


def search_chunks(query_text: str, top_k: int = 5):
    query_embedding = embedder.encode(
        [f"query: {query_text}"],
        normalize_embeddings=True
    ).tolist()[0]

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    items = []
    for i in range(len(result["documents"][0])):
        items.append(
            {
                "text": result["documents"][0][i].replace("passage: ", "", 1),
                "score": result["distances"][0][i],
                "language": result["metadatas"][0][i].get("language"),
                "page": result["metadatas"][0][i].get("page"),
                "source": result["metadatas"][0][i].get("source"),
            }
        )
    return items


def retrieve(query: str, top_k: int = 5):
    translated_query = translate_to_spanish(query)
    results = search_chunks(translated_query, top_k=top_k)

    return {
        "original_query": query,
        "translated_query": translated_query,
        "results": results,
    }