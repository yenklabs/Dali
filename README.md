# Dali

> **An open benchmark for citation integrity, evidence reconstructability, and replay determinism in legal AI systems.**

[![CI](https://github.com/yenk/Dali/actions/workflows/test-suite.yml/badge.svg)](https://github.com/yenk/Dali/actions/workflows/test-suite.yml)
[![Replay verification](https://github.com/yenk/Dali/actions/workflows/replay-verification.yml/badge.svg)](https://github.com/yenk/Dali/actions/workflows/replay-verification.yml)
[![Latest release](https://img.shields.io/github/v/release/yenk/Dali)](https://github.com/yenk/Dali/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Cite](https://img.shields.io/badge/cite-CITATION.cff-orange)](CITATION.cff)

![Dali v0.2 Evidence Reconstructability Benchmark](docs/assets/dali-v0.2-benchmark-snapshot.png)

## What Dali is

Dali evaluates whether the evidence behind an AI-generated legal citation can be independently reconstructed, verified, and re-evaluated under a fixed policy version. A citation checker asks whether a citation exists. Dali asks whether the workflow that produced it can be audited and defended.

Every Dali run produces a deterministic, policy-versioned, hash-sealed `CitationIntegrityResult` artifact. The deterministic Tier 1 evaluator runs offline; CI re-verifies replay equality on every pull request.

## Why it matters now

The legal industry lacks shared benchmarks, public corpora, or reproducible evidence standards for studying AI-generated citation failures. Court-documented incidents have continued to issue since *Mata v. Avianca* (2023). Dali consolidates the missing public infrastructure into one MIT-licensed, deterministically replayable artifact.

## v0.2 snapshot

- **524 citations** evaluated across 3 OpenAI models and 5 jurisdiction tracks.
- **GPT-4.1: 23%** of generated citation URLs return HTTP 404; on adversarial citation-trap prompts the model took the bait **76%** of the time.
- **Portuguese civil-law verified at 3%; UK common-law at 76%** — same models, same task, different legal system.

Full per-model leaderboard, jurisdictional breakdown, methodology, and reproducible run instructions: [results/v0.2/](results/v0.2/) and [LEADERBOARD.md](LEADERBOARD.md). Narrative writeups of the three Tier 1 cases: [CASE-STUDIES.md](CASE-STUDIES.md).

## Start here

| You are a... | Start with | Time to first contribution |
|---|---|---|
| **AI researcher / eval engineer** | [docs/for-researchers.md](docs/for-researchers.md) | 60 min |
| **Legal researcher / practitioner** | [docs/for-legal-practitioners.md](docs/for-legal-practitioners.md) | 30 min |
| **Software engineer** | [docs/for-engineers.md](docs/for-engineers.md) | 2 hr |
| **Methodology reviewer** | [docs/reviewer-guide.md](docs/reviewer-guide.md) | — |

## Quick start

```bash
git clone https://github.com/yenk/Dali && cd Dali
pip install -r requirements.txt
python -m dali_cli replay
```

The Tier 1 evaluator runs offline (no API keys, no network) and verifies replay determinism through the cryptographic-lineage hash chain. Same six verbs — `lint`, `score`, `replay`, `probe`, `draft`, `pack` — work from the terminal ([dali_cli/README.md](dali_cli/README.md)) and from an AI editor over MCP ([dali_mcp/README.md](dali_mcp/README.md)).

## Repository map

| Path | Purpose |
|---|---|
| `benchmarks/tier1/` | Canonical court-documented citation-failure corpus |
| `benchmarks/tier2/` | Synthetic probe prompts for live-model evaluation |
| `corpus/` | Python package — schema, validator, anonymizer, taxonomy, lineage |
| `runners/` | Canonical CLI entry points (`run_integrity.py`, `run_synthetic.py`) |
| `dali_cli/` | Short-verb CLI dispatcher (`python -m dali_cli <verb>`) |
| `dali_mcp/` | MCP server exposing the same six verbs to AI editors |
| `scoring/` | Tier 2 scoring modules — existence, verification, support |
| `schemas/` | Public JSON schemas — `CitationIntegrityResult`, `EvidenceBundle`, canonical citation |
| `specs/` | RFCs — currently RFC-001 (Evidence JSON v1) |
| `results/` | Versioned, immutable benchmark run artifacts |
| `docs/` | Methodology, FAQ, persona doorways, cryptographic lineage, roadmap |
| `tests/` | pytest suite — 136 tests covering corpus, runner, schemas, CLI, MCP |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution tracks, taxonomy, labels, and the PR checklist. For methodology and scoring, see [METHODOLOGY.md](METHODOLOGY.md) and [docs/policy-versioning.md](docs/policy-versioning.md). For the cryptographic-lineage contract, see [docs/cryptographic-lineage.md](docs/cryptographic-lineage.md).

## Related projects

- **Dali Platform** (hosted evaluation, complementary): [dali.gammalex.com](https://dali.gammalex.com)
- **GammaLex** (commercial legal-AI product; Dali is independent, MIT-licensed open infrastructure): [gammalex.com](https://gammalex.com)

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
