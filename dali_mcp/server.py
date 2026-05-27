#!/usr/bin/env python3
"""Dali MCP server — contributor tools over the Model Context Protocol.

Start the server:
    python -m dali_mcp

Or via uvx (no install required):
    uvx --from . dali-mcp

Tools exposed:
    validate_corpus_record    — validate a CitationFailureCase JSON object
    validate_prompt_jsonl     — validate a synthetic prompt JSONL entry
    generate_prompt_template  — scaffold a new synthetic prompt
    create_contribution_bundle — validate + summarise a batch for PR submission
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

from dali_mcp.tools.corpus_tools import (
    _validate_corpus_record_impl,
)
from dali_mcp.tools.prompt_tools import (
    _create_contribution_bundle_impl,
    _generate_prompt_template_impl,
    _validate_prompt_jsonl_impl,
)

mcp = FastMCP(
    "Dali",
    instructions=(
        "You are a Dali contributor assistant. Use these tools to validate "
        "corpus records and synthetic prompts, scaffold new entries, and "
        "bundle contributions for pull-request submission. "
        "Always run validate_corpus_record or validate_prompt_jsonl before "
        "creating a bundle."
    ),
)


@mcp.tool()
def validate_corpus_record(record_json: str) -> str:
    """Validate a CitationFailureCase corpus record.

    Accepts a JSON object (as a string) representing one record from
    data/public/citation_failure_cases.json. Returns a validation report
    indicating whether the record is scoring-eligible, what required fields
    are missing, and any taxonomy or lineage violations.

    Args:
        record_json: JSON string of a single CitationFailureCase record.
            Must include at minimum: case_id, incident_name, year, jurisdiction.

    Returns:
        A JSON string with keys:
            valid (bool) — passes all scoring gates
            scoring_eligible (bool) — can count toward published metrics
            issues (list[str]) — list of validation failures, empty if valid
            summary (str) — human-readable one-line status
    """
    return json.dumps(_validate_corpus_record_impl(record_json), indent=2)


@mcp.tool()
def validate_prompt_jsonl(prompt_json: str) -> str:
    """Validate a synthetic prompt JSONL entry for the Tier 2 corpus.

    Accepts a single JSONL record (as a JSON string). Checks required fields,
    taxonomy values, and prompt quality rules.

    Args:
        prompt_json: JSON string of one synthetic prompt record.
            Required fields: id, category, subcategory, prompt, difficulty.

    Returns:
        A JSON string with keys:
            valid (bool)
            issues (list[str])
            summary (str)
    """
    return json.dumps(_validate_prompt_jsonl_impl(prompt_json), indent=2)


@mcp.tool()
def generate_prompt_template(
    category: str,
    subcategory: str,
    difficulty: str,
    notes: str = "",
) -> str:
    """Generate a scaffolded synthetic prompt template.

    Returns a ready-to-fill JSONL record with the correct field structure
    for the given category, subcategory, and difficulty. Includes a unique
    ID stub based on the subcategory and valid taxonomy values.

    Args:
        category: One of: legal, research, adversarial
        subcategory: One of: case_citations, statutory_interpretation,
            contract_law, uk_commonwealth, brazil, academic_claims,
            policy_citations, hallucination_prone
        difficulty: One of: known_case, obscure_case, fabricated_likely,
            ambiguous, adversarial, standard
        notes: Optional guidance note for what the prompt should test.
            Appears in the 'notes' field of the template.

    Returns:
        A JSONL-formatted JSON string ready to paste into the appropriate
        synthetic/ file. The 'prompt' field contains a placeholder to replace.
    """
    return _generate_prompt_template_impl(category, subcategory, difficulty, notes)


@mcp.tool()
def create_contribution_bundle(prompts_json: str) -> str:
    """Validate and summarise a batch of synthetic prompts for PR submission.

    Accepts a JSON array of prompt records (each matching the synthetic
    prompt schema). Validates every record, summarises pass/fail counts
    by subcategory, and returns a checklist of issues to fix before
    opening a pull request.

    Args:
        prompts_json: JSON array string of synthetic prompt records.

    Returns:
        A JSON string with keys:
            total (int) — total records in the batch
            valid (int) — records that pass all checks
            invalid (int) — records with issues
            issues_by_id (dict) — {id: [issues]} for each failing record
            pr_checklist (list[str]) — pre-PR checklist items
            ready_to_submit (bool) — True if all records are valid
    """
    return json.dumps(_create_contribution_bundle_impl(prompts_json), indent=2)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
