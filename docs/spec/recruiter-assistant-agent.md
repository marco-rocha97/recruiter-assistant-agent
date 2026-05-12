# SPEC: Candidate Screening Agent

> If there's no clear pain, there's no SPEC. There's just an idea.
> The SPEC answers: what problem, for whom, and how do we know it worked?
> Stack, architecture, APIs, and databases live in the Tech Spec — not here.

---

## Project Context

This is a **portfolio demo**, not a production product. The candidate pool is a **fixed public Kaggle CV dataset** prepared once at build time. Visitors interact with the live app by submitting a job description only — they never upload candidate data. The product framing below ("recruiter", "shortlist", etc.) describes the real problem the demo simulates, so a reviewer can judge engineering and product judgment from a working end-to-end interaction.

---

## Problem Definition

- **Concrete pain:** In-house HR recruiters use their ATS keyword search to narrow a candidate pool, but keyword matches are noisy and shallow — so the recruiter still re-opens dozens of resume PDFs one by one to validate real fit. This screening pass takes hours per role and the resulting shortlist is inconsistent: strong candidates get missed, weak candidates make it through, and the rationale behind each decision is not auditable.
- **Affected persona(s):** In-house HR recruiter screening candidates for their own company's open roles (not agency recruiters, not hiring managers, not founders).
- **Current behavior:** Recruiter exports/filters candidates from the ATS using keyword queries derived from the JD, then opens each remaining PDF resume manually, mentally scoring it against requirements, and assembles a shortlist in a notepad or spreadsheet.

---

## Success Metrics

- **Observable change in user behavior (real-world framing):** Recruiter stops opening resumes one by one. They submit a JD and review the agent's ranked shortlist with justifications, and only deep-read the top candidates the agent surfaced.
- **Demo-side measurable metric:** **Agreement rate ≥ 80%** between the agent's top shortlist and a hand-labeled ground-truth shortlist over a fixed JD set against the Kaggle dataset. This is the number reported on the demo and in the portfolio writeup.
- **Narrative claim (not measured on the demo):** Time-to-shortlist per role drops by at least 75% versus the manual ATS-then-PDF flow. Used to frame the value proposition in the portfolio writeup; not a number the live app produces.

---

## User Stories

> Format: As [persona], I want [observable action] so that [clear benefit].
> Cover: happy path, edge cases, expected failures.

- As a recruiter, I want to submit a job description (file or pasted text) so that I get a ranked shortlist without opening each resume.
- As a recruiter, I want to see why each shortlisted candidate was ranked where they were so that I can trust the result and defend it to the hiring manager.
- As a recruiter, I want to override the agent's ranking and mark a candidate as "shortlisted" or "rejected" myself so that the final decision stays with me.
- As a recruiter, I want the agent to never use demographic information (gender, age, photo, address) when ranking so that the screening is fair and defensible.
- As a portfolio reviewer, I want to see how the demo's candidate pool was built — including how many CVs were dropped because they could not be parsed and which ones — so that I can judge the dataset quality and the author's engineering honesty.

---

## Expected Behaviors

> Describe what users see and do — nothing about internal architecture.
> Use Given/When/Then for acceptance criteria.

```gherkin
Scenario: Visitor submits a JD against the demo candidate pool
  Given the demo app is loaded with the fixed Kaggle candidate pool
  When the visitor submits a job description (file or pasted text)
  Then the visitor sees a ranked shortlist of candidates from the demo pool
  And each candidate row shows: name, fit ranking, matched requirements, missing requirements
  And the visitor can click any candidate to see the resume evidence behind the decision
  And no upload of candidate data is requested at any point
```

```gherkin
Scenario: Visitor inspects dataset transparency
  Given the demo app is loaded
  When the visitor opens the "About this dataset" view
  Then the visitor sees the total number of CVs in the active candidate pool
  And the visitor sees how many CVs were excluded during dataset preparation because they could not be parsed
  And the visitor can see the list of excluded CV identifiers and the reason each was excluded (e.g., "scanned image — no extractable text")
```

```gherkin
Scenario: Demographic information is ignored
  Given a resume contains a photo, gender, age, or home address
  When the agent ranks the candidate
  Then no demographic field appears in the ranking justification
  And the recruiter can confirm via the explainability panel that ranking signals were limited to skills, experience, education, and JD-relevant evidence
```

```gherkin
Scenario: Recruiter overrides the agent
  Given the agent has produced a ranked shortlist
  When the recruiter manually marks a candidate as "shortlisted" or "rejected"
  Then the override is saved against that candidate for that role
  And the agent's original ranking remains visible for audit
```

```gherkin
Scenario: JD cannot be interpreted
  Given the uploaded JD file is empty, has no extractable text, or contains no identifiable requirements
  When the recruiter submits the batch
  Then the recruiter is shown a clear error explaining what was missing
  And no candidate ranking is produced until a valid JD is provided
```

---

## Experience Design

- **User journey:**
  1. Visitor lands on the demo and sees a single primary action: submit a JD.
  2. Visitor submits the JD (file upload or pasted text) against the fixed Kaggle candidate pool.
  3. Visitor receives a ranked shortlist with per-candidate justifications.
  4. Visitor reviews top candidates, opens the resume evidence panel, and applies overrides (shortlist / reject) as needed.
  5. From any screen, the visitor can open the "About this dataset" view to see pool size and the list of CVs excluded during preparation.

