# Dali CLI — `python -m dali_cli`

Six short-verb subcommands. Same vocabulary as the MCP tools in [`dali_mcp/`](../dali_mcp/). Same code path as the canonical runners in [`runners/`](../runners/). Same cryptographic-lineage hashes on every output.

`runners/run_integrity.py` and `python -m corpus.validator` remain the canonical underlying entry points; this CLI is a thin convenience dispatcher.

## Six verbs

| Verb | Does | Underlying command |
|---|---|---|
| `lint` | Validate a corpus file | `corpus.validator` |
| `score` | Run the Tier 1 deterministic evaluator | `runners/run_integrity.py` |
| `replay` | Run the evaluator twice and verify replay-hash equality | `runners/run_integrity.py --verify-replay` |
| `probe` | Validate a Tier 2 prompt record or JSONL file | `dali_mcp.tools.prompt_tools._check_prompt_impl` |
| `draft` | Scaffold a new Tier 2 prompt template | `dali_mcp.tools.prompt_tools._new_prompt_impl` |
| `pack` | Bundle a batch of prompts and emit a PR-ready checklist | `dali_mcp.tools.prompt_tools._bundle_prompts_impl` |

## Quick reference

```bash
# Validate the canonical corpus
python -m dali_cli lint

# Run the Tier 1 evaluator (default corpus path)
python -m dali_cli score

# Run + verify replay determinism (recommended demo command)
python -m dali_cli replay

# Validate a Tier 2 prompt file (JSON, JSON array, or JSONL all accepted)
python -m dali_cli probe benchmarks/tier2/legal/case_citations.jsonl

# Scaffold a new prompt template
python -m dali_cli draft \
  --category adversarial \
  --subcategory hallucination_prone \
  --difficulty adversarial \
  --notes "Tests fabrication on recent AI-regulation queries"

# Bundle one or more prompt JSONL files for PR submission
python -m dali_cli pack benchmarks/tier2/legal/*.jsonl
```

## Defaults

- `lint`, `score`, `replay` default to `benchmarks/tier1/corpus/citation_failure_cases.json` when no corpus is passed.
- `score` and `replay` write to `results/demo/integrity.json` unless `--output` is given.

## `score` and `replay` — extra flags

Both accept the full flag set of `runners/run_integrity.py`:

| Flag | Effect |
|---|---|
| `--output PATH` | Write the result JSON to PATH |
| `--check-reachability` | Issue HTTP HEAD against each `source_url` to populate `authority_reachable` |
| `--include-pre-canonical` | Include 2021–2022 records in the evaluation set |
| `--include-needs-verification` | Include records flagged `needs_verification=true` |
| `--allow-cross-version` | Permit aggregating results from different policy versions |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | All checks passed |
| 1 | Argument / config / IO error |
| 2 | No scoring-eligible records, or validation failures in `lint`/`probe`/`pack` |
| 3 | Cross-version policy conflict (without `--allow-cross-version`) — `score`/`replay` only |
| 4 | Replay-determinism mismatch — `replay` only |

## Same vocabulary, two surfaces

The CLI and the MCP server expose the **exact same six verbs** with byte-identical output. Pick whichever surface matches your workflow:

| Verb | Terminal | MCP (AI editor) |
|---|---|---|
| `lint` | `python -m dali_cli lint` | `lint` tool in Claude/Cursor/VS Code |
| `score` | `python -m dali_cli score` | `score` tool |
| `replay` | `python -m dali_cli replay` | `replay` tool |
| `probe` | `python -m dali_cli probe <file>` | `probe` tool |
| `draft` | `python -m dali_cli draft --category … --subcategory … --difficulty …` | `draft` tool |
| `pack` | `python -m dali_cli pack <files>` | `pack` tool |

For the MCP setup that gives you the same six tools inside an AI editor, see [dali_mcp/README.md](../dali_mcp/README.md).

## See also

- [docs/cryptographic-lineage.md](../docs/cryptographic-lineage.md) — what the three SHA-256 hashes on every result actually prove
- [METHODOLOGY.md](../METHODOLOGY.md) — scoring rubric and policy versioning
- [CONTRIBUTING.md](../CONTRIBUTING.md) — contribution tracks and PR checklist
