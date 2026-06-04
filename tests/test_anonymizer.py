"""Tests for anonymizer — no attorney name leaks in public artifact."""

import json
from pathlib import Path

import pytest

from dali.corpus.anonymizer import anonymize_corpus, detect_leaks
from dali.corpus.loader import load_corpus
from dali.corpus.schema import CitationFailureCase
from dali.corpus.taxonomy import (
    ActualStatus,
    CitationFailureClass,
    CurationSource,
    SourceType,
)


ATTORNEY_NAMES = [
    "Steven A. Schwartz",
    "Steven Schwartz",
    "Peter LoDuca",
    "David M. Schwartz",
    "David Schwartz",
    "E. Danya Perry",
    "Danya Perry",
]

ATTORNEY_BLOCKLIST = Path("data/benchmark/tier1/corpus/internal/attorney_names_blocklist.txt")


def _make_case_with_names() -> CitationFailureCase:
    """Record with attorney names embedded in every free-text field."""
    return CitationFailureCase(
        case_id="test-anon-001",
        incident_name="Test Incident (anonymizer)",
        year=2023,
        jurisdiction="US-NY-SDNY",
        source_url="https://example.com/docket/99",
        retrieval_date="2026-05-25",
        source_type=SourceType.SANCTIONS_ORDER,
        alleged_generated_citation="Fake v. Real, 111 F.3d 222",
        actual_status=ActualStatus.NONEXISTENT_AUTHORITY,
        failure_class=[CitationFailureClass.NONEXISTENT_AUTHORITY],
        ground_truth_notes="Steven Schwartz used ChatGPT and filed fake citations.",
        judicial_response="Court ordered Steven A. Schwartz to explain himself.",
        sanctions_or_consequence="Peter LoDuca was also sanctioned jointly.",
        attorney_names_internal=["Steven A. Schwartz", "Peter LoDuca"],
    )


class TestAnonymizeCorpus:
    def test_returns_list_of_dicts(self):
        cases = [_make_case_with_names()]
        out = anonymize_corpus(cases, extra_names=ATTORNEY_NAMES)
        assert isinstance(out, list)
        assert len(out) == 1
        assert isinstance(out[0], dict)

    def test_attorney_names_field_absent(self):
        """attorney_names_internal must be stripped from output."""
        cases = [_make_case_with_names()]
        out = anonymize_corpus(cases, extra_names=ATTORNEY_NAMES)
        assert "attorney_names_internal" not in out[0]

    def test_ground_truth_notes_cleaned(self):
        cases = [_make_case_with_names()]
        out = anonymize_corpus(cases, extra_names=ATTORNEY_NAMES)
        notes = out[0].get("ground_truth_notes", "")
        assert "Steven Schwartz" not in notes
        assert "counsel of record" in notes.lower() or "filing attorney" in notes.lower()

    def test_judicial_response_cleaned(self):
        cases = [_make_case_with_names()]
        out = anonymize_corpus(cases, extra_names=ATTORNEY_NAMES)
        judicial = out[0].get("judicial_response", "")
        assert "Steven A. Schwartz" not in judicial

    def test_sanctions_cleaned(self):
        cases = [_make_case_with_names()]
        out = anonymize_corpus(cases, extra_names=ATTORNEY_NAMES)
        sanctions = out[0].get("sanctions_or_consequence", "")
        assert "Peter LoDuca" not in sanctions

    def test_case_id_preserved(self):
        cases = [_make_case_with_names()]
        out = anonymize_corpus(cases, extra_names=ATTORNEY_NAMES)
        assert out[0]["case_id"] == "test-anon-001"

    def test_no_redaction_marks(self):
        """Anonymizer must replace with neutral language, not [REDACTED]."""
        cases = [_make_case_with_names()]
        out = anonymize_corpus(cases, extra_names=ATTORNEY_NAMES)
        result_json = json.dumps(out[0])
        assert "[REDACTED]" not in result_json

    def test_extra_names_blocklist(self):
        """Names from extra_names param are scrubbed even if not in attorney_names_internal."""
        case = CitationFailureCase(
            case_id="test-anon-002",
            incident_name="Danya Perry filed a brief.",
            year=2023,
            jurisdiction="US-2D-CIR",
            source_url="https://example.com",
            retrieval_date="2026-05-25",
            source_type=SourceType.JUDICIAL_OPINION,
            alleged_generated_citation="Fake v. Real",
            actual_status=ActualStatus.NONEXISTENT_AUTHORITY,
            failure_class=[CitationFailureClass.NONEXISTENT_AUTHORITY],
            ground_truth_notes="E. Danya Perry submitted AI-generated citations.",
            attorney_names_internal=[],  # not listed internally
        )
        out = anonymize_corpus([case], extra_names=["E. Danya Perry", "Danya Perry"])
        assert "Danya Perry" not in out[0].get("ground_truth_notes", "")
        assert "Danya Perry" not in out[0].get("incident_name", "")


class TestDetectLeaks:
    def test_detects_name_in_dict(self):
        """detect_leaks works on raw dicts (output of anonymize_corpus)."""
        leaked_dict = {
            "case_id": "test",
            "ground_truth_notes": "Steven Schwartz did this.",
        }
        leaks = detect_leaks([leaked_dict], ["Steven Schwartz"])
        assert len(leaks) > 0

    def test_no_leaks_after_anonymization(self):
        cases = [_make_case_with_names()]
        anon = anonymize_corpus(cases, extra_names=ATTORNEY_NAMES)
        leaks = detect_leaks(anon, ATTORNEY_NAMES)
        assert leaks == [], f"attorney name leaked after anonymization: {leaks}"

    def test_empty_names_returns_empty(self):
        dicts = [{"case_id": "x", "notes": "Steven Schwartz was here"}]
        leaks = detect_leaks(dicts, [])
        assert leaks == []

    def test_nested_field_detected(self):
        nested = {
            "case_id": "x",
            "workflow_context": {"ai_system_type": "Steven Schwartz's tool"},
        }
        leaks = detect_leaks([nested], ["Steven Schwartz"])
        assert any("workflow_context" in l for l in leaks)


class TestBlocklistFile:
    def test_blocklist_exists(self):
        assert ATTORNEY_BLOCKLIST.is_file(), f"blocklist not found at {ATTORNEY_BLOCKLIST}"

    def test_blocklist_nonempty(self):
        names = ATTORNEY_BLOCKLIST.read_text().strip().splitlines()
        assert len(names) > 0

    def test_known_names_in_blocklist(self):
        names = ATTORNEY_BLOCKLIST.read_text().strip().splitlines()
        assert "Steven A. Schwartz" in names
        assert "Peter LoDuca" in names


class TestEndToEndAnonymization:
    """Load the real corpus, anonymize it, and assert zero name leaks."""

    def test_real_corpus_no_leaks(self):
        if not ATTORNEY_BLOCKLIST.is_file():
            pytest.skip("blocklist not found")
        blocklist = ATTORNEY_BLOCKLIST.read_text().strip().splitlines()
        corpus_path = Path("data/benchmark/tier1/corpus/internal/citation_failure_cases.json")
        if not corpus_path.is_file():
            pytest.skip("corpus not found")

        records = load_corpus(corpus_path)
        anon = anonymize_corpus(records, extra_names=blocklist)
        leaks = detect_leaks(anon, blocklist)
        assert leaks == [], f"name leak(s) in public artifact: {leaks}"
