# Plan: Candidate Screening Agent

> Reference SPEC: [`docs/specs/SPEC.md`](../SPEC.md)
> This plan breaks the SPEC into **independent tasks**, each ready to become a dedicated Tech Spec.
> There is **no** stack, schema, architecture, or estimation here — only behavior and sequencing.

---

## Target Outcome

- **Anchor result** (from SPEC): A visitor submits a job description as plain text and receives a ranked shortlist from the prepared Kaggle pool, with per-candidate matched/missing requirements and resume evidence — and can always reach a transparency view that shows pool size and the list of CVs excluded at preparation time. The portfolio narrative is supported by an agreement rate ≥ 80% against a hand-labeled ground-truth set, but the live demo does not need to compute that number to be shippable.
- **MVP of this plan:** **T01 + T02 + T03**. These three close the demo's anchor result: a fixed parsed pool exists (T01), the visitor submits a JD and sees a ranked, explained shortlist (T02), and the visitor can audit dataset quality from inside the demo (T03).
- **Later phases:** **T04** (recruiter override) and **T05** (agreement-rate evaluation harness). Both reinforce SPEC commitments but are not required for a shippable portfolio demo of the anchor result.

---

## Task Map

| #   | Task                                                                                           | Covers (SPEC)                                                                          | Depends on | Phase   | Status  |
| --- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ---------- | ------- | ------- |
| T01 | Build-time dataset preparation                                                                 | Story 5; Dataset Preparation section; Open Question on PII scrubbing                   | —          | MVP     | pending |
| T02 | JD submission → ranked shortlist with explainability                                           | Stories 1, 2, 4; Scenarios "Visitor submits a JD", "Demographic info ignored", "JD cannot be interpreted"; Loading/Empty/Success/Error states | T01        | MVP     | pending |
| T03 | "About this dataset" transparency view                                                         | Story 5; Scenario "Visitor inspects dataset transparency"                              | T01        | MVP     | pending |
| T04 | Recruiter override (shortlist / reject)                                                        | Story 3; Scenario "Recruiter overrides the agent"                                      | T02        | Phase 2 | pending |
| T05 | Agreement-rate evaluation harness (≥ 80% vs. ground-truth shortlist)                           | Success Metric "Agreement rate ≥ 80%"                                                  | T02        | Phase 2 | pending |

> Suggested order: **T01 → (T02 ∥ T03) → T04 → T05**.
> T02 and T03 can proceed in parallel once T01 has produced the pool artifact and the exclusion log.

---

## Task Details

### T01 — Build-time dataset preparation

- **Behavior delivered:** A fixed candidate pool ships with the demo. Every CV in the pool has been parsed into the structured fields the ranking relies on (skills, experience, education); CVs that fail this gate are excluded from the pool and recorded with a reason. PII (names, emails, contact info) is scrubbed before any field can be shown to a visitor.
- **Stories/behaviors covered in SPEC:**
  - Story 5 ("portfolio reviewer wants to see how the demo's candidate pool was built").
  - "Dataset Preparation (build-time, not runtime)" section in full.
  - Open Question (resolved): the source dataset is the Kaggle "Resume Dataset" referenced in the SPEC, and PII scrubbing is required at build time.
- **Acceptance criteria:**
  - Given the build pipeline runs over the Kaggle source, when a CV cannot be parsed into the structured fields required for ranking, then it is excluded from the shipped pool and recorded with an exclusion reason (e.g., "scanned image — no extractable text").
  - Given the build pipeline completes, then the shipped artifact contains: the parsed pool (only CVs that passed the gate), the exclusion log (CV identifiers + reasons), and the total counts that the transparency view will surface.
  - Given any field of any CV will be exposed to a visitor (in the shortlist or the explainability panel), then names, emails, and contact info have been scrubbed before that exposure.
  - Given the SPEC out-of-scope on pool size ("Pools above ~50 CVs"), then the shipped pool stays within that bound.
