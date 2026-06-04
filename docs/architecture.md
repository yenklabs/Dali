# Architecture

This page describes the public benchmark layers and artifact flow for
deterministic corpus evaluation and live model benchmarking.

Dali's public architecture is intentionally small: corpus records, reproducible
runners, versioned methodology, result schemas, and published evidence
artifacts.

## Public benchmark layers

| Layer | Name | Purpose | Main files |
|---|---|---|---|
| **Tier 1** | Canonical Case Corpus | Court-documented citation failures with deterministic scoring | `benchmarks/tier1/`, `runners/run_integrity.py` |
| **Tier 2** | Synthetic Probes | Controlled prompt probes for live model evaluation | `benchmarks/tier2/`, `runners/run_synthetic.py` |
| **Schemas** | Result contracts | Stable JSON contracts for reusable artifacts | `schemas/`, `specs/` |
| **Results** | Published benchmark runs | Reviewable outputs and run metadata | `results/v0.2/` |
| **Contributor tools** | MCP + validators | Corpus and prompt validation workflows | `dali_mcp/`, `corpus/validator.py` |

## Artifact flow

```text
Court-documented incident
        |
        v
Tier 1 corpus record
        |
        v
Deterministic evaluator
        |
        v
CitationIntegrityResult
        |
        v
Versioned result artifact + evidence hash
```

Tier 2 extends the same evidence discipline to live model behavior:

```text
Synthetic prompt corpus
        |
        v
Model response
        |
        v
Citation extraction
        |
        v
URL recoverability + support scoring
        |
        v
Per-model result JSON + methodology metadata
```

## What is deterministic

Tier 1 is deterministic. It runs locally without API keys and applies a
workflow-centric defensibility rubric to court-documented failures.

Stable inputs produce stable `CitationIntegrityResult` artifacts under the same
policy version.

## What is live evaluation

Tier 2 is live model evaluation. It depends on model responses, source
reachability, and scorer configuration. Every run writes methodology metadata so
readers can inspect model aliases, policy versions, parser versions, and scorer
settings.

Tier 2 results are benchmark evidence, not universal claims about a model.

## Public artifacts

| Artifact | Purpose |
|---|---|
| `results/demo/integrity.json` | Local Tier 1 smoke output, gitignored |
| `results/v0.2/{date}/integrity.json` | Versioned Tier 1 run output |
| `results/v0.2/{date}/<model_id>.json` | Per-model Tier 2 output |
| `results/v0.2/{date}/methodology.json` | Run provenance and configuration |
| `results/v0.2/schema.json` | Schema for per-prompt Tier 2 records |
| `schemas/integrity-result.schema.json` | Schema for `CitationIntegrityResult` |

## Related docs

- [README.md](../README.md)
- [docs/examples.md](examples.md)
- [METHODOLOGY.md](../METHODOLOGY.md)
- [results/v0.2](../results/v0.2/)
