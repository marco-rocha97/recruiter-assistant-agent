"""
Build-time dataset preparation pipeline.

Runs once before each Docker image build. Produces:
  data/pool/candidate_NNN.json  — one per included candidate
  data/exclusions.json          — audit log of all exclusions
  data/chroma/                  — Chroma persistent directory

Pipeline stages:
  1. Load      CSV → validate required columns → row stream
  2. Sample    diverse selection: 2–3 per category, capped at --pool-size
  3. Check     injection classifier on concatenated CV text
  4. Extract   direct column mapping → ParsedCandidate (no LLM)
  5. Index     embed structured text → Chroma upsert + write pool JSON

Invocation (from repo root, using backend's uv environment):
  uv run --directory backend python ../scripts/prepare_dataset.py \\
    --source ../data/source/Resume.csv \\
    --pool-dir ../data/pool \\
    --chroma-dir ../data/chroma \\
    --exclusions ../data/exclusions.json \\
    --pool-size 50

Note: The LiteLLM client (complete/embed) is imported for embed() in Stage 5.
complete() is implemented in client.py and reserved for T02's ranking graph;
it is not called in this pipeline.
"""

import argparse
import ast
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Bootstrap sys.path so that:
#  - backend/src is importable for lib.guardrails and lib.llm
#  - repo root is importable for scripts.schemas
# Both are needed when running via:
#   uv run --directory backend python ../scripts/prepare_dataset.py
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(_REPO_ROOT))

# noqa: E402 — imports must follow sys.path manipulation
import pandas as pd  # noqa: E402

