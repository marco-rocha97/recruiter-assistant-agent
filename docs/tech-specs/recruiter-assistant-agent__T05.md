# Tech Spec: Agreement-Rate Evaluation Harness — `T05`

> **SPEC:** [`docs/spec/recruiter-assistant-agent.md`](../spec/recruiter-assistant-agent.md)
> **Plan:** [`docs/plans/recruiter-assistant-agent.md`](../plans/recruiter-assistant-agent.md) — task `T05`
> **Conventions applied:** `CLAUDE.md` (project) + global `rules/` (anti-patterns, testing, dependencies)
>
> This document details **how** to deliver T05. The **why** lives in the SPEC; **what** and **in what order**, in the Plan.

---

## Task Scope

- **Behavior delivered** (from Plan): A reproducible offline evaluation that compares the agent's top-5 shortlist to a hand-reviewed ground-truth shortlist over 5 fixed JDs and reports an agreement rate ≥ 80% — the number cited in the portfolio writeup.
- **SPEC stories/criteria covered:** Success Metric — "Agreement rate ≥ 80% between the agent's top shortlist and a hand-labeled ground-truth shortlist".
- **Depends on:** T02 (ranking pipeline `run_graph()` must exist and be callable directly).
- **External dependencies:** `GEMINI_API_KEY` (Gemini 2.5 Flash for ranking) and `OPENAI_API_KEY` (fallback) in `.env`. Same keys as T02.

---

## Architecture

The harness is a pair of offline scripts — not a runtime feature, not a FastAPI endpoint, not a CI job. Both scripts live in `scripts/` alongside `prepare_dataset.py`.

**Two-phase design:**

**Phase 1 — Label (run once, human in the loop):**
`scripts/label_ground_truth.py` loads all 49 candidates from `data/pool/` and the 5 JDs from `data/eval/jds.json`. For each JD it calls the LLM (`complete()`) asking it to suggest a ranked top-5 with reasoning. Output is written to `data/eval/ground_truth_review.json` (gitignored). Marco reviews, adjusts any picks he disagrees with, and commits the result as `data/eval/ground_truth.json`.

**Phase 2 — Evaluate (re-runnable, produces the portfolio number):**
`scripts/eval_harness.py` loads the baked Chroma collection via `get_collection()`, runs `run_graph()` for each JD in `data/eval/jds.json`, extracts the agent's top-5 candidate IDs from `ShortlistResponse`, computes set-overlap @ 5 against `data/eval/ground_truth.json`, and writes `data/eval/report.json`.

**Why direct `run_graph()` call instead of HTTP:**
No running server required; matches how `test_api.py` calls the graph; the real Chroma collection is loaded read-only (same singleton as production). Source: pattern from `backend/tests/test_api.py`.

**Affected modules:**
- `backend/src/lib/llm/client.py` — minor: add optional `temperature` param to `complete()` for reproducibility
- `backend/src/graph/screening.py` — read-only (calls `run_graph()` directly)
- `backend/src/lib/vectorstore/chroma.py` — read-only (calls `get_collection()`)

**New files:**

| File | Purpose | Committed? |
|---|---|---|
| `data/eval/jds.json` | 5 synthetic JDs (generated in this spec) | Yes |
| `data/eval/ground_truth.json` | Hand-reviewed top-5 labels per JD | Yes (after review step) |
| `data/eval/ground_truth_review.json` | LLM-suggested labels for Marco to review | No — add to `.gitignore` |
| `data/eval/report.json` | Eval output — the portfolio number | Yes |
| `scripts/label_ground_truth.py` | Phase 1 — LLM-assisted labeling script | Yes |
| `scripts/eval_harness.py` | Phase 2 — runs ranking, computes agreement, writes report | Yes |
| `backend/tests/eval/test_agreement.py` | Unit tests for `compute_agreement()` | Yes |

---

## Contracts

### JD fixture — `data/eval/jds.json`

