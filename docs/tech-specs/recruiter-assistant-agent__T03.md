# Tech Spec: "About this dataset" Transparency View — T03

> **SPEC:** [`docs/spec/recruiter-assistant-agent.md`](../spec/recruiter-assistant-agent.md)
> **Plan:** [`docs/plans/recruiter-assistant-agent.md`](../plans/recruiter-assistant-agent.md) — task `T03`
> **Conventions applied:** `CLAUDE.md` (project) + global `patterns.md`, `architecture.md`, `anti-patterns.md`
>
> This document details **how** to deliver T03. The **why** lives in the SPEC; **what** and **in what order**, in the Plan.

---

## Task Scope

- **Behavior delivered:** From any screen, a visitor can open "About this dataset" and see the active pool size (49 candidates) and the full exclusion log (CV identifier, category, reason) produced at build time. The entry point is the header link already rendered by T02's `DatasetLink` component.
- **SPEC stories/criteria covered:** Story 5; Scenario "Visitor inspects dataset transparency"; Non-negotiable principle "Dataset quality is surfaced, never silenced"; Experience Design — "About this dataset" entry point remains visible from empty and success states.
- **Depends on:** T01 — `data/exclusions.json` (confirmed present: `total_included: 49`, `total_excluded: 1`). T02 — existing `DatasetLink`, `App.tsx`, frontend scaffold.
- **External dependencies:** None.

---

## Architecture

```
Visitor browser (React SPA)
  │
  │  clicks "About this dataset" (DatasetLink → button)
  ▼
DatasetModal opens (App.tsx state: isDatasetOpen)
  │
  │  useDatasetInfo() TanStack Query useQuery (staleTime: Infinity)
  │  GET /dataset
  ▼
FastAPI — backend/src/main.py
  │
  │  dataset_router.get("/dataset")
  ▼
features/dataset/router.py
  reads DATA_DIR / "exclusions.json" (module-level singleton, read once)
  → DatasetInfo (Pydantic)
  ▼
HTTP 200 | 500
```

### New files

| File | Purpose |
|---|---|
| `backend/src/features/dataset/__init__.py` | package marker |
| `backend/src/features/dataset/schemas.py` | `ExclusionEntry` + `DatasetInfo` Pydantic models |
| `backend/src/features/dataset/router.py` | `GET /dataset` — reads `exclusions.json`, module-level singleton |
| `backend/tests/dataset/__init__.py` | package marker |
| `backend/tests/dataset/test_dataset.py` | FastAPI TestClient integration tests |
| `frontend/src/features/dataset/types.ts` | TypeScript interfaces mirroring backend schemas |
| `frontend/src/features/dataset/api.ts` | `useDatasetInfo()` — TanStack Query `useQuery` |
| `frontend/src/features/dataset/components/DatasetModal.tsx` | modal dialog with pool info, focus trap, Escape handler |
| `frontend/src/features/dataset/components/__tests__/DatasetModal.test.tsx` | Vitest component tests |

### Changed files

| File | Change |
|---|---|
| `backend/src/main.py` | `include_router(dataset_router)` |
| `frontend/src/components/DatasetLink.tsx` | `<a>` → `<button>` with `onOpen: () => void` prop |
| `frontend/src/components/__tests__/DatasetLink.test.tsx` | update test: click fires `onOpen` |
| `frontend/src/App.tsx` | `isDatasetOpen` state + `DatasetModal` rendering |

> **Decision source:** Feature-first per global `architecture.md`. `features/dataset/` is a distinct business domain (transparency, not ranking). No shared components yet — `DatasetModal` stays in its own feature folder until a second feature needs it.

---

## Contracts

### API endpoint

```
GET /dataset

Response 200 — success:
{
  "total_source": 9544,
  "total_selected": 50,
  "total_included": 49,
  "total_excluded": 1,
  "exclusions": [
    {
      "source_id": "3054",
      "category": "Network Support Engineer",
      "reason": "no_skills"
    }
  ]
}

Response 500 — file missing or unreadable:
{
  "detail": "Dataset info unavailable"
}
```

CORS: inherited from `main.py` middleware — no changes needed.

### Backend schemas — `backend/src/features/dataset/schemas.py`

