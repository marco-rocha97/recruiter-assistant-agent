"""
Phase 2 — Offline evaluation harness.

Loads data/eval/jds.json and data/eval/ground_truth.json, runs the ranking
pipeline for each JD, and computes set-overlap @ 5 against the ground truth.
Writes data/eval/report.json with the agreement_rate and per-JD breakdown.

Invocation (from repo root, using backend's uv environment):
  uv run --directory backend python ../scripts/eval_harness.py

Requires:
  - data/eval/ground_truth.json (committed after Marco's review step).
    If missing, the script exits with a clear error message.
  - GEMINI_API_KEY (and optionally OPENAI_API_KEY) in .env.

Design: direct run_graph() call, no running server required. Matches the
pattern used in backend/tests/ranking/test_nodes.py. Temperature is set to 0
for reproducibility — same model and temperature produce the same ranking,
making the committed report.json a stable portfolio reference.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

# Bootstrap sys.path so that backend/src is importable (same pattern as
# prepare_dataset.py — both run via uv run --directory backend).
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(_REPO_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_JDS_PATH = _REPO_ROOT / "data" / "eval" / "jds.json"
_GROUND_TRUTH_PATH = _REPO_ROOT / "data" / "eval" / "ground_truth.json"
_REPORT_PATH = _REPO_ROOT / "data" / "eval" / "report.json"

_EVAL_MODEL = "gemini/gemini-2.5-flash"
_EVAL_TEMPERATURE = 0


def compute_agreement(
    agent_top5: list[str],
    ground_truth_top5: list[str],
) -> float:
    """
    Set overlap @ 5: |intersection| / min(len(agent_top5), 5). Returns 0.0–1.0.

    The denominator is always 5 when the agent returns a full shortlist.
    When the agent returns fewer than 5 candidates (niche JD or small pool),
    the denominator falls back to the actual count and a warning is logged.
    Duplicate IDs in agent_top5 are collapsed to a set before comparison.
    """
    agent_set = set(agent_top5)
    truth_set = set(ground_truth_top5)

    if len(agent_top5) < 5:
        logger.warning(
            "agent_top5 has %d candidates (expected 5); using %d as denominator. "
            "Consider replacing this JD in jds.json if the pool is too small.",
            len(agent_top5),
            len(agent_top5),
        )

    denominator = min(len(agent_top5), 5)
    if denominator == 0:
        return 0.0

    overlap = len(agent_set & truth_set)
    return overlap / denominator


def run_eval(
    jds: list[dict],
    ground_truth: dict[str, list[str]],
) -> dict:
    """
    Runs ranking for each JD, computes agreement, returns report dict.

    Args:
        jds: List of JD dicts loaded from data/eval/jds.json.
        ground_truth: Dict mapping jd_id → list of 5 candidate_id strings.

    Returns:
        Report dict matching the schema in the Tech Spec Contracts section.
    """
    # Import here so the module is importable for unit tests without
    # triggering the Chroma and LangGraph initialisation at import time.
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
    load_dotenv(_REPO_ROOT / "backend" / ".env")

    from src.graph.screening import run_graph  # noqa: E402

    per_jd = []
    agreements = []

    for jd in jds:
        jd_id = jd["id"]
        jd_title = jd["title"]
        jd_text = jd["text"]
        gt_top5 = ground_truth[jd_id]

        logger.info("Running ranking for JD %s: %s", jd_id, jd_title)
        state = run_graph(jd_text)

        if state.get("error"):
            logger.error("Ranking failed for %s: %s", jd_id, state["error"].message)
            agent_top5: list[str] = []
        else:
            agent_top5 = [r.candidate_id for r in state["shortlist"].rankings]

        agreement = compute_agreement(agent_top5, gt_top5)
        overlap = len(set(agent_top5) & set(gt_top5))
        agreements.append(agreement)

        logger.info(
            "  agent=%s  overlap=%d  agreement=%.3f",
            agent_top5,
            overlap,
            agreement,
        )

        per_jd.append(
            {
                "jd_id": jd_id,
                "jd_title": jd_title,
                "agent_top5": agent_top5,
                "ground_truth_top5": gt_top5,
                "overlap": overlap,
                "agreement": agreement,
            }
        )

    agreement_rate = sum(agreements) / len(agreements) if agreements else 0.0

    return {
        "agreement_rate": agreement_rate,
        "jd_count": len(jds),
        "model": _EVAL_MODEL,
        "temperature": _EVAL_TEMPERATURE,
        "run_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "per_jd": per_jd,
    }


def main() -> None:
    if not _GROUND_TRUTH_PATH.exists():
        print(
            f"ERROR: {_GROUND_TRUTH_PATH} not found.\n"
            "Run label_ground_truth.py first, review the output, and commit\n"
            "data/eval/ground_truth_review.json as data/eval/ground_truth.json.\n"
            "See the Tech Spec (docs/tech-specs/recruiter-assistant-agent__T05.md) "
            "for the full labeling workflow.",
            file=sys.stderr,
        )
        sys.exit(1)

    jds = json.loads(_JDS_PATH.read_text(encoding="utf-8"))
    ground_truth = json.loads(_GROUND_TRUTH_PATH.read_text(encoding="utf-8"))

    report = run_eval(jds, ground_truth)

    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("Written %s", _REPORT_PATH)
    logger.info(
        "Agreement rate: %.3f (%d/%d JDs ≥ 80%%: %s)",
        report["agreement_rate"],
        sum(1 for e in report["per_jd"] if e["agreement"] >= 0.8),
        report["jd_count"],
        "PASS" if report["agreement_rate"] >= 0.80 else "FAIL — review per_jd breakdown",
    )


if __name__ == "__main__":
    main()
