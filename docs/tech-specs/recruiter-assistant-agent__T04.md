# Tech Spec: Recruiter Override (Shortlist / Reject) — T04

> **SPEC:** [`docs/spec/recruiter-assistant-agent.md`](../spec/recruiter-assistant-agent.md)
> **Plan:** [`docs/plans/recruiter-assistant-agent.md`](../plans/recruiter-assistant-agent.md) — task `T04`
> **Conventions applied:** `CLAUDE.md` (project) + global `patterns.md`, `architecture.md`, `anti-patterns.md`
>
> This document details **how** to deliver T04. The **why** lives in the SPEC; **what** and **in what order**, in the Plan.

---

## Task Scope

- **Behavior delivered:** After a ranked shortlist is produced, the visitor can mark any candidate as "shortlisted" or "rejected". The override persists across page refreshes (via `localStorage`). Clicking an active override button toggles it back to "no override". Submitting a new JD clears all overrides. The agent's original ranking is always visible alongside the override, preserving the audit trail the SPEC requires.
- **SPEC stories/criteria covered:** Story 3 ("override the agent's ranking"); Scenario "Recruiter overrides the agent"; Non-negotiable principle "The recruiter is always the decision-maker".
- **Depends on:** T02 — existing `App.tsx`, `Shortlist.tsx`, `CandidateRow.tsx`, `types.ts`, and the `useRankCandidates` mutation.
- **External dependencies:** None. T04 is a pure-frontend feature. No new backend endpoint is required; override state is browser-local.

---

## Architecture

T04 adds one new component and extends three existing files. No backend changes.

```
App.tsx
  overrides: OverrideMap          ← new state, initialised from localStorage
  handleOverride(id, status)      ← new handler, syncs to localStorage
  clears overrides on mutate()    ← existing mutation call site
  │
  ▼
Shortlist.tsx                     ← passes overrides + onOverride to each row
  │
  ▼
CandidateRow.tsx                  ← receives override: OverrideStatus | null
  │  shows override chip + original rank (always visible)
  │
  └─► OverrideControls.tsx        ← NEW: two toggle buttons (Shortlist / Reject)
```

### New files

| File | Purpose |
|---|---|
| `frontend/src/features/ranking/components/OverrideControls.tsx` | Two toggle buttons per candidate; handles aria-pressed and null-toggle logic |
| `frontend/src/features/ranking/components/__tests__/OverrideControls.test.tsx` | Vitest unit tests |

### Changed files

| File | Change |
|---|---|
| `frontend/src/features/ranking/types.ts` | Add `OverrideStatus` + `OverrideMap` |
| `frontend/src/features/ranking/components/CandidateRow.tsx` | Accept `override` + `onOverride` props; render override chip + `OverrideControls` |
| `frontend/src/App.tsx` | Add `overrides` state (localStorage-initialised), `handleOverride`, clear-on-new-JD |
| `frontend/src/features/ranking/components/__tests__/CandidateRow.test.tsx` | Add tests for override chip visibility |

> **Decision source:** Pure-frontend persistence matches CLAUDE.md locked decision (no user accounts, no multi-recruiter). `localStorage` was chosen over `useState`-only to give reviewers a persistent demo experience — see Trade-offs.

---

## Contracts

### Internal interfaces — `frontend/src/features/ranking/types.ts`

```typescript
// New additions — append to existing types.ts

export type OverrideStatus = 'shortlisted' | 'rejected';

// Absent key = no override applied. Never store null values.
export type OverrideMap = Record<string, OverrideStatus>;
```

`OverrideStatus` is the canonical vocabulary for overrides. `OverrideMap` keys are `candidate_id` strings matching `CandidateRanking.candidate_id`.

### `OverrideControls` component API

```typescript
// frontend/src/features/ranking/components/OverrideControls.tsx

interface OverrideControlsProps {
  current: OverrideStatus | null;
  onOverride: (status: OverrideStatus | null) => void;
}
```