from lib.guardrails.injection import classify_injection  # noqa: E402
from lib.llm.client import embed  # noqa: E402
from scripts.schemas import (  # noqa: E402
    EducationEntry,
    ExclusionEntry,
    ExclusionLog,
    ExclusionReason,
    ExperienceEntry,
    ParsedCandidate,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Column names after BOM stripping — these are the canonical names used throughout
CATEGORY_COL = "job_position_name"
SKILLS_COL = "skills"
CAREER_OBJ_COL = "career_objective"
RESPONSIBILITIES_COL = "responsibilities"
POSITIONS_COL = "positions"
COMPANIES_COL = "professional_company_names"
START_DATES_COL = "start_dates"
END_DATES_COL = "end_dates"
DEGREE_NAMES_COL = "degree_names"
INSTITUTIONS_COL = "educational_institution_name"
PASSING_YEARS_COL = "passing_years"

MIN_TEXT_LEN = 100


# ---------------------------------------------------------------------------
# Stage 1 — Load and validate
# ---------------------------------------------------------------------------


def stage1_load(source_path: Path) -> pd.DataFrame:
    """
    Load CSV, strip BOM from column names, validate required columns are present.

    The source CSV has a BOM prefix on the first column name (﻿job_position_name).
    pandas with encoding='utf-8-sig' strips BOM from file start, and we also
    strip it manually from column names as a belt-and-suspenders measure.
    """
    logger.info("Stage 1: Loading CSV from %s", source_path)
    df = pd.read_csv(source_path, encoding="utf-8-sig", low_memory=False)

    # Strip BOM from any column name that somehow carries it
    df.columns = [c.lstrip("﻿").strip() for c in df.columns]

    required = {CATEGORY_COL, SKILLS_COL}
    missing = required - set(df.columns)
    if missing:
        found = sorted(df.columns.tolist())
        raise ValueError(
            f"Required columns missing from CSV: {sorted(missing)}. Columns found: {found}"
        )

    total = len(df)
    logger.info("Stage 1: Loaded %d rows, %d columns", total, len(df.columns))
    return df


# ---------------------------------------------------------------------------
# Stage 2 — Diverse sampling
# ---------------------------------------------------------------------------


def stage2_sample(df: pd.DataFrame, pool_size: int) -> pd.DataFrame:
    """
    Select up to `pool_size` rows with 2–3 candidates per category.

    Groups by job_position_name (BOM-stripped), samples min(3, group_size)
    from each, then shuffles and caps at pool_size.
    """
    logger.info("Stage 2: Diverse sampling (target pool size: %d)", pool_size)

    # Normalize category — strip whitespace/newlines
    df = df.copy()
    df[CATEGORY_COL] = df[CATEGORY_COL].fillna("").str.strip()

    sampled_frames = []
    per_category = 3  # take up to 3 per category; the cap handles the rest

    for category, group in df.groupby(CATEGORY_COL):
        if not category:
            continue
        n = min(per_category, len(group))
        sampled_frames.append(group.sample(n=n, random_state=42))

    if not sampled_frames:
        raise ValueError("No valid category groups found — CSV may be empty or malformed")

    selected = (
        pd.concat(sampled_frames)
        .sample(frac=1, random_state=42)  # shuffle
        .head(pool_size)
        .reset_index(drop=False)  # keep original index as 'index' column
    )

    n_categories = df[CATEGORY_COL].nunique()
    logger.info("Stage 2: Selected %d rows across %d categories", len(selected), n_categories)
    return selected


# ---------------------------------------------------------------------------
# Stage 3 — Injection check
# ---------------------------------------------------------------------------


def _build_cv_text(row: "pd.Series[Any]") -> str:
    """
    Concatenate the CV fields used for injection checking.

    Uses: career_objective + skills (raw string) + responsibilities.
    Does NOT use address or any other PII field.
    """
    parts = [
        str(row.get(CAREER_OBJ_COL, "") or ""),
        str(row.get(SKILLS_COL, "") or ""),
        str(row.get(RESPONSIBILITIES_COL, "") or ""),
    ]
    return " ".join(p for p in parts if p)


def stage3_injection_check(
    row: "pd.Series[Any]",
    source_id: str,
    category: str,
) -> ExclusionEntry | None:
    """
    Run the injection classifier on the concatenated CV text.

    Returns an ExclusionEntry if the text should be excluded, else None.
    Also returns an ExclusionEntry if the text is too short (< MIN_TEXT_LEN chars).
    """
    cv_text = _build_cv_text(row)

    if len(cv_text.strip()) < MIN_TEXT_LEN:
        return ExclusionEntry(
            source_id=source_id,
            category=category,
            reason=ExclusionReason.no_text,
        )

    is_injection, matched = classify_injection(cv_text)
    if is_injection:
        logger.warning(
            "Injection detected in %s (category=%s): matched %r",
            source_id,
            category,
            matched,
        )
        return ExclusionEntry(
            source_id=source_id,
            category=category,
            reason=ExclusionReason.injection_detected,
        )

    return None


# ---------------------------------------------------------------------------
# Stage 4 — Direct column mapping to ParsedCandidate (no LLM extraction)
# ---------------------------------------------------------------------------


def _parse_list_field(raw: Any) -> list[str]:
    """
    Parse a Python list serialized as a string (e.g. "['Python', 'SQL']").

    Returns an empty list on any parse error rather than raising.
    """
    if not raw or (isinstance(raw, float)):  # NaN from pandas
        return []
    try:
        result = ast.literal_eval(str(raw))
        if isinstance(result, list):
            return [str(item).strip() for item in result if str(item).strip()]
        return []
    except (ValueError, SyntaxError):
        return []


def _parse_duration_months(start_raw: str, end_raw: str) -> int | None:
    """
    Attempt to derive duration in months from start and end date strings.

    Accepts common formats like "Nov 2019", "Jan 2021", "Till Date".
    Returns None if either date is unparseable or end is "Till Date" / "Present".
    """
    from datetime import datetime

    end_lower = end_raw.strip().lower()
    if end_lower in ("till date", "present", "current", "ongoing", "now", ""):
        return None

    formats = ["%b %Y", "%B %Y", "%m/%Y", "%Y-%m", "%Y"]
    start_dt = None
    end_dt = None

    for fmt in formats:
        try:
            start_dt = datetime.strptime(start_raw.strip(), fmt)
            break
        except (ValueError, AttributeError):
            continue

    for fmt in formats:
        try:
            end_dt = datetime.strptime(end_raw.strip(), fmt)
            break
        except (ValueError, AttributeError):
            continue

    if start_dt is None or end_dt is None:
        return None

    delta_months = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)
    return max(delta_months, 0) if delta_months >= 0 else None