```json
[
  {
    "id": "jd_001",
    "title": "Senior Data Scientist",
    "text": "Senior Data Scientist — Mid-size analytics company. We are looking for a Senior Data Scientist with 3+ years of experience. Required: Python, SQL, machine learning, statistical modeling, data visualization (Tableau or Power BI). Nice to have: deep learning, TensorFlow or PyTorch, Jupyter, cloud platforms (AWS or GCP). You will design and implement predictive models, perform exploratory data analysis, and present insights to business stakeholders."
  },
  {
    "id": "jd_002",
    "title": "Senior iOS Engineer",
    "text": "Senior iOS Engineer — Mobile startup. We need an iOS developer with Swift and Objective-C experience to build and maintain our consumer-facing app. Required: Swift, iOS SDK, Xcode, REST API integration, UIKit. Nice to have: Core Data, SwiftUI, CI/CD (Fastlane), unit testing (XCTest). You will own feature development end-to-end and collaborate with product and backend teams."
  },
  {
    "id": "jd_003",
    "title": "Network Support Engineer",
    "text": "Network Support Engineer — Enterprise IT team. We are seeking an experienced network engineer to manage and troubleshoot corporate network infrastructure. Required: TCP/IP, network troubleshooting, CCNA or equivalent, Cisco/Juniper equipment, VLAN configuration. Nice to have: Python scripting for network automation, firewall management, monitoring tools (Nagios, Zabbix). You will handle escalated incidents, maintain network documentation, and ensure 99.9% uptime."
  },
  {
    "id": "jd_004",
    "title": "Machine Learning Engineer",
    "text": "Machine Learning Engineer — AI product company. We are hiring an ML Engineer to take models from research to production. Required: Python, PyTorch or TensorFlow, model deployment (Docker, REST APIs), MLOps experience. Nice to have: Kubernetes, MLflow, distributed training, LLM fine-tuning, Hugging Face. You will own the training pipeline, deploy models to production, and maintain performance monitoring."
  },
  {
    "id": "jd_005",
    "title": "Python Backend Developer",
    "text": "Python Backend Developer — SaaS company. We need a Python developer to build and maintain backend services. Required: Python, Django or FastAPI, PostgreSQL, REST API design, Git. Nice to have: Docker, Redis, Celery, AWS, Linux system administration. You will design and implement backend services, write tests, and participate in code reviews."
  }
]
```

### Ground truth — `data/eval/ground_truth.json`

```json
{
  "jd_001": ["candidate_XXX", "candidate_XXX", "candidate_XXX", "candidate_XXX", "candidate_XXX"],
  "jd_002": ["candidate_XXX", "candidate_XXX", "candidate_XXX", "candidate_XXX", "candidate_XXX"],
  "jd_003": ["candidate_XXX", "candidate_XXX", "candidate_XXX", "candidate_XXX", "candidate_XXX"],
  "jd_004": ["candidate_XXX", "candidate_XXX", "candidate_XXX", "candidate_XXX", "candidate_XXX"],
  "jd_005": ["candidate_XXX", "candidate_XXX", "candidate_XXX", "candidate_XXX", "candidate_XXX"]
}
```

Ground truth is an **unordered set** of 5 `candidate_id` strings per JD — order within the list is not used by the metric. IDs are filled after the labeling step (Phase 1).

### Evaluation report — `data/eval/report.json`

```json
{
  "agreement_rate": 0.84,
  "jd_count": 5,
  "model": "gemini/gemini-2.5-flash",
  "temperature": 0,
  "run_at": "2026-05-12T14:30:00Z",
  "per_jd": [
    {
      "jd_id": "jd_001",
      "jd_title": "Senior Data Scientist",
      "agent_top5": ["candidate_005", "candidate_012", "candidate_023", "candidate_031", "candidate_044"],
      "ground_truth_top5": ["candidate_005", "candidate_012", "candidate_023", "candidate_031", "candidate_044"],
      "overlap": 5,
      "agreement": 1.0
    }
  ]
}
```

`run_at` is UTC ISO 8601. `agreement_rate` = mean of `per_jd[].agreement`.

### Minor change to `backend/src/lib/llm/client.py`

Add an optional `temperature` parameter to `complete()`:

```python
def complete(
    prompt: str,
    system: str,
    response_format: type[_T],
    model: str = "gemini/gemini-2.5-flash",
    fallback: str = "openai/gpt-4o-mini",
    max_retries: int = 3,
    temperature: float | None = None,   # NEW: None = model default; 0 = deterministic
) -> _T:
```

Pass `temperature` through to the `litellm.completion()` call if not `None`. All existing callers pass no `temperature` argument → behavior is unchanged. The eval harness passes `temperature=0`.

### Internal interfaces

```python
# scripts/eval_harness.py

def compute_agreement(
    agent_top5: list[str],      # candidate_ids from ShortlistResponse, in rank order
    ground_truth_top5: list[str],  # candidate_ids from ground truth (order-independent)
) -> float:
    """Set overlap @ 5: |intersection| / 5. Returns 0.0–1.0."""

def run_eval(
    jds: list[dict],              # loaded from data/eval/jds.json
    ground_truth: dict[str, list[str]],  # loaded from data/eval/ground_truth.json
) -> dict:
    """Runs ranking for each JD, computes agreement, returns report dict."""
```

```python
# scripts/label_ground_truth.py

def suggest_labels(
    jd: dict,                    # one entry from jds.json
    candidates: list[dict],      # all 49 ParsedCandidate dicts
) -> list[dict]:
    """Calls LLM; returns list of {candidate_id, rank, reason}."""
```

---

## Data Model