```python
from pydantic import BaseModel

class ExclusionEntry(BaseModel):
    source_id: str
    category: str
    reason: str   # string, not enum — see Trade-offs

class DatasetInfo(BaseModel):
    total_source: int
    total_selected: int
    total_included: int
    total_excluded: int
    exclusions: list[ExclusionEntry]
```

### Backend router — `backend/src/features/dataset/router.py`

```python
import json
from fastapi import APIRouter, HTTPException
from src.features.dataset.schemas import DatasetInfo
from src.lib.vectorstore.chroma import DATA_DIR

router = APIRouter()

_dataset_info: DatasetInfo | None = None

@router.get("/dataset", response_model=DatasetInfo)
def get_dataset() -> DatasetInfo:
    global _dataset_info
    if _dataset_info is None:
        path = DATA_DIR / "exclusions.json"
        try:
            _dataset_info = DatasetInfo.model_validate_json(path.read_text())
        except Exception:
            raise HTTPException(status_code=500, detail="Dataset info unavailable")
    return _dataset_info
```

Module-level singleton — same pattern as `get_collection()` in `lib/vectorstore/chroma.py`. `exclusions.json` is baked at build time and never changes at runtime, so reading once is correct.

### Wire router — `backend/src/main.py` addition

```python
from src.features.dataset.router import router as dataset_router
# add after existing imports, before app = FastAPI(...)
# then:
app.include_router(dataset_router)
```

The router carries no prefix — `GET /dataset` matches the established flat API pattern (same as `POST /rank`).

### Frontend types — `frontend/src/features/dataset/types.ts`

```typescript
export interface ExclusionEntry {
  source_id: string;
  category: string;
  reason: string;
}

export interface DatasetInfo {
  total_source: number;
  total_selected: number;
  total_included: number;
  total_excluded: number;
  exclusions: ExclusionEntry[];
}
```

### Frontend API hook — `frontend/src/features/dataset/api.ts`

```typescript
import { useQuery } from '@tanstack/react-query';
import type { DatasetInfo } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export function useDatasetInfo() {
  return useQuery<DatasetInfo>({
    queryKey: ['dataset'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/dataset`);
      if (!res.ok) throw new Error('Failed to load dataset info');
      return res.json();
    },
    staleTime: Infinity,
  });
}
```

`staleTime: Infinity` — the exclusion log is baked at build time and never mutates at runtime. Refetching on window focus would be pointless. See Trade-offs.

### Frontend modal — `frontend/src/features/dataset/components/DatasetModal.tsx`

```typescript
import { useEffect, useRef } from 'react';
import { useDatasetInfo } from '../api';

