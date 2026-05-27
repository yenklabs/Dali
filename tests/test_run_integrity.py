"""End-to-end test for run_integrity.py — local reference evaluator."""

import json
import tempfile
from pathlib import Path

import pytest

from corpus.schema import CitationFailureCase
from corpus.taxonomy import (
    ActualStatus,
    CitationFailureClass,
    DefensibilityRisk,
    MutationType,
    SourceType,
)
from runners.run_integrity import evaluate_local, main as run_main


def _case(**kwargs) -> CitationFailureCase:
    defaults = dict(
        case_id="e2e-001",
        incident_name="End-to-end Test",
        year=2023,
        jurisdiction="US-NY-SDNY",
        source_url="https://example.com/docket/1",
        retrieval_date="2026-05-25",
        source_type=SourceType.SANCTIONS_ORDER,
        alleged_generated_citation="Fake v. Real, 123 F.3d 456 (9th Cir. 2020)",
        actual_status=ActualStatus.NONEXISTENT_AUTHORITY,
        failure_class=[
            CitationFailureClass.NONEXISTENT_AUTHORITY,
            CitationFailureClass.RECONSTRUCTABILITY_FAILURE,
        ],
        ground_truth_notes="Test record for runner.",
    )
    defaults.update(kwargs)
    return CitationFailureCase(**defaults)


POLICY_V = "taxonomy=2.0.0;rubric=1.0.0;scoring=1.0.0;normalization=1.0.0;schema=1.0.0"


class TestEvaluateLocal:
    def test_returns_result(self):
        case = _case()
        result = evaluate_local(case, POLICY_V, {case.case_id: case})
        assert result.case_id == "e2e-001"

    def test_nonexistent_authority_not_exists(self):
        case = _case()
        result = evaluate_local(case, POLICY_V, {case.case_id: case})
        assert result.citation_exists is False

    def test_critical_risk_for_nonexistent_plus_workflow_gap(self):
        case = _case()
        result = evaluate_local(case, POLICY_V, {case.case_id: case})
        assert result.defensibility_risk == DefensibilityRisk.CRITICAL

    def test_high_risk_without_workflow_gap(self):
        case = _case(failure_class=[CitationFailureClass.NONEXISTENT_AUTHORITY])
        result = evaluate_local(case, POLICY_V, {case.case_id: case})
        assert result.defensibility_risk == DefensibilityRisk.HIGH

    def test_policy_version_stamped(self):
        case = _case()
        result = evaluate_local(case, POLICY_V, {case.case_id: case})
        assert result.policy_version == POLICY_V

    def test_evidence_hash_is_hex(self):
        case = _case()
        result = evaluate_local(case, POLICY_V, {case.case_id: case})
        assert len(result.evidence_hash) == 64
        int(result.evidence_hash, 16)

    def test_evidence_hash_deterministic_same_timestamp(self):
        """Same case + same policy + same timestamp → same hash."""
        case = _case()
        by_id = {case.case_id: case}
        r1 = evaluate_local(case, POLICY_V, by_id)
        # Overwrite timestamp to force determinism check
        ts = r1.run_timestamp
        import hashlib, json
        expected = hashlib.sha256(
            json.dumps(
                {"case_id": "e2e-001", "policy_version": POLICY_V, "run_timestamp": ts},
                sort_keys=True, separators=(",", ":"),
            ).encode()
        ).hexdigest()
        assert r1.evidence_hash == expected

    def test_misaligned_for_nonexistent(self):
        case = _case()
        result = evaluate_local(case, POLICY_V, {case.case_id: case})
        assert result.semantic_alignment == "misaligned"

    def test_fabricated_quote_fidelity(self):
        case = _case()
        result = evaluate_local(case, POLICY_V, {case.case_id: case})
        assert result.quote_fidelity == "fabricated"

    def test_infeasible_recovery_for_critical(self):
        case = _case()
        result = evaluate_local(case, POLICY_V, {case.case_id: case})
        assert result.verification_recoverable == "infeasible"

    def test_mutation_lineage_empty_for_tier1(self):
        case = _case()
        result = evaluate_local(case, POLICY_V, {case.case_id: case})
        assert result.mutation_lineage == []

    def test_mutation_lineage_populated_for_derivative(self):
        parent = _case(case_id="parent-001")
        child = _case(
            case_id="child-001",
            year=2026,
            failure_class=[CitationFailureClass.CITATION_MUTATION],
            parent_incident_id="parent-001",
            synthetic_derivative=True,
            mutation_type=MutationType.REPORTER_SWAP,
        )
        by_id = {"parent-001": parent, "child-001": child}
        result = evaluate_local(child, POLICY_V, by_id)
        assert "parent-001" in result.mutation_lineage

    def test_medium_risk_citation_mutation(self):
        from corpus.schema import WorkflowContext
        wf = WorkflowContext(source_chain_complete=True)
        case = _case(
            failure_class=[CitationFailureClass.CITATION_MUTATION],
            actual_status=ActualStatus.PARALLEL_CITATION_MISMATCH,
            workflow_context=wf,
        )
        result = evaluate_local(case, POLICY_V, {case.case_id: case})
        assert result.defensibility_risk == DefensibilityRisk.MEDIUM


class TestRunMain:
    def test_runs_against_seed_corpus(self, tmp_path):
        corpus_path = Path("data/public/citation_failure_cases.json")
        if not corpus_path.is_file():
            pytest.skip("seed corpus not found")

        output = tmp_path / "integrity.json"
        exit_code = run_main([
            "--corpus", str(corpus_path),
            "--output", str(output),
        ])
        assert exit_code == 0
        assert output.is_file()

        data = json.loads(output.read_text())
        assert "results" in data
        assert len(data["results"]) > 0
        assert data["policy_version"].startswith("taxonomy=")
        assert data["evaluator"] == "local-reference"

    def test_result_shape(self, tmp_path):
        corpus_path = Path("data/public/citation_failure_cases.json")
        if not corpus_path.is_file():
            pytest.skip("seed corpus not found")

        output = tmp_path / "integrity.json"
        run_main(["--corpus", str(corpus_path), "--output", str(output)])
        data = json.loads(output.read_text())

        required_fields = {
            "case_id", "citation_exists", "authority_reachable",
            "semantic_alignment", "quote_fidelity", "defensibility_risk",
            "workflow_reconstructable", "verification_recoverable",
            "mutation_lineage", "policy_version", "evidence_hash", "run_timestamp",
        }
        for result in data["results"]:
            for field in required_fields:
                assert field in result, f"missing field {field!r} in result for {result.get('case_id')}"

    def test_missing_corpus_returns_error(self, tmp_path):
        output = tmp_path / "out.json"
        exit_code = run_main([
            "--corpus", str(tmp_path / "nonexistent.json"),
            "--output", str(output),
        ])
        assert exit_code == 1
