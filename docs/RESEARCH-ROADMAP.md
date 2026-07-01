# Dali Research Roadmap

Future public artifacts follow this progression. Each layer builds on the previous one.

```text
Open Evidence Corpus
        ↓
Verification Taxonomy
        ↓
Citation Benchmark
        ↓
Baseline Research Models
        ↓
Interactive Hugging Face Spaces
        ↓
Community Contributions
        ↓
Annual Evidence Reports
```

## Repository map

```text
Dali/
├── datasets/          → published dataset artifacts (index + HF mirrors)
├── models/            → lightweight baseline research models (roadmap)
├── benchmarks/        → evaluation workflows and releases
├── methodology/       → public methodology index
├── evidence/          → evidence artifact index
├── docs/              → methodology, specs, guides
├── tools/             → CLI, MCP, scripts
└── CONTRIBUTING.md
```

Canonical runtime code remains in `dali/`; canonical benchmark data remains in `data/benchmark/` during the transition. Top-level indexes link to both.

## Guiding principle

The benchmark is not the product. The datasets are not the product. The models are not the product.

Together they form Dali's open evidence infrastructure.

Every new artifact should be:

- Open
- Reproducible
- Independently verifiable
- Community extensible
- Useful beyond Dali itself

## Models roadmap

| Release | Model | Purpose |
|---------|-------|---------|
| v0.1 | Verification Taxonomy Classifier | Predict standardized verification outcome labels |
| v0.2 | Citation Risk Classifier | Estimate citation verification risk from evidence metadata |
| v0.3 | Authority Matching Baseline | Reproducible authority matching baseline |
| v0.4 | Proposition Support Classifier | Classify proposition support relationships |

See [`models/README.md`](../models/README.md).

## Hugging Face ecosystem

- [Organization](https://huggingface.co/yenklabs)
- [Datasets](https://huggingface.co/yenklabs/datasets)
- Planned Spaces: Evidence Explorer, Benchmark Dashboard, Citation Verification Demo