export function DatasetModal({ onClose }: { onClose: () => void }) {
  const { data, isLoading, isError } = useDatasetInfo();
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeButtonRef.current?.focus();

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    // backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      {/* panel — stop propagation so clicks inside don't close */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dataset-title"
        className="relative w-full max-w-lg rounded-lg bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 id="dataset-title" className="text-base font-semibold text-gray-900">
            About this dataset
          </h2>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            aria-label="Close dataset info"
            className="rounded p-1 text-gray-500 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            ✕
          </button>
        </div>

        {isLoading && (
          <p className="text-sm text-gray-500">Loading dataset info…</p>
        )}

        {isError && (
          <p className="text-sm text-red-600">
            Dataset info is temporarily unavailable.
          </p>
        )}

        {data && (
          <div className="space-y-4 text-sm text-gray-700">
            <div className="flex gap-8">
              <div>
                <p className="text-2xl font-bold text-gray-900">{data.total_included}</p>
                <p className="text-xs text-gray-500 mt-0.5">active candidates</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{data.total_excluded}</p>
                <p className="text-xs text-gray-500 mt-0.5">excluded during preparation</p>
              </div>
            </div>

            {data.exclusions.length > 0 && (
              <div>
                <p className="font-medium text-gray-900 mb-2">Exclusion log</p>
                <ul className="divide-y divide-gray-100 border border-gray-100 rounded-md overflow-hidden">
                  {data.exclusions.map((e) => (
                    <li key={e.source_id} className="px-3 py-2 bg-gray-50">
                      <span className="font-mono text-xs text-gray-500 mr-2">
                        {e.source_id}
                      </span>
                      <span className="text-gray-700">{e.category}</span>
                      <span className="ml-2 inline-block rounded bg-red-50 px-1.5 py-0.5 text-xs text-red-700">
                        {e.reason}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <p className="text-xs text-gray-400">
              Source: {data.total_source.toLocaleString()} CVs sampled from a public Kaggle resume dataset.
              {data.total_selected} were selected for processing; {data.total_included} passed all gates.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
```

**Focus management:** On mount, focus goes to the close button (the only interactive element). Escape closes. Backdrop click closes. Click inside the panel does not close (event propagation stopped). No Tab-trap needed — a single focusable element never traps focus against itself.

### Updated DatasetLink — `frontend/src/components/DatasetLink.tsx`

```typescript
export function DatasetLink({ onOpen }: { onOpen: () => void }) {
  return (
    <button
      onClick={onOpen}
      className="text-xs text-indigo-600 underline underline-offset-2 hover:text-indigo-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded"
    >
      About this dataset
    </button>
  );
}
```

### Updated App.tsx additions

```typescript
// new state:
const [isDatasetOpen, setIsDatasetOpen] = useState(false);

// in header, replace current DatasetLink usage:
<DatasetLink onOpen={() => setIsDatasetOpen(true)} />

// at end of return, before closing </div>:
{isDatasetOpen && <DatasetModal onClose={() => setIsDatasetOpen(false)} />}
```

Import `DatasetModal` from `'./features/dataset/components/DatasetModal'`.

---

## Data Model

### `DatasetInfo` field reference

| Field | Type | Source | Notes |
|---|---|---|---|
| `total_source` | `int` | `exclusions.json` | Total rows in raw Kaggle CSV (9544) |
| `total_selected` | `int` | `exclusions.json` | After diverse sampling gate (50) |
| `total_included` | `int` | `exclusions.json` | Passed all pipeline gates (49) |
| `total_excluded` | `int` | `exclusions.json` | Failed at least one gate (1) |
| `exclusions` | `list[ExclusionEntry]` | `exclusions.json` | Per-CV exclusion records |

### `ExclusionEntry` field reference

| Field | Type | Notes |
|---|---|---|
| `source_id` | `str` | Kaggle CSV row index as bare integer string (e.g. `"3054"`) — matches T01 deviation |
| `category` | `str` | Job category from `job_position_name` column |
| `reason` | `str` | One of: `parse_failed`, `no_text`, `injection_detected`, `extraction_failed`, `no_skills` |

> The `source_id` format is bare integer strings, not `"row_NNNN"` — this is the T01 deviation documented in `recruiter-assistant-agent__T01.md § Deviations`.

---

## External Integrations

None. T03 reads a local file baked into the Docker image. No external API calls.

---

## Trade-offs and Rejected Alternatives

**Decision: Modal triggered by button (not hash-scroll or route)**
- Rejected: hash-scroll section (`href="#dataset"`, scroll to anchor at bottom of page)
- Rejected: React Router route (`/dataset`)
- Reason: Modal requires no new dependency (React Router was not in CLAUDE.md locked decisions) and no layout restructure. A hash-scroll section requires the section to be present in the DOM at all times and makes the layout more complex (the dataset view competes for space with the shortlist). Modal is the established pattern for secondary information in SPAs. User decision, Round 1.

**Decision: `reason` as `str` in `features/dataset/schemas.py`, not `ExclusionReason` enum**
- Rejected: import `ExclusionReason` from `scripts/schemas.py`
- Reason: `scripts/` is build-time code living outside `backend/`. Importing it at runtime violates the build-time/runtime split specified in `CLAUDE.md` ("Build-time (`scripts/prepare_dataset.py`) runs once, locally or in CI [...] Runtime (`backend/`) never ingests new CVs"). The values stored in `exclusions.json` were already validated at build time; runtime string validation is sufficient.

**Decision: `staleTime: Infinity` on `useDatasetInfo()` query**
- Rejected: default TanStack Query staleTime (0 — marks as stale immediately, refetches on window focus)
- Reason: `exclusions.json` is baked into the Docker image and never mutated at runtime. Refetching on window focus would trigger unnecessary API calls with no value. `Infinity` is semantically correct: the data is immutable for the lifetime of a deployed container.
- Source: TanStack Query docs — `staleTime: Infinity` is the documented pattern for static data.

**Decision: Module-level singleton for `DatasetInfo` in backend router**
- Rejected: `path.read_text()` on every request
- Reason: Same pattern as `get_collection()` in `chroma.py` (T01). `exclusions.json` is static. Reading from disk on every call adds I/O with no benefit. Singleton eliminates this cleanly.
- Source: Existing pattern in `backend/src/lib/vectorstore/chroma.py`.

**Decision: `GET /dataset` on FastAPI backend (not a static file served from frontend `public/`)**
- Rejected: copy `data/exclusions.json` into `frontend/public/exclusions.json` at build time; fetch as `/exclusions.json`
- Reason: Avoids a manual build-time copy step; no two copies of the file; consistent with established API pattern (`POST /rank`); TanStack Query loading/error states are already wired for API calls. User decision, Round 1.

**Decision: No Tab focus trap in modal**
- Rejected: full Tab/Shift-Tab focus cycle trap (first → last → first)
- Reason: The modal's panel contains exactly one focusable element (the close button). A Tab trap on a single-element modal is vacuous — Tab cycles nowhere. If future content adds more focusable elements (a scrollable list with interactive items), a trap can be added then. CLAUDE.md: "Don't design for hypothetical future requirements."

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `exclusions.json` absent from Docker image (e.g. build step skipped) | `GET /dataset` returns 500; modal shows error | Error state in `DatasetModal` displays "Dataset info temporarily unavailable." instead of crashing. Backend 500 is caught by TanStack Query's `isError`. |
| `DatasetInfo` singleton cached with stale data after redeploy | Old exclusion log served until next cold start | Acceptable for a portfolio demo: Cloud Run creates a new container on each deploy. No long-running process retains the old singleton. |
| Modal not closed when visitor navigates with browser back | Modal stays open unexpectedly | Not applicable: the SPA has no router and no browser-history navigation. `popstate` events are not triggered. |
| `exclusions.json` contains a very large number of excluded CVs | Modal list is long | Acceptable: pool is capped at ≤50 CVs (SPEC ceiling), so exclusions can never exceed ~50 entries. No pagination needed. |

---

## Testing Plan

### Backend — `backend/tests/dataset/test_dataset.py`

Uses FastAPI `TestClient`. Mocks `DATA_DIR` via `monkeypatch`.

**Happy path:**
- `GET /dataset` with valid `exclusions.json` present → HTTP 200, body parses to `DatasetInfo`, `total_included == 49`, `exclusions` list has one entry with `source_id == "3054"`, `reason == "no_skills"`

**Error path:**
- `GET /dataset` when `DATA_DIR / "exclusions.json"` does not exist → HTTP 500, `detail == "Dataset info unavailable"`

**Singleton behavior:**
- Two consecutive `GET /dataset` calls → file is read only once (mock `path.read_text` called once; assert `call_count == 1`)

> **Note:** The singleton is module-level global. Tests that verify singleton behavior must reset `_dataset_info = None` between test runs via monkeypatch or by re-importing the module. Prefer `monkeypatch.setattr("src.features.dataset.router._dataset_info", None)` to reset between tests.

### Frontend — `frontend/src/features/dataset/components/__tests__/DatasetModal.test.tsx`

Uses Vitest + Testing Library. TanStack Query `QueryClientProvider` must wrap the component under test.

**Loading state:**
- While `useDatasetInfo` is pending → renders "Loading dataset info…" text

**Success state:**
- `useDatasetInfo` resolves with fixture data → renders `total_included` count, `total_excluded` count, exclusion list with `source_id` + `category` + `reason`

**Error state:**
- `useDatasetInfo` rejects → renders "Dataset info is temporarily unavailable." text

**Close via button:**
- Click close button → `onClose` called once

**Close via Escape:**
- `fireEvent.keyDown(document, { key: 'Escape' })` → `onClose` called once

**Close via backdrop:**
- Click backdrop (the outer overlay div) → `onClose` called once

**No close on panel click:**
- Click inside the panel `role="dialog"` element → `onClose` NOT called

### Frontend — `DatasetLink.test.tsx` update

- Click the button → `onOpen` callback fires (replacing the old link-renders test)

> **Framework:** Vitest + Testing Library. Source: existing test pattern in `frontend/src/features/ranking/components/__tests__/`.

---

## Implementation Sequence

Each step is a cohesive commit. Prerequisites: T01 artifacts exist (`data/exclusions.json`), T02 frontend scaffold exists (`App.tsx`, `DatasetLink.tsx`, `features/ranking/`).

1. **Backend schemas** — `backend/src/features/dataset/__init__.py` + `schemas.py` (`ExclusionEntry`, `DatasetInfo`)
2. **Backend router** — `backend/src/features/dataset/router.py` with `GET /dataset` + module-level singleton
3. **Wire router** — add `from src.features.dataset.router import router as dataset_router` + `app.include_router(dataset_router)` to `backend/src/main.py`
4. **Backend tests** — `backend/tests/dataset/__init__.py` + `test_dataset.py` (happy path, 500, singleton); run `uv run --directory backend pytest tests/dataset` — must pass
5. **Frontend types** — `frontend/src/features/dataset/types.ts` (`ExclusionEntry`, `DatasetInfo`)
6. **Frontend API hook** — `frontend/src/features/dataset/api.ts` (`useDatasetInfo()` with `staleTime: Infinity`)
7. **DatasetModal component** — `frontend/src/features/dataset/components/DatasetModal.tsx` with focus-on-mount, Escape handler, backdrop close, loading/error/success states
8. **DatasetModal tests** — `frontend/src/features/dataset/components/__tests__/DatasetModal.test.tsx` (all 7 cases above); run `pnpm test` — must pass
9. **Update DatasetLink** — change `<a href="#dataset">` → `<button onClick={onOpen}>` in `DatasetLink.tsx`; update its test
10. **Wire into App.tsx** — add `isDatasetOpen` state + `DatasetModal` rendering; pass `onOpen` to `DatasetLink`
11. **Smoke test** — run `uv run --directory backend uvicorn src.main:app --reload` + `pnpm dev`; click "About this dataset"; confirm modal shows "49 active candidates", "1 excluded during preparation", exclusion entry for `3054 / Network Support Engineer / no_skills`; confirm Escape closes; confirm `curl http://localhost:8000/dataset` returns correct JSON

---

## Conventions Applied (from CLAUDE.md)

- **Python tooling:** uv, ruff, pytest — per CLAUDE.md locked decisions
- **LiteLLM / LangGraph:** not involved in T03 — transparency view reads a static file only
- **FastAPI `APIRouter`:** registers `GET /dataset` without prefix, consistent with the flat `POST /rank` pattern in `main.py`
- **Architecture:** feature-first per global `architecture.md`; `features/dataset/` is a new domain folder — justified because the dataset transparency feature is distinct from ranking and has its own data model, API endpoint, and UI components
- **Frontend tooling:** pnpm, Vite, Tailwind, TanStack Query v5 (`useQuery`), Vitest — per CLAUDE.md locked decisions and global `patterns.md`
- **No new libraries:** `fastapi`, `pydantic` already in `pyproject.toml`; `@tanstack/react-query`, `tailwindcss`, React already installed
- **Build-time/runtime split:** `scripts/schemas.py` is not imported by backend runtime code — `reason` is typed as `str` in `features/dataset/schemas.py` — per CLAUDE.md "Build-time vs. runtime split" section
- **Language:** all identifiers, comments, and strings in English — per global `language.md`
- **No comments explaining what:** inline comments omitted; identifiers are self-describing

---

## Ready to Code?

- [x] Architecture described with all modules and new files named
- [x] Contracts (endpoint, Pydantic schemas, frontend types, hook, component interface) in final form
- [x] Data model with types, field-by-field notes, and T01 deviation accounted for (`source_id` format)
- [x] All non-trivial decisions have a rejected alternative documented (modal vs. scroll/route, str vs. enum, staleTime, singleton, no Tab trap)
- [x] Known risks listed with mitigations (missing file, singleton staleness, large exclusion list)
- [x] Testing plan covers happy path + 2 backend error cases + 6 frontend modal cases (loading, success, error, Escape, close button, backdrop)
- [x] Implementation sequence is executable without clarification questions (11 steps, each a cohesive commit)
- [x] No new library introduced without explicit rationale
- [x] CLAUDE.md conventions cited and respected
- [x] T01 deviation cited: `source_id` is bare integer string, not `"row_NNNN"`