- **Interface states:**
  - **Empty state:** "Submit a job description to see how the demo ranks candidates from the sample pool." — single primary action, with a secondary link to "About this dataset".
  - **Loading state:** While the JD is being analyzed and matched against the candidate pool, the visitor sees clear progress feedback (not a frozen UI), with an indication of how long the wait is expected to last.
  - **Success state:** Ranked shortlist appears with matched/missing requirements per candidate. The "About this dataset" entry point remains visible for transparency.
  - **Error state:** Plain-language message explaining what failed (invalid JD, JD has no identifiable requirements, agent unavailable) and the next action the visitor should take.

- **Non-negotiable principles:**
  - The recruiter is always the decision-maker. The agent **ranks and recommends**; it never auto-rejects a candidate or contacts them.
  - Every ranking decision must be explainable from resume evidence. No black-box scores.
  - Dataset quality is surfaced, never silenced — CVs excluded during preparation are listed (with reasons) in the "About this dataset" view, not silently dropped.

- **Accessibility:** Full keyboard navigation across the shortlist, ranking, and override controls. Each candidate row has a screen-reader-friendly label including name, ranking, and key matched requirements.

---

## Business Constraints

- **Audience the demo must convince:**
  - **Portfolio reviewers / prospective employers** — must be able to (a) reach a ranked shortlist within seconds of landing, (b) understand from the explainability panel why each candidate was ranked, and (c) inspect the dataset transparency view to judge engineering honesty about excluded CVs.

- **Non-negotiable business rules:**
  - **No demographic scoring.** Gender, age, race, photo, and home address must never be used as ranking signals. The explainability panel must make this verifiable.
  - **Explainability per ranking.** Every shortlist position must be backed by resume evidence visible to the visitor; no unjustified scores.
  - **Recruiter-final decision (preserved as product principle).** The agent ranks and recommends; it never auto-rejects a candidate and never sends communication to candidates. The override action exists in the UI to reinforce this.
  - **Dataset transparency.** The visitor can always reach a view that states the active pool size and lists every CV excluded at preparation time, with the reason.

- **Critical timeline:** None set at SPEC stage. To be defined in the Plan.

> Technical decisions (infra cost, build time, API limits) live in the Tech Spec.

---

## Out of Scope

> Explicitly list what is NOT included. Prevents scope creep.

- **Visitor-supplied candidate resumes** — visitors cannot upload their own candidate PDFs. Reason: this is a portfolio demo; ingesting third-party PII per visitor adds privacy exposure and per-visitor processing cost with no portfolio benefit. The ranked-shortlist capability is shown against the prepared Kaggle pool instead.
- **Runtime CV ingestion** — the candidate pool is fixed at build time; the live app does not accept new CVs from any source.
- **Sourcing candidates** — no search of LinkedIn, job boards, or any external source.
- **Interview scheduling** — no calendar integration, no candidate-facing emails, no booking flows.
- **ATS write-back** — no integration with any ATS; results stay inside the demo UI.
- **Auto-rejection or any candidate communication** — agent never contacts candidates.
- **Pools above ~50 CVs** — v1 is sized for a fast, low-cost demo. Larger pools deferred.
- **Multi-recruiter collaboration / role sharing** — v1 is single-session. No accounts, no shared roles.

---

## Dataset Preparation (build-time, not runtime)

> Concerns the candidate pool that ships with the demo. Not a runtime user feature.

- **Source:** A fixed subset of CVs from a public Kaggle resume dataset.
- **Validation gate before going live:** Every CV in the shipped pool must have been successfully parsed into the structured fields the ranking relies on (skills, experience, education). CVs that fail this gate are excluded from the pool.
- **Visitor-visible transparency:** The "About this dataset" view exposes pool size and the full list of excluded CVs with the reason each was excluded. This makes dataset quality auditable from inside the demo.
- **Refresh cadence:** Built once for v1; not re-ingested at runtime.

---

## Open Questions

- Which Kaggle CV dataset will be used, and does its license permit a public interactive demo (display of CV content in the explainability panel, derivative outputs in the shortlist)? [Resume Dataset](https://www.kaggle.com/datasets/saugataroyarghya/resume-dataset/data)
- Does the chosen dataset already anonymize candidate names / emails / contact info, or does the build step need to scrub PII before any field is shown to a visitor? Yes
- Is the JD a file upload only, or also a pasted-text fallback? Pasted text removes one click and helps reviewers reach the shortlist faster, but adds a parallel input path. Just plain text, no files.

---

## Ready to Plan?

- [x] Problem has a concrete, observable user pain (not a feature wishlist)
- [x] At least one specific persona identified (in-house HR recruiter)
- [x] Success metric is measurable and anchored (time-to-shortlist −75%, agreement rate ≥80%)
- [x] User stories cover happy path + at least one failure case
- [x] Acceptance criteria are observable (no internal implementation references)
- [x] Out-of-scope is explicit
- [x] No stack, schema, or technical decisions included