- **Depends on:** —
- **Pending assumptions that may block:** Kaggle dataset license must permit a public interactive demo (display of CV-derived content in the explainability panel). Listed under External Dependencies.
- **Tech Spec:** pending
- **Negotiation notes:** Pool size left as a Tech Spec decision; only the SPEC ceiling (~50) is binding here.

### T02 — JD submission → ranked shortlist with explainability

- **Behavior delivered:** A visitor pastes a job description, and (after a clear loading state) sees a ranked shortlist of candidates from the prepared pool. Each row shows the candidate, fit ranking, matched requirements, and missing requirements; clicking a row opens the resume evidence behind the decision. Demographic fields (gender, age, photo, address) never appear as ranking signals or in the justification. If the JD is empty or has no identifiable requirements, the visitor sees a plain-language error explaining what was missing and no ranking is produced.
- **Stories/behaviors covered in SPEC:**
  - Story 1 (submit a JD, get a ranked shortlist).
  - Story 2 (see why each candidate was ranked where they were).
  - Story 4 (no demographic information used in ranking).
  - Scenario "Visitor submits a JD against the demo candidate pool".
  - Scenario "Demographic information is ignored".
  - Scenario "JD cannot be interpreted".
  - Experience Design: Empty / Loading / Success / Error states.
  - Non-negotiable principle: explainability per ranking — every shortlist position is backed by resume evidence.
  - Open Question (resolved): JD is plain-text only, no file upload.
- **Acceptance criteria:**
  - Given the demo is loaded with the prepared pool, when the visitor submits a JD as plain text, then a ranked shortlist appears whose rows each show name (post-scrub), fit ranking, matched requirements, and missing requirements.
  - Given a shortlist is shown, when the visitor opens any candidate's evidence panel, then the resume evidence backing the matched/missing requirements is visible.
  - Given a resume contains a photo, gender, age, or home address, when the candidate is ranked, then no demographic field appears in the ranking justification, and the explainability panel only cites skills, experience, education, and JD-relevant evidence.
  - Given the JD is empty or contains no identifiable requirements, when the visitor submits it, then a plain-language error is shown and no ranking is produced.
  - Given the JD is being analyzed, while the request is in flight, then the visitor sees clear progress feedback (not a frozen UI) with an indication of expected duration.
- **Depends on:** T01 (needs the parsed pool and the post-scrub fields).
- **Pending assumptions:** None additional once T01 has shipped the pool artifact.
- **Tech Spec:** pending
- **Negotiation notes:** Kept unified (not split into "ranking pipeline" + "UI"). Splitting by layer is an anti-pattern in this workflow; the user-observable behavior is one flow.

### T03 — "About this dataset" transparency view

- **Behavior delivered:** From any screen, the visitor can open an "About this dataset" view that states the active pool size and lists every CV excluded during preparation along with the reason each was excluded. This view exists to make dataset quality auditable from inside the demo.
- **Stories/behaviors covered in SPEC:**
  - Story 5 (portfolio reviewer wants to judge dataset quality and engineering honesty).
  - Scenario "Visitor inspects dataset transparency".
  - Non-negotiable principle: "Dataset quality is surfaced, never silenced".
  - Experience Design: "About this dataset" entry point remains visible from empty and success states.
- **Acceptance criteria:**
  - Given the demo is loaded, when the visitor opens "About this dataset", then the visitor sees the total number of CVs in the active candidate pool.
  - Given the same view is open, then the visitor sees how many CVs were excluded during dataset preparation and the full list of excluded CV identifiers with the reason each was excluded.
  - Given the visitor is on the empty state or the success (shortlist) state, then the entry point to "About this dataset" is reachable from that screen.
- **Depends on:** T01 (needs the pool size and the exclusion log produced at build time).
- **Pending assumptions:** —
- **Tech Spec:** pending

### T04 — Recruiter override (shortlist / reject) — Phase 2

