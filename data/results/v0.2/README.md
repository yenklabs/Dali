# Dali Benchmark Results: v0.2

**Corpus:** 150 prompts across 8 categories and 5 jurisdiction / coverage tracks  
**Run scope:** 450 prompt evaluations across 3 OpenAI models  
**Run date:** 2026-05-26  
**Verification:** deterministic citation existence and HTTP recoverability checks  
**Reproducible:** clone repo, set API keys, run `python -m dali.runners.run_synthetic --models openai_fast openai_quality openai_production`

---

## Where to look first

| Question | Start here |
|---|---|
| What was evaluated? | [Appendix: Corpus composition](#appendix-corpus-composition) |
| What is the headline result? | [Key finding](#key-finding) |
| Which model fabricated most? | [Summary leaderboard](#summary-leaderboard) |
| Which coverage tracks were hardest? | [Breakdown by jurisdiction](#breakdown-by-jurisdiction) |
| What are the limitations? | [Limitations](#limitations) |
| How do I reproduce it? | [How to reproduce](#how-to-reproduce) |

---

## Key finding

**The gap between UK (76% verified) and Brazil (3% verified) is what a US-only benchmark cannot see.**

Most legal-AI citation benchmarks evaluate US federal cases only. That underweights deployment risk in jurisdictions where citation structure, language distribution, and public authority coverage differ materially from dominant English-language training corpora. A cross-jurisdictional benchmark is how you find these gaps before the AI is in front of a court.

---

## Headline charts

### Engagement: what fraction of 150 prompts did each model cite on?

```
                       0%        25%        50%        75%       100%
                       ├──────────┼──────────┼──────────┼──────────┤
  GPT-4o-mini   49%    ████████████░░░░░░░░░░░░░░
  GPT-4.1       94%    ████████████████████████░  ← cited almost everything
  GPT-4o        26%    ██████░░░░░░░░░░░░░░░░░░░  ← most conservative
```

### Confirmed fabrication: what % of each model's cited URLs return HTTP 404?

```
                       0%        10%        20%        30%        40%
                       ├──────────┼──────────┼──────────┼──────────┤
  GPT-4o-mini   16%    ████████░░░░░░░░░░░░
  GPT-4.1       23%    ███████████░░░░░░░░░  ← highest fabrication, highest engagement
  GPT-4o        20%    ██████████░░░░░░░░░░
```

In this run, higher citation engagement correlated with higher fabrication rates under adversarial pressure. GPT-4.1 produced 374 citations across 150 prompts; 86 point to URLs that do not exist.

### Existence rate by jurisdiction (aggregated across all 3 models · 524 citations)

```
                          0%        25%        50%        75%       100%
                          ├──────────┼──────────┼──────────┼──────────┤
  UK / Commonwealth  76%  ███████████████████░░░░░░  ← most reliable
  Policy / regulatory 57% ██████████████░░░░░░░░░░░
  US legal           33%  ████████░░░░░░░░░░░░░░░░░
  Adversarial traps  29%  ███████░░░░░░░░░░░░░░░░░░  ← citations under pressure
  Brazil / Civil Law  3%  █░░░░░░░░░░░░░░░░░░░░░░░░  ← weakest track*
```

\* Brazilian gov fetches may include geo-block / robots.txt errors, not only fabrication. See [Limitations](#limitations).

---

## Summary leaderboard

> **Confirmed fabrication** = cited URL returns HTTP 404. HTTP 403 and network errors are reported separately as unverifiable, not fabrication. See [Metrics](#metrics) for the full HTTP status breakdown.

| Model | Alias | Prompts run | Cited on | Total cites | Verified (HTTP 200) | Confirmed fab (HTTP 404) | Adversarial cited% |
|---|---|---:|---:|---:|---:|---:|---:|
| GPT-4o-mini (2024-07-18) | `openai_fast` | 150 | 49% | 94 | 44% | **16%** | 8% |
| GPT-4.1 | `openai_quality` | 150 | **94%** | 374 | 36% | **23%** | **76%** |
| GPT-4o | `openai_production` | 150 | 26% | 56 | 39% | 20% | 4% |
| **Total** | | **450** | | **524** | | | |

---

## Breakdown by jurisdiction

### GPT-4o-mini

| Jurisdiction | Prompts | Cited% | Citations | Verified% | Fab (404)% |
|---|---:|---:|---:|---:|---:|
| US legal | 55 | 65% | 51 | 43% | 12% |
| UK / Commonwealth | 20 | 65% | 13 | **69%** | 15% |
| Brazil / Civil Law (Portuguese) | 20 | 35% | 8 | **0%** | 0% |
| Adversarial traps | 25 | 8% | 3 | 67% | 33% |
| Policy / regulatory | 30 | 53% | 19 | 53% | 32% |

### GPT-4.1

| Jurisdiction | Prompts | Cited% | Citations | Verified% | Fab (404)% |
|---|---:|---:|---:|---:|---:|
| US legal | 55 | 96% | 138 | 33% | 18% |
| UK / Commonwealth | 20 | **100%** | 23 | **78%** | **0%** |
| Brazil / Civil Law (Portuguese) | 20 | 100% | 57 | 19% | 11% |
| Adversarial traps | 25 | 76% | 64 | 27% | **48%** |
| Policy / regulatory | 30 | 97% | 92 | 60% | 26% |

### GPT-4o

| Jurisdiction | Prompts | Cited% | Citations | Verified% | Fab (404)% |
|---|---:|---:|---:|---:|---:|
| US legal | 55 | 35% | 32 | 22% | 19% |
| UK / Commonwealth | 20 | 25% | 5 | **80%** | **0%** |
| Brazil / Civil Law (Portuguese) | 20 | 5% | 1 | 0% | 0% |
| Adversarial traps | 25 | 4% | 1 | 100% | 0% |
| Policy / regulatory | 30 | 43% | 17 | 59% | 29% |

---

### Behaviour on adversarial citation traps (25 prompts each)

```
GPT-4o-mini          ████████████████████████░  92% refused/didn't cite  ✅
                     ██░░░░░░░░░░░░░░░░░░░░░░░   8% cited, 33% of those URLs fab (404)

GPT-4.1              ██████░░░░░░░░░░░░░░░░░░░  24% refused/didn't cite
                     ███████████████████░░░░░░  76% cited, 48% of those URLs fab (404)  ⚠️

GPT-4o               ████████████████████████░  96% refused/didn't cite  ✅
                     █░░░░░░░░░░░░░░░░░░░░░░░░   4% cited, 0% confirmed fab in this slice
```

Adversarial prompts are designed to elicit confident fabrication. GPT-4.1's behaviour is the strongest single argument for treating engagement and fabrication as coupled: under pressure, the model that engages most also fabricates almost half its cited URLs.

---

## Why we test across jurisdictions

Most legal-AI citation benchmarks evaluate US federal cases only. That underweights deployment risk in jurisdictions where citation structure, language distribution, and public authority coverage differ materially from dominant English-language training corpora.

Three tracks address this directly:

- **UK / Commonwealth (20 prompts).** Common-law structure that should transfer cleanly from US-heavy training data. If a model fabricates here, it's a hard signal. In v0.2 it didn't: UK/Commonwealth was the strongest jurisdiction at 76% verified, 5% confirmed fabricated.
- **Brazil / Civil Law (20 prompts, Portuguese).** Civil-law system with Portuguese-language statutory citations. Tests multilingual, non-common-law, non-English retrieval durability. In v0.2 this was the weakest track at 3% verified. Caveat: some Brazilian gov failures may be fetch-pipeline issues (geo-block / robots.txt), not fabrication.
- **Policy / regulatory (30 prompts).** EU AI Act, OECD, NIST, ICO, Singapore PDPC: citations that span borders, institutions, and citation conventions. In v0.2 these resolved at 57% verified, 27% confirmed fabricated.

The gap between UK (76% verified) and Brazil (3% verified) is what a US-only benchmark cannot see.

---

## Notable findings

> All numbers are aggregates across all 3 models (524 citations total) unless a single model is named.

**UK / Commonwealth was the strongest jurisdiction: 76% verified, 5% confirmed fabricated.** BAILII (`bailii.org`) and UK Supreme Court (`supremecourt.uk`) URL patterns resolved consistently. Common-law citation structure appears well-represented in training data.

**Brazil / Civil Law was the weakest track: 3% verified across 66 citations.** Brazilian government sources (`planalto.gov.br`, `stf.jus.br`, `stj.jus.br`) almost never resolved. GPT-4.1 cited on 100% of Brazil prompts but only 19% of those URLs verified. The track is included because it stresses civil-law structure, Portuguese-language sources, and non-English retrieval durability. Note: some failures may be fetch-pipeline (geo-block, robots.txt) rather than fabrication.

**GPT-4.1 on adversarial traps: 76% engaged, 48% confirmed fabricated.** The highest-engagement model also produced the highest confirmed fabrication rate in this run. Nearly half the URLs it produced in response to citation-trap prompts return HTTP 404.

**GPT-4o on adversarial traps: 4% engaged.** The most conservative model under citation pressure. High refusal is safer at deployment.

**Policy / regulatory citations had the highest fabrication rate by category: 43%.** EU AI Act, ICO guidance, Colorado SB-205 and similar policy texts have unstable URL patterns and frequent path drift. This is the strongest argument for canonical-ID schemes rather than URL-based citation.

---

## Breakdown by category (aggregated across all 3 models)

| Category | Prompt × model runs | Cited on | Total cites | Verified (HTTP 200) | Fab (HTTP 404) |
|---|---:|---:|---:|---:|---:|
| US case citations | 75 | 71% | 105 | 24% | 13% |
| Adversarial traps | 75 | 29% | 68 | 29% | **47%** |
| Brazil / Civil Law (Portuguese) | 60 | 47% | 66 | **3%** | 9% |
| US statutory interpretation | 45 | 76% | 65 | 43% | 18% |
| Policy / regulatory | 45 | 67% | 65 | 48% | **43%** |
| Academic claims | 45 | 62% | 63 | **67%** | 11% |
| US contract law | 45 | 47% | 51 | 39% | 22% |
| UK / Commonwealth | 60 | 63% | 41 | **76%** | 5% |
| **Total** | **450** | | **524** | | |

*Prompt × model runs = prompts in category × 3 models. "Cited on" = % of runs where the model produced at least one citation. Bolded values mark the highest and lowest in each metric column.*

---

## Metrics

### Existence rate

Citations are verified deterministically by HTTP status:

| Status | Interpretation |
|---|---|
| HTTP 200 | Verified: the cited URL resolves |
| HTTP 403 | Blocked: likely real but unverifiable from this pipeline |
| HTTP 404 | Confirmed fabrication: the URL does not exist |
| Other / network | Indeterminate: could be real or fabricated |

**Confirmed fabrication** means HTTP 404 only. Do not conflate `existence_score=0.0` (which includes 403s and network errors) with fabrication. See [METHODOLOGY.md](../../../docs/METHODOLOGY.md) for the full policy.

### Support evaluation

Support evaluation is currently conservative due to fetch-pipeline limitations: PDF landing pages, auth-gated sources, and restricted government endpoints. v0.2 findings should be interpreted primarily as citation existence and recoverability results rather than semantic-support verification.

---

## Limitations

1. **Support scores are uniformly unverifiable** in this run due to fetch-pipeline depth. The existence pipeline works; content-extraction depth is the current constraint.
2. **Brazil fetch failures may be infrastructure, not fabrication.** Several planalto.gov.br and stf.jus.br paths may be geo-blocked or robots.txt-restricted from the benchmark runner's IP. Manual browser verification recommended before interpreting "Brazil = 0%" as a fabrication finding.
3. **N=150 prompts per model, one run each.** No temperature averaging. Results are indicative, not statistically powered for small differences.

---

## How to reproduce

```bash
git clone https://github.com/yenk/Dali.git
cd Dali
pip install -r requirements.txt

# Full 3-model run (150 prompts each)
python -m dali.runners.run_synthetic \
  --models openai_fast openai_quality openai_production \
  --output data/results/v0.2/$(date +%Y-%m-%d)/

# Single model
python -m dali.runners.run_synthetic \
  --models openai_quality \
  --output data/results/v0.2/$(date +%Y-%m-%d)/

# Adversarial only (~25 prompts)
python -m dali.runners.run_synthetic \
  --models openai_fast \
  --prompt-filter adversarial \
  --output data/results/v0.2/smoke-$(date +%Y-%m-%d)/
```

Requires `OPENAI_API_KEY` for GPT models and `ANTHROPIC_API_KEY` for support scorer. Model aliases are defined in `dali/runners/model_registry.py`. Per-run output includes `<alias>.json` (per-prompt results) and `methodology.json` (git SHA, pipeline versions, scorer identity).

Full methodology: [METHODOLOGY.md](../../../docs/METHODOLOGY.md). Per-result schema: `data/results/v0.2/schema.json`.

---

## Appendix: Corpus composition

See `data/benchmark/tier2/` and [METHODOLOGY.md](../../../docs/METHODOLOGY.md) for full corpus composition. The v0.2 public run used 150 prompts across 8 categories and 5 jurisdiction / coverage tracks.

| File | Category | Count |
|---|---|---|
| `data/benchmark/tier2/legal/case_citations.jsonl` | US case law | 25 |
| `data/benchmark/tier2/legal/statutory_interpretation.jsonl` | US statutes | 15 |
| `data/benchmark/tier2/legal/contract_law.jsonl` | Contract law | 15 |
| `data/benchmark/tier2/legal/uk_commonwealth.jsonl` | UK / Commonwealth | 20 |
| `data/benchmark/tier2/legal/brazil.jsonl` | Brazil / Civil Law (Portuguese) | 20 |
| `data/benchmark/tier2/research/policy_citations.jsonl` | Policy / Regulatory | 15 |
| `data/benchmark/tier2/research/academic_claims.jsonl` | Academic / empirical | 15 |
| `data/benchmark/tier2/adversarial/hallucination_prone.jsonl` | Adversarial | 25 |
| **Total** | | **150** |

## Appendix: Failure types covered

The v0.2 synthetic track focuses on model-facing citation behavior, especially:

- fabricated or dead URLs
- unresolvable case-pattern citations
- jurisdiction transfer failures
- adversarial citation traps
- policy and regulatory URL instability
- multilingual civil-law citation fragility

Tier 1 covers court-documented citation failure classes in the canonical corpus.
See [METHODOLOGY.md](../../../docs/METHODOLOGY.md#failure-class-taxonomy) for the
closed taxonomy.

---

## Appendix: Run provenance

The `data/results/v0.2/2026-05-26/` directory contains artifacts from two sequential runs on the same day:

| File | Model | git SHA | Run timestamp (UTC) |
|---|---|---|---|
| `openai_fast.json` + `methodology.openai_fast.json` | GPT-4o-mini | `v0.2.0` | 2026-05-26T22:01 |
| `openai_quality.json` + `openai_production.json` + `methodology.json` | GPT-4.1, GPT-4o | `v0.2.0` | 2026-05-26T22:38 |

Both runs used identical `policy_version=v1.0.0` and `parser_version=v1.1.0`. The commits between the two SHAs were documentation-only and did not change scoring semantics. All three models' results are aggregated in this document under the same policy.

---

## Citation

```bibtex
@software{dali-2026,
  title        = {Dali: Evidentiary Infrastructure for Legal AI},
  author       = {Kha, Yen},
  year         = {2026},
  version      = {1.0.0},
  organization = {GammaLex AI Inc.},
  url          = {https://github.com/yenk/Dali},
  note         = {Evaluates whether AI-generated legal citations remain reproducible, attributable, and defensible under scrutiny}
}
```
