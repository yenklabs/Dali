"""Unit tests for the six MCP tool implementations.

Tests target the pure-Python ``_*_impl`` functions, not the FastMCP wrapper.
No MCP runtime is required to run this suite.
"""

from __future__ import annotations

import json

import pytest

from dali_mcp.tools.corpus_tools import _check_case_impl
from dali_mcp.tools.integrity_tools import (
    _evaluate_case_impl,
    _verify_replay_impl,
)
from dali_mcp.tools.prompt_tools import (
    _bundle_prompts_impl,
    _check_prompt_impl,
    _new_prompt_impl,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

VALID_CASE = {
    "case_id": "mcp-test-001",
    "incident_name": "MCP smoke test",
    "year": 2024,
    "jurisdiction": "US-NY-SDNY",
    "source_url": "https://example.com/order/1",
    "retrieval_date": "2026-06-04",
    "source_type": "sanctions_order",
    "alleged_generated_citation": "Fake v. Real, 123 F.3d 456 (9th Cir. 2020)",
    "actual_status": "nonexistent_authority",
    "failure_class": ["nonexistent_authority", "reconstructability_failure"],
    "ground_truth_notes": "Synthetic test record for MCP integration.",
}


VALID_PROMPT = {
    "id": "case_citations_001",
    "category": "legal",
    "subcategory": "case_citations",
    "prompt": "Cite the controlling federal authority on personal jurisdiction over a non-resident defendant in a contract dispute.",
    "difficulty": "known_case",
}


# ---------------------------------------------------------------------------
# check_case
# ---------------------------------------------------------------------------

class TestCheckCase:
    def test_valid_record_passes(self):
        result = _check_case_impl(json.dumps(VALID_CASE))
        assert result["valid"] is True
        assert result["issues"] == []

    def test_missing_required_field_reports_issue(self):
        bad = {**VALID_CASE}
        del bad["case_id"]
        result = _check_case_impl(json.dumps(bad))
        assert result["valid"] is False
        assert any("case_id" in i for i in result["issues"])

    def test_invalid_json_reports_parse_error(self):
        result = _check_case_impl("{not json")
        assert result["valid"] is False
        assert any("JSON" in i for i in result["issues"])

    def test_unknown_failure_class_rejected(self):
        bad = {**VALID_CASE, "failure_class": ["not_a_real_class"]}
        result = _check_case_impl(json.dumps(bad))
        assert result["valid"] is False
        assert any("failure_class" in i for i in result["issues"])

    def test_year_out_of_range_rejected(self):
        bad = {**VALID_CASE, "year": 2010}
        result = _check_case_impl(json.dumps(bad))
        assert result["valid"] is False


# ---------------------------------------------------------------------------
# evaluate_case (the MCP equivalent of the demo)
# ---------------------------------------------------------------------------

class TestEvaluateCase:
    def test_valid_record_returns_full_result(self):
        result = _evaluate_case_impl(json.dumps(VALID_CASE))
        assert result["ok"] is True
        assert "result" in result
        r = result["result"]
        # Verdict fields
        assert r["case_id"] == "mcp-test-001"
        assert r["citation_exists"] is False  # nonexistent_authority
        assert r["defensibility_risk"] == "critical"
        # Cryptographic lineage — three hashes, all 64-char hex
        for hash_field in ("corpus_record_hash", "replay_hash", "evidence_hash"):
            assert hash_field in r
            assert len(r[hash_field]) == 64
            int(r[hash_field], 16)  # raises ValueError if not hex

    def test_summary_includes_hash_preview(self):
        result = _evaluate_case_impl(json.dumps(VALID_CASE))
        assert "replay_hash:" in result["summary"]
        assert "corpus_hash:" in result["summary"]
        assert "evidence_hash:" in result["summary"]

    def test_invalid_json_returns_parse_error(self):
        result = _evaluate_case_impl("{broken")
        assert result["ok"] is False
        assert "JSON" in result["error"]

    def test_malformed_record_returns_construct_error(self):
        # Missing required schema field that the dataclass needs
        bad = {"case_id": "x"}
        result = _evaluate_case_impl(json.dumps(bad))
        assert result["ok"] is False
        assert "summary" in result


# ---------------------------------------------------------------------------
# verify_replay (the MCP equivalent of --verify-replay)
# ---------------------------------------------------------------------------

class TestVerifyReplay:
    def test_clean_record_passes(self):
        result = _verify_replay_impl(json.dumps(VALID_CASE))
        assert result["ok"] is True
        assert result["replay_hash_match"] is True
        assert result["corpus_record_hash_match"] is True
        assert "PASS" in result["summary"]
        assert len(result["replay_hash"]) == 64

    def test_invalid_json_reports_parse_error(self):
        result = _verify_replay_impl("not-json")
        assert result["ok"] is False

    def test_returns_policy_version_string(self):
        result = _verify_replay_impl(json.dumps(VALID_CASE))
        assert result["policy_version"].startswith("taxonomy=")


# ---------------------------------------------------------------------------
# check_prompt
# ---------------------------------------------------------------------------

class TestCheckPrompt:
    def test_valid_prompt_passes(self):
        result = _check_prompt_impl(json.dumps(VALID_PROMPT))
        assert result["valid"] is True
        assert result["destination_file"].endswith("case_citations.jsonl")

    def test_short_prompt_rejected(self):
        bad = {**VALID_PROMPT, "prompt": "too short"}
        result = _check_prompt_impl(json.dumps(bad))
        assert result["valid"] is False
        assert any("too short" in i for i in result["issues"])

    def test_subcategory_must_match_category(self):
        bad = {**VALID_PROMPT, "category": "research"}  # case_citations is legal-only
        result = _check_prompt_impl(json.dumps(bad))
        assert result["valid"] is False
        assert any("subcategory" in i for i in result["issues"])


# ---------------------------------------------------------------------------
# new_prompt
# ---------------------------------------------------------------------------

class TestNewPrompt:
    def test_returns_template_with_destination(self):
        out = _new_prompt_impl("adversarial", "hallucination_prone", "adversarial")
        assert "hallucination_prone.jsonl" in out
        assert "<REPLACE" in out  # placeholder for the contributor to fill

    def test_invalid_category_reports_error(self):
        out = _new_prompt_impl("not_a_real_category", "x", "y")
        parsed = json.loads(out)
        assert "error" in parsed


# ---------------------------------------------------------------------------
# bundle_prompts
# ---------------------------------------------------------------------------

class TestBundlePrompts:
    def test_all_valid_ready_to_submit(self):
        batch = [VALID_PROMPT, {**VALID_PROMPT, "id": "case_citations_002"}]
        result = _bundle_prompts_impl(json.dumps(batch))
        assert result["total"] == 2
        assert result["valid"] == 2
        assert result["invalid"] == 0
        assert result["ready_to_submit"] is True

    def test_duplicate_ids_caught(self):
        batch = [VALID_PROMPT, VALID_PROMPT]  # same id twice
        result = _bundle_prompts_impl(json.dumps(batch))
        assert result["ready_to_submit"] is False
        assert any(
            "Duplicate" in msg
            for issues in result["issues_by_id"].values()
            for msg in issues
        )

    def test_mixed_batch_reports_invalid(self):
        batch = [
            VALID_PROMPT,
            {**VALID_PROMPT, "id": "p2", "prompt": "x"},  # too short
        ]
        result = _bundle_prompts_impl(json.dumps(batch))
        assert result["valid"] == 1
        assert result["invalid"] == 1
        assert result["ready_to_submit"] is False