`onOverride(null)` is called when the visitor clicks the currently-active button (toggle off). `onOverride` is already bound to a specific `candidate_id` by the parent — `OverrideControls` does not need to know the ID.

### `CandidateRow` extended API

```typescript
// Added to existing CandidateRowProps

override: OverrideStatus | null;
onOverride: (status: OverrideStatus | null) => void;
```

### `Shortlist` extended API

```typescript
// Added to existing ShortlistProps

overrides: OverrideMap;
onOverride: (candidateId: string, status: OverrideStatus | null) => void;
```

`Shortlist` maps `overrides[ranking.candidate_id] ?? null` to each row and binds `onOverride` to the candidate's ID before passing it down.

### `App.tsx` — override state and handler

```typescript
const STORAGE_KEY = 'recruiter_overrides';

const [overrides, setOverrides] = useState<OverrideMap>(() => {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
  } catch {
    return {};
  }
});

function handleOverride(candidateId: string, status: OverrideStatus | null): void {
  setOverrides(prev => {
    const next = { ...prev };
    if (status === null) {
      delete next[candidateId];
    } else {
      next[candidateId] = status;
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    return next;
  });
}
```

**Clear on new JD** — in the existing `mutation.mutate(jdText)` call site, add:

```typescript
setOverrides({});
localStorage.removeItem(STORAGE_KEY);
mutation.mutate(jdText);
```

---

## Data Model

| Field | Type | Lives in | Notes |
|---|---|---|---|
| `overrides` | `OverrideMap` | `App.tsx` state + `localStorage` | Keyed by `candidate_id`; absent key = no override |
| `STORAGE_KEY` | `'recruiter_overrides'` | `App.tsx` constant | Single localStorage slot; entire map serialised as JSON |

**Absence over null.** `OverrideMap` never stores `null` values — deleting the key is the canonical "no override" representation. This keeps the JSON in localStorage clean and makes the `?? null` fallback in `Shortlist` the single coercion point.

**No changes to pool data or API response.** `CandidateRanking` (from the backend) is untouched. Override state is always kept separate from server data.

---

## Component Behaviour

### `OverrideControls.tsx`

- Renders two buttons: **Shortlist** and **Reject** (in that order; Shortlist first is the positive action).
- Each button has `aria-pressed={current === status}` — standard toggle button pattern.
- Accessible label: `aria-label="Mark as shortlisted"` / `aria-label="Mark as rejected"` — required because the buttons may rely on icons in addition to text.
- **Toggle logic:**
  - `current = null` → clicking either button calls `onOverride(status)`.
  - `current = 'shortlisted'` → clicking Shortlist calls `onOverride(null)`; clicking Reject calls `onOverride('rejected')`.
  - `current = 'rejected'` → clicking Reject calls `onOverride(null)`; clicking Shortlist calls `onOverride('shortlisted')`.
- Keyboard: standard button focus and Enter/Space are inherited from `<button>` — no additional `onKeyDown` handler needed.

### `CandidateRow.tsx` changes

- **Override chip:** when `override` is non-null, render a small coloured chip beside the rank badge — green for `'shortlisted'`, red for `'rejected'`. Chip label matches the `OverrideStatus` value (e.g. "Shortlisted").
- **Original rank badge:** always visible regardless of override — SPEC requires the original ranking to remain visible for audit.
- **`OverrideControls`:** rendered below the row summary line (above `EvidencePanel` when expanded). Always visible — not gated on row expansion — because override actions are primary controls per the SPEC.

---

## Trade-offs and Rejected Alternatives

**Decision: `localStorage` over `useState`-only**
- Rejected: In-memory state only (`useState`).
- Reason: A portfolio reviewer may submit a JD, step away, and return to the same browser tab. Persisting overrides across refreshes shows deliberate UX care and reinforces the "recruiter is the decision-maker" product principle. The added cost is ~10 lines.
- Source: User decision, Round 1.

