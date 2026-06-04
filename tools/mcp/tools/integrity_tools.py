"""MCP tool implementations: evaluate_case, verify_replay.

Bring the Tier 1 demo into MCP so contributors never need a terminal.
Same code path as ``dali/runners/run_integrity.py``; the cryptographic lineage
properties (corpus_record_hash, replay_hash, evidence_hash) are surfaced
identically.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from dali.corpus.loader import _case_from_raw
from dali.corpus.policy import POLICY_VERSION
from dali.corpus.schema import CitationIntegrityResult
from dali.runners.run_integrity import evaluate_local


def _result_to_dict(result: CitationIntegrityResult) -> dict:
    """Convert the dataclass result to a JSON-serializable dict."""
    def _enum_safe(obj):
        if hasattr(obj, "value"):
            return obj.value
        if isinstance(obj, dict):
            return {k: _enum_safe(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_enum_safe(v) for v in obj]
        return obj

    from dataclasses import asdict
    return _enum_safe(asdict(result))


def _parse_record(record_json: str) -> tuple[dict | None, str | None]:
    """Parse the input JSON into a dict; return (record, error_message)."""
    try:
        record = json.loads(record_json)
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"
    if not isinstance(record, dict):
        return None, "Record must be a JSON object, not an array or primitive."
    return record, None


def _evaluate_case_impl(record_json: str) -> dict:
    """Run the deterministic Tier 1 evaluator on a single corpus record.

    Returns the full CitationIntegrityResult plus a one-line summary
    formatted like the CLI demo output.
    """
    record, err = _parse_record(record_json)
    if err is not None:
        return {"ok": False, "error": err, "summary": "Parse error."}

    try:
        case = _case_from_raw(record)
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to construct CitationFailureCase: {e}",
            "summary": (
                "Record could not be parsed into the corpus schema. "
                "Run check_case first to identify missing or invalid fields."
            ),
        }

    policy_version_str = POLICY_VERSION.as_string()
    try:
        result = evaluate_local(case, policy_version_str, {case.case_id: case})
    except Exception as e:
        return {
            "ok": False,
            "error": f"Evaluator raised: {type(e).__name__}: {e}",
            "summary": "Evaluator error — record may have inconsistent fields.",
        }

    result_dict = _result_to_dict(result)
    summary_lines = [
        f"case_id:        {result.case_id}",
        f"verification:   {'OK' if result.citation_exists else 'FAILED'}",
        f"recoverability: {result.verification_recoverable}",
        f"risk:           {result.defensibility_risk.value}",
        f"policy_version: {result.policy_version}",
        f"corpus_hash:    {result.corpus_record_hash[:16]}…",
        f"replay_hash:    {result.replay_hash[:16]}…",
        f"evidence_hash:  {result.evidence_hash[:16]}…",
    ]
    if result.mutation_lineage:
        summary_lines.append(f"lineage:        {' ← '.join(result.mutation_lineage)}")

    return {
        "ok": True,
        "result": result_dict,
        "summary": "\n".join(summary_lines),
    }


def _verify_replay_impl(record_json: str) -> dict:
    """Run evaluate_local twice on the same record and compare replay_hash.

    The MCP equivalent of ``dali/runners/run_integrity.py --verify-replay``.
    Returns ``ok: true`` only when the two runs produce identical
    replay_hash and corpus_record_hash values.
    """
    record, err = _parse_record(record_json)
    if err is not None:
        return {"ok": False, "error": err, "summary": "Parse error."}

    try:
        case = _case_from_raw(record)
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to construct CitationFailureCase: {e}",
            "summary": "Record could not be parsed; run check_case first.",
        }

    policy_version_str = POLICY_VERSION.as_string()
    by_id = {case.case_id: case}
    try:
        r1 = evaluate_local(case, policy_version_str, by_id)
        r2 = evaluate_local(case, policy_version_str, by_id)
    except Exception as e:
        return {
            "ok": False,
            "error": f"Evaluator raised: {type(e).__name__}: {e}",
            "summary": "Evaluator error.",
        }

    replay_match = r1.replay_hash == r2.replay_hash
    corpus_match = r1.corpus_record_hash == r2.corpus_record_hash
    passed = replay_match and corpus_match

    return {
        "ok": passed,
        "replay_hash_match": replay_match,
        "corpus_record_hash_match": corpus_match,
        "replay_hash": r1.replay_hash,
        "corpus_record_hash": r1.corpus_record_hash,
        "policy_version": r1.policy_version,
        "summary": (
            f"verify_replay: PASS — replay_hash byte-identical across runs "
            f"({r1.replay_hash[:16]}…)"
            if passed
            else (
                "verify_replay: FAIL — determinism broken. "
                f"replay_hash {r1.replay_hash[:16]}… vs {r2.replay_hash[:16]}…"
            )
        ),
    }
