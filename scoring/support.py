"""Local support scoring utilities for the public benchmark runner."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Optional

MAX_TOKENS = 256
SOURCE_CHAR_LIMIT = 3000


def _get_scorer_model() -> str:
    model = os.environ.get("DALI_SCORER_MODEL", "").strip()
    if not model:
        raise EnvironmentError(
            "DALI_SCORER_MODEL is not set. Set it to any model ID supported by "
            "runners/models.py before running Tier 2 with support scoring. "
            "Use a cross-vendor model (different provider than your subject models) "
            "to avoid self-evaluation bias."
        )
    return model


@dataclass
class SupportScore:
    score: float
    verdict: str
    reasoning: str


def extract_claim_for_citation(citation_text: str, llm_output: str) -> Optional[str]:
    """Extract the sentence from llm_output most closely associated with citation_text."""
    pos = llm_output.find(citation_text)
    if pos == -1:
        prefix = citation_text[:40]
        pos = llm_output.find(prefix)
    if pos == -1:
        return None

    start = max(0, llm_output.rfind(".", 0, pos) + 1)
    end_raw = llm_output.find(".", pos)
    end = end_raw + 1 if end_raw != -1 else len(llm_output)
    sentence = llm_output[start:end].strip()
    return sentence[:400] if sentence else None


def _verdict_from_score(score: float) -> str:
    if score >= 0.6:
        return "supported"
    if score >= 0.3:
        return "partial"
    return "unsupported"


def _parse_response(raw_text: str) -> SupportScore:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        payload = json.loads(cleaned)
    except Exception:
        return SupportScore(0.0, "unverifiable", "unable to parse model response")

    try:
        score = float(payload.get("score", 0.0))
    except Exception:
        score = 0.0
    score = max(0.0, min(1.0, score))

    verdict = str(payload.get("verdict", "")).strip() or _verdict_from_score(score)
    if verdict not in {"supported", "partial", "unsupported", "unverifiable"}:
        verdict = _verdict_from_score(score)

    reasoning = str(payload.get("reasoning", "")).strip() or "no reasoning provided"
    return SupportScore(score=score, verdict=verdict, reasoning=reasoning)


def _build_prompt(claim: str, source_text: str) -> str:
    source_excerpt = source_text[:SOURCE_CHAR_LIMIT]
    return (
        "You are a citation integrity auditor. Given a legal or factual CLAIM and the "
        "SOURCE TEXT it is supposed to be grounded in, evaluate whether the source actually supports the claim.\n\n"
        "Respond with JSON only — no preamble, no explanation outside the JSON object.\n\n"
        'Response schema: {"score": float 0.0–1.0, "verdict": "supported"|"partial"|"unsupported"|"unverifiable", "reasoning": "one sentence"}\n\n'
        f"CLAIM:\n{claim}\n\nSOURCE TEXT:\n{source_excerpt}"
    )


def score_support(
    claim: str,
    source_text: str,
    *,
    api_key: Optional[str] = None,
) -> SupportScore:
    """Score how well source_text supports claim."""
    if not claim or not source_text or len(source_text.strip()) < 50:
        return SupportScore(0.0, "unverifiable", "source too short")

    del api_key  # retained for API compatibility with older callers
    try:
        from runners.models import call_model

        raw = call_model(_get_scorer_model(), _build_prompt(claim, source_text))
        return _parse_response(raw)
    except Exception as exc:
        return SupportScore(0.0, "unverifiable", f"scoring unavailable: {exc.__class__.__name__}")


def score_support_batch(
    claim_source_pairs: list[tuple[str, str]],
    *,
    api_key: Optional[str] = None,
) -> list[SupportScore]:
    """Score multiple claim+source pairs."""
    return [score_support(claim, source, api_key=api_key) for claim, source in claim_source_pairs]
