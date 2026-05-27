# Dali

**Dali is designed for probabilistic AI systems operating in high-consequence legal environments where reproducibility, provenance, and evidentiary integrity matter.**

Dali evaluates whether AI-generated citations and supporting workflows remain reconstructable, attributable, and defensible under scrutiny.

Where traditional citation checkers ask “does this citation exist?”, Dali asks “can this workflow be reconstructed and replayed if challenged?”


## Core concepts

| Concept | What it means |
|---|---|
| **Citation integrity** | Whether the cited authority exists and resolves to a real source |
| **Workflow reconstructability** | Whether the pathway that produced the citation can be traced |
| **Reconstructable evidence** | Whether the result can be reproduced and re-verified under a versioned policy |

## How it works

```text
        Legal AI workflow
                |
                v
         Citation generated
                |
                v
   Can this workflow be reconstructed
        and replayed if challenged?
                |
                v
          Dali evaluates
                |
   +-----------+------------+-------------+
   |            |            |            |          
   v            v            v            v           
Attribution  Provenance  Replayability  Defensibility
```

Dali produces a versioned `CitationIntegrityResult` for every evaluated citation, including reproducible scoring metadata and evidence hashes so benchmark runs can be replayed consistently over time.

## Evaluation tiers

| Tier | Corpus | Purpose |
|---|---|---|
| **Tier 1** | Court-documented citation failures (e.g. *Mata v. Avianca*) | Deterministic, policy-versioned ground truth |
| **Tier 2** | Synthetic probe corpus across US, UK / Commonwealth, Brazil, adversarial traps, and cross-jurisdictional policy/academic | Live model evaluation |

Tier 1 is the benchmark standard. Tier 2 extends evaluation to model-facing prompt behavior.

## Latest results (v0.2 · 2026-05-26)

**450 prompt evaluations** across 3 OpenAI models, producing **524 citations** in aggregate. Scored by Claude 3.5 Haiku (cross-vendor — no model grades itself).

### The model that cited most willingly also fabricated most often

```
                       0%        25%        50%        75%       100%
                       ├──────────┼──────────┼──────────┼──────────┤
  GPT-4o-mini   49%    ████████████░░░░░░░░░░░░░  → 94 cites, 16% return HTTP 404
  GPT-4.1       94%    ████████████████████████░  → 374 cites, 23% return HTTP 404
  GPT-4o        26%    ██████░░░░░░░░░░░░░░░░░░░  → 56 cites, 20% return HTTP 404
```

GPT-4.1 was the most engaged model and the most fabrication-prone: of its 374 citations, **86 point to URLs that do not exist**. On adversarial citation-trap prompts specifically, GPT-4.1 took the bait 76% of the time, fabricating 48% of those URLs.

### Why we test across jurisdictions

US-only legal benchmarks underweight risk in places where AI legal tooling is being deployed but training-data coverage is thinner. Aggregated across all 524 citations:

| Jurisdiction track | Verified (HTTP 200) | Confirmed fabricated (HTTP 404) |
|---|---:|---:|
| UK / Commonwealth (UKSC, BAILII) | **76%** | 5% |
| Cross-jurisdictional research / policy | 57% | 27% |
| US legal (cases, statutes, contracts) | 33% | 17% |
| Adversarial citation traps | 29% | 47% |
| Brazil (Portuguese, civil law) | **3%** | 9% |

UK common-law citation structure transfers cleanly from training data. Brazilian Portuguese civil-law does not — and the gap is large enough that a US-only benchmark would have missed it entirely. A cross-jurisdictional benchmark is how you find these gaps before the AI is in front of a court.

→ Bar charts, per-model leaderboard, full per-jurisdiction breakdown, methodology, and reproducible run instructions: **[results/v0.2/](results/v0.2/)**

---

## Quick start

```bash
git clone https://github.com/yenk/Dali
cd Dali
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python runners/run_integrity.py \
  --corpus data/public/citation_failure_cases.json \
  --output results/demo/integrity.json
```

This runs the deterministic Tier 1 evaluator locally. No API keys or hosted services required.

Expected output:

```text
Loaded 4 canonical cases (3 scoring-eligible)
Results written to results/demo/integrity.json
```

Each result is a `CitationIntegrityResult` artifact with reconstructability, defensibility risk, verification recoverability, and a deterministic evidence hash.

For Tier 2 setup, model registry, and benchmark commands see [docs/examples.md](docs/examples.md).

## What this enables

Using the canonical corpus and the shared `CitationIntegrityResult` contract, you can:

- evaluate AI-assisted citation workflows against real court-documented failures
- measure provenance continuity and workflow reconstructability
- test retrieval and RAG systems for authority integrity regressions
- compare citation integrity behavior across models or pipeline versions
- replay evaluations under fixed policy versions for reproducibility
- produce deterministic benchmark artifacts and evidence hashes

## Near-term roadmap

- eyecite integration as the canonical parser
- canonical citation schema (CourtListener-backed)
- Evidence JSON v1.0 RFC publication
- expanded cross-jurisdiction corpus (UK/Commonwealth, Brazil)
- multi-model comparison runs (GPT-4o-mini · GPT-4.1 · GPT-4o complete as of v0.2)

Longer-range direction: [docs/roadmap.md](docs/roadmap.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the quick start, corpus field reference, and contribution tracks. Open issues are tagged `good first issue` and `help wanted`.

For methodology, scoring rubric, and policy versioning see [METHODOLOGY.md](METHODOLOGY.md) and [docs/policy-versioning.md](docs/policy-versioning.md).

## How to cite

See [CITATION.cff](CITATION.cff), or:

```bibtex
@misc{dali-2026,
  title   = {Dali: Open Citation Integrity and Evidentiary Infrastructure for Legal AI},
  author  = {Kha, Yen},
  year    = {2026},
  version = {0.2},
  url     = {https://github.com/yenk/Dali}
}
```

## License

MIT. See [LICENSE](LICENSE).
Dali is an open evidentiary infrastructure project for legal AI systems, maintained by GammaLex AI Inc.
