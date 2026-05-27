"""MCP tool implementations: check_prompt, new_prompt, bundle_prompts."""

from __future__ import annotations

import json
import uuid

VALID_CATEGORIES = {"legal", "research", "adversarial"}

VALID_SUBCATEGORIES = {
    "legal": {
        "case_citations",
        "statutory_interpretation",
        "contract_law",
        "uk_commonwealth",
        "brazil",
    },
    "research": {"academic_claims", "policy_citations"},
    "adversarial": {"hallucination_prone"},
}

VALID_DIFFICULTIES = {
    "known_case",
    "obscure_case",
    "fabricated_likely",
    "ambiguous",
    "adversarial",
    "standard",
}

# Subcategory → file mapping for contributor guidance
SUBCATEGORY_FILES = {
    "case_citations": "synthetic/legal/case_citations.jsonl",
    "statutory_interpretation": "synthetic/legal/statutory_interpretation.jsonl",
    "contract_law": "synthetic/legal/contract_law.jsonl",
    "uk_commonwealth": "synthetic/legal/uk_commonwealth.jsonl",
    "brazil": "synthetic/legal/brazil.jsonl",
    "academic_claims": "synthetic/research/academic_claims.jsonl",
    "policy_citations": "synthetic/research/policy_citations.jsonl",
    "hallucination_prone": "synthetic/adversarial/hallucination_prone.jsonl",
}

REQUIRED_PROMPT_FIELDS = ("id", "category", "subcategory", "prompt", "difficulty")
MIN_PROMPT_LENGTH = 30


def _check_prompt_impl(prompt_json: str) -> dict:
    issues: list[str] = []

    try:
        record = json.loads(prompt_json)
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "issues": [f"Invalid JSON: {e}"],
            "summary": "Parse error: entry is not valid JSON.",
        }

    if not isinstance(record, dict):
        return {
            "valid": False,
            "issues": ["Entry must be a JSON object."],
            "summary": "Invalid structure.",
        }

    # Required fields
    for field in REQUIRED_PROMPT_FIELDS:
        if not record.get(field):
            issues.append(f"Missing required field: '{field}'")

    # ID format
    prompt_id = record.get("id", "")
    if prompt_id and not all(c.isalnum() or c == "_" for c in prompt_id):
        issues.append(
            f"'id' must contain only lowercase alphanumeric characters and "
            f"underscores, got: '{prompt_id}'"
        )

    # Category taxonomy
    category = record.get("category")
    if category and category not in VALID_CATEGORIES:
        issues.append(
            f"'category' value '{category}' is invalid. "
            f"Valid values: {sorted(VALID_CATEGORIES)}"
        )

    # Subcategory taxonomy + category consistency
    subcategory = record.get("subcategory")
    if subcategory and category in VALID_SUBCATEGORIES:
        if subcategory not in VALID_SUBCATEGORIES[category]:
            valid_for_cat = sorted(VALID_SUBCATEGORIES[category])
            issues.append(
                f"'subcategory' value '{subcategory}' is not valid for "
                f"category '{category}'. Valid subcategories: {valid_for_cat}"
            )
    elif subcategory and category not in VALID_CATEGORIES:
        pass  # category error already reported

    # Difficulty taxonomy
    difficulty = record.get("difficulty")
    if difficulty and difficulty not in VALID_DIFFICULTIES:
        issues.append(
            f"'difficulty' value '{difficulty}' is invalid. "
            f"Valid values: {sorted(VALID_DIFFICULTIES)}"
        )

    # Prompt length
    prompt_text = record.get("prompt", "")
    if isinstance(prompt_text, str) and len(prompt_text) < MIN_PROMPT_LENGTH:
        issues.append(
            f"'prompt' is too short ({len(prompt_text)} chars). "
            f"Minimum is {MIN_PROMPT_LENGTH} characters."
        )

    # Destination file hint
    destination = SUBCATEGORY_FILES.get(subcategory or "")
    dest_hint = f"Add to: {destination}" if destination else ""

    if not issues:
        summary = (
            f"Prompt '{record.get('id', '?')}' is valid. {dest_hint}".strip()
        )
    else:
        summary = (
            f"Prompt '{record.get('id', '?')}' has {len(issues)} issue(s)."
        )

    return {
        "valid": not bool(issues),
        "issues": issues,
        "summary": summary,
        "destination_file": destination,
    }


