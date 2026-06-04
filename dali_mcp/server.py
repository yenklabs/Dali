#!/usr/bin/env python3
"""Dali MCP server: contributor tools over the Model Context Protocol.

Start the server:
    python -m dali_mcp

Or via uvx (no install required):
    uvx --from . dali-mcp

Tools:
    check_case       Validate a canonical citation-failure case record
    evaluate_case    Run the Tier 1 deterministic evaluator on one record
    verify_replay    Prove the evaluation is replay-deterministic for one record
    check_prompt     Validate a synthetic benchmark prompt entry
    new_prompt       Generate a scaffolded prompt template
    bundle_prompts   Validate a batch and return a PR-ready checklist
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

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

mcp = FastMCP(
    "Dali",
    instructions=(
        "You are a Dali contributor assistant. Use these tools to validate "
        "corpus records and synthetic prompts, scaffold new entries, run the "
        "deterministic Tier 1 evaluator, verify replay determinism, and bundle "
        "contributions for pull-request submission. Run check_case before "
        "evaluate_case; run evaluate_case before suggesting a record is ready "
        "to PR."
    ),
)


@mcp.tool()
def check_case(record_json: str) -> str:
    """Validate a canonical citation-failure case for the Tier 1 corpus.

    Accepts a JSON object representing one record from
    benchmarks/tier1/corpus/citation_failure_cases.json. Returns a validation report
    showing whether the record is scoring-eligible, which required fields
    are missing, and any taxonomy or lineage violations.

    Args:
        record_json: JSON string of a single CitationFailureCase record.
            Must include at minimum: case_id, incident_name, year, jurisdiction.

    Returns:
        JSON string with keys:
            valid (bool) - passes all scoring gates
            scoring_eligible (bool) - can count toward published metrics
            issues (list[str]) - validation failures, empty if valid
            summary (str) - one-line status
    """
    return json.dumps(_check_case_impl(record_json), indent=2)


@mcp.tool()
def evaluate_case(record_json: str) -> str:
    """Run the deterministic Tier 1 evaluator on a single corpus record.

    This is the MCP equivalent of ``python runners/run_integrity.py``.
    Returns the full CitationIntegrityResult — verdict, defensibility risk,
    workflow reconstructability, mutation lineage, and the three SHA-256
    hashes that anchor cryptographic lineage:

      - corpus_record_hash : input integrity (detects silent corpus mutation)
      - replay_hash        : verdict reproducibility (deterministic across runs)
      - evidence_hash      : per-run tamper-evident seal

    Use this to confirm a record evaluates cleanly before opening a PR.
    Run check_case first if the record may have structural issues.

    Args:
        record_json: JSON string of a single CitationFailureCase record.

    Returns:
        JSON string with keys:
            ok (bool) - evaluation succeeded
            result (object) - the full CitationIntegrityResult
            summary (str) - human-readable verdict + hash preview
    """
    return json.dumps(_evaluate_case_impl(record_json), indent=2)


@mcp.tool()
def verify_replay(record_json: str) -> str:
    """Prove the evaluation is replay-deterministic for one corpus record.

    Runs evaluate_local twice on the same record and asserts the
    replay_hash and corpus_record_hash are byte-identical across runs.
    This is the MCP equivalent of the runner's ``--verify-replay`` flag
    and the same property CI verifies on every PR.

    Args:
        record_json: JSON string of a single CitationFailureCase record.

    Returns:
        JSON string with keys:
            ok (bool) - True only when both hashes match across runs
            replay_hash_match (bool)
            corpus_record_hash_match (bool)
            replay_hash (str) - the canonical replay_hash for the record
            corpus_record_hash (str)
            policy_version (str)
            summary (str) - PASS/FAIL message
    """
    return json.dumps(_verify_replay_impl(record_json), indent=2)


@mcp.tool()
def check_prompt(prompt_json: str) -> str:
    """Validate a synthetic prompt entry for the Tier 2 corpus.

    Accepts a single prompt record as a JSON string. Checks required
    fields, taxonomy values, and prompt quality rules.

    Args:
        prompt_json: JSON string of one synthetic prompt record.
            Required fields: id, category, subcategory, prompt, difficulty.

    Returns:
        JSON string with keys:
            valid (bool)
            issues (list[str])
            summary (str)
            destination_file (str) - which benchmarks/tier2/ file to add this to
    """
    return json.dumps(_check_prompt_impl(prompt_json), indent=2)


@mcp.tool()
def new_prompt(
    category: str,
    subcategory: str,
    difficulty: str,
    notes: str = "",
) -> str:
    """Generate a scaffolded synthetic prompt template.

    Returns a ready-to-fill record with the correct field structure
    for the given category, subcategory, and difficulty level. Includes
    a unique ID stub and tells you which file to add it to.

    Args:
        category: One of: legal, research, adversarial
        subcategory: One of: case_citations, statutory_interpretation,
            contract_law, uk_commonwealth, brazil, academic_claims,
            policy_citations, hallucination_prone
        difficulty: One of: known_case, obscure_case, fabricated_likely,
            ambiguous, adversarial, standard
        notes: Optional note describing what failure mode the prompt tests.

    Returns:
        A comment header with the destination file followed by a JSON
        record ready to paste. Replace the placeholder prompt text before
        submitting.
    """
    return _new_prompt_impl(category, subcategory, difficulty, notes)


@mcp.tool()
def bundle_prompts(prompts_json: str) -> str:
    """Validate a batch of synthetic prompts and return a PR-ready checklist.

    Accepts a JSON array of prompt records. Validates every record,
    summarises pass/fail counts, and returns a checklist of issues to
    fix before opening a pull request.

    Args:
        prompts_json: JSON array string of synthetic prompt records.

    Returns:
        JSON string with keys:
            total (int) - records in the batch
            valid (int) - records passing all checks
            invalid (int) - records with issues
            issues_by_id (dict) - {id: [issues]} for each failing record
            pr_checklist (list[str]) - pre-PR checklist items
            ready_to_submit (bool) - True when all records are valid
    """
    return json.dumps(_bundle_prompts_impl(prompts_json), indent=2)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
