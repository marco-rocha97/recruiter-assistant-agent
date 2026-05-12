from pydantic import BaseModel


class ExclusionEntry(BaseModel):
    source_id: str
    category: str
    reason: str  # string, not enum — build-time/runtime split (see Tech Spec trade-offs)


class DatasetInfo(BaseModel):
    total_source: int
    total_selected: int
    total_included: int
    total_excluded: int
    exclusions: list[ExclusionEntry]
