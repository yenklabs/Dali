# Dali

> **An open benchmark for citation integrity, evidence reconstructability, and replay determinism in legal AI systems.**

[![CI](https://github.com/yenk/Dali/actions/workflows/test-suite.yml/badge.svg)](https://github.com/yenk/Dali/actions/workflows/test-suite.yml)
[![Replay verification](https://github.com/yenk/Dali/actions/workflows/replay-verification.yml/badge.svg)](https://github.com/yenk/Dali/actions/workflows/replay-verification.yml)
[![Latest release](https://img.shields.io/github/v/release/yenk/Dali)](https://github.com/yenk/Dali/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Cite](https://img.shields.io/badge/cite-CITATION.cff-orange)](CITATION.cff)

![Dali v0.2 Evidence Reconstructability Benchmark](docs/assets/dali-v0.2-benchmark-snapshot.png)

## What is Dali?

Dali evaluates whether the evidence behind an AI-generated legal citation can be independently reconstructed, verified, and re-evaluated under a fixed policy version. A citation checker asks whether a citation exists. Dali asks whether the workflow that produced it can be audited and defended.

Every Dali run produces a deterministic, policy-versioned, hash-sealed `CitationIntegrityResult` artifact. The deterministic Tier 1 evaluator runs offline; CI re-verifies replay equality on every pull request.

## Why does it matter?

The legal industry lacks shared benchmarks, public corpora, or reproducible evidence standards for studying AI-generated citation failures. Court-documented incidents have continued to issue since [*Mata v. Avianca*](docs/CASE-STUDIES.md#1-mata-v-avianca-inc-sdny-2023) (2023), including [*United States v. Cohen*](docs/CASE-STUDIES.md#2-united-states-v-cohen-sdny-2023) and [*Park v. Kim*](docs/CASE-STUDIES.md#3-park-v-kim-2d-cir-2024), which anchor the Tier 1 canonical corpus in [data/benchmark/tier1/corpus/citation_failure_cases.json](data/benchmark/tier1/corpus/citation_failure_cases.json). Dali consolidates that missing public infrastructure into one MIT-licensed, deterministically replayable artifact, with reproducibility defined through [cryptographic lineage](docs/cryptographic-lineage.md) and the public [methodology](docs/METHODOLOGY.md).

## What did we find?

- **524 citations** evaluated across 3 OpenAI models and 5 jurisdiction tracks.
- **GPT-4.1: 23%** of generated citation URLs return HTTP 404; on adversarial citation-trap prompts the model took the bait **76%** of the time.
- **Portuguese civil-law verified at 3%; UK common-law at 76%** — same models, same task, different legal system.

Full per-model leaderboard, jurisdictional breakdown, methodology, and reproducible run instructions: [data/results/v0.2/](data/results/v0.2/) and [LEADERBOARD.md](docs/LEADERBOARD.md). Narrative writeups of the three Tier 1 cases: [CASE-STUDIES.md](docs/CASE-STUDIES.md).

## How do I contribute?

Choose the path that matches your role:

- **AI researcher / eval engineer**: [docs/for-researchers.md](docs/for-researchers.md)
- **Legal researcher / practitioner**: [docs/for-legal-practitioners.md](docs/for-legal-practitioners.md)
- **Software engineer**: [docs/for-engineers.md](docs/for-engineers.md)
- **Methodology reviewer**: [docs/reviewer-guide.md](docs/reviewer-guide.md)

### Quick start

```bash
git clone https://github.com/yenk/Dali && cd Dali
pip install -r requirements.txt
python -m tools.cli replay
```

The Tier 1 evaluator runs entirely offline with no API keys or network access required. Every evaluation verifies replay determinism through Dali's cryptographic lineage chain.

Standalone setup guide: [docs/quickstart.md](docs/quickstart.md).

Dali exposes the same contributor workflow through both the CLI and MCP:

| Action | Command |
|---|---|
| Validate a corpus record | `lint` |
| Run the evaluator | `score` |
| Verify replay determinism | `replay` |
| Validate a prompt | `probe` |
| Create a prompt template | `draft` |
| Bundle prompts | `pack` |

Use them locally through the CLI:

- [tools/cli/README.md](tools/cli/README.md)

Or from AI-native editors and assistants through MCP:

- [tools/mcp/README.md](tools/mcp/README.md)

Dali is designed so researchers, developers, legal professionals, and AI practitioners can contribute evidence, benchmarks, and evaluation artifacts through a consistent, reproducible workflow.

For contribution rules, taxonomy, labels, and the PR checklist, see [CONTRIBUTING.md](CONTRIBUTING.md). For methodology and scoring, see [METHODOLOGY.md](docs/METHODOLOGY.md) and [docs/policy-versioning.md](docs/policy-versioning.md). For cryptographic lineage, see [docs/cryptographic-lineage.md](docs/cryptographic-lineage.md). For a deeper repo tour, see [tools/cli/README.md](tools/cli/README.md) and [tools/mcp/README.md](tools/mcp/README.md).

## How to cite

See [CITATION.cff](CITATION.cff), or:

```bibtex
@software{dali-2026,
  title        = {Dali: Evidentiary Infrastructure for Legal AI},
  author       = {Kha, Yen},
  year         = {2026},
  version      = {0.2.1},
  organization = {GammaLex AI Inc.},
  url          = {https://github.com/yenk/Dali},
  note         = {Open benchmark for citation integrity, provenance, and evidence reconstructability in legal AI}
}
```

## License

MIT. See [LICENSE](LICENSE).