**Decision: Clear overrides on new JD, not keyed by JD fingerprint**
- Rejected: Key `localStorage` by `SHA-256(jd_text)` so the same JD restores its overrides.
- Reason: For a demo with one active session, simple is better — new JD = fresh evaluation. Fingerprinting adds a crypto import, a collision-avoidance concern, and a stale-data scenario where stale overrides from a previous session confuse the visitor. User decision, Round 1.

**Decision: Absent key = no override (never store `null`)**
- Rejected: `Record<string, OverrideStatus | null>`.
- Reason: Storing explicit `null` values pollutes the serialised JSON and requires every consumer to distinguish `null` from absent. Deleting the key is idiomatic for "no value" in a Record.

**Decision: `OverrideStatus` separate from `CandidateRanking`**
- Rejected: Add an `override` field directly to `CandidateRanking`.
- Reason: `CandidateRanking` is a backend response type. Merging server data with client-side state conflates two independent lifecycles and makes the original rank harder to preserve for audit. Override state is always a client-side overlay, not a mutation of the API response.

**Decision: `OverrideControls` as a separate component**
- Rejected: Inline the toggle buttons in `CandidateRow`.
- Reason: Per `architecture.md`, one file / one responsibility. The toggle interaction logic (`aria-pressed`, null-toggle, label derivation) is a self-contained concern that is cleaner to test in isolation from the row expansion logic already in `CandidateRow`.

**Decision: No new backend endpoint**
- Rejected: `POST /overrides` to persist overrides server-side.
- Reason: No user accounts; multi-recruiter collaboration is out of SPEC scope. Adding a backend endpoint would require a session or user ID that does not exist in this demo. `localStorage` achieves the persistence goal without introducing infra complexity.
- Source: Plan — "Persistence model for 'saved against that candidate for that role' is a Tech Spec decision (single-session vs. browser-local — multi-recruiter collaboration is out of SPEC scope)".

**Decision: `OverrideControls` always visible, not gated on row expansion**
- Rejected: Show override buttons only when a row is expanded.
- Reason: Overrides are primary actions (SPEC: "recruiter is always the decision-maker"). Gating them on expansion adds an extra click and hides a key feature from portfolio reviewers scanning the shortlist.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Corrupted `localStorage` value | `JSON.parse` throws; overrides fail to load | `try/catch` in `useState` initialiser; falls back to `{}` silently |
| Visitor has `localStorage` disabled (strict privacy mode) | `setItem` / `removeItem` throw | Wrap `localStorage` calls in `try/catch`; degrade to session-only state without error |
| Override state survives a backend redeploy with a new pool | Stored `candidate_id` no longer valid | `OverrideMap` keys that don't match any ranking are silently ignored (no-op lookup in `Shortlist`) |
| New JD submitted without explicit clear call | Stale overrides shown against a different shortlist | Clear is co-located with `mutation.mutate()` call — a single touch point in `App.tsx` |

---

## Testing Plan

### `OverrideControls.test.tsx` — Vitest + Testing Library

- Renders "Shortlist" and "Reject" buttons.
- `current=null` → both buttons have `aria-pressed="false"`.
- `current='shortlisted'` → Shortlist button has `aria-pressed="true"`, Reject has `aria-pressed="false"`.
- `current='rejected'` → Reject button has `aria-pressed="true"`, Shortlist has `aria-pressed="false"`.
- Click "Reject" when `current=null` → `onOverride` called with `'rejected'`.
- Click "Shortlist" when `current='shortlisted'` → `onOverride` called with `null` (toggle off).
- Click "Reject" when `current='shortlisted'` → `onOverride` called with `'rejected'` (switch).
- Click "Shortlist" when `current='rejected'` → `onOverride` called with `'shortlisted'` (switch).

### `CandidateRow.test.tsx` additions

