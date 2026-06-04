"""Tests for taxonomy enums — closure, uniqueness, descriptions."""

import pytest

from dali.corpus.taxonomy import (
    FAILURE_CLASS_DESCRIPTIONS,
    ActualStatus,
    AnnotationConfidence,
    CitationFailureClass,
    CurationSource,
    DefensibilityRisk,
    MutationType,
    SourceType,
)


class TestCitationFailureClass:
    def test_twelve_classes(self):
        assert len(CitationFailureClass) == 12

    def test_all_values_unique(self):
        values = [c.value for c in CitationFailureClass]
        assert len(values) == len(set(values))

    def test_nonexistent_authority_present(self):
        assert CitationFailureClass.NONEXISTENT_AUTHORITY.value == "nonexistent_authority"

    def test_all_classes_have_descriptions(self):
        for cls in CitationFailureClass:
            assert cls in FAILURE_CLASS_DESCRIPTIONS, f"missing description for {cls}"
            assert len(FAILURE_CLASS_DESCRIPTIONS[cls]) > 10

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            CitationFailureClass("not_a_real_class")

    def test_expected_classes_present(self):
        expected = {
            "nonexistent_authority",
            "fabricated_quote",
            "citation_mutation",
            "parallel_citation_mismatch",
            "wrong_jurisdiction",
            "temporal_validity_failure",
            "semantic_misalignment",
            "provenance_gap",
            "reconstructability_failure",
        }
        actual = {c.value for c in CitationFailureClass}
        for e in expected:
            assert e in actual, f"expected failure class not found: {e}"


class TestMutationType:
    def test_eight_types(self):
        assert len(MutationType) == 8

    def test_all_values_unique(self):
        values = [m.value for m in MutationType]
        assert len(values) == len(set(values))

    def test_reporter_swap_present(self):
        assert MutationType.REPORTER_SWAP.value == "reporter_swap"

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            MutationType("not_a_real_type")


class TestDefensibilityRisk:
    def test_four_levels(self):
        assert len(DefensibilityRisk) == 4

    def test_values(self):
        values = {r.value for r in DefensibilityRisk}
        assert values == {"critical", "high", "medium", "low"}


class TestActualStatus:
    def test_nonexistent_authority_present(self):
        assert ActualStatus.NONEXISTENT_AUTHORITY.value == "nonexistent_authority"


class TestSourceType:
    def test_sanctions_order_present(self):
        assert SourceType.SANCTIONS_ORDER.value == "sanctions_order"