def stage4_extract(
    row: "pd.Series[Any]",
    candidate_id: str,
    category: str,
) -> ParsedCandidate | ExclusionEntry:
    """
    Map CSV columns directly to ParsedCandidate. No LLM call.

    Returns ExclusionEntry on parse failure or empty skills list.
    """
    source_id = str(row.get("index", "unknown"))

    # Skills
    skills_raw = str(row.get(SKILLS_COL, "") or "")
    skills = _parse_list_field(skills_raw)
    skills = [s for s in skills if s]  # filter empty strings

    if not skills:
        return ExclusionEntry(
            source_id=source_id,
            category=category,
            reason=ExclusionReason.no_skills,
        )

    # Experience — zip positions, companies, start_dates, end_dates
    positions = _parse_list_field(row.get(POSITIONS_COL, ""))
    companies = _parse_list_field(row.get(COMPANIES_COL, ""))
    starts = _parse_list_field(row.get(START_DATES_COL, ""))
    ends = _parse_list_field(row.get(END_DATES_COL, ""))

    experience: list[ExperienceEntry] = []
    max_exp = max(len(positions), len(companies), len(starts), len(ends))
    for i in range(max_exp):
        title = positions[i] if i < len(positions) else ""
        if not title:
            continue  # skip entries with no title
        company = companies[i] if i < len(companies) else None
        start = starts[i] if i < len(starts) else ""
        end = ends[i] if i < len(ends) else ""
        duration = _parse_duration_months(start, end) if start and end else None
        experience.append(
            ExperienceEntry(
                title=title,
                company=company or None,
                duration_months=duration,
            )
        )

    # Education — zip degree_names, institutions, passing_years
    degrees = _parse_list_field(row.get(DEGREE_NAMES_COL, ""))
    institutions = _parse_list_field(row.get(INSTITUTIONS_COL, ""))
    years_raw = _parse_list_field(row.get(PASSING_YEARS_COL, ""))

    education: list[EducationEntry] = []
    max_edu = max(len(degrees), len(institutions), len(years_raw))
    for i in range(max_edu):
        degree = degrees[i] if i < len(degrees) else ""
        if not degree:
            continue
        institution = institutions[i] if i < len(institutions) else None
        year_str = years_raw[i] if i < len(years_raw) else ""
        year: int | None = None
        try:
            year = int(year_str)
        except (ValueError, TypeError):
            year = None
        education.append(
            EducationEntry(
                degree=degree,
                institution=institution or None,
                year=year,
            )
        )

    # Summary — career_objective if non-empty
    summary_raw = str(row.get(CAREER_OBJ_COL, "") or "").strip()
    summary = summary_raw if summary_raw else None

    return ParsedCandidate(
        id=candidate_id,
        category=category,
        skills=skills,
        experience=experience,
        education=education,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Stage 5 — Embed + index + write artifacts
# ---------------------------------------------------------------------------


def _build_chroma_text(candidate: ParsedCandidate) -> str:
    """
    Build the structured text representation embedded in Chroma.

    No raw CV text. No PII. Only the structured fields from ParsedCandidate.
    Format matches what T02's JD query will be embedded against.
    """
    skills_str = ", ".join(candidate.skills)
    lines = [f"Skills: {skills_str}"]

    for exp in candidate.experience:
        parts = [exp.title]
        if exp.company:
            parts.append(f"at {exp.company}")
        if exp.duration_months is not None:
            parts.append(f"({exp.duration_months} months)")
        lines.append("Experience: " + " ".join(parts))

    for edu in candidate.education:
        parts = [edu.degree]
        if edu.institution:
            parts.append(edu.institution)
        if edu.year:
            parts.append(str(edu.year))
        lines.append("Education: " + ", ".join(parts))

    if candidate.summary:
        lines.append(f"Summary: {candidate.summary}")

    return "\n".join(lines)


def stage5_index(
    candidates: list[ParsedCandidate],
    pool_dir: Path,
    chroma_dir: Path,
    dry_run: bool = False,
) -> list[ExclusionEntry]:
    """
    Embed each candidate's structured text, upsert into Chroma, write pool JSON.

    Rate-limiting: 1 second sleep between embedding calls to avoid hitting
    Gemini free-tier limits (upgraded from the spec's 4s since this is
    embeddings-only; 15 RPM = 4s for completions, embeddings have higher quota).

    Returns a list of ExclusionEntry for any candidate that fails embedding.
    """
    import chromadb

    pool_dir.mkdir(parents=True, exist_ok=True)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    if not dry_run:
        chroma_client = chromadb.PersistentClient(path=str(chroma_dir))
        # Delete existing collection to rebuild from scratch on each run
        try:
            chroma_client.delete_collection("candidates")
        except Exception:
            pass
        collection = chroma_client.get_or_create_collection("candidates")

    failed: list[ExclusionEntry] = []

    for i, candidate in enumerate(candidates):
        chroma_text = _build_chroma_text(candidate)

        if not dry_run:
            try:
                embedding = embed(chroma_text)
                collection.upsert(
                    ids=[candidate.id],
                    embeddings=[embedding],
                    documents=[chroma_text],
                    metadatas=[{"category": candidate.category}],
                )
                # Rate-limit between embedding calls
                if i < len(candidates) - 1:
                    time.sleep(1)
            except Exception as exc:
                logger.error("Embedding failed for %s: %s", candidate.id, exc)
                failed.append(
                    ExclusionEntry(
                        source_id=candidate.id,
                        category=candidate.category,
                        reason=ExclusionReason.extraction_failed,
                    )
                )
                continue

        # Write pool JSON — only if embedding succeeded (or dry_run)
        pool_file = pool_dir / f"{candidate.id}.json"
        pool_file.write_text(
            candidate.model_dump_json(indent=2),
            encoding="utf-8",
        )
        logger.info("Written %s", pool_file.name)

    return failed


# ---------------------------------------------------------------------------
# Exclusion log
# ---------------------------------------------------------------------------


def write_exclusion_log(
    log: ExclusionLog,
    exclusions_path: Path,
) -> None:
    exclusions_path.parent.mkdir(parents=True, exist_ok=True)
    exclusions_path.write_text(
        log.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info(
        "Exclusions: total_source=%d, total_selected=%d, total_included=%d, total_excluded=%d",
        log.total_source,
        log.total_selected,
        log.total_included,
        log.total_excluded,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build-time dataset preparation pipeline for recruiter-assistant-agent"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("../data/source/Resume.csv"),
        help="Path to source CSV (default: ../data/source/Resume.csv)",
    )
    parser.add_argument(
        "--pool-dir",
        type=Path,
        default=Path("../data/pool"),
        help="Output directory for candidate JSON files (default: ../data/pool)",
    )
    parser.add_argument(
        "--chroma-dir",
        type=Path,
        default=Path("../data/chroma"),
        help="Chroma persistent directory (default: ../data/chroma)",
    )
    parser.add_argument(
        "--exclusions",
        type=Path,
        default=Path("../data/exclusions.json"),
        help="Output path for exclusions.json (default: ../data/exclusions.json)",
    )
    parser.add_argument(
        "--pool-size",
        type=int,
        default=50,
        help="Maximum number of candidates in the pool (default: 50)",
    )
    parser.add_argument(
        "--min-pool-size",
        type=int,
        default=20,
        help="Minimum required included candidates; exits non-zero if below (default: 20)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip embedding and Chroma upsert; write pool JSON without vectors. "
        "Useful for verifying Stages 1–4 without an API key.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.dry_run:
        logger.info("DRY RUN — embedding and Chroma upsert will be skipped")

    # Stage 1: Load
    df = stage1_load(args.source)
    total_source = len(df)

    # Stage 2: Sample
    selected_df = stage2_sample(df, args.pool_size)
    total_selected = len(selected_df)

    # Stages 3 & 4: per-row injection check + column mapping
    exclusions: list[ExclusionEntry] = []
    candidates: list[ParsedCandidate] = []
    candidate_counter = 0

    for _, row in selected_df.iterrows():
        source_id = f"row_{int(row.get('index', 0)):04d}"
        category = str(row.get(CATEGORY_COL, "")).strip()

        # Stage 3: injection check
        exc = stage3_injection_check(row, source_id, category)
        if exc is not None:
            exclusions.append(exc)
            continue

        # Stage 4: column mapping
        candidate_counter += 1
        candidate_id = f"candidate_{candidate_counter:03d}"
        result = stage4_extract(row, candidate_id, category)

        if isinstance(result, ExclusionEntry):
            exclusions.append(result)
            candidate_counter -= 1  # id not consumed
        else:
            candidates.append(result)

    logger.info(
        "After gates: %d candidates included, %d excluded so far",
        len(candidates),
        len(exclusions),
    )

    # Stage 5: embed + index (or dry-run: just write JSONs)
    embedding_failures = stage5_index(
        candidates=candidates,
        pool_dir=args.pool_dir,
        chroma_dir=args.chroma_dir,
        dry_run=args.dry_run,
    )
    exclusions.extend(embedding_failures)

    # Remove from candidates list any that failed embedding
    failed_ids = {e.source_id for e in embedding_failures}
    final_candidates = [c for c in candidates if c.id not in failed_ids]

    total_included = len(final_candidates)
    total_excluded = len(exclusions)

    # Write exclusion log
    log = ExclusionLog(
        total_source=total_source,
        total_selected=total_selected,
        total_included=total_included,
        total_excluded=total_excluded,
        exclusions=exclusions,
    )
    write_exclusion_log(log, args.exclusions)

    # Consistency check
    assert total_selected == total_included + total_excluded, (
        f"Totals inconsistent: selected={total_selected}, "
        f"included={total_included}, excluded={total_excluded}"
    )

    # Pool size gate
    if total_included < args.min_pool_size:
        logger.error(
            "Pool too small: %d candidates included, minimum is %d. "
            "Review exclusions.json for details.",
            total_included,
            args.min_pool_size,
        )
        sys.exit(1)

    logger.info(
        "Pipeline complete: %d candidates in pool, %d excluded. Pool: %s — Exclusions: %s",
        total_included,
        total_excluded,
        args.pool_dir,
        args.exclusions,
    )


if __name__ == "__main__":
    main()
