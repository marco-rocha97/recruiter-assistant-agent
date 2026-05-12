"""
FastAPI application entry point.

Exposes POST /rank — the single endpoint that accepts a job description and
returns a ranked shortlist or a plain-language error.

Lifespan: get_collection() is called at startup to open the Chroma PersistentClient
once and fail fast if data/chroma is missing, before the app accepts any traffic.

CORS: allow_origins defaults to "*" for local dev and Cloud Run preview URLs.
Production restriction to the Firebase Hosting origin is handled via the
CORS_ORIGINS env var in the Cloud Run deploy config — not baked into code.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.features.dataset.router import router as dataset_router
from src.features.ranking.schemas import RankRequest
from src.graph.screening import run_graph
from src.lib.vectorstore.chroma import get_collection


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_collection()  # fail fast if data/chroma is missing
    yield


app = FastAPI(title="Recruiter Assistant Agent", lifespan=lifespan)
app.include_router(dataset_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.post("/rank")
def rank(request: RankRequest):
    state = run_graph(request.jd_text)
    if state["error"]:
        err = state["error"]
        status = 422 if err.error_code in ("invalid_jd", "injection_detected") else 500
        return JSONResponse(status_code=status, content=err.model_dump())
    return state["shortlist"]