def _new_prompt_impl(
    category: str,
    subcategory: str,
    difficulty: str,
    notes: str = "",
) -> str:
    issues: list[str] = []

    if category not in VALID_CATEGORIES:
        issues.append(
            f"Invalid category '{category}'. "
            f"Valid values: {sorted(VALID_CATEGORIES)}"
        )
    if category in VALID_SUBCATEGORIES and subcategory not in VALID_SUBCATEGORIES.get(category, set()):
        issues.append(
            f"Invalid subcategory '{subcategory}' for category '{category}'. "
            f"Valid values: {sorted(VALID_SUBCATEGORIES.get(category, set()))}"
        )
    if difficulty not in VALID_DIFFICULTIES:
        issues.append(
            f"Invalid difficulty '{difficulty}'. "
            f"Valid values: {sorted(VALID_DIFFICULTIES)}"
        )

    if issues:
        return json.dumps({"error": "Invalid parameters", "issues": issues}, indent=2)

    # Generate a unique ID stub
    short_id = uuid.uuid4().hex[:6]
    prompt_id = f"{subcategory}_{short_id}"

    template = {
        "id": prompt_id,
        "category": category,
        "subcategory": subcategory,
        "prompt": "<REPLACE: write your prompt here (minimum 30 characters)>",
        "difficulty": difficulty,
        "notes": notes or "<REPLACE: describe what failure mode this prompt is testing>",
    }

    destination = SUBCATEGORY_FILES.get(subcategory, f"synthetic/{category}/")
    header = (
        f"# Template generated for {category}/{subcategory} ({difficulty})\n"
        f"# Add this entry (without the # comment lines) to: {destination}\n"
        f"# Replace the <REPLACE> placeholders before submitting.\n"
    )

    return header + json.dumps(template)


def _bundle_prompts_impl(prompts_json: str) -> dict:
    try:
        records = json.loads(prompts_json)
    except json.JSONDecodeError as e:
        return {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "issues_by_id": {},
            "pr_checklist": [],
            "ready_to_submit": False,
            "error": f"Invalid JSON input: {e}",
        }

    if not isinstance(records, list):
        return {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "issues_by_id": {},
            "pr_checklist": [],
            "ready_to_submit": False,
            "error": "Input must be a JSON array of prompt records.",
        }

    valid_count = 0
    invalid_count = 0
    issues_by_id: dict[str, list[str]] = {}

    for record in records:
        result = _check_prompt_impl(json.dumps(record))
        record_id = record.get("id", f"<unknown-{len(issues_by_id)}>")
        if result["valid"]:
            valid_count += 1
        else:
            invalid_count += 1
            issues_by_id[record_id] = result["issues"]

    # Check for duplicate IDs
    ids = [r.get("id") for r in records if isinstance(r, dict)]
    seen: set[str] = set()
    duplicates = []
    for i in ids:
        if i in seen:
            duplicates.append(i)
        seen.add(str(i))
    if duplicates:
        for dup in duplicates:
            issues_by_id.setdefault(dup, []).append(
                f"Duplicate id '{dup}': each prompt must have a unique id."
            )
            invalid_count += 1
            valid_count = max(0, valid_count - 1)

    pr_checklist = [
        "[ ] pytest tests/ passes",
        "[ ] All prompts pass check_prompt (no issues above)",
        "[ ] Prompts added to the correct synthetic/ file",
        "[ ] No PII or unpublished matter in prompt text",
        "[ ] Commit author identity is set (name + email)",
        "[ ] PR description explains what failure mode the prompts test",
    ]

    return {
        "total": len(records),
        "valid": valid_count,
        "invalid": invalid_count,
        "issues_by_id": issues_by_id,
        "pr_checklist": pr_checklist,
        "ready_to_submit": invalid_count == 0,
    }