- No override chip rendered when `override=null`.
- Green "Shortlisted" chip visible when `override='shortlisted'`.
- Red "Rejected" chip visible when `override='rejected'`.
- Original rank badge visible in all three override states.
- `OverrideControls` rendered regardless of row expansion state.

### `App.tsx` behaviour (spy on `localStorage`)

- On mount, `localStorage.getItem('recruiter_overrides')` is called.
- `handleOverride('candidate_001', 'shortlisted')` → `localStorage.setItem` called with updated map.
- `handleOverride('candidate_001', null)` → `localStorage.setItem` called with key absent.
- Calling `mutation.mutate()` (new JD) → `localStorage.removeItem('recruiter_overrides')` called; `overrides` resets to `{}`.

> **Framework/pattern:** Vitest + Testing Library. Follows existing patterns in `frontend/src/features/ranking/components/__tests__/`. `localStorage` is a global in jsdom; spy on `localStorage.setItem` / `getItem` / `removeItem` with `vi.spyOn(localStorage, 'setItem')`.

---

## Implementation Sequence

1. **Types** — add `OverrideStatus` + `OverrideMap` to `frontend/src/features/ranking/types.ts`.
2. **`OverrideControls` component** — `OverrideControls.tsx` with toggle logic + `aria-pressed`; write `OverrideControls.test.tsx` alongside; run `pnpm test` — must pass.
3. **`CandidateRow` extension** — accept `override` + `onOverride` props; add override chip + `OverrideControls`; original rank badge remains; update `CandidateRow.test.tsx`; run `pnpm test` — must pass.
4. **`App.tsx` extension** — add `overrides` state (localStorage-initialised), `handleOverride`, clear-on-new-JD at `mutation.mutate()` call site; pass `overrides` + `onOverride` to `<Shortlist>`.
5. **`Shortlist` prop threading** — accept `overrides` + `onOverride`; for each row pass `override={overrides[ranking.candidate_id] ?? null}` and a bound `onOverride` callback.
6. **App.tsx tests** — add localStorage spy tests for mount, override set, toggle off, and new-JD clear.
7. **Smoke test** — `pnpm dev`; submit a JD; override two candidates; refresh the page — overrides must persist; submit a new JD — overrides must clear.

---

## Conventions Applied (from CLAUDE.md)

- **Frontend tooling:** pnpm + Vite + React 18 + TypeScript + Tailwind + TanStack Query v5 + Vitest — per CLAUDE.md locked decisions and global `patterns.md`.
- **State:** local `useState` in `App.tsx`; no Zustand, no Context for mutable state — per global `patterns.md` ("Local: `useState` / `useReducer`").
- **Architecture:** `OverrideControls` created in `features/ranking/components/` (feature-first) — per global `architecture.md`.
- **No new libraries:** no new dependencies. `localStorage` is a browser global; `JSON.parse` / `JSON.stringify` are standard.
- **Accessibility:** `aria-pressed` on toggle buttons; `aria-label` on buttons whose meaning is not solely text — per SPEC non-negotiable accessibility rules.
- **Language:** all identifiers, labels, and test descriptions in English — per global `language.md`.
- **Comments:** none added beyond what is non-obvious. `STORAGE_KEY` constant requires no comment — name is self-explanatory.

---

## Ready to Code?

- [x] Architecture described with all modules and changed files named
- [x] Contracts (component interfaces, state shape, localStorage key) in final form
- [x] Data model with types, absent-key convention, and lifecycle documented
- [x] All non-trivial decisions have a rejected alternative documented
- [x] Known risks listed with mitigations (corrupted storage, disabled storage, stale IDs, clear timing)
- [x] Testing plan covers happy path + toggle-off + switch + localStorage lifecycle (10 test cases)
- [x] Implementation sequence is executable without clarification questions (7 steps, each a cohesive commit)
- [x] No new library introduced
- [x] CLAUDE.md conventions cited and respected
- [x] No backend changes — T04 is a pure-frontend feature