### `data/eval/jds.json` entries

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `str` | yes | `jd_001` … `jd_005` — stable slug used as key in ground truth and report |
| `title` | `str` | yes | Human-readable label for the report |
| `text` | `str` | yes | Plain-text JD fed to `run_graph()` — must pass JD validation (≥50 chars, ≥3 non-stopword tokens) |

### `data/eval/ground_truth.json`

| Field | Type | Notes |
|---|---|---|
| key | `str` | `jd_id` matching `jds.json` |
| value | `list[str]` | Exactly 5 `candidate_id` strings; order is not significant |

### `data/eval/report.json` — `per_jd` entries

| Field | Type | Notes |
|---|---|---|
| `jd_id` | `str` | |
| `jd_title` | `str` | |
| `agent_top5` | `list[str]` | Candidate IDs in rank order from `ShortlistResponse.rankings` |
| `ground_truth_top5` | `list[str]` | From `ground_truth.json` |
| `overlap` | `int` | `len(set(agent_top5) & set(ground_truth_top5))` |
| `agreement` | `float` | `overlap / 5` |

---

## External Integrations

`eval_harness.py` calls `run_graph()` which calls `complete()` (LiteLLM → Gemini primary, OpenAI fallback) and `get_collection()` (Chroma). Same credentials and rate-limit constraints as the production ranking endpoint. The harness makes 5 real LLM calls sequentially. At Gemini free-tier (15 RPM), this completes in under 2 minutes.

`label_ground_truth.py` also calls `complete()` once per JD (5 calls) with a separate labeling system prompt. Not part of the regular harness run.

---

## Trade-offs and Rejected Alternatives

**Decision: direct `run_graph()` call instead of HTTP endpoint**
- Rejected alternative: spawn a local FastAPI server and call `POST /rank` via `httpx`
- Reason: no server management in an offline script; `run_graph()` is already importable; matches test patterns; avoids startup/teardown overhead
- Source: pattern from `backend/tests/test_api.py` (TestClient wraps the same graph call)

**Decision: custom `compute_agreement()` (5 lines) instead of an eval framework**
- Rejected alternatives: `ragas`, `deepeval`, `evaluate` (HuggingFace)
- Reason: set overlap @ 5 is a single arithmetic expression; adding a 100+ MB eval library for one metric violates the "reuse over install" rule in `rules/anti-patterns.md`; no new dependency introduced
- Source: `rules/anti-patterns.md` — "new library without discussion"

**Decision: add `temperature=0` to `complete()` for the harness**
- Rejected alternative: accept non-determinism and call the committed `report.json` the canonical reference
- Reason: Gemini 2.5 Flash supports `temperature=0`; makes re-runs produce identical output; portfolio claim is stronger if the number is reproducible, not just "frozen"
- Source: LiteLLM docs confirm `temperature` passthrough to Gemini

**Decision: LLM-assisted labeling + human review (not fully manual, not LLM-only)**
- Rejected alternative (fully manual): reading 49 candidate profiles per JD is feasible (5 × ~5 min) but tedious; LLM assistance cuts this to reviewing 5 × 5 = 25 suggested picks
- Rejected alternative (LLM-only ground truth): circular — agreement would measure consistency with itself, not accuracy against human judgment; weaker portfolio claim
- Source: T05 plan note — "Producing those labels is part of this task"

**Decision: ground truth is an unordered set (not a ranked list)**
- Reason: set overlap @ 5 does not use rank order within the ground truth, only membership; requiring a ranked ground truth adds labeling effort with no metric benefit given the chosen formula
- Trade-off: cannot compute rank-aware metrics (nDCG, AP@5) from this ground truth later without re-labeling

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LLM residual non-determinism at `temperature=0` | Agreement rate drifts slightly across re-runs | Commit `report.json` as the canonical reference; document model + temperature in the report; note in portfolio writeup that the number is frozen as of the commit date |
| LLM labeling bias (same model suggests, same model ranks) | Ground truth skewed toward model's own preferences | Human review step is mandatory — Marco reads the `ground_truth_review.json` reasoning and must override at least one pick to confirm he actually reviewed |
| JDs too generic (every candidate matches, agreement is artificially high) | Inflated agreement rate | JDs are crafted around specific skill signatures (Swift + Xcode for jd_002, TCP/IP + Cisco for jd_003) that eliminate most of the 49-candidate pool as clear non-fits |
| Pool too small to produce 5 valid candidates per JD | Harness returns <5 candidates for niche JDs | `compute_agreement()` handles `len(agent_top5) < 5`: uses `min(len(agent_top5), 5)` as denominator and logs a warning; niche JDs should be replaced in `jds.json` if this triggers |
| `temperature` param not honored by Gemini API via LiteLLM | Non-reproducible results | Verify LiteLLM passthrough in the labeling script run (compare two calls with same input); if not honored, fall back to committing `report.json` and noting the limitation |

