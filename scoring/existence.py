"""Existence scoring utilities for the benchmark runner."""

from __future__ import annotations


def score_existence(http_status: int, fetch_error: str | None) -> float:
    """Map http_status + fetch_error to existence score.

    Returns 1.0 / 0.5 / 0.0 consistent with verifier.py.
    Kept here so the public benchmark repo is self-contained.
    """
    if fetch_error in ("timeout",) or http_status == 408:
        return 0.5
    if fetch_error and fetch_error.startswith("request_error:"):
        return 0.5
    if 200 <= http_status <= 299:
        return 1.0
    return 0.0
