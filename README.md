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
| **Tier 2** | 150-prompt synthetic probe corpus across multiple jurisdictions | Live model evaluation |

Tier 1 is the benchmark standard. Tier 2 extends evaluation to model-facing prompt behavior.

### Tier 2 jurisdiction and category coverage

```
synthetic/                                              total: 150
│
├── legal/                                                95 prompts
│   ├── case_citations          (25)  US federal cases
│   ├── statutory_interpretation (15)  US statutes (USC, FRCP)
│   ├── contract_law            (15)  US contract doctrine + Restatements
│   ├── uk_commonwealth         (20)  UK, AUS, CAN, NZ — UKSC, AGLC
│   └── brazil                  (20)  STF/STJ, Portuguese-language
│
├── adversarial/                                          25 prompts
│   └── hallucination_prone     (25)  citation traps designed to
│                                     provoke fabrication
│
└── research/                                             30 prompts
    ├── academic_claims         (15)  scholarly references, DOIs
    └── policy_citations        (15)  EU AI Act, OECD, US policy
```

| Jurisdiction | Prompts | Share |
|---|---|---|
| US | ~95 | 63% |
| UK / Commonwealth (UK, AUS, CAN, NZ) | 20 | 13% |
| Brazil (Portuguese) | 20 | 13% |
| Cross-jurisdictional (EU, OECD, academic) | 15 | 10% |

The Brazil track is in Portuguese, stressing multilingual citation behavior in a civil-law system. Most legal AI benchmarks do not test this.

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
- first public multi-model benchmark runs

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
