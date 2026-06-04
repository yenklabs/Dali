# Quick Start

The fastest way to verify Dali locally is to run the deterministic Tier 1
evaluator and confirm replay determinism.

## 1. Clone and install

```bash
git clone https://github.com/yenk/Dali && cd Dali
pip install -r requirements.txt
```

## 2. Verify replay determinism

```bash
python -m tools.cli replay
```

This runs Tier 1 entirely offline:

- no API keys required
- no network access required
- deterministic output under the pinned policy version

## 3. Use the six contributor verbs

The CLI and MCP server expose the same workflow:

| Action | Command |
|---|---|
| Validate a corpus record | `lint` |
| Run the evaluator | `score` |
| Verify replay determinism | `replay` |
| Validate a prompt | `probe` |
| Create a prompt template | `draft` |
| Bundle prompts | `pack` |

### CLI

Use the verbs locally through the CLI:

- [tools/cli/README.md](../tools/cli/README.md)

### MCP

Use the same verbs from Claude Desktop, Cursor, VS Code, or other
MCP-compatible tools:

- [tools/mcp/README.md](../tools/mcp/README.md)

## 4. Go deeper

- Methodology and scoring: [METHODOLOGY.md](METHODOLOGY.md)
- Policy versioning: [policy-versioning.md](policy-versioning.md)
- Cryptographic lineage: [cryptographic-lineage.md](cryptographic-lineage.md)
- Contribution workflow: [../CONTRIBUTING.md](../CONTRIBUTING.md)
