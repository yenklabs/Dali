# AI Context (local MCP server)

Local-first repository context retrieval for Dali contributors. Builds a hybrid index (keyword + dependency graph), returns token-budgeted markdown capsules, and exposes MCP tools so agents can ground answers in the actual codebase before calling Dali's corpus tools (`lint`, `score`, `replay`, etc.).

This directory vendors the [AI Context](https://github.com/nikeinc/ai-context) MCP prototype used alongside `tools/mcp/`.

## Install

```bash
cd tools/ai-context
npm install
```

## MCP tools

| Tool | Purpose |
|---|---|
| `run_pipeline` | Recommended single-call: index (incremental) + retrieve + compact capsule |
| `index_workspace` | Force full or incremental index rebuild |
| `index_status` | Index health, cache hit rate, latency metrics |
| `get_context_capsule` | Retrieve context for a query with a token budget |

## When to use vs Dali MCP

| Question type | Use |
|---|---|
| "Where is replay hash computed?" / "How does the validator work?" | `ai-context` → `run_pipeline` |
| "Lint this corpus record" / "Score this case" / "Pack these prompts" | `dali` MCP → `lint`, `score`, `pack`, etc. |
| Adding a new case end-to-end | `run_pipeline` first (find schema + file paths), then `lint` → `score` → `replay` |

Typical agent sequence for a contributor task:

1. `run_pipeline` with the user's task text (default `tokenBudget`: 1400)
2. Use returned `capsule` to locate the right files and conventions
3. Make edits
4. `lint` / `score` / `replay` on changed corpus records before opening a PR

## Configuration

- Index cache: `.ai-context/index.db` at the repo root (gitignored)
- Worker concurrency: `AI_CONTEXT_INDEX_WORKERS=<n>` (default auto, max 8)
- Token-first mode: on by default for symbol-focused queries; set `AI_CONTEXT_TOKEN_FIRST=0` to disable

See [docs/agent-context.md](../../docs/agent-context.md) for full Cursor/VS Code setup.
