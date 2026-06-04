"""End-to-end tests for the tools.cli short-verb dispatcher.

Each verb is tested against the same canonical corpus the CLI demo uses.
The CLI is a thin wrapper over existing logic, so these tests primarily
verify routing, argument forwarding, and exit codes — not re-test the
underlying evaluator (covered by ``test_run_integrity.py``).
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from tools.cli import main as cli_main

CORPUS_PATH = Path("data/benchmark/tier1/corpus/citation_failure_cases.json")


# ---------------------------------------------------------------------------
# lint
# ---------------------------------------------------------------------------

class TestLint:
    def test_lint_canonical_corpus_passes(self):
        if not CORPUS_PATH.is_file():
            pytest.skip("seed corpus not found")
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cli_main(["lint", str(CORPUS_PATH)])
        assert exit_code == 0
        out = buf.getvalue()
        assert "scoring-eligible:" in out

    def test_lint_uses_default_path_when_omitted(self):
        if not CORPUS_PATH.is_file():
            pytest.skip("seed corpus not found")
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cli_main(["lint"])
        assert exit_code == 0

    def test_lint_missing_file_returns_error(self, tmp_path):
        exit_code = cli_main(["lint", str(tmp_path / "nonexistent.json")])
        assert exit_code == 1


# ---------------------------------------------------------------------------
# score
# ---------------------------------------------------------------------------

class TestScore:
    def test_score_canonical_corpus(self, tmp_path):
        if not CORPUS_PATH.is_file():
            pytest.skip("seed corpus not found")
        out = tmp_path / "integrity.json"
        exit_code = cli_main([
            "score", str(CORPUS_PATH),
            "--output", str(out),
        ])
        assert exit_code == 0
        data = json.loads(out.read_text())
        # All three cryptographic hashes must surface through the CLI wrapper
        first = data["results"][0]
        for hash_field in ("corpus_record_hash", "replay_hash", "evidence_hash"):
            assert hash_field in first
            assert len(first[hash_field]) == 64


# ---------------------------------------------------------------------------
# replay (the determinism gate)
# ---------------------------------------------------------------------------

class TestReplay:
    def test_replay_canonical_corpus_passes(self, tmp_path):
        if not CORPUS_PATH.is_file():
            pytest.skip("seed corpus not found")
        out = tmp_path / "integrity.json"
        exit_code = cli_main([
            "replay", str(CORPUS_PATH),
            "--output", str(out),
        ])
        assert exit_code == 0, (
            "replay must pass on the canonical corpus — if this fails the "
            "determinism property is broken"
        )


# ---------------------------------------------------------------------------
# probe (single record + JSONL)
# ---------------------------------------------------------------------------

VALID_PROMPT = {
    "id": "cli_probe_test_001",
    "category": "legal",
    "subcategory": "case_citations",
    "prompt": "Cite the controlling federal authority on personal jurisdiction in a contract dispute.",
    "difficulty": "known_case",
}


class TestProbe:
    def test_probe_single_json_file(self, tmp_path):
        path = tmp_path / "prompt.json"
        path.write_text(json.dumps(VALID_PROMPT))
        exit_code = cli_main(["probe", str(path)])
        assert exit_code == 0

    def test_probe_jsonl_with_mixed_validity(self, tmp_path, capsys):
        path = tmp_path / "prompts.jsonl"
        bad = {**VALID_PROMPT, "id": "p2", "prompt": "x"}  # too short
        path.write_text(
            json.dumps(VALID_PROMPT) + "\n" + json.dumps(bad) + "\n"
        )
        exit_code = cli_main(["probe", str(path)])
        assert exit_code == 2  # mixed batch → non-zero exit
        captured = capsys.readouterr().out
        assert "FAIL" in captured
        assert "OK" in captured


# ---------------------------------------------------------------------------
# draft
# ---------------------------------------------------------------------------

class TestDraft:
    def test_draft_emits_template(self, capsys):
        exit_code = cli_main([
            "draft",
            "--category", "adversarial",
            "--subcategory", "hallucination_prone",
            "--difficulty", "adversarial",
        ])
        assert exit_code == 0
        captured = capsys.readouterr().out
        assert "hallucination_prone" in captured
        assert "<REPLACE" in captured


# ---------------------------------------------------------------------------
# pack
# ---------------------------------------------------------------------------

class TestPack:
    def test_pack_clean_batch(self, tmp_path, capsys):
        path = tmp_path / "prompts.jsonl"
        path.write_text(
            json.dumps(VALID_PROMPT) + "\n"
            + json.dumps({**VALID_PROMPT, "id": "cli_pack_002"}) + "\n"
        )
        exit_code = cli_main(["pack", str(path)])
        assert exit_code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["ready_to_submit"] is True
        assert out["total"] == 2
