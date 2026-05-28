# Dali

**Dali is open evidentiary infrastructure for evaluating whether AI-generated legal citations remain reproducible, attributable, and verifiable over time.**

Dali is designed for probabilistic AI systems operating in legal environments where reproducibility, provenance, and reconstructability matter.

> A citation checker asks whether a citation exists.
>
> Dali asks whether the citation, retrieval pathway, verification state, and policy context can still be reconstructed months or years later during litigation, audit, or appellate review.


## Core concepts

| Concept | What it means |
|---|---|
| **Citation integrity** | Whether the cited authority exists and resolves to a real source |
| **Workflow reconstructability** | Whether the pathway that produced the citation can be traced |
| **Replayable evidence** | Whether the evaluation can be reproduced and re-verified under a fixed policy version |

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
Attribution  Provenance  Replayability  Verifiability
```

Dali produces a deterministic, versioned `CitationIntegrityResult` for every evaluated citation, including reproducible scoring metadata and evidence hashes so benchmark runs can be replayed consistently over time.

## Evaluation tiers

| Tier | Corpus | Purpose |
|---|---|---|
| **Tier 1** | Court-documented citation failures (e.g. *Mata v. Avianca*) | Deterministic, policy-versioned ground truth |
| **Tier 2** | Synthetic probe corpus across US, UK / Commonwealth, Brazil, adversarial traps, and cross-jurisdictional policy / academic workflows | Live model evaluation |

Tier 1 establishes the canonical benchmark corpus. Tier 2 extends evaluation into model-facing prompt behavior and cross-jurisdiction citation robustness.

## Latest results (v0.2 · 2026-05-26)

**450 prompt evaluations across 3 OpenAI models produced 524 citations in aggregate, evaluated under a deterministic, policy-versioned verification pipeline.**

> **Tier 1 corpus (canonical standard): 3 scoring-eligible cases**  
> (*Mata v. Avianca*, *US v. Cohen*, *Park v. Kim*)
>
> Expanding this corpus is the highest-priority contribution track. See [CONTRIBUTING.md](CONTRIBUTING.md).
>
> The 524-citation figures below reflect Tier 2 synthetic probe evaluations.

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

US-only legal benchmarks underweight risk where legal citation structure, language distribution, and public-authority coverage differ materially from dominant English-language training corpora.

Aggregated across all 524 generated citations:

| Jurisdiction track | Verified (HTTP 200) | Confirmed fabricated (HTTP 404) |
|---|---:|---:|
| UK / Commonwealth (UKSC, BAILII) | **76%** | 5% |
| Cross-jurisdictional research / policy | 57% | 27% |
| US legal (cases, statutes, contracts) | 33% | 17% |
| Adversarial citation traps | 29% | 47% |
| Brazil (Portuguese, civil law) | **3%** | 9% |

UK common-law citation structures transferred relatively well from dominant English-language training distributions.

Brazilian Portuguese civil-law workflows showed the weakest transferability across all evaluated tracks, with only 3% resolving successfully under deterministic verification.

A cross-jurisdiction benchmark is how you identify these failures before the system is operating in front of courts, regulators, or legal review bodies.

→ Bar charts, per-model leaderboard, full per-jurisdiction breakdown, methodology, and reproducible run instructions: **[results/v0.2/](results/v0.2/)**

---

## Quick start

```bash
git clone https://github.com/yenk/Dali
cd Dali
python -m venv .venv
```

Activate the environment:

```bash
# Bash / Zsh
source .venv/bin/activate

# Fish
source .venv/bin/activate.fish
```

```bash
pip install -r requirements.txt
python runners/run_integrity.py \
  --corpus benchmarks/tier1/corpus/citation_failure_cases.json \
  --output results/demo/integrity.json
```

This runs the deterministic Tier 1 evaluator locally. No API keys or hosted services required.

Expected output:

```text
INFO run_integrity: loading corpus: benchmarks/tier1/corpus/citation_failure_cases.json
INFO run_integrity: corpus: 4 total, 3 scoring-eligible, 0 pre-canonical, 1 needs-verification
INFO run_integrity: evaluating 3 record(s)
INFO run_integrity:   evaluating: mata-v-avianca-2023
INFO run_integrity:   evaluating: us-v-cohen-2023
INFO run_integrity:   evaluating: mata-derivative-reporter-swap-001
INFO run_integrity: wrote 3 result(s) to results/demo/integrity.json

--- Integrity Run Summary ---

  case_id:        mata-v-avianca-2023
  authority:      Mata v. Avianca, Inc.
  citation:       Varghese v. China Southern Airlines Co., 925 F.3d 1339 (11th Cir. 2019)
  source_url:     https://www.courtlistener.com/docket/63107798/mata-v-avianca-inc/
  verification:   FAILED
  recoverability: infeasible
  risk:           critical

  case_id:        us-v-cohen-2023
  authority:      United States v. Cohen (post-conviction motion citation incident)
  citation:       Three nonexistent federal decisions cited in a supervised-release termination mo...
  source_url:     https://www.courtlistener.com/docket/8009608/united-states-v-cohen/
  verification:   FAILED
  recoverability: infeasible
  risk:           critical
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

- eyecite integration as the canonical legal citation parser
- CourtListener-backed canonical citation schema and resolution layer
- Evidence JSON v1.0 RFC publication
- expanded cross-jurisdiction benchmark corpus (UK / Commonwealth, Brazil)
- deterministic replay and reproducibility artifacts
- multi-model comparison runs across OpenAI, Gemini, and open-weight models
- expanded benchmark coverage for:
  - misattribution
  - proposition drift
  - fabricated authority detection
- contributor and academic partnership expansion around legal AI reproducibility research

Longer-range direction: [docs/roadmap.md](docs/roadmap.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the quick start, corpus field reference, and contribution tracks. Open issues are tagged `good first issue` and `help wanted`.

For methodology, scoring rubric, and policy versioning see [METHODOLOGY.md](METHODOLOGY.md) and [docs/policy-versioning.md](docs/policy-versioning.md).

## How to cite

See [CITATION.cff](CITATION.cff), or:

```bibtex
@software{dali-2026,
  title        = {Dali: Evidentiary Infrastructure for Legal AI},
  author       = {Kha, Yen},
  year         = {2026},
  version      = {0.2.0},
  organization = {GammaLex AI Inc.},
  url          = {https://github.com/yenk/Dali},
  note         = {Evaluates whether AI-generated legal citations remain reproducible, attributable, and defensible under scrutiny}
}
```

## License

MIT. See [LICENSE](LICENSE).

Dali is an open evidentiary infrastructure project for legal AI systems.

Maintained by GammaLex AI Inc.
Primary author: Yen Kha.
