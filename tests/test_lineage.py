"""Tests for mutation lineage — parent resolution, chain walking, cycle detection."""

import pytest

from corpus.lineage import derivatives_of, mutation_chain, resolve_parent
from corpus.schema import CitationFailureCase
from corpus.taxonomy import (
    ActualStatus,
    CitationFailureClass,
    CurationSource,
    MutationType,
    SourceType,
)


def _case(case_id, year=2023, parent_id=None, synthetic=False, mutation_type=None, **kwargs) -> CitationFailureCase:
    return CitationFailureCase(
        case_id=case_id,
        incident_name=f"Case {case_id}",
        year=year,
        jurisdiction="US-NY-SDNY",
        source_url="https://example.com",
        retrieval_date="2026-05-25",
        source_type=SourceType.SANCTIONS_ORDER,
        alleged_generated_citation="Fake v. Real, 999 F.3d 1",
        actual_status=ActualStatus.NONEXISTENT_AUTHORITY,
        failure_class=[CitationFailureClass.NONEXISTENT_AUTHORITY],
        ground_truth_notes="Test.",
        parent_incident_id=parent_id,
        synthetic_derivative=synthetic,
        mutation_type=mutation_type,
        **kwargs,
    )


@pytest.fixture
def corpus():
    tier1 = _case("mata-v-avianca-2023")
    derivative1 = _case(
        "mata-reporter-swap-001",
        year=2026,
        parent_id="mata-v-avianca-2023",
        synthetic=True,
        mutation_type=MutationType.REPORTER_SWAP,
    )
    derivative2 = _case(
        "mata-quote-fabrication-001",
        year=2026,
        parent_id="mata-v-avianca-2023",
        synthetic=True,
        mutation_type=MutationType.FABRICATED_QUOTATION,
    )
    unrelated = _case("park-v-kim-2024")
    return [tier1, derivative1, derivative2, unrelated]


class TestResolveParent:
    def test_no_parent(self, corpus):
        by_id = {r.case_id: r for r in corpus}
        assert resolve_parent(corpus[0], by_id) is None

    def test_resolves_parent(self, corpus):
        by_id = {r.case_id: r for r in corpus}
        parent = resolve_parent(corpus[1], by_id)
        assert parent is not None
        assert parent.case_id == "mata-v-avianca-2023"

    def test_unresolved_parent_returns_none(self):
        orphan = _case("orphan", parent_id="does-not-exist")
        by_id = {"orphan": orphan}
        assert resolve_parent(orphan, by_id) is None


class TestMutationChain:
    def test_tier1_has_empty_chain(self, corpus):
        by_id = {r.case_id: r for r in corpus}
        chain = mutation_chain(corpus[0], by_id)
        assert chain == []

    def test_tier2_chain_has_parent(self, corpus):
        by_id = {r.case_id: r for r in corpus}
        chain = mutation_chain(corpus[1], by_id)
        assert chain == ["mata-v-avianca-2023"]

    def test_depth_limit_prevents_runaway(self):
        """A deep chain (>16) should stop at the limit, not recurse infinitely."""
        records = [_case(str(i), parent_id=str(i + 1)) for i in range(20)]
        records.append(_case("20"))
        by_id = {r.case_id: r for r in records}
        chain = mutation_chain(records[0], by_id)
        assert len(chain) <= 16

    def test_cycle_detection(self):
        """Self-referential lineage must not infinite-loop."""
        a = _case("a", parent_id="b")
        b = _case("b", parent_id="a")
        by_id = {"a": a, "b": b}
        chain = mutation_chain(a, by_id)
        assert len(chain) <= 16


class TestDerivativesOf:
    def test_finds_both_derivatives(self, corpus):
        derivs = derivatives_of("mata-v-avianca-2023", corpus)
        ids = {d.case_id for d in derivs}
        assert "mata-reporter-swap-001" in ids
        assert "mata-quote-fabrication-001" in ids

    def test_unrelated_not_included(self, corpus):
        derivs = derivatives_of("mata-v-avianca-2023", corpus)
        assert all(d.synthetic_derivative for d in derivs)
        assert not any(d.case_id == "park-v-kim-2024" for d in derivs)

    def test_no_derivatives_returns_empty(self, corpus):
        assert derivatives_of("park-v-kim-2024", corpus) == []

    def test_non_synthetic_derivative_excluded(self):
        """Records with parent_incident_id but synthetic_derivative=False are NOT derivatives."""
        parent = _case("parent")
        non_synthetic = _case("non-synth", parent_id="parent", synthetic=False)
        assert derivatives_of("parent", [parent, non_synthetic]) == []
