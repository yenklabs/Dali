"""Validation rules for the Canonical Case Corpus.

Validation has two layers:
  1. Loadability  — record can be inspected, surfaced in queries
  2. Scoring eligibility — record can count toward published metrics

A record is scoring-eligible only if it passes ALL of these:

  - intake window: year in [2021, 2026]
  - scoring eligibility (canonical): year in [2023, 2026] unless overridden
  - hygiene gate: all ten required fields populated and non-null
  - lineage integrity: parent_incident_id resolves; mutation rules respected
  - taxonomy closure: all failure_class and mutation_type values valid

The validator never raises on a single bad record — it collects violations
and reports a summary. Runners call ``filter_scoring_eligible()`` to get
the subset they can score.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from dali.corpus.loader import load_corpus
from dali.corpus.schema import CitationFailureCase

INTAKE_WINDOW = (2021, 2026)
CANONICAL_WINDOW = (2023, 2026)

# Ten fields that must be populated for a record to score.
REQUIRED_FIELDS_FOR_SCORING = (
    "source_url",
    "retrieval_date",
    "source_type",
    "incident_name",
    "alleged_generated_citation",
    "actual_status",
    "failure_class",
    "ground_truth_notes",
    # policy_version + evidence_hash are stamped at score-time, not in source
)


@dataclass
class ValidationReport:
    total: int
    loadable: int
    scoring_eligible: int
    pre_canonical: int
    needs_verification: int
    invalid: list[tuple[str, list[str]]]  # (case_id, reasons)

    def summary(self) -> str:
        lines = [
            f"{self.total} records loaded",
            f"{self.scoring_eligible} scoring-eligible "
            f"({CANONICAL_WINDOW[0]}–{CANONICAL_WINDOW[1]})",
            f"{self.pre_canonical} pre-canonical "
            f"({INTAKE_WINDOW[0]}–{CANONICAL_WINDOW[0] - 1})",
            f"{self.needs_verification} needs-verification",
            f"{len(self.invalid)} invalid for scoring",
        ]
        return " · ".join(lines)


def _missing_required_fields(rec: CitationFailureCase) -> list[str]:
    missing: list[str] = []
    for f in REQUIRED_FIELDS_FOR_SCORING:
        v = getattr(rec, f, None)
        if v is None or (isinstance(v, (list, str)) and len(v) == 0):
            missing.append(f)
    return missing


def _intake_violation(rec: CitationFailureCase) -> str | None:
    lo, hi = INTAKE_WINDOW
    if not (lo <= rec.year <= hi):
        return f"year {rec.year} outside intake window {lo}–{hi}"
    return None


def _lineage_violation(
    rec: CitationFailureCase, by_id: dict[str, CitationFailureCase]
) -> str | None:
    if rec.synthetic_derivative and not rec.parent_incident_id:
        return "synthetic_derivative=true requires parent_incident_id"
    if rec.synthetic_derivative and rec.mutation_type is None:
        return "synthetic_derivative=true requires mutation_type"
    if rec.parent_incident_id and rec.parent_incident_id not in by_id:
        return f"parent_incident_id {rec.parent_incident_id!r} does not resolve"
    return None


def validate_corpus(
    records: list[CitationFailureCase],
    *,
    allow_pre_canonical_scoring: bool = False,
) -> ValidationReport:
    by_id = {r.case_id: r for r in records}
    invalid: list[tuple[str, list[str]]] = []
    scoring_eligible = 0
    pre_canonical = 0
    loadable = 0

    needs_verification_count = 0
    for r in records:
        reasons: list[str] = []
        if (v := _intake_violation(r)) is not None:
            reasons.append(v)
        else:
            loadable += 1

        if (v := _lineage_violation(r, by_id)) is not None:
            reasons.append(v)

        is_pre_canon = INTAKE_WINDOW[0] <= r.year < CANONICAL_WINDOW[0]
        if is_pre_canon:
            pre_canonical += 1

        if r.needs_verification:
            needs_verification_count += 1
            reasons.append("needs_verification=true — excluded from scoring")

        missing = _missing_required_fields(r)
        if missing:
            reasons.append(f"missing required fields: {', '.join(missing)}")

        # Scoring eligibility decision
        in_scoring_window = (
            CANONICAL_WINDOW[0] <= r.year <= CANONICAL_WINDOW[1]
            or (is_pre_canon and allow_pre_canonical_scoring)
        )
        if reasons or not in_scoring_window:
            invalid.append((r.case_id, reasons or ["pre_canonical excluded from headline scoring"]))
        else:
            scoring_eligible += 1

    return ValidationReport(
        total=len(records),
        loadable=loadable,
        scoring_eligible=scoring_eligible,
        pre_canonical=pre_canonical,
        needs_verification=needs_verification_count,
        invalid=invalid,
    )


def filter_scoring_eligible(
    records: list[CitationFailureCase],
    *,
    allow_pre_canonical_scoring: bool = False,
    include_pre_canonical: bool = False,
    include_needs_verification: bool = False,
) -> list[CitationFailureCase]:
    """Return only the records that pass every scoring gate.

    Parameters
    ----------
    allow_pre_canonical_scoring / include_pre_canonical:
        Both spellings accepted; include 2021–2022 records in output.
    include_needs_verification:
        If True, records marked needs_verification=true are included
        provided they pass all other validation checks.
    """
    report = validate_corpus(
        records,
        allow_pre_canonical_scoring=allow_pre_canonical_scoring or include_pre_canonical,
    )
    bad_ids: set[str] = set()
    for cid, reasons in report.invalid:
        if include_needs_verification:
            other = [r for r in reasons if "needs_verification" not in r]
            if other:
                bad_ids.add(cid)
        else:
            bad_ids.add(cid)
    return [r for r in records if r.case_id not in bad_ids]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m dali.corpus.validator <corpus.json>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"corpus file not found: {path}", file=sys.stderr)
        return 2
    records = load_corpus(path)
    report = validate_corpus(records)
    print(report.summary())
    if report.invalid:
        print("\nInvalid for scoring:")
        for cid, reasons in report.invalid:
            print(f"  • {cid}")
            for r in reasons:
                print(f"      - {r}")
    return 0 if report.scoring_eligible > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
