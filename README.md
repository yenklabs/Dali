# Dali

> **Dali is the open verification layer for AI:** it creates, scores, and preserves evidence so AI-assisted outputs can be independently verified, exchanged, and replayed.

[![CI](https://github.com/yenklabs/Dali/actions/workflows/test-suite.yml/badge.svg)](https://github.com/yenklabs/Dali/actions/workflows/test-suite.yml)
[![Replay verification](https://github.com/yenklabs/Dali/actions/workflows/replay-verification.yml/badge.svg)](https://github.com/yenklabs/Dali/actions/workflows/replay-verification.yml)
[![Latest release](https://img.shields.io/github/v/release/yenklabs/Dali)](https://github.com/yenklabs/Dali/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Cite](https://img.shields.io/badge/cite-CITATION.cff-orange)](CITATION.cff)

![Dali v0.2 Evidence Reconstructability Benchmark](docs/assets/dali-v0.2-benchmark-snapshot.png)

## What is Dali?

Dali is the open verification layer for AI: it creates, scores, and preserves evidence so AI-assisted outputs can be independently verified, exchanged, and replayed. Legal AI is the proving ground — a citation checker asks whether a citation exists; Dali asks whether the workflow that produced it can be audited and defended under a fixed policy version.

Every Dali run produces a deterministic, policy-versioned, hash-sealed `CitationIntegrityResult` artifact. The deterministic Tier 1 evaluator runs offline; CI re-verifies replay equality on every pull request.

## For legal teams and diligence readers

**Dali** is MIT-licensed open evidence infrastructure maintained by [GammaLex AI Inc.](https://gammalex.com). This repository publishes the benchmark methodology, court-documented failure corpus, deterministic evaluation runners, and tamper-evident artifacts — so regulators, opposing counsel, or internal risk teams can reproduce findings without trusting a vendor narrative.

**[Dali Platform](https://dali.gammalex.com)** is GammaLex’s hosted product layer: citation review on briefs and filings, sealed evidence records (policy version + three-hash lineage), MCP/API integration, and exportable audit artifacts. The open repo is the reproducibility anchor; the platform is where legal teams operationalize review at matter scale. Public datasets mirror on Hugging Face under the [YenkLabs](https://huggingface.co/yenklabs) research org. For product access or diligence packages: [hello@gammalex.com](mailto:hello@gammalex.com).

## Open evidence ecosystem

Failures are seed data. Benchmarks measure trust. Dali is the engine.

```text
                    Dali
        Evidence Infrastructure Platform
                     │
─────────────────────────────────────────
Evidence Corpus · Benchmarks · Taxonomy
Evidence Packages · Replay Engine · APIs
```

| Public asset                         | Location                                                                                                                                                     |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Seed evidence corpus                 | [open-evidence-corpus](https://huggingface.co/datasets/yenklabs/open-evidence-corpus)                                                                        |
| Seed benchmark sample (public)       | [dali-citation-benchmark](https://huggingface.co/datasets/yenklabs/dali-citation-benchmark) — 5 hand-curated cases, 14 authorities, for methodology review and contribution |
| Full evaluation run                  | [data/results/](https://github.com/yenklabs/Dali/blob/main/data/results) and [LEADERBOARD.md](https://github.com/yenklabs/Dali/blob/main/docs/LEADERBOARD.md) — 524 citations, 3 models, 5 jurisdiction tracks |
| Verification taxonomy                | [dali-verification-taxonomy](https://huggingface.co/datasets/yenklabs/dali-verification-taxonomy)                                                            |
| Evidence interchange (EPS / RFC-001) | [RFC-001](https://github.com/yenklabs/Dali/blob/main/docs/specs/RFC-001-evidence-json-v1.md) · [yenklabs.com draft](https://yenklabs.com/artifacts/evidence-package-spec-v0.1) |
| Investigations                       | [yenklabs.com/failures](https://yenklabs.com/failures)                                                                                                       |

Full index: [huggingface.co/yenklabs](https://huggingface.co/yenklabs)

## Research artifacts

Dali publishes reusable research assets that support reproducible evaluation. Seed samples and the full evaluation run are named separately.

### Datasets

- [Dali Open Evidence Corpus](datasets/open-evidence-corpus/) — [Hugging Face](https://huggingface.co/datasets/yenklabs/open-evidence-corpus) · *available*
- [Dali Citation Benchmark (Seed Sample)](datasets/citation-benchmark/) — [Hugging Face](https://huggingface.co/datasets/yenklabs/dali-citation-benchmark) · *available* (5 cases / 14 authorities)
- [Dali Verification Taxonomy](datasets/verification-taxonomy/) — [Hugging Face](https://huggingface.co/datasets/yenklabs/dali-verification-taxonomy) · *available*
- [Dali Evaluation Prompts](datasets/evaluation-prompts/) — *planned*

### Benchmarks

- [Reproducible evaluation workflows](benchmarks/)
- Cross-jurisdiction benchmark suite — [`data/benchmark/`](data/benchmark/)
- [Full evaluation run / releases](data/results/) — 524 citations · 3 models · 5 jurisdiction tracks · *available*

### Models

Planned baseline research models built from open evidence artifacts. [Models roadmap](models/README.md) — all *planned*:

- Verification Taxonomy Classifier
- Citation Risk Classifier
- Authority Matching Baseline
- Proposition Support Classifier

Models support the evidence ecosystem. They do not replace it.

### Evidence

- [Reusable evidence artifacts](evidence/) supporting reproducibility and independent verification
- [Methodology](methodology/) and [research roadmap](docs/RESEARCH-ROADMAP.md)

## Why does it matter?

AI systems lack a standard way to create, exchange, verify, and preserve evidence. The legal industry has been an early proving ground — court-documented incidents since [*Mata v. Avianca*](docs/CASE-STUDIES.md#1-mata-v-avianca-inc-sdny-2023) (2023), including [*United States v. Cohen*](docs/CASE-STUDIES.md#2-united-states-v-cohen-sdny-2023) and [*Park v. Kim*](docs/CASE-STUDIES.md#3-park-v-kim-2d-cir-2024), which anchor the Tier 1 canonical corpus in [data/benchmark/tier1/corpus/citation_failure_cases.json](data/benchmark/tier1/corpus/citation_failure_cases.json). Dali consolidates missing public infrastructure into one MIT-licensed, deterministically replayable verification layer, with reproducibility defined through [cryptographic lineage](docs/cryptographic-lineage.md) and the public [methodology](docs/METHODOLOGY.md).

The full evaluation harness came first. The seed corpus above is a small, hand-picked public sample of that same case work, published separately so the methodology can be reviewed and contributed to without running the full harness.

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
git clone https://github.com/yenklabs/Dali && cd Dali
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
  author       = {Kha, Yen},
  title        = {Dali: Open Verification Layer for AI},
  organization = {GammaLex AI Inc.},
  year         = {2026},
  version      = {0.2.1},
  url          = {https://github.com/yenklabs/Dali},
  note         = {Early-stage open verification layer for AI — creates, scores, and preserves evidence so AI-assisted outputs can be independently verified, exchanged, and replayed}
}
```

## License

MIT. See [LICENSE](LICENSE).
