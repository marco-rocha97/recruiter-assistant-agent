"""
Unit tests for compute_agreement() in scripts/eval_harness.py.

compute_agreement() is a pure function — no LLM, no Chroma, no filesystem.
The conftest.py in this directory adds the repo root to sys.path so that
scripts.eval_harness is importable.
"""

import pytest
from scripts.eval_harness import compute_agreement


def test_perfect_agreement():
    """agent_top5 == ground_truth_top5 (same 5 ids) → 1.0."""
    ids = ["candidate_001", "candidate_002", "candidate_003", "candidate_004", "candidate_005"]
    assert compute_agreement(ids, ids) == 1.0


def test_partial_overlap_3():
    """3 of 5 ids match → 0.6."""
    agent = ["candidate_001", "candidate_002", "candidate_003", "candidate_010", "candidate_011"]
    truth = ["candidate_001", "candidate_002", "candidate_003", "candidate_020", "candidate_021"]
    assert compute_agreement(agent, truth) == pytest.approx(0.6)


def test_no_overlap():
    """0 ids in common → 0.0."""
    agent = ["candidate_001", "candidate_002", "candidate_003", "candidate_004", "candidate_005"]
    truth = ["candidate_006", "candidate_007", "candidate_008", "candidate_009", "candidate_010"]
    assert compute_agreement(agent, truth) == 0.0


def test_partial_overlap_order_independent():
    """Same 5 ids in different list order → 1.0 (order must not matter)."""
    agent = ["candidate_005", "candidate_004", "candidate_003", "candidate_002", "candidate_001"]
    truth = ["candidate_001", "candidate_002", "candidate_003", "candidate_004", "candidate_005"]
    assert compute_agreement(agent, truth) == 1.0


def test_agent_returns_fewer_than_5():
    """agent_top5 has 3 ids, 2 of which are in ground truth → 2/3 ≈ 0.667."""
    agent = ["candidate_001", "candidate_002", "candidate_010"]
    truth = ["candidate_001", "candidate_002", "candidate_020", "candidate_021", "candidate_022"]
    result = compute_agreement(agent, truth)
    assert result == pytest.approx(2 / 3)


def test_duplicate_ids_in_agent_output():
    """Repeated id in agent list is treated as a set — duplicates collapsed."""
    # candidate_001 appears twice; the set has 4 unique ids, 3 overlap with truth
    agent = [
        "candidate_001",
        "candidate_001",
        "candidate_002",
        "candidate_003",
        "candidate_010",
    ]
    truth = ["candidate_001", "candidate_002", "candidate_003", "candidate_020", "candidate_021"]
    # denominator = min(5, 5) = 5; overlap = |{001,002,003} ∩ {001,002,003,020,021}| = 3
    assert compute_agreement(agent, truth) == pytest.approx(0.6)
