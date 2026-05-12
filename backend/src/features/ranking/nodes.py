"""
LangGraph node functions for the candidate-screening pipeline.

Each node accepts and returns ScreeningState. Nodes that detect an error
set state["error"] and return immediately — conditional edges in the graph
then route directly to END so no subsequent node is called.

Import side-effects to be aware of:
- get_collection() is NOT called at import time; it's called inside
  search_candidates() so tests can mock it at the module level.
- embed() and complete() are imported by name so tests can patch them
  at src.features.ranking.nodes.embed / .complete.
"""

import json

from src.features.ranking.prompts import RANKING_SYSTEM_PROMPT
from src.features.ranking.schemas import ScreeningError, ShortlistResponse
from src.graph.state import ScreeningState
from src.lib.guardrails.injection import classify_injection
from src.lib.llm.client import complete, embed
from src.lib.vectorstore.chroma import POOL_DIR, get_collection

STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "in",
        "of",
        "to",
        "and",
        "is",
        "are",
        "was",
        "were",
        "for",
        "on",
        "with",
        "as",
        "at",
        "by",
        "from",
        "or",
        "but",
        "this",
        "that",
        "it",
        "be",
        "do",
        "have",
        "has",
        "will",
        "we",
        "you",
        "they",
        "our",
        "your",
        "their",
        "who",
        "what",
        "which",
        "how",
        "when",
        "where",
    }
)


def validate_jd(state: ScreeningState) -> ScreeningState:
    text = state["jd_text"].strip()
    if len(text) < 50:
        return {
            **state,
            "error": ScreeningError(
                error_code="invalid_jd",
                message=(
                    "Job description is too short. Paste the full job description"
                    " to see a ranked shortlist."
                ),
            ),
        }
    tokens = [
        t.lower().strip(".,;:!?")
        for t in text.split()
        if t.lower().strip(".,;:!?") not in STOPWORDS
    ]
    if len(tokens) < 3:
        return {
            **state,
            "error": ScreeningError(
                error_code="invalid_jd",
                message=(
                    "No identifiable requirements found. Include specific skills,"
                    " experience, or qualifications in the job description."
                ),
            ),
        }
    return state


def check_injection(state: ScreeningState) -> ScreeningState:
    is_injection, _ = classify_injection(state["jd_text"])
    if is_injection:
        return {
            **state,
            "error": ScreeningError(
                error_code="injection_detected",
                message=(
                    "The job description contains text that looks like an attempt to"
                    " manipulate the AI. Please submit a real job description."
                ),
            ),
        }
    return state


def embed_jd(state: ScreeningState) -> ScreeningState:
    try:
        embedding = embed(state["jd_text"])
        return {**state, "jd_embedding": embedding}
    except RuntimeError:
        return {
            **state,
            "error": ScreeningError(
                error_code="ranking_failed",
                message="An error occurred while processing your request. Please try again.",
            ),
        }


def search_candidates(state: ScreeningState) -> ScreeningState:
    try:
        collection = get_collection()
        results = collection.query(
            query_embeddings=[state["jd_embedding"]],
            n_results=15,
        )
        candidate_ids = results["ids"][0]
        candidates = []
        for cid in candidate_ids:
            pool_file = POOL_DIR / f"{cid}.json"
            candidates.append(json.loads(pool_file.read_text()))
        return {**state, "candidates": candidates}
    except Exception:
        return {
            **state,
            "error": ScreeningError(
                error_code="ranking_failed",
                message="An error occurred while processing your request. Please try again.",
            ),
        }


def rank_candidates(state: ScreeningState) -> ScreeningState:
    queried_ids = {c["id"] for c in state["candidates"]}
    user_content = (
        f"<job_description>\n{state['jd_text']}\n</job_description>\n\n"
        f"<candidates>\n{json.dumps(state['candidates'], indent=2)}\n</candidates>"
    )
    try:
        result = complete(
            prompt=user_content,
            system=RANKING_SYSTEM_PROMPT,
            response_format=ShortlistResponse,
        )
        # Discard any candidate_id the LLM hallucinated outside the queried set
        valid_rankings = [r for r in result.rankings if r.candidate_id in queried_ids]
        return {**state, "shortlist": ShortlistResponse(rankings=valid_rankings)}
    except Exception:
        return {
            **state,
            "error": ScreeningError(
                error_code="ranking_failed",
                message="An error occurred while processing your request. Please try again.",
            ),
        }
