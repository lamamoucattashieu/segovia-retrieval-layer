from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from retrieval import collection_info, retrieve

app = FastAPI(title="Segovia Retrieval Layer")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)
    include_debug: bool = False


@app.get("/")
def root():
    return {
        "service": "Segovia Retrieval Layer",
        "docs": "/docs",
        "health": "/health",
        "retrieve": "/retrieve",
    }


@app.get("/health")
def health():
    try:
        info = collection_info()
        return {
            "status": "ok",
            **info,
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
        }


@app.post("/retrieve")
def retrieve_route(payload: QueryRequest):
    try:
        return retrieve(
            query=payload.query,
            top_k=payload.top_k,
            include_debug=payload.include_debug,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc