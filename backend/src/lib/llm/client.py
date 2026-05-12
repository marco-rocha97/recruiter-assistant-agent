"""
LiteLLM wrapper for structured completion and embedding calls.

Design:
- complete() uses Gemini Flash as primary with OpenAI mini as fallback.
  Retries with exponential backoff to respect Gemini free-tier 15 RPM.
- embed() uses Gemini gemini-embedding-001 (renamed from text-embedding-004).
  No fallback in T01 scope.
- Both functions are used by T02 (ranking graph) without changes.

Auth: GEMINI_API_KEY and OPENAI_API_KEY env vars, consumed by LiteLLM.
"""

import logging
import time
from typing import TypeVar

import litellm
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_T = TypeVar("_T", bound=BaseModel)


def complete(
    prompt: str,
    system: str,
    response_format: type[_T],
    model: str = "gemini/gemini-2.5-flash",
    fallback: str = "openai/gpt-4o-mini",
    max_retries: int = 3,
    temperature: float | None = None,  # None = model default; 0 = deterministic
) -> _T:
    """
    Structured LLM completion with exponential-backoff retry and provider fallback.

    System and user content are always passed as separate messages — never
    concatenated into a single string. This preserves the trust boundary
    required by the guardrail rules in CLAUDE.md.

    Args:
        prompt: The user-side content (may contain untrusted text, must arrive
                already wrapped in delimited fences by the caller).
        system: The trusted system instruction (never interpolated with user text).
        response_format: Pydantic model class; LiteLLM returns a parsed instance.
        model: Primary LiteLLM model identifier.
        fallback: Provider to try once after max_retries on the primary.
        max_retries: Attempts on the primary model before switching to fallback.
        temperature: Sampling temperature passed to the provider. None defers to
                     the model default. Pass 0 for deterministic/reproducible output
                     (used by the eval harness to produce a stable portfolio number).

    Returns:
        An instance of response_format.

    Raises:
        RuntimeError: If all retries on primary AND the fallback attempt fail.
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    extra_kwargs: dict = {}
    if temperature is not None:
        extra_kwargs["temperature"] = temperature

    last_exc: Exception | None = None
    base_delay = 4.0  # seconds — respects Gemini free-tier 15 RPM

    for attempt in range(max_retries):
        try:
            response = litellm.completion(
                model=model,
                messages=messages,
                response_format=response_format,
                **extra_kwargs,
            )
            raw = response.choices[0].message.content
            return response_format.model_validate_json(raw)
        except Exception as exc:
            last_exc = exc
            delay = base_delay * (2**attempt)
            logger.warning(
                "complete() attempt %d/%d failed on %s: %s — retrying in %.1fs",
                attempt + 1,
                max_retries,
                model,
                last_exc,
                delay,
            )
            time.sleep(delay)

    # Primary exhausted — try fallback once
    logger.warning("Primary model %s exhausted, attempting fallback %s", model, fallback)
    try:
        response = litellm.completion(
            model=fallback,
            messages=messages,
            response_format=response_format,
            **extra_kwargs,
        )
        raw = response.choices[0].message.content
        return response_format.model_validate_json(raw)
    except Exception as exc:
        raise RuntimeError(
            f"complete() failed after {max_retries} retries on {model} "
            f"and one attempt on {fallback}: {exc}"
        ) from exc


def embed(
    text: str,
    model: str = "gemini/gemini-embedding-001",
) -> list[float]:
    """
    Single text embedding via LiteLLM.

    Used at dataset-prep time (Stage 5) to index ParsedCandidate structured
    representations into Chroma. No fallback for T01 — if the embedding call
    fails after retries the candidate is excluded with 'extraction_failed'.

    Args:
        text: The structured candidate text to embed. Never contains raw CV
              text or PII — always the formatted Skills/Experience/Education
              representation built from ParsedCandidate.
        model: LiteLLM model identifier for the embedding provider.

    Returns:
        A list of floats (the embedding vector).

    Raises:
        RuntimeError: If the LiteLLM call fails.
    """
    try:
        response = litellm.embedding(model=model, input=[text])
        return response.data[0]["embedding"]
    except Exception as exc:
        raise RuntimeError(f"embed() failed for model {model}: {exc}") from exc
