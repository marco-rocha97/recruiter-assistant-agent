"""
LangGraph state for the candidate-screening pipeline.

Each field is set by exactly one node and consumed by downstream nodes.
Once `error` is set, conditional edges route the graph straight to END —
no subsequent node should be invoked.
"""

from typing import TypedDict

from src.features.ranking.schemas import ScreeningError, ShortlistResponse


class ScreeningState(TypedDict):
    jd_text: str
    jd_embedding: list[float] | None
    candidates: list[dict] | None  # top-15 pool JSON dicts from Chroma query
    candidate_distances: dict[str, float] | None  # candidate_id → L2 distance
    shortlist: ShortlistResponse | None
    error: ScreeningError | None