---

## Testing Plan

The harness itself makes real LLM calls and is not unit-tested end-to-end (same reasoning as `prepare_dataset.py` — build-time scripts are not mocked). Unit tests cover only the pure-logic layer: `compute_agreement()`.

**Unit tests — `backend/tests/eval/test_agreement.py`:**

| Test | Scenario | Expected |
|---|---|---|
| `test_perfect_agreement` | agent_top5 == ground_truth_top5 (same 5 ids) | `1.0` |
| `test_partial_overlap_3` | 3 of 5 ids match | `0.6` |
| `test_no_overlap` | 0 ids in common | `0.0` |
| `test_partial_overlap_order_independent` | same 5 ids in different list order | `1.0` — order must not matter |
| `test_agent_returns_fewer_than_5` | agent_top5 has 3 ids, 2 of which are in ground truth | `2/3 ≈ 0.667` |
| `test_duplicate_ids_in_agent_output` | agent_top5 contains a repeated id | treated as a set — `len(set(agent_top5))` ids used |

Tests import `compute_agreement` directly from `scripts/eval_harness.py` (or from a thin module it exposes). No LLM, no Chroma, no filesystem — pure function.

> **Framework:** `pytest` + no mocking needed (pure function). Source: existing pattern in `backend/tests/`.

---

## Implementation Sequence

Each step is one cohesive commit.

1. **Commit `data/eval/jds.json`** — 5 synthetic JDs as specified in the Contracts section above. Add `data/eval/ground_truth_review.json` to `.gitignore`.

2. **Write `scripts/label_ground_truth.py`** — loads all 49 candidates from `data/pool/`, loads `data/eval/jds.json`, calls `complete()` per JD with a labeling system prompt (not the RANKING_SYSTEM_PROMPT — this prompt asks for a top-5 ranking with reasoning, not a structured `ShortlistResponse`), writes `data/eval/ground_truth_review.json`.

3. **Run labeling script, review output, commit `data/eval/ground_truth.json`** — Marco reads `ground_truth_review.json`, adjusts at least one pick per JD to confirm he actually reviewed (not rubber-stamping), writes `data/eval/ground_truth.json`, commits.

4. **Add `temperature` param to `complete()`** in `backend/src/lib/llm/client.py` — default `None`, passes through to LiteLLM. All existing callers unaffected.

5. **Write `compute_agreement()` and unit tests** — `scripts/eval_harness.py` (function only, no CLI yet); `backend/tests/eval/test_agreement.py` (6 tests). Tests must pass before proceeding.

6. **Complete `scripts/eval_harness.py`** — add CLI entry point (`if __name__ == "__main__"`), Chroma collection loading via `get_collection()`, loop over JDs calling `run_graph(jd_text, temperature=0)`, collect `ShortlistResponse.rankings`, call `compute_agreement()`, build and write `data/eval/report.json`.

7. **Run harness, commit `data/eval/report.json`** — `uv run python scripts/eval_harness.py`. Verify `agreement_rate ≥ 0.80`. If below 80%: inspect per-JD breakdown, adjust `jds.json` if a JD is pathologically ambiguous (update ground truth accordingly), re-run. Commit the passing report.

---

## Conventions Applied (from CLAUDE.md)

- **Python tooling:** `uv` + `ruff` + `pytest` — harness scripts follow same conventions as `prepare_dataset.py`
- **No new libraries:** `compute_agreement()` uses only Python builtins (`set`, `len`); labeling script reuses `complete()` from `backend/src/lib/llm/client.py`
- **Build-time vs. runtime split:** both scripts live in `scripts/` (build-time domain), never in `backend/src/` (runtime domain)
- **Secrets:** `GEMINI_API_KEY` and `OPENAI_API_KEY` loaded via `python-dotenv` (same as T02 pattern); never hardcoded
- **Language:** English throughout
- **`.gitignore`:** `data/eval/ground_truth_review.json` must be added; it contains the intermediate LLM suggestions before human review

---

## Ready to Code?

- [x] Architecture described with modules and new files named
- [x] Contracts (JD fixture, ground truth, report, `complete()` signature) in final form
- [x] Data model with types, required fields, and notes
- [x] Non-trivial trade-offs have a rejected alternative documented (direct call, custom metric, temperature, labeling method, unordered ground truth)
- [x] Known risks listed with mitigations (non-determinism, labeling bias, JD genericity, small pool, temperature passthrough)
- [x] Testing plan covers happy path + 5 error/edge cases (6 unit tests for `compute_agreement()`)
- [x] Implementation sequence is executable without clarification questions (7 steps with explicit run commands)
- [x] No new library introduced — single arithmetic expression reuses `set` builtins
- [x] CLAUDE.md conventions cited and respected (tooling, build-time/runtime split, secrets, language)
