#!/usr/bin/env python3
"""Dali MCP server: contributor tools over the Model Context Protocol.

Start the server:
    python -m dali_mcp

Or via uvx (no install required):
    uvx --from . dali-mcp

Tools:
    check_case      Validate a canonical citation-failure case record
    check_prompt    Validate a synthetic benchmark prompt entry
    new_prompt      Generate a scaffolded prompt template
    bundle_prompts  Validate a batch and return a PR-ready checklist
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

from dali_mcp.tools.corpus_tools import _check_case_impl
from dali_mcp.tools.prompt_tools import (
    _bundle_prompts_impl,
    _check_prompt_impl,
    _new_prompt_impl,
)

mcp = FastMCP(
    "Dali",
    instructions=(
        "You are a Dali contributor assistant. Use these tools to validate "
        "corpus records and synthetic prompts, scaffold new entries, and "
        "bundle contributions for pull-request submission. "
        "Run check_case or check_prompt before calling bundle_prompts."
    ),
)


@mcp.tool()
def check_case(record_json: str) -> str:
    """Validate a canonical citation-failure case for the Tier 1 corpus.

    Accepts a JSON object representing one record from
    data/public/citation_failure_cases.json. Returns a validation report
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
            destination_file (str) - which synthetic/ file to add this to
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
