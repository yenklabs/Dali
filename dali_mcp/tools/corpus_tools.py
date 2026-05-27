"""MCP tool implementation: validate_corpus_record."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from corpus.loader import load_corpus
from corpus.validator import validate_corpus

REQUIRED_FIELDS_FOR_SCORING = (
    "source_url",
    "retrieval_date",
    "source_type",
    "incident_name",
    "alleged_generated_citation",
    "actual_status",
    "failure_class",
    "ground_truth_notes",
)

VALID_ACTUAL_STATUSES = {
    "nonexistent_authority",
    "real_authority_wrong_holding",
    "fabricated_quote",
    "wrong_jurisdiction",
    "overruled_or_invalid",
    "unreachable_source",
    "parallel_citation_mismatch",
    "unknown",
}

VALID_FAILURE_CLASSES = {
    "nonexistent_authority",
    "fabricated_quote",
    "real_case_wrong_holding",
    "wrong_jurisdiction",
    "wrong_court_level",
    "overruled_authority",
    "temporal_validity_failure",
    "parallel_citation_mismatch",
    "semantic_misalignment",
    "citation_mutation",
    "provenance_gap",
    "reconstructability_failure",
}

VALID_SOURCE_TYPES = {
    "sanctions_order",
    "judicial_opinion",
    "motion",
    "disciplinary_record",
    "news_report",
    "other",
}


def _check_case_impl(record_json: str) -> dict:
    issues: list[str] = []

    try:
        record = json.loads(record_json)
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "scoring_eligible": False,
            "issues": [f"Invalid JSON: {e}"],
            "summary": "Parse error: record is not valid JSON.",
        }

    if not isinstance(record, dict):
        return {
            "valid": False,
            "scoring_eligible": False,
            "issues": ["Record must be a JSON object, not an array or primitive."],
            "summary": "Invalid structure.",
        }

    # Required identity fields
    for field in ("case_id", "incident_name", "year", "jurisdiction"):
        if not record.get(field):
            issues.append(f"Missing required field: '{field}'")

    # Year range
    year = record.get("year")
    if isinstance(year, int):
        if not (2021 <= year <= 2026):
            issues.append(f"year {year} is outside the intake window 2021–2026")
    elif year is not None:
        issues.append(f"'year' must be an integer, got {type(year).__name__}")

    # Scoring-required fields
    missing_scoring = [
        f for f in REQUIRED_FIELDS_FOR_SCORING
        if not record.get(f)
    ]
    if missing_scoring:
        issues.append(
            "Missing fields required for scoring: "
            + ", ".join(f"'{f}'" for f in missing_scoring)
        )

    # Taxonomy: actual_status
    actual_status = record.get("actual_status")
    if actual_status and actual_status not in VALID_ACTUAL_STATUSES:
        issues.append(
            f"'actual_status' value '{actual_status}' is not in the taxonomy. "
            f"Valid values: {sorted(VALID_ACTUAL_STATUSES)}"
        )

    # Taxonomy: failure_class
    failure_classes = record.get("failure_class", [])
    if isinstance(failure_classes, list):
        bad = [fc for fc in failure_classes if fc not in VALID_FAILURE_CLASSES]
        if bad:
            issues.append(
                f"Unknown failure_class values: {bad}. "
                f"Valid values: {sorted(VALID_FAILURE_CLASSES)}"
            )
        if not failure_classes and not record.get("needs_verification"):
            issues.append(
                "'failure_class' is empty. At least one failure class is "
                "required for scoring-eligible records."
            )
    else:
        issues.append("'failure_class' must be a JSON array.")

    # source_type taxonomy
    source_type = record.get("source_type")
    if source_type and source_type not in VALID_SOURCE_TYPES:
        issues.append(
            f"'source_type' value '{source_type}' is not in the taxonomy. "
            f"Valid values: {sorted(VALID_SOURCE_TYPES)}"
        )

    # Lineage consistency
    if record.get("synthetic_derivative"):
        if not record.get("parent_incident_id"):
            issues.append(
                "synthetic_derivative=true requires 'parent_incident_id' to be set."
            )
        if not record.get("mutation_type"):
            issues.append(
                "synthetic_derivative=true requires 'mutation_type' to be set."
            )

    # needs_verification with missing source_url
    if record.get("needs_verification") and not record.get("source_url"):
        issues.append(
            "Record has needs_verification=true and no source_url. "
            "The most common fix is to add the court document URL to 'source_url' "
            "and set needs_verification=false once verified."
        )

    # Attorney name check (warn if proper-noun strings appear in free-text fields)
    free_text_fields = (
        "judicial_response",
        "sanctions_or_consequence",
        "ground_truth_notes",
    )
    attorney_hint_fields = []
    for ftf in free_text_fields:
        text = record.get(ftf) or ""
        if "Esq." in text or "Esq" in text or ", Esq" in text:
            attorney_hint_fields.append(ftf)
    if attorney_hint_fields:
        issues.append(
            f"Possible attorney name (Esq.) detected in: {attorney_hint_fields}. "
            "Run corpus/anonymizer.py before submitting."
        )

    scoring_eligible = (
        not issues
        and not record.get("needs_verification")
        and isinstance(year, int)
        and 2023 <= year <= 2026
    )

    if not issues:
        summary = (
            f"Record '{record.get('case_id', '?')}' is valid"
            + (" and scoring-eligible." if scoring_eligible else " (loadable, not scoring-eligible).")
        )
    else:
        summary = (
            f"Record '{record.get('case_id', '?')}' has {len(issues)} issue(s) "
            "and cannot be submitted as-is."
        )

    return {
        "valid": not bool(issues),
        "scoring_eligible": scoring_eligible,
        "issues": issues,
        "summary": summary,
    }
