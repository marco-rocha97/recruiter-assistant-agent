"""
Rule-based prompt-injection classifier.

Used at dataset-prep time (T01) to screen CV text, and at request time (T02) to
screen incoming job-description text. A regex match is deterministic and reproducible
— a rejection logged in exclusions.json can always be replayed exactly.
"""

import re

INJECTION_PATTERNS: list[str] = [
    r"(?i)ignore (previous|prior|above|all) instructions",
    r"(?i)you are now",
    r"(?i)disregard (your|all) (instructions|rules|guidelines|system prompt)",
    r"(?i)do not follow",
    r"(?i)new (persona|role|identity)",
    r"(?i)\bsystem prompt\b",
    r"(?i)\bjailbreak\b",
    r"(?i)DAN mode",
    r"(?i)act as (?!a recruiter|an HR|a hiring)",
    r"(?i)pretend (to be|you are)",
    r"(?i)forget (everything|all|your training|previous (instructions|context))",
    r"(?i)override (your|the) (instructions|system|prompt|guidelines)",
]


def classify_injection(text: str) -> tuple[bool, str | None]:
    """
    Return (is_injection, matched_pattern | None).

    True means the text contains a suspected prompt-injection pattern.
    Called at dataset-prep time (T01) and at request time on JD text (T02).
    A positive result at build time causes the CV to be excluded with reason
    'injection_detected' and logged in exclusions.json.
    """
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text):
            return True, pattern
    return False, None
