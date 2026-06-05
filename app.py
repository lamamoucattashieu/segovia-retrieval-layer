from fastapi import FastAPI
from pydantic import BaseModel

from retrieval import retrieve, seed_demo_data

app = FastAPI(title="Retrieval Prototype")


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


@app.on_event("startup")
def startup_event():
    seed_demo_data()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/retrieve")
def retrieve_route(payload: QueryRequest):
    return retrieve(payload.query, top_k=payload.top_k)