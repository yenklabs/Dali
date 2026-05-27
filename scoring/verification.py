"""Local citation verification utilities for the public benchmark runner.

This module keeps the public benchmark self-contained. It extracts likely
citations from model output, fetches reachable URLs directly, and returns a
simple verification record for the synthetic runner.
"""

from __future__ import annotations

import asyncio
import hashlib
import html
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from scoring.existence import score_existence

_URL_RE = re.compile(r"https?://[^\s\])>\"']+")
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;/:A-Z0-9]+", re.IGNORECASE)
_CASE_RE = re.compile(
    r"[A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*)*\s+v\.\s+"
    r"[A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*)*,\s+"
    r"\d+\s+[A-Z][A-Za-z.\d]*\s+\d+\s+\(\d{4}\)"
)
_MALFORMED_URL_RE = re.compile(r"\b(?:htp|ttp|https//|http//):?[^\s\])>\"']+", re.IGNORECASE)
_CASE_LIKE_RE = re.compile(
    r"[A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*)*\s+v\.\s+"
    r"[A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*)*[, ]+\s*"
    r"\d+\s+[A-Z][A-Za-z.\d]*\s+\d+(?:\s+\(\d{4}\))?"
)


@dataclass
class CitationSnapshot:
    source_url: str
    final_url: str
    http_status: int = 0
    content_hash: Optional[str] = None
    storage_path: Optional[str] = None
    byte_size: int = 0
    fetch_error: Optional[str] = None
    exists_verified: bool = False
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extracted_text: str = ""


@dataclass
class VerifiedCitation:
    raw_text: str
    source_ref: str
    resolution_method: str
    verdict: str
    existence_score: float
    snapshot: Optional[CitationSnapshot] = None


def _normalize_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_candidates(llm_output: str) -> list[tuple[int, int, str, str]]:
    candidates: list[tuple[int, int, str, str]] = []
    for match in _URL_RE.finditer(llm_output):
        candidates.append((match.start(), match.end(), "url_explicit", match.group(0)))
    for match in _DOI_RE.finditer(llm_output):
        doi = match.group(0).rstrip(").,;]")
        candidates.append((match.start(), match.end(), "doi", f"https://doi.org/{doi}"))
    for match in _CASE_RE.finditer(llm_output):
        candidates.append((match.start(), match.end(), "case_pattern", match.group(0).strip()))

    priority = {"url_explicit": 0, "doi": 1, "case_pattern": 2}
    selected: list[tuple[int, int, str, str]] = []
    for candidate in sorted(candidates, key=lambda item: (item[0], priority[item[2]], -(item[1] - item[0]))):
        start, end, method, text = candidate
        overlaps = False
        for s, e, m, _ in selected:
            if not (end <= s or start >= e):
                if priority[method] >= priority[m]:
                    overlaps = True
                    break
        if not overlaps:
            selected.append(candidate)

    return selected


def inspect_citation_extraction(llm_output: str) -> dict:
    """Return parser diagnostics for classification and debug output."""
    raw_url_matches = [m.group(0) for m in _URL_RE.finditer(llm_output)]
    raw_doi_matches = [m.group(0) for m in _DOI_RE.finditer(llm_output)]
    raw_case_matches = [m.group(0).strip() for m in _CASE_RE.finditer(llm_output)]
    raw_malformed_url_matches = [m.group(0) for m in _MALFORMED_URL_RE.finditer(llm_output)]

    parsed = _extract_candidates(llm_output)
    parsed_payload = [
        {
            "method": method,
            "raw_text": text,
            "span": [start, end],
        }
        for start, end, method, text in parsed
    ]

    malformed_case_candidates: list[str] = []
    for match in _CASE_LIKE_RE.finditer(llm_output):
        candidate = match.group(0).strip()
        if _CASE_RE.fullmatch(candidate):
            continue
        malformed_case_candidates.append(candidate)

    malformed_candidates = [
        {"type": "malformed_url", "raw_text": text}
        for text in raw_malformed_url_matches
    ] + [
        {"type": "malformed_case_citation", "raw_text": text}
        for text in malformed_case_candidates
    ]

    total_raw = len(raw_url_matches) + len(raw_doi_matches) + len(raw_case_matches)
    normalization_steps = [
        f"raw_matches_total={total_raw}",
        "overlap_resolution=prioritize_url_then_doi_then_case",
        f"selected_candidates={len(parsed_payload)}",
        f"malformed_candidates={len(malformed_candidates)}",
    ]

    return {
        "raw_matches": {
            "url_explicit": raw_url_matches,
            "doi": raw_doi_matches,
            "case_pattern": raw_case_matches,
        },
        "normalization_steps": normalization_steps,
        "parsed_candidates": parsed_payload,
        "malformed_candidates": malformed_candidates,
    }


def _fetch_url(url: str, timeout: float = 10.0) -> CitationSnapshot:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Dali-Benchmark-Runner/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            text = _normalize_text(raw.decode("utf-8", errors="replace"))
            return CitationSnapshot(
                source_url=url,
                final_url=resp.geturl(),
                http_status=getattr(resp, "status", 200),
                content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                byte_size=len(raw),
                exists_verified=True,
                extracted_text=text,
            )
    except urllib.error.HTTPError as exc:
        return CitationSnapshot(
            source_url=url,
            final_url=url,
            http_status=getattr(exc, "code", 0) or 0,
            fetch_error=f"http_{getattr(exc, 'code', 0) or 0}",
        )
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return CitationSnapshot(
            source_url=url,
            final_url=url,
            http_status=0,
            fetch_error=f"request_error:{reason.__class__.__name__}",
        )
    except Exception as exc:
        return CitationSnapshot(
            source_url=url,
            final_url=url,
            http_status=0,
            fetch_error=f"request_error:{exc.__class__.__name__}",
        )


def _verify_citations_sync(
    llm_output: str,
    *,
    evidence_id: str,
    audit_id: str,
    upload: bool = False,
) -> list[VerifiedCitation]:
    # evidence_id/audit_id/upload are retained for signature compatibility.
    del evidence_id, audit_id, upload

    verified: list[VerifiedCitation] = []
    for _, _, method, raw_text in _extract_candidates(llm_output):
        if method == "case_pattern":
            verified.append(
                VerifiedCitation(
                    raw_text=raw_text,
                    source_ref=raw_text,
                    resolution_method=method,
                    verdict="unresolvable",
                    existence_score=0.0,
                    snapshot=None,
                )
            )
            continue

        snapshot = _fetch_url(raw_text)
        existence_score = score_existence(snapshot.http_status, snapshot.fetch_error)
        if snapshot.fetch_error:
            verdict = "unreachable" if existence_score == 0.5 else "dead"
        elif snapshot.http_status in range(200, 300):
            verdict = "redirected" if snapshot.final_url != snapshot.source_url else "verified"
        else:
            verdict = "dead"

        verified.append(
            VerifiedCitation(
                raw_text=raw_text,
                source_ref=raw_text,
                resolution_method=method,
                verdict=verdict,
                existence_score=existence_score,
                snapshot=snapshot,
            )
        )

    return verified


async def verify_citations(
    llm_output: str,
    *,
    evidence_id: str,
    audit_id: str,
    upload: bool = False,
) -> list[VerifiedCitation]:
    """Verify citations in llm_output using the public benchmark's local flow."""
    return await asyncio.to_thread(
        _verify_citations_sync,
        llm_output,
        evidence_id=evidence_id,
        audit_id=audit_id,
        upload=upload,
    )
