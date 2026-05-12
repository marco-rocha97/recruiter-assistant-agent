# Recruiter Assistant Agent

A LangGraph-based candidate-screening agent, shipped as a public portfolio demo.

A visitor pastes a job description as plain text and receives a ranked shortlist with per-candidate matched/missing requirements and resume evidence, scored against a fixed candidate pool baked into the build.

---

## What this is

A **portfolio demo**, not a production product. The candidate pool is a fixed public Kaggle CV dataset prepared once at build time. Visitors interact with the live app by submitting a job description only — they never upload candidate data.

The product framing ("recruiter", "shortlist") describes the real problem the demo simulates, so a reviewer can judge engineering and product judgment from a working end-to-end interaction.

---

## Architecture

### Build-time vs. runtime split

```
Build time (scripts/prepare_dataset.py)
  Kaggle CSV → diverse sample → injection check → column mapping → Gemini embed → Chroma index
  Outputs: data/pool/*.json  data/exclusions.json  data/chroma/

Runtime (backend — FastAPI + LangGraph, not yet built)
  POST /rank  ←  JD text (plain)
              →  ranked shortlist with matched/missing requirements + resume evidence
```

Build-time artifacts are committed to the repo and baked into the Docker image. The runtime server never ingests new CVs and never writes to the pool.

### Repo layout

```
backend/                       # FastAPI app — deployed to GCP Cloud Run
  src/
    lib/
      guardrails/injection.py  # rule-based injection classifier (shared T01+T02)
      llm/client.py            # LiteLLM wrapper: complete() + embed()
  tests/
    guardrails/
      test_injection.py        # unit + fixture regression tests
      fixtures/injection_payloads.jsonl
  pyproject.toml               # uv-managed; single Python project for backend + scripts

scripts/
  prepare_dataset.py           # 5-stage build-time pipeline
  schemas.py                   # Pydantic schemas for pool artifacts
  tests/
    test_prepare_dataset.py    # integration tests with mocked LiteLLM

data/
  pool/                        # 49 candidate JSON files (committed, baked into image)
  exclusions.json              # audit log (committed, exposed in transparency view)
  chroma/                      # Chroma persistent index (committed, baked into image)
  source/                      # gitignored — raw Kaggle CSV

docs/
  spec/recruiter-assistant-agent.md
  plans/recruiter-assistant-agent.md
  tech-specs/recruiter-assistant-agent__T01.md
```

---

## Stack

| Concern | Choice | Why |
|---|---|---|
| Backend | FastAPI on GCP Cloud Run | Matches existing stack; scales to zero; free tier |
| Frontend | React + Vite on Firebase Hosting | Static; free; stays inside GCP |
| Vector store | Chroma, local file baked into container | Built once; zero runtime infra; fits ~50 CVs |
| LLM access | LiteLLM — Gemini primary, OpenAI fallback | Free-tier-first; single vendor via one interface |
| Agent framework | LangGraph | Required by the brief; WS3 stack item |
| Tracing | Langfuse (wired up when MVP ships) | WS3 stack item; not a blocker |
| Python tooling | uv + ruff + pytest | 2026 default |
| Frontend tooling | pnpm + Vitest + Tailwind + TanStack Query | Per global patterns |

---

## Dataset preparation (T01 — complete)

The pipeline runs once before each Docker image build and produces the three committed artifacts above.

### Stages

```
Stage 1 — Load      CSV → validate columns (job_position_name, skills)
Stage 2 — Sample    diverse selection: up to 3 CVs per job category, capped at 50
Stage 3 — Check     rule-based injection classifier on concatenated CV text
Stage 4 — Extract   direct column mapping → ParsedCandidate (no LLM call)
Stage 5 — Index     Gemini embedding → Chroma upsert + write pool JSON
```

### Current pool stats (from exclusions.json)

| Metric | Count |
|---|---|
| Source rows in Kaggle CSV | 9,544 |
| Rows after diverse sampling | 50 |
| Candidates included in pool | 49 |
| Candidates excluded | 1 (`no_skills`) |

### Run it

