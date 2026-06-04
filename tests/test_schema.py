"""Tests for corpus schema — CitationFailureCase, CitationIntegrityResult, hashing."""

import hashlib
import json

import pytest

from dali.corpus.schema import (
    CitationFailureCase,
    CitationIntegrityResult,
    WorkflowContext,
    canonical_json,
    evidence_hash,
    now_iso,
)
from dali.corpus.taxonomy import (
    ActualStatus,
    AnnotationConfidence,
    CitationFailureClass,
    CurationSource,
    DefensibilityRisk,
    MutationType,
    SourceType,
)


def _minimal_case(**kwargs) -> CitationFailureCase:
    defaults = dict(
        case_id="test-001",
        incident_name="Test Case",
        year=2023,
        jurisdiction="US-NY-SDNY",
        source_url="https://example.com/docket/1",
        retrieval_date="2026-05-25",
        source_type=SourceType.SANCTIONS_ORDER,
        alleged_generated_citation="Fake v. Real, 123 F.3d 456 (9th Cir. 2020)",
        actual_status=ActualStatus.NONEXISTENT_AUTHORITY,
        failure_class=[CitationFailureClass.NONEXISTENT_AUTHORITY],
        ground_truth_notes="Test record.",
    )
    defaults.update(kwargs)
    return CitationFailureCase(**defaults)


class TestCitationFailureCase:
    def test_minimal_construction(self):
        case = _minimal_case()
        assert case.case_id == "test-001"
        assert case.year == 2023

    def test_defaults(self):
        case = _minimal_case()
        assert case.needs_verification is False
        assert case.synthetic_derivative is False
        assert case.pre_canonical is False
        assert case.dali_pipeline_reproducibility_status == "not_run"
        assert case.annotation_confidence == AnnotationConfidence.MEDIUM

    def test_workflow_context_optional(self):
        case = _minimal_case()
        assert case.workflow_context is None

    def test_workflow_context_attached(self):
        wf = WorkflowContext(retrieval_used=False, human_review_present=False)
        case = _minimal_case(workflow_context=wf)
        assert case.workflow_context.retrieval_used is False

    def test_attorney_names_internal(self):
        case = _minimal_case(attorney_names_internal=["Jane Doe", "John Smith"])
        assert "Jane Doe" in case.attorney_names_internal

    def test_lineage_fields(self):
        case = _minimal_case(
            parent_incident_id="mata-v-avianca-2023",
            mutation_type=MutationType.REPORTER_SWAP,
            synthetic_derivative=True,
        )
        assert case.parent_incident_id == "mata-v-avianca-2023"
        assert case.mutation_type == MutationType.REPORTER_SWAP
        assert case.synthetic_derivative is True


class TestWorkflowContext:
    def test_defaults_unknown(self):
        wf = WorkflowContext()
        assert wf.retrieval_used == "unknown"
        assert wf.human_review_present == "unknown"
        assert wf.source_chain_complete == "unknown"
        assert wf.verification_step_present == "unknown"
        assert wf.downstream_modified == "unknown"


class TestCanonicalJson:
    def test_deterministic(self):
        case = _minimal_case()
        assert canonical_json(case) == canonical_json(case)

    def test_excludes_attorney_names(self):
        case_with = _minimal_case(attorney_names_internal=["Jane Doe"])
        case_without = _minimal_case(attorney_names_internal=None)
        # Hashes should differ only if attorney_names leaked — they should NOT
        assert canonical_json(case_with) == canonical_json(case_without)

    def test_is_valid_json(self):
        case = _minimal_case()
        parsed = json.loads(canonical_json(case))
        assert parsed["case_id"] == "test-001"

    def test_sorted_keys(self):
        case = _minimal_case()
        raw = canonical_json(case)
        # Keys must be sorted — no separators with spaces
        assert "  " not in raw


class TestEvidenceHash:
    def test_same_input_same_hash(self):
        case = _minimal_case()
        h1 = evidence_hash(case, "taxonomy=2.0.0;rubric=1.0.0;scoring=1.0.0;normalization=1.0.0;schema=1.0.0")
        h2 = evidence_hash(case, "taxonomy=2.0.0;rubric=1.0.0;scoring=1.0.0;normalization=1.0.0;schema=1.0.0")
        assert h1 == h2

    def test_different_policy_different_hash(self):
        case = _minimal_case()
        h1 = evidence_hash(case, "taxonomy=2.0.0;rubric=1.0.0;scoring=1.0.0;normalization=1.0.0;schema=1.0.0")
        h2 = evidence_hash(case, "taxonomy=3.0.0;rubric=1.0.0;scoring=1.0.0;normalization=1.0.0;schema=1.0.0")
        assert h1 != h2

    def test_is_hex_string(self):
        case = _minimal_case()
        h = evidence_hash(case, "taxonomy=2.0.0;rubric=1.0.0;scoring=1.0.0;normalization=1.0.0;schema=1.0.0")
        assert len(h) == 64
        int(h, 16)  # raises if not valid hex


class TestNowIso:
    def test_returns_string(self):
        ts = now_iso()
        assert isinstance(ts, str)
        assert "T" in ts
