"""
Pydantic schemas for the dataset-preparation pipeline artifacts.

ParsedCandidate is the unit of both pool/<id>.json and the Chroma index.
ExclusionLog is the full audit record written to exclusions.json.

PII contract: 'name', 'email', 'phone', 'address', 'gender', 'age', 'photo'
are intentionally absent from all schemas. Any column that carries PII is
never read after Stage 1 validation. This is enforced structurally — if a
field is not in the schema it cannot be returned, even if a source column
contains it.
"""

from enum import StrEnum

from pydantic import BaseModel


class ExclusionReason(StrEnum):
    parse_failed = "parse_failed"  # CSV row malformed or missing required column
    no_text = "no_text"  # concatenated CV text empty or < 100 chars
    injection_detected = "injection_detected"  # classifier triggered
    extraction_failed = "extraction_failed"  # API error or Pydantic schema violation
    no_skills = "no_skills"  # skills list empty after column mapping


class ExperienceEntry(BaseModel):
    title: str
    company: str | None = None
    duration_months: int | None = None


class EducationEntry(BaseModel):
    degree: str
    institution: str | None = None
    year: int | None = None


class ParsedCandidate(BaseModel):
    id: str  # "candidate_001" — stable, zero-padded 3-digit global index
    category: str  # from job_position_name column (BOM-stripped)
    skills: list[str]  # validated non-empty at gate
    experience: list[ExperienceEntry]
    education: list[EducationEntry]
    summary: str | None = None
    # NEVER: name, email, phone, address, gender, age, photo — absent by design


class ExclusionEntry(BaseModel):
    source_id: str  # CSV row index as zero-padded string, e.g. "row_0042"
    category: str
    reason: ExclusionReason


class ExclusionLog(BaseModel):
    total_source: int  # total rows in source CSV
    total_selected: int  # rows after diverse sampling (Stage 2)
    total_included: int  # rows that passed all gates (Stages 3–4)
    total_excluded: int  # rows that failed any gate
    exclusions: list[ExclusionEntry]