Download the [Kaggle Resume Dataset](https://www.kaggle.com/datasets/saugataroyarghya/resume-dataset/data) to `data/source/Resume.csv`, then:

```bash
# Validate Stages 1–4 without an API key
uv run --directory backend python ../scripts/prepare_dataset.py \
  --source ../data/source/Resume.csv \
  --pool-dir ../data/pool \
  --chroma-dir ../data/chroma \
  --exclusions ../data/exclusions.json \
  --pool-size 50 \
  --dry-run

# Full pipeline (requires GEMINI_API_KEY — writes Chroma index)
uv run --directory backend python ../scripts/prepare_dataset.py \
  --source ../data/source/Resume.csv \
  --pool-dir ../data/pool \
  --chroma-dir ../data/chroma \
  --exclusions ../data/exclusions.json \
  --pool-size 50
```

### Pool artifact format

`data/pool/candidate_001.json`:
```json
{
  "id": "candidate_001",
  "category": "Senior iOS Engineer",
  "skills": ["Python", "Machine Learning", "SQL"],
  "experience": [{"title": "Data Scientist", "company": "Acme Corp", "duration_months": 24}],
  "education": [{"degree": "B.Sc. Computer Science", "institution": "State University", "year": 2019}],
  "summary": "..."
}
```

PII fields (`name`, `email`, `phone`, `address`, `gender`, `age`, `photo`) are absent by schema design — they are never extracted, stored, or passed to any LLM call.

---

## Security guardrails

### Injection classifier (`backend/src/lib/guardrails/injection.py`)

A rule-based regex classifier applied at two points:

1. **Build time (T01):** every CV's concatenated text is checked before extraction. Positive → excluded with `injection_detected` in `exclusions.json`.
2. **Request time (T02, pending):** incoming JD text is checked before the ranking graph runs.

The classifier is deterministic and reproducible. A regression fixture set (`backend/tests/guardrails/fixtures/injection_payloads.jsonl`) locks 10+ known injection payloads — this suite must stay green.

### Prompt construction (`backend/src/lib/llm/client.py`)

- System and user content are always passed as separate messages, never concatenated.
- Any LLM call that consumes untrusted text wraps it in delimited `<resume>` or `<jd>` fences.
- Responses are validated against Pydantic schemas — any schema violation is rejected, never auto-repaired.

---

## Running tests

```bash
cd backend

# Injection classifier unit tests + fixture regression
uv run pytest tests/guardrails

# Dataset pipeline integration tests (LiteLLM mocked)
uv run pytest ../scripts/tests

# All tests
uv run pytest tests/ ../scripts/tests/

# Lint + format
uv run ruff check . && uv run ruff format .
```

---

## Environment

```bash
# Required for Stage 5 embedding and T02 ranking
GEMINI_API_KEY=...

# Fallback for completion calls if Gemini quota is exhausted
OPENAI_API_KEY=...
```

Copy `.env.example` to `.env` (gitignored). Never commit API keys.

---

## Task status

| # | Task | Phase | Status |
|---|---|---|---|
| T01 | Build-time dataset preparation | MVP | **complete** |
| T02 | JD submission → ranked shortlist with explainability | MVP | pending |
| T03 | "About this dataset" transparency view | MVP | pending |
| T04 | Recruiter override (shortlist / reject) | Phase 2 | pending |
| T05 | Agreement-rate evaluation harness (≥ 80%) | Phase 2 | pending |

MVP = T01 + T02 + T03. The demo is shippable once all three are done.

---

## Non-negotiable product rules

- **No demographic ranking signals.** Gender, age, photo, and home address never reach any LLM prompt. Enforced by schema absence at build time.
- **Explainability per ranking.** Every shortlist row carries the resume evidence behind it. No black-box scores.
- **Recruiter is decision-maker.** The agent ranks and recommends; it never auto-rejects candidates.
- **Dataset transparency.** The exclusion log ships as a committed artifact and is exposed in the "About this dataset" view — nothing is silently dropped.

---

## Docs

- [SPEC](docs/spec/recruiter-assistant-agent.md) — problem, user stories, acceptance criteria
- [Plan](docs/plans/recruiter-assistant-agent.md) — task map and sequencing
- [Tech Spec T01](docs/tech-specs/recruiter-assistant-agent__T01.md) — dataset preparation implementation details
