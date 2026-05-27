"""Tests for corpus validator — intake window, scoring eligibility, provenance gate."""

import pytest

from corpus.schema import CitationFailureCase, WorkflowContext
from corpus.taxonomy import (
    ActualStatus,
    CitationFailureClass,
    CurationSource,
    MutationType,
    SourceType,
)
from corpus.validator import (
    CANONICAL_WINDOW,
    INTAKE_WINDOW,
    filter_scoring_eligible,
    validate_corpus,
)


def _case(case_id="test-001", year=2023, **kwargs) -> CitationFailureCase:
    defaults = dict(
        case_id=case_id,
        incident_name="Test Case",
        year=year,
        jurisdiction="US-NY-SDNY",
        source_url="https://example.com/docket/1",
        retrieval_date="2026-05-25",
        source_type=SourceType.SANCTIONS_ORDER,
        alleged_generated_citation="Fake v. Real, 123 F.3d 456",
        actual_status=ActualStatus.NONEXISTENT_AUTHORITY,
        failure_class=[CitationFailureClass.NONEXISTENT_AUTHORITY],
        ground_truth_notes="Test.",
        curation_source=CurationSource.HAND_CURATED,
    )
    defaults.update(kwargs)
    return CitationFailureCase(**defaults)


class TestIntakeWindow:
    def test_year_in_window_accepted(self):
        records = [_case(year=2023), _case(case_id="b", year=2024)]
        report = validate_corpus(records)
        assert report.loadable == 2

    def test_year_below_window_excluded(self):
        records = [_case(year=2020)]
        report = validate_corpus(records)
        assert report.scoring_eligible == 0
        assert any("2020" in r for _, reasons in report.invalid for r in reasons)

    def test_year_above_window_excluded(self):
        records = [_case(year=2027)]
        report = validate_corpus(records)
        assert report.scoring_eligible == 0

    def test_boundary_2021_pre_canonical(self):
        records = [_case(year=2021)]
        report = validate_corpus(records)
        assert report.pre_canonical == 1
        assert report.scoring_eligible == 0

    def test_boundary_2026_eligible(self):
        records = [_case(year=2026)]
        report = validate_corpus(records)
        assert report.scoring_eligible == 1


class TestScoringEligibility:
    def test_needs_verification_excluded(self):
        records = [_case(needs_verification=True)]
        report = validate_corpus(records)
        assert report.scoring_eligible == 0
        assert any("needs_verification" in r for _, reasons in report.invalid for r in reasons)

    def test_missing_source_url_excluded(self):
        records = [_case(source_url=None)]
        report = validate_corpus(records)
        assert report.scoring_eligible == 0

    def test_missing_alleged_citation_excluded(self):
        records = [_case(alleged_generated_citation=None)]
        report = validate_corpus(records)
        assert report.scoring_eligible == 0

    def test_empty_failure_class_excluded(self):
        records = [_case(failure_class=[])]
        report = validate_corpus(records)
        assert report.scoring_eligible == 0

    def test_full_record_eligible(self):
        records = [_case()]
        report = validate_corpus(records)
        assert report.scoring_eligible == 1

    def test_include_pre_canonical_flag(self):
        records = [_case(year=2021)]
        report = validate_corpus(records, allow_pre_canonical_scoring=True)
        assert report.scoring_eligible == 1


class TestLineageValidation:
    def test_synthetic_without_parent_invalid(self):
        records = [_case(synthetic_derivative=True, parent_incident_id=None)]
        report = validate_corpus(records)
        assert any("parent_incident_id" in r for _, reasons in report.invalid for r in reasons)

    def test_synthetic_without_mutation_type_invalid(self):
        records = [
            _case(case_id="parent"),
            _case(
                case_id="child",
                year=2026,
                synthetic_derivative=True,
                parent_incident_id="parent",
                mutation_type=None,
            ),
        ]
        report = validate_corpus(records)
        invalid_ids = {cid for cid, _ in report.invalid}
        assert "child" in invalid_ids

    def test_unresolved_parent_invalid(self):
        records = [_case(parent_incident_id="does-not-exist")]
        report = validate_corpus(records)
        assert any("does-not-exist" in r for _, reasons in report.invalid for r in reasons)

    def test_valid_lineage_chain(self):
        parent = _case(case_id="parent-001")
        child = _case(
            case_id="child-001",
            year=2026,
            synthetic_derivative=True,
            parent_incident_id="parent-001",
            mutation_type=MutationType.REPORTER_SWAP,
        )
        report = validate_corpus([parent, child])
        assert report.scoring_eligible == 2


class TestFilterScoringEligible:
    def test_returns_only_eligible(self):
        records = [
            _case(case_id="good", year=2023),
            _case(case_id="bad", year=2023, needs_verification=True),
        ]
        eligible = filter_scoring_eligible(records)
        assert len(eligible) == 1
        assert eligible[0].case_id == "good"

    def test_include_pre_canonical(self):
        records = [_case(case_id="old", year=2021), _case(case_id="new", year=2023)]
        eligible = filter_scoring_eligible(records, allow_pre_canonical_scoring=True)
        assert len(eligible) == 2


class TestValidationReport:
    def test_summary_string(self):
        records = [_case()]
        report = validate_corpus(records)
        summary = report.summary()
        assert "1 records loaded" in summary
        assert "scoring-eligible" in summary
