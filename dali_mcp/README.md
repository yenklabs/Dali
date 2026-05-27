# Dali MCP — Contributor Tools

Dali exposes four MCP tools so you can validate, scaffold, and bundle
corpus records and synthetic prompts directly from Claude or any
MCP-capable editor — without running terminal commands.

## Tools

| Tool | What it does |
|---|---|
| `validate_corpus_record` | Validates a CitationFailureCase JSON object — checks required fields, taxonomy values, lineage rules, and scoring eligibility |
| `validate_prompt_jsonl` | Validates a single synthetic prompt JSONL entry — checks required fields, category/subcategory/difficulty taxonomy, and prompt length |
| `generate_prompt_template` | Scaffolds a new prompt template for a given category, subcategory, and difficulty — ready to fill in and paste |
| `create_contribution_bundle` | Validates a batch of prompts and returns a PR-ready checklist |

These tools wrap the same validation logic used by the CLI (`corpus/validator.py`, `runners/`) so there are no discrepancies between editor and terminal validation.

---

## Setup

### Prerequisites

```bash
pip install mcp
```

The `mcp` package is listed under `# MCP server` in `requirements.txt`. The rest of Dali (Tier 1 evaluator) runs on stdlib only — `mcp` is only required if you want the editor integration.

### Claude Desktop

Add to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dali": {
      "command": "python",
      "args": ["-m", "dali_mcp"],
      "cwd": "/path/to/your/Dali/clone"
    }
  }
}
```

Replace `/path/to/your/Dali/clone` with the absolute path to your local repo.

Restart Claude Desktop. The four tools will appear in Claude's tool list.

### VS Code (with MCP extension)

Add to your `.vscode/mcp.json`:

```json
{
  "servers": {
    "dali": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "dali_mcp"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

### Cursor

Add to your Cursor MCP settings:

```json
{
  "mcpServers": {
    "dali": {
      "command": "python",
      "args": ["-m", "dali_mcp"],
      "cwd": "/path/to/your/Dali/clone"
    }
  }
}
```

---

## Usage examples

### Validate a corpus record

Ask Claude:
> "Use validate_corpus_record to check this record: `{ "case_id": "my-case-2024", "year": 2024, ... }`"

The tool returns a report with `valid`, `scoring_eligible`, `issues`, and a one-line `summary`.

### Scaffold a new adversarial prompt

Ask Claude:
> "Use generate_prompt_template for category=adversarial, subcategory=hallucination_prone, difficulty=adversarial, notes=Tests fabrication under recent AI regulation prompts"

The tool returns a ready-to-fill JSONL entry and tells you which file to add it to.

### Bundle prompts for a PR

Ask Claude:
> "Use create_contribution_bundle on this list of prompts: [...]"

Returns pass/fail by prompt ID and a PR checklist.

---

## CLI equivalent

All tools have direct CLI equivalents if you prefer the terminal:

```bash
# Validate corpus
python -m corpus.validator data/public/citation_failure_cases.json

# Validate synthetic prompts (schema validation via CI)
python -m pytest tests/ -q
```

The MCP server is an editor-friendly wrapper — not a separate code path.
