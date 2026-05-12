"""
Pydantic schemas for the ranking feature.

RankRequest       — incoming API request body.
CandidateRanking  — a single ranked candidate entry in the shortlist.
ShortlistResponse — the successful API response body (up to 5 CandidateRanking items).
ScreeningError    — internal error carrier propagated through the LangGraph state;
                    mapped directly to the HTTP error response body by the API layer.
"""

from typing import Literal

from pydantic import BaseModel


class RankRequest(BaseModel):
    jd_text: str


class CandidateRanking(BaseModel):
    candidate_id: str
    rank: int
    category: str
    matched_requirements: list[str]
    missing_requirements: list[str]
    evidence: str
    vector_score: float = 0.0  # derived post-LLM from Chroma L2 distance; not LLM-generated


class ShortlistResponse(BaseModel):
    rankings: list[CandidateRanking]


class ScreeningError(BaseModel):
    error_code: Literal["invalid_jd", "injection_detected", "ranking_failed"]
    message: str
