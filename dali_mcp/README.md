# Dali MCP — contribute without touching a terminal

Six short verb tools. Same code path as the CLI. Talk to Claude, Cursor, or VS Code instead of typing Python.

If you've ever wanted to add a court-documented AI-citation failure to a research benchmark but didn't want to deal with `pip install`, this is the path.

---

## What you can do

| Tool | What you ask the AI | Output |
|---|---|---|
| `lint` | "Validate this corpus record" | Pass/fail + list of missing or invalid fields |
| `score` | "Run the Tier 1 evaluator on this record" | Full verdict + three cryptographic hashes (the demo, but in MCP) |
| `replay` | "Verify this record evaluates deterministically" | PASS/FAIL on replay-hash equality across two runs |
| `probe` | "Validate this Tier 2 prompt" | Pass/fail + which file to add it to |
| `draft` | "Scaffold a new adversarial prompt" | Ready-to-fill JSON template |
| `pack` | "Bundle these 5 prompts for PR" | Validation summary + pre-PR checklist |

`score` is the one that matters most — it runs the same code path as `python runners/run_integrity.py` and surfaces the cryptographic lineage that anchors Dali's reproducibility claim. No terminal required.

---

## Install (5 minutes, one-time)

### 1. Clone the repo and install dependencies

```bash
git clone https://github.com/yenk/Dali && cd Dali
pip install -r requirements.txt
```

That's the only terminal command. From here on, everything happens in your AI editor.

### 2. Wire the server into your AI editor

Pick the one you use. Each config below uses `python -m dali_mcp` — the server itself runs via the `dali_mcp` Python package that you just installed.

**Claude Desktop** — edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dali": {
      "command": "python",
      "args": ["-m", "dali_mcp"],
      "cwd": "/absolute/path/to/your/Dali/clone"
    }
  }
}
```

Where to find `claude_desktop_config.json`:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Restart Claude Desktop. You'll see "dali" listed in the MCP server tray.

**Cursor** — Settings → MCP → Add Server, paste the same JSON.

**VS Code (with the MCP extension)** — add `.vscode/mcp.json` at your workspace root:

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

### 3. Smoke test (30 seconds)

Paste this into your AI editor:

> Use `score` on this record:
> ```json
> {"case_id":"smoke-test","incident_name":"Smoke test","year":2024,"jurisdiction":"US-NY-SDNY","source_url":"https://example.com/order/1","retrieval_date":"2026-06-04","source_type":"sanctions_order","alleged_generated_citation":"Fake v. Real, 123 F.3d 456 (9th Cir. 2020)","actual_status":"nonexistent_authority","failure_class":["nonexistent_authority","reconstructability_failure"],"ground_truth_notes":"Smoke test."}
> ```

Expected: the AI returns `verification: FAILED`, `risk: critical`, and three SHA-256 hashes (`corpus_record_hash`, `replay_hash`, `evidence_hash`). If you see that, your setup works.

---

## Five ready-to-paste contributor prompts

These are the workflows most contributors will actually do. Paste any into your AI editor as-is.

### 1. Add a new court-documented case (legal practitioners)

> I found a court order where AI-generated citations were sanctioned. Help me add it to Dali. The case is [paste case name and URL]. Walk me through filling out the corpus record, then `lint` it, then `score` it to confirm a clean Tier 1 verdict, then `replay` it to confirm determinism. When everything passes, give me the JSON ready to paste into `benchmarks/tier1/corpus/citation_failure_cases.json`.

### 2. Run the Tier 1 demo against an existing case

> Open `benchmarks/tier1/corpus/citation_failure_cases.json`, pick the Mata v. Avianca record, and `score` it. Show me the full verdict and explain what each of the three hashes (corpus_record_hash, replay_hash, evidence_hash) proves.

### 3. Scaffold a new adversarial prompt

> `draft` an adversarial / hallucination_prone prompt at adversarial difficulty. The failure mode I want to test is: lawyers asking for recent appellate decisions on AI-generated evidence (a topic where the model is likely to fabricate citations). Then write the actual prompt text and `probe` it to validate.

### 4. Bundle five prompts into a PR-ready submission

> I have five Tier 2 prompts I want to contribute [paste the JSON array]. `pack` them, show me anything I need to fix, and produce the pre-PR checklist.

### 5. Verify a record I changed still evaluates the same

> I edited the Park v. Kim record in `benchmarks/tier1/corpus/citation_failure_cases.json`. `replay` it and confirm the replay_hash still matches its prior value. If it doesn't, that means my edit changed the verdict — show me what's different.

---

## What each tool returns

All tools return JSON strings. Your AI assistant will parse and present them.

| Tool | Key return fields |
|---|---|
| `lint` | `valid`, `scoring_eligible`, `issues[]`, `summary` |
| `score` | `ok`, `result` (full `CitationIntegrityResult` with all hashes), `summary` |
| `replay` | `ok`, `replay_hash_match`, `corpus_record_hash_match`, `replay_hash`, `policy_version`, `summary` |
| `probe` | `valid`, `issues[]`, `summary`, `destination_file` |
| `draft` | A commented JSON template (string), with placeholder `<REPLACE>` markers |
| `pack` | `total`, `valid`, `invalid`, `issues_by_id`, `pr_checklist[]`, `ready_to_submit` |

---

## How this maps to terminal commands

Every MCP tool has a direct CLI equivalent. They share the same Python functions, so output is byte-identical.

| MCP tool | Terminal equivalent |
|---|---|
| `lint` | `python -m corpus.validator <corpus.json>` |
| `score` | `python runners/run_integrity.py --corpus <corpus.json> --output <out.json>` |
| `replay` | `python runners/run_integrity.py --corpus <corpus.json> --output <out.json> --verify-replay` |
| `probe` + `pack` | `pytest tests/` (schema validation runs here) |

---

## Troubleshooting

**"dali" doesn't appear in my editor's MCP server list**
The `cwd` field in the JSON config must be the **absolute** path to your Dali clone. `~` and relative paths don't work. On macOS, run `pwd` inside the Dali directory and paste that exact string.

**`score` returns "Failed to construct CitationFailureCase"**
The record is missing or has the wrong type for a required field. Run `lint` first — it lists every missing or invalid field with the exact fix.

**`replay` returns ok: false**
Either the runner has a determinism regression (unlikely; CI catches this on every PR) or the record itself contains non-deterministic content (e.g., a `datetime.now()` in a field, which should not happen in a well-formed corpus record). Open an issue with `methodology` label and include the record JSON.

**Python version**
The MCP server needs Python 3.10+. If `python -m dali_mcp` errors, try `python3 -m dali_mcp` and update your editor's MCP config accordingly.

---

## Related

- **Persona doorways:**
  [for legal practitioners](../docs/for-legal-practitioners.md) · [for AI researchers](../docs/for-researchers.md) · [for engineers](../docs/for-engineers.md)
- **Cryptographic lineage** — what the three hashes actually prove: [docs/cryptographic-lineage.md](../docs/cryptographic-lineage.md)
- **Methodology** — the scoring rubric and policy versioning: [METHODOLOGY.md](../METHODOLOGY.md)
- **Full contributor guide** — taxonomy, labels, PR checklist: [CONTRIBUTING.md](../CONTRIBUTING.md)
