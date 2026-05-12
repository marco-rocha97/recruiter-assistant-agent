"""
LangGraph StateGraph assembly for the candidate-screening pipeline.

The graph is compiled once at module load time (_graph = _build_graph()).
run_graph() is the public entrypoint called by the FastAPI layer.

Conditional edges: after each node except rank_candidates, _route() checks
whether an error was set. If so, the graph terminates immediately — no further
nodes are executed.
"""

from langgraph.graph import END, StateGraph

from src.features.ranking.nodes import (
    check_injection,
    embed_jd,
    rank_candidates,
    search_candidates,
    validate_jd,
)
from src.graph.state import ScreeningState


def _route(state: ScreeningState) -> str:
    return "end" if state.get("error") else "continue"


def _build_graph():
    g = StateGraph(ScreeningState)
    g.add_node("validate_jd", validate_jd)
    g.add_node("check_injection", check_injection)
    g.add_node("embed_jd", embed_jd)
    g.add_node("search_candidates", search_candidates)
    g.add_node("rank_candidates", rank_candidates)

    g.set_entry_point("validate_jd")
    g.add_conditional_edges("validate_jd", _route, {"continue": "check_injection", "end": END})
    g.add_conditional_edges("check_injection", _route, {"continue": "embed_jd", "end": END})
    g.add_conditional_edges("embed_jd", _route, {"continue": "search_candidates", "end": END})
    g.add_conditional_edges(
        "search_candidates", _route, {"continue": "rank_candidates", "end": END}
    )
    g.add_edge("rank_candidates", END)
    return g.compile()


_graph = _build_graph()


def run_graph(jd_text: str) -> ScreeningState:
    """Invoke the screening pipeline with the given job description text."""
    initial: ScreeningState = {
        "jd_text": jd_text,
        "jd_embedding": None,
        "candidates": None,
        "shortlist": None,
        "error": None,
    }
    return _graph.invoke(initial)
