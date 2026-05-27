# Dali MCP Contributor Tools

Dali exposes four MCP tools so you can validate, scaffold, and bundle
corpus records and synthetic prompts directly from Claude or any
MCP-capable editor, without running terminal commands.

## Tools

| Tool | Purpose |
|---|---|
| `check_case` | Validate a canonical citation-failure case |
| `check_prompt` | Validate a synthetic benchmark prompt |
| `new_prompt` | Generate a prompt scaffold |
| `bundle_prompts` | Create a PR-ready contribution bundle |

These tools wrap the same validation logic used by the CLI
(`corpus/validator.py`, `runners/`) so there are no discrepancies
between editor and terminal validation.

---

## Setup

### Prerequisites

```bash
pip install mcp
```

The `mcp` package is listed under the MCP server section in
`requirements.txt`. The rest of Dali (Tier 1 evaluator) runs on
stdlib only. `mcp` is only required for the editor integration.

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

Replace `/path/to/your/Dali/clone` with the absolute path to your
local repo. Restart Claude Desktop. The four tools will appear in
the tool list.

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

Ask your editor assistant:
> "Use check_case to validate this record: { "case_id": "my-case-2024", "year": 2024, ... }"

The tool returns `valid`, `scoring_eligible`, `issues`, and a one-line `summary`.

### Scaffold a new adversarial prompt

Ask your editor assistant:
> "Use new_prompt for category=adversarial, subcategory=hallucination_prone, difficulty=adversarial, notes=Tests fabrication under recent AI regulation prompts"

The tool returns a ready-to-fill entry and tells you which file to add it to.

### Bundle prompts for a PR

Ask your editor assistant:
> "Use bundle_prompts on this list: [...]"

Returns pass/fail by prompt ID and a pre-PR checklist.

---

## CLI equivalent

All tools have direct CLI equivalents for terminal users:

```bash
# Validate corpus
python -m corpus.validator data/public/citation_failure_cases.json

# Validate synthetic prompts (via CI schema check)
pytest tests/ -q
```

The MCP server is an editor-friendly wrapper around the same logic,
not a separate code path.