- **Behavior delivered:** After a ranking is produced, the visitor can mark any candidate as "shortlisted" or "rejected". The override is saved against that candidate for that role, and the agent's original ranking remains visible for audit. The override exists to reinforce the SPEC's "recruiter is the decision-maker" product principle.
- **Stories/behaviors covered in SPEC:**
  - Story 3 (override the agent's ranking).
  - Scenario "Recruiter overrides the agent".
  - Non-negotiable principle: "The recruiter is always the decision-maker".
- **Acceptance criteria:**
  - Given the agent has produced a ranked shortlist, when the visitor marks a candidate as "shortlisted" or "rejected", then the override is saved against that candidate for that role.
  - Given an override has been applied, then the agent's original ranking remains visible for audit alongside the override.
- **Depends on:** T02 (needs an existing ranked shortlist to override).
- **Pending assumptions:** Persistence model for "saved against that candidate for that role" is a Tech Spec decision (single-session vs. browser-local — multi-recruiter collaboration is out of SPEC scope).
- **Tech Spec:** pending
- **Negotiation notes:** Deferred from MVP. Anchor result is reachable without override; override reinforces a product principle but is not required for the demo to demonstrate ranking + explainability + transparency.

### T05 — Agreement-rate evaluation harness — Phase 2

- **Behavior delivered:** A reproducible evaluation that compares the agent's top shortlist to a hand-labeled ground-truth shortlist over a fixed JD set against the prepared pool, and reports an agreement rate. The number is the one cited in the portfolio writeup ("≥ 80%"). The live demo does not need to compute this on each visit.
- **Stories/behaviors covered in SPEC:**
  - Success Metric: "Agreement rate ≥ 80% between the agent's top shortlist and a hand-labeled ground-truth shortlist".
- **Acceptance criteria:**
  - Given a fixed JD set and a hand-labeled ground-truth shortlist per JD, when the harness runs over the prepared pool, then it produces an agreement rate between the agent's top shortlist and the ground truth.
  - Given the harness has run, then the result is reproducible from the same inputs and is the number quoted in the portfolio writeup.
- **Depends on:** T02 (needs the ranking output to compare).
- **Pending assumptions:** A hand-labeled ground-truth shortlist must exist for the chosen JD set. Producing those labels is part of this task.
- **Tech Spec:** pending
- **Negotiation notes:** Deferred from MVP. The agreement rate is a portfolio narrative number; the demo's anchor result does not require it to render at runtime.

---

## External Dependencies

Items outside the repo that may block one or more tasks:

- [x] Kaggle "Resume Dataset" license review [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) — must permit a public interactive demo (display of CV-derived content in the explainability panel and derivative outputs in the shortlist). **Blocks T01.**
- [ ] Hand-labeled ground-truth shortlist for the agreement-rate evaluation. **Blocks T05.**

---

## Out of This Plan

Items from the SPEC **deliberately deferred** (or excluded entirely per SPEC out-of-scope):

- **Recruiter override (T04)** — reason: not required for the demo's anchor result; reinforces a product principle but does not produce the ranked-shortlist outcome the demo is judged on.
- **Agreement-rate evaluation harness (T05)** — reason: the ≥ 80% number lives in the portfolio writeup, not on the live demo. Building the harness is valuable but does not gate shipping the demo.
- **Visitor-supplied candidate resumes** — out of SPEC scope. Not planned.
- **Runtime CV ingestion** — out of SPEC scope. Pool is fixed at build time (T01).
- **Sourcing candidates (LinkedIn, job boards, external sources)** — out of SPEC scope. Not planned.
- **Interview scheduling, candidate-facing emails, ATS write-back, auto-rejection or any candidate communication** — out of SPEC scope. Not planned.
- **Pools above ~50 CVs** — out of SPEC scope. T01 stays within the SPEC ceiling.
- **Multi-recruiter collaboration / role sharing / accounts** — out of SPEC scope. Not planned.

---

## Ready for Tech Spec?

- [x] Every task cites at least one story/behavior from the SPEC
- [x] Every task fits in one Tech Spec (no mega-tasks)
- [x] Dependencies are explicit and cycle-free
- [x] MVP is identified and closes the anchor result
- [x] Zero implementation details (no stack, schema, endpoint, infra)
- [x] SPEC out-of-scope is respected
- [x] External blocking dependencies are listed
