"""
Phase 1 — LLM-assisted ground truth labeling.

Loads all 49 candidates from data/pool/ and the 5 JDs from data/eval/jds.json.
For each JD, calls complete() asking the LLM to suggest a ranked top-5 with
reasoning. Writes data/eval/ground_truth_review.json for human review.

Marco then reads that file, overrides at least one pick per JD to confirm he
actually reviewed, and commits the result as data/eval/ground_truth.json.

Invocation (from repo root, using backend's uv environment):
  uv run --directory backend python ../scripts/label_ground_truth.py

Requires GEMINI_API_KEY (and optionally OPENAI_API_KEY for fallback) in .env
at the repo root or backend/ directory.
"""

import json
import logging
import sys
import time
from pathlib import Path

# Bootstrap sys.path so that backend/src is importable (same pattern as
# prepare_dataset.py — both run via uv run --directory backend).
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(_REPO_ROOT))

# noqa: E402 — imports must follow sys.path manipulation
from dotenv import load_dotenv  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from lib.llm.client import complete  # noqa: E402

load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_REPO_ROOT / "backend" / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_POOL_DIR = _REPO_ROOT / "data" / "pool"
_JDS_PATH = _REPO_ROOT / "data" / "eval" / "jds.json"
_REVIEW_PATH = _REPO_ROOT / "data" / "eval" / "ground_truth_review.json"

LABELING_SYSTEM_PROMPT = """\
You are an expert technical recruiter reviewing candidate profiles for a job description.

You will receive:
1. A job description (JD) for a specific role.
2. A list of candidate profiles, each with an id, skills, experience, and education.

Your task: select the 5 candidates who are the best fit for this job description.

Rules:
- Base your selection ONLY on the provided candidate data (skills, experience, education).
- Return exactly 5 candidate_id values, ranked from best fit (rank 1) to fifth-best (rank 5).
- For each pick, provide a concise reason (1-2 sentences) citing specific evidence from the profile.
- Do not invent or assume information not present in the candidate profiles.
- If fewer than 5 candidates are clearly relevant, pick the best available and note the limitation.
"""


class CandidatePick(BaseModel):
    candidate_id: str
    rank: int
    reason: str


class LabelingResponse(BaseModel):
    picks: list[CandidatePick]


def load_candidates(pool_dir: Path) -> list[dict]:
    """Load all candidate JSON files from the pool directory."""
    candidates = []
    for path in sorted(pool_dir.glob("candidate_*.json")):
        candidates.append(json.loads(path.read_text(encoding="utf-8")))
    logger.info("Loaded %d candidates from %s", len(candidates), pool_dir)
    return candidates


def suggest_labels(jd: dict, candidates: list[dict]) -> list[dict]:
    """
    Calls LLM; returns list of {candidate_id, rank, reason}.

    The candidate list is formatted as structured JSON — no raw CV text,
    no PII (already scrubbed at dataset-prep time).
    """
    user_content = (
        f"<job_description>\n{jd['text']}\n</job_description>\n\n"
        f"<candidates>\n{json.dumps(candidates, indent=2)}\n</candidates>"
    )
    result = complete(
        prompt=user_content,
        system=LABELING_SYSTEM_PROMPT,
        response_format=LabelingResponse,
    )
    return [pick.model_dump() for pick in result.picks]


def main() -> None:
    jds = json.loads(_JDS_PATH.read_text(encoding="utf-8"))
    candidates = load_candidates(_POOL_DIR)

    review: dict[str, list[dict]] = {}

    for jd in jds:
        logger.info("Labeling JD %s: %s", jd["id"], jd["title"])
        picks = suggest_labels(jd, candidates)
        review[jd["id"]] = picks
        logger.info(
            "  Suggested picks: %s",
            [p["candidate_id"] for p in sorted(picks, key=lambda p: p["rank"])],
        )
        # Rate-limit between calls — Gemini free-tier is 15 RPM
        time.sleep(4)

    _REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REVIEW_PATH.write_text(json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Written %s", _REVIEW_PATH)
    logger.info(
        "Next step: review %s, override at least one pick per JD, "
        "then commit the result as data/eval/ground_truth.json",
        _REVIEW_PATH.name,
    )


if __name__ == "__main__":
    main()
