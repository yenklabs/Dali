"""Tier 1 Integrity Runner — Canonical Case Corpus.

Self-contained reference evaluator. No external services required.

Loads the Canonical Case Corpus, evaluates each scoring-eligible record
using the deterministic local rubric, and writes structured
CitationIntegrityResult output to a JSON file.

This runner is intentionally dependency-free beyond the dali/corpus/ package
so that anyone can run the benchmark without external infrastructure.

Usage
-----
    # Default — deterministic local evaluation, no network:
    python -m dali.runners.run_integrity \\
        --corpus data/benchmark/tier1/corpus/citation_failure_cases.json \\
        --output data/results/v0.2/<date>/integrity.json

    # Also check whether source URLs are still reachable (HTTP HEAD only):
    python -m dali.runners.run_integrity \\
        --corpus data/benchmark/tier1/corpus/citation_failure_cases.json \\
        --output data/results/v0.2/<date>/integrity.json \\
        --check-reachability

    # Include pre-canonical (2021-2022) records in output:
    python -m dali.runners.run_integrity ... --include-pre-canonical

    # Allow cross-version aggregation (produces a warning in output):
    python -m dali.runners.run_integrity ... --allow-cross-version

Exit codes
----------
    0  — all scoring-eligible records evaluated successfully
    1  — argument / config error
    2  — no scoring-eligible records found
    3  — cross-version policy conflict (without --allow-cross-version)
    4  — --verify-replay mismatch (deterministic replay broken)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional, Union

# Allow direct execution from the repo root without requiring PYTHONPATH.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dali.corpus.loader import load_corpus
from dali.corpus.policy import POLICY_VERSION, assert_same_version_or_raise
from dali.corpus.schema import (
    CitationFailureCase,
    CitationIntegrityResult,
    compute_replay_hash,
    corpus_record_hash,
    now_iso,
)
from dali.corpus.taxonomy import CitationFailureClass, DefensibilityRisk, MutationType
from dali.corpus.validator import filter_scoring_eligible, validate_corpus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("run_integrity")

UnknownableBool = Union[bool, Literal["unknown"]]
RECONSTRUCTABILITY_FAILURE_LABELS = {CitationFailureClass.RECONSTRUCTABILITY_FAILURE.value}


# ---------------------------------------------------------------------------
# Local rubric — deterministic, no network, no API
# ---------------------------------------------------------------------------

def _defensibility_risk(
    actual_status: str,
    failure_classes: list[str],
    verification_step_present: UnknownableBool,
    source_chain_complete: UnknownableBool,
) -> DefensibilityRisk:
    """Map corpus annotation + workflow context to the four-level risk rubric.

    Rubric (workflow-centric — see METHODOLOGY.md):
      critical — nonexistent authority AND workflow gaps that preclude Rule 11 defense
      high     — material misrepresentation recoverable only through manual investigation
      medium   — citation mismatch with reconstructable lineage; automatic detection feasible
      low      — formatting / non-material drift; full provenance intact
    """
    is_nonexistent = actual_status == "nonexistent_authority"
    has_workflow_gap = (
        any(label in failure_classes for label in RECONSTRUCTABILITY_FAILURE_LABELS)
        or "provenance_gap" in failure_classes
        or verification_step_present is False
        or source_chain_complete is False
    )

    if is_nonexistent and has_workflow_gap:
        return DefensibilityRisk.CRITICAL
    if is_nonexistent:
        return DefensibilityRisk.HIGH
    if "citation_mutation" in failure_classes or "parallel_citation_mismatch" in failure_classes:
        return DefensibilityRisk.MEDIUM if source_chain_complete is True else DefensibilityRisk.HIGH
    if any(
        fc in failure_classes
        for fc in (
            "fabricated_quote",
            "semantic_misalignment",
            "wrong_jurisdiction",
            "temporal_validity_failure",
            "real_case_wrong_holding",
        )
    ):
        return DefensibilityRisk.HIGH
    return DefensibilityRisk.LOW


def _workflow_reconstructable(
    source_chain_complete: UnknownableBool,
    retrieval_used: UnknownableBool,
    human_review_present: UnknownableBool,
) -> UnknownableBool:
    if source_chain_complete is True:
        return True
    if source_chain_complete is False:
        return False
    if retrieval_used is False and human_review_present is False:
        return False
    return "unknown"


def _verification_recoverable(
    actual_status: str,
    failure_classes: list[str],
    workflow_reconstructable: UnknownableBool,
) -> Literal["automatic", "manual", "infeasible"]:
    if actual_status == "nonexistent_authority" and workflow_reconstructable is False:
        return "infeasible"
    if actual_status == "nonexistent_authority":
        return "manual"
    if "citation_mutation" in failure_classes or "parallel_citation_mismatch" in failure_classes:
        return "automatic"
    if "fabricated_quote" in failure_classes:
        return "manual"
    if workflow_reconstructable is False:
        return "infeasible"
    return "manual"


def _result_evidence_hash(case_id: str, policy_version: str, run_timestamp: str) -> str:
    """Per-run tamper-evident seal over case identity + policy version + timestamp.

    Differs across runs by design — the timestamp is part of the seal. For the
    replay invariant (same input + same policy → same hash forever) see
    :func:`corpus.schema.compute_replay_hash`, surfaced on the result as
    ``replay_hash``.
    """
    payload = json.dumps(
        {"case_id": case_id, "policy_version": policy_version, "run_timestamp": run_timestamp},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _check_reachable(url: str, timeout: float = 10.0) -> bool:
    """HTTP HEAD check. Returns False on any error."""
    try:
        import urllib.request
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Dali-Benchmark-Checker/1.0")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except Exception:
        return False


def _resolve_mutation_lineage(
    case: CitationFailureCase,
    by_id: dict[str, CitationFailureCase],
) -> list[str]:
    lineage: list[str] = []
    seen: set[str] = set()
    cur = case
    for _ in range(16):
        pid = cur.parent_incident_id
        if not pid or pid in seen:
            break
        lineage.append(pid)
        seen.add(pid)
        parent = by_id.get(pid)
        if parent is None:
            break
        cur = parent
    return lineage


def _fc_values(failure_class: list[CitationFailureClass]) -> list[str]:
    return [fc.value if hasattr(fc, "value") else str(fc) for fc in failure_class]


def evaluate_local(
    case: CitationFailureCase,
    policy_version_str: str,
    by_id: dict[str, CitationFailureCase],
    *,
    check_reachability: bool = False,
) -> CitationIntegrityResult:
    """Evaluate one case using the deterministic local rubric.

    No LLM calls. No external services. Uses corpus annotation
    as ground truth and applies the workflow-centric defensibility rubric.
    """
    run_timestamp = now_iso()
    fc_values = _fc_values(case.failure_class)
    actual_status = case.actual_status.value if hasattr(case.actual_status, "value") else str(case.actual_status)

    wf = case.workflow_context
    retrieval_used: UnknownableBool = wf.retrieval_used if wf else "unknown"
    human_review_present: UnknownableBool = wf.human_review_present if wf else "unknown"
    source_chain_complete: UnknownableBool = wf.source_chain_complete if wf else "unknown"
    verification_step_present: UnknownableBool = wf.verification_step_present if wf else "unknown"

    # Citation existence — from corpus annotation
    citation_exists = actual_status not in ("nonexistent_authority", "unknown")

    # Source URL reachability — optional HTTP HEAD, else unknown
    if check_reachability and case.source_url:
        authority_reachable = _check_reachable(case.source_url)
    else:
        authority_reachable = False  # conservative default without network check

    # Semantic alignment from known failure
    if actual_status == "nonexistent_authority":
        semantic_alignment: Literal["aligned", "partially_aligned", "misaligned", "unknown"] = "misaligned"
    elif "semantic_misalignment" in fc_values or "citation_mutation" in fc_values:
        semantic_alignment = "partially_aligned"
    elif citation_exists:
        semantic_alignment = "aligned"
    else:
        semantic_alignment = "unknown"

    # Quote fidelity
    if "fabricated_quote" in fc_values or actual_status == "nonexistent_authority":
        quote_fidelity: Literal["exact", "partial", "fabricated", "not_applicable"] = "fabricated"
    elif citation_exists:
        quote_fidelity = "not_applicable"
    else:
        quote_fidelity = "not_applicable"

    # Temporal validity
    if "temporal_validity_failure" in fc_values:
        temporal_validity: Literal["valid_at_time", "invalid_at_time", "unknown"] = "invalid_at_time"
    else:
        temporal_validity = "unknown"

    # Jurisdiction match
    if "wrong_jurisdiction" in fc_values:
        jurisdiction_match: UnknownableBool = False
    else:
        jurisdiction_match = "unknown"

    # Provenance completeness
    provenance_complete = (
        "provenance_gap" not in fc_values
        and source_chain_complete is True
        and not case.needs_verification
    )

    # Workflow fields
    # reconstructability_failure in failure_class is ground truth from the court record
    # and overrides the heuristic derivation from workflow_context fields.
    if any(label in fc_values for label in RECONSTRUCTABILITY_FAILURE_LABELS):
        wf_reconstructable: UnknownableBool = False
    else:
        wf_reconstructable = _workflow_reconstructable(source_chain_complete, retrieval_used, human_review_present)
    v_recoverable = _verification_recoverable(actual_status, fc_values, wf_reconstructable)
    defensibility = _defensibility_risk(actual_status, fc_values, verification_step_present, source_chain_complete)

    # Mutation lineage
    mutation_lineage = _resolve_mutation_lineage(case, by_id)

    # Per-run seal (timestamped — differs across runs by design)
    evidence_hash = _result_evidence_hash(case.case_id, policy_version_str, run_timestamp)
    # Replay-invariant hashes (timestamp-free — stable across runs forever)
    record_hash = corpus_record_hash(case)
    replay_hash = compute_replay_hash(case, policy_version_str)

    return CitationIntegrityResult(
        case_id=case.case_id,
        citation_exists=citation_exists,
        authority_reachable=authority_reachable,
        semantic_alignment=semantic_alignment,
        quote_fidelity=quote_fidelity,
        temporal_validity=temporal_validity,
        jurisdiction_match=jurisdiction_match,
        provenance_complete=provenance_complete,
        failure_classes_detected=list(case.failure_class),
        defensibility_risk=defensibility,
        workflow_reconstructable=wf_reconstructable,
        verification_recoverable=v_recoverable,
        mutation_lineage=mutation_lineage,
        policy_version=policy_version_str,
        evidence_hash=evidence_hash,
        run_timestamp=run_timestamp,
        corpus_record_hash=record_hash,
        replay_hash=replay_hash,
    )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _enum_safe(obj):
    if hasattr(obj, "value"):
        return obj.value
    if isinstance(obj, dict):
        return {k: _enum_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_enum_safe(v) for v in obj]
    return obj


def _result_to_dict(result: CitationIntegrityResult) -> dict:
    return _enum_safe(asdict(result))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Tier 1 Integrity Runner — Canonical Case Corpus (self-contained)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--corpus",
        default="data/benchmark/tier1/corpus/citation_failure_cases.json",
        help="Path to citation_failure_cases.json (default: data/benchmark/tier1/corpus/...)",
    )
    p.add_argument(
        "--output",
        required=True,
        help="Path for the output integrity.json",
    )
    p.add_argument(
        "--check-reachability",
        action="store_true",
        help="Perform HTTP HEAD checks on source URLs to populate authority_reachable",
    )
    p.add_argument(
        "--include-pre-canonical",
        action="store_true",
        help="Include 2021–2022 records (pre_canonical=true) in evaluation output",
    )
    p.add_argument(
        "--include-needs-verification",
        action="store_true",
        help="Include records marked needs_verification=true (excluded by default)",
    )
    p.add_argument(
        "--allow-cross-version",
        action="store_true",
        help="Permit aggregating results from different policy versions",
    )
    p.add_argument(
        "--verify-replay",
        action="store_true",
        help=(
            "Run the evaluator twice and assert every replay_hash is byte-identical "
            "across runs. Proves deterministic replay. Exit code 4 on mismatch."
        ),
    )
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    policy_version_str = POLICY_VERSION.as_string()

    # Load + validate
    logger.info("loading corpus: %s", args.corpus)
    try:
        all_records = load_corpus(args.corpus)
    except Exception as exc:
        logger.error("corpus load failed: %s", exc)
        return 1

    report = validate_corpus(all_records)
    logger.info(
        "corpus: %d total, %d scoring-eligible, %d pre-canonical, %d needs-verification",
        report.total, report.scoring_eligible, report.pre_canonical, report.needs_verification,
    )

    eligible = filter_scoring_eligible(
        all_records,
        include_pre_canonical=args.include_pre_canonical,
        include_needs_verification=args.include_needs_verification,  # type: ignore[arg-type]
    )

    if not eligible:
        logger.error("no records selected for evaluation — check corpus or loosen filters")
        return 2

    logger.info("evaluating %d record(s)%s", len(eligible),
                " (with reachability checks)" if args.check_reachability else "")

    by_id = {r.case_id: r for r in all_records}

    # Evaluate
    results: list[CitationIntegrityResult] = []
    for case in eligible:
        logger.info("  evaluating: %s", case.case_id)
        result = evaluate_local(
            case,
            policy_version_str,
            by_id,
            check_reachability=args.check_reachability,
        )
        results.append(result)

    # Cross-version guard
    try:
        assert_same_version_or_raise(
            [r.policy_version for r in results],
            allow_cross=args.allow_cross_version,
        )
    except ValueError as exc:
        logger.error("policy version conflict: %s", exc)
        return 3

    # Build output
    risk_counts: dict[str, int] = {}
    for r in results:
        key = r.defensibility_risk.value if hasattr(r.defensibility_risk, "value") else str(r.defensibility_risk)
        risk_counts[key] = risk_counts.get(key, 0) + 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    distinct_versions = list({r.policy_version for r in results})
    output = {
        "run_timestamp": now_iso(),
        "policy_version": policy_version_str,
        "evaluator": "local-reference",
        "cross_version_aggregation": len(distinct_versions) > 1,
        "policy_versions_present": distinct_versions,
        "summary": {
            "total_evaluated": len(results),
            "defensibility_risk_distribution": risk_counts,
        },
        "results": [_result_to_dict(r) for r in results],
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    logger.info("wrote %d result(s) to %s", len(results), output_path)

    # Deterministic replay check — runs evaluation a second time and asserts
    # every replay_hash matches. This proves the determinism claim.
    if args.verify_replay:
        verify_exit = _verify_replay(eligible, policy_version_str, by_id, results)
        if verify_exit != 0:
            return verify_exit

    _print_summary(results, eligible)
    return 0


def _verify_replay(
    eligible: list,
    policy_version_str: str,
    by_id: dict,
    first_results: list[CitationIntegrityResult],
) -> int:
    """Re-evaluate the same cases and assert byte-identical replay_hash values.

    Returns 0 on full match, 4 on any mismatch.
    """
    logger.info("verify-replay: re-evaluating %d case(s) for determinism check", len(eligible))
    first_by_id = {r.case_id: r for r in first_results}
    mismatches: list[tuple[str, str, str]] = []
    for case in eligible:
        second = evaluate_local(case, policy_version_str, by_id)
        first = first_by_id[case.case_id]
        if first.replay_hash != second.replay_hash:
            mismatches.append((case.case_id, first.replay_hash, second.replay_hash))
        if first.corpus_record_hash != second.corpus_record_hash:
            mismatches.append(
                (f"{case.case_id} (corpus_record_hash)", first.corpus_record_hash, second.corpus_record_hash)
            )

    if mismatches:
        logger.error("verify-replay: %d mismatch(es) — determinism is broken", len(mismatches))
        for case_id, h1, h2 in mismatches:
            logger.error("  %s: %s != %s", case_id, h1[:16], h2[:16])
        return 4

    logger.info("verify-replay: PASS — all %d replay_hash values byte-identical", len(eligible))
    return 0


def _print_summary(results: list[CitationIntegrityResult], records: list) -> None:
    record_by_id = {r.case_id: r for r in records}
    print("\n--- Integrity Run Summary ---\n")
    for result in results:
        rec = record_by_id.get(result.case_id)
        risk = (
            result.defensibility_risk.value
            if hasattr(result.defensibility_risk, "value")
            else str(result.defensibility_risk)
        )
        verification = "OK" if result.citation_exists else "FAILED"
        authority = rec.incident_name if rec else result.case_id
        citation_raw = (rec.alleged_generated_citation or "") if rec else ""
        citation = (citation_raw[:80] + "...") if len(citation_raw) > 80 else citation_raw
        source_url = (rec.source_url or "") if rec else ""

        print(f"  case_id:        {result.case_id}")
        print(f"  authority:      {authority}")
        if citation:
            print(f"  citation:       {citation}")
        if source_url:
            print(f"  source_url:     {source_url}")
        print(f"  verification:   {verification}")
        print(f"  recoverability: {result.verification_recoverable}")
        print(f"  risk:           {risk}")
        print(f"  policy_version: {result.policy_version}")
        print(f"  corpus_hash:    {result.corpus_record_hash[:16]}…  ← tamper-detect on input corpus")
        print(f"  replay_hash:    {result.replay_hash[:16]}…  ← deterministic across runs (verify with --verify-replay)")
        print(f"  evidence_hash:  {result.evidence_hash[:16]}…  ← per-run tamper-evident seal")
        if result.mutation_lineage:
            print(f"  lineage:        {' ← '.join(result.mutation_lineage)}")
        print()


if __name__ == "__main__":
    sys.exit(main())
