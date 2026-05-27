# Dali Benchmark Results — v0.2

**Corpus:** 150 prompts across 8 categories and 5 jurisdictions  
**Run scope:** **450 prompt evaluations** — 3 models × 150-prompt corpus  
**Run date:** 2026-05-26  
**Scorer:** `claude-3-5-haiku-20241022` (cross-vendor — scores all OpenAI subjects, no self-evaluation)  
**Reproducible:** clone repo → set API keys → `python runners/run_synthetic.py --models openai_fast openai_quality openai_production`

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

**The model most willing to cite is the model most willing to fabricate.** GPT-4.1 produced 374 citations across 150 prompts; 86 of them point to URLs that do not exist.

### Existence rate by jurisdiction (aggregated across all 3 models · 524 citations)

```
                          0%        25%        50%        75%       100%
                          ├──────────┼──────────┼──────────┼──────────┤
  UK / Commonwealth  76%  ███████████████████░░░░░░  ← most reliable
  Research / policy  57%  ██████████████░░░░░░░░░░░
  US legal           33%  ████████░░░░░░░░░░░░░░░░░
  Adversarial traps  29%  ███████░░░░░░░░░░░░░░░░░░  ← citations under pressure
  Brazil (PT)         3%  █░░░░░░░░░░░░░░░░░░░░░░░░  ← weakest jurisdiction*
```

\* Brazilian gov fetches may include geo-block / robots.txt errors, not only fabrication. See Limitations.

---

## Summary leaderboard

> **Confirmed fabrication** = cited URL returns HTTP 404 (does not exist).  
> `existence_score=0.0` also includes network-unreachable and other non-404 failures — do not conflate these. See [METHODOLOGY.md](../../METHODOLOGY.md) for the full HTTP status breakdown.
>
> **Support scores** show `unverifiable` across all models: the scorer ran on every citation but could not extract supporting text from the fetched content (PDF landing pages, auth-gated sources, network-blocked govts). This is a fetch-pipeline limitation, not a scoring failure. See Limitations below.

| Model | Alias | Prompts run | Cited on | Total cites | Verified (HTTP 200) | Confirmed fab (HTTP 404) | Adversarial cited% |
|---|---|---:|---:|---:|---:|---:|---:|
| GPT-4o-mini (2024-07-18) | `openai_fast` | 150 | 49% | 94 | 44% | **16%** | 8% |
| GPT-4.1 | `openai_quality` | 150 | **94%** | 374 | 36% | **23%** | **76%** |
| GPT-4o | `openai_production` | 150 | 26% | 56 | 39% | 20% | 4% |
| **Total** | — | **450** | — | **524** | — | — | — |

---

## Breakdown by jurisdiction

### GPT-4o-mini

| Jurisdiction | Prompts | Cited% | Citations | Verified% | Fab (404)% |
|---|---:|---:|---:|---:|---:|
| US legal | 55 | 65% | 51 | 43% | 12% |
| UK / Commonwealth | 20 | 65% | 13 | **69%** | 15% |
| Brazil (Portuguese) | 20 | 35% | 8 | **0%** | 0% |
| Adversarial traps | 25 | 8% | 3 | 67% | 33% |
| Research / policy | 30 | 53% | 19 | 53% | 32% |

### GPT-4.1

| Jurisdiction | Prompts | Cited% | Citations | Verified% | Fab (404)% |
|---|---:|---:|---:|---:|---:|
| US legal | 55 | 96% | 138 | 33% | 18% |
| UK / Commonwealth | 20 | **100%** | 23 | **78%** | **0%** |
| Brazil (Portuguese) | 20 | 100% | 57 | 19% | 11% |
| Adversarial traps | 25 | 76% | 64 | 27% | **48%** |
| Research / policy | 30 | 97% | 92 | 60% | 26% |

### GPT-4o

| Jurisdiction | Prompts | Cited% | Citations | Verified% | Fab (404)% |
|---|---:|---:|---:|---:|---:|
| US legal | 55 | 35% | 32 | 22% | 19% |
| UK / Commonwealth | 20 | 25% | 5 | **80%** | **0%** |
| Brazil (Portuguese) | 20 | 5% | 1 | 0% | 0% |
| Adversarial traps | 25 | 4% | 1 | 100% | 0% |
| Research / policy | 30 | 43% | 17 | 59% | 29% |

---

### Behaviour on adversarial citation traps (25 prompts each)

```
GPT-4o-mini          ████████████████████████░  92% refused/didn't cite  ✅
                     ██░░░░░░░░░░░░░░░░░░░░░░░   8% cited — 33% of those URLs fab (404)

GPT-4.1              ██████░░░░░░░░░░░░░░░░░░░  24% refused/didn't cite
                     ███████████████████░░░░░░  76% cited — 48% of those URLs fab (404)  ⚠️

GPT-4o               ████████████████████████░  96% refused/didn't cite  ✅
                     █░░░░░░░░░░░░░░░░░░░░░░░░   4% cited — 0% confirmed fab in this slice
```

Adversarial prompts are designed to elicit confident fabrication. GPT-4.1's behaviour here is the strongest single argument for treating engagement and fabrication as inversely linked — when pushed, the model that engages most also fabricates almost half its responses.

---

## Why we test across jurisdictions

Most legal-AI citation benchmarks evaluate US federal cases only. That underweights the actual deployment risk: AI legal tooling is being adopted in jurisdictions where training-data coverage is thinner, citation conventions differ, and the consequences of fabrication are identical.

Three tracks address this directly:

- **UK / Commonwealth (20 prompts).** Common-law structure that should transfer cleanly from US-heavy training data. If a model fabricates here, it's a hard signal. In v0.2 it didn't — UK/Commonwealth was the strongest jurisdiction at 76% verified, 5% confirmed fabricated.
- **Brazil (20 prompts, Portuguese).** Civil-law system with Portuguese-language statutory citations. Tests multilingual + non-common-law citation behavior. In v0.2 this was the weakest jurisdiction at 3% verified. Caveat: some Brazilian gov failures may be fetch-pipeline issues (geo-block / robots.txt), not fabrication.
- **Cross-jurisdictional research & policy (30 prompts).** EU AI Act, OECD, NIST, ICO, Singapore PDPC — citations that span borders and citation conventions. In v0.2 these resolved at 57% verified, 27% confirmed fabricated.

The gap between UK (76% verified) and Brazil (3% verified) is what a US-only benchmark cannot see. That gap is the case for cross-jurisdictional testing.

---

## Notable findings

> All numbers are aggregates across all 3 models (524 citations total) unless a single model is named.

**UK / Commonwealth was the strongest jurisdiction: 76% verified, 5% confirmed fabricated.** BAILII (`bailii.org`) and UK Supreme Court (`supremecourt.uk`) URL patterns resolved consistently. Common-law citation structure appears well-represented in OpenAI training data.

**Brazil was the weakest jurisdiction: 3% verified across 66 citations.** Brazilian government sources (`planalto.gov.br`, `stf.jus.br`, `stj.jus.br`) almost never resolved. GPT-4.1 cited on 100% of Brazil prompts but only 19% of those URLs verified. Caveat: some failures may be fetch-pipeline (geo-block, robots.txt) rather than fabrication — verify individual URLs in a browser before claiming a specific citation is invented.

**GPT-4.1 on adversarial traps: 76% engaged, 48% confirmed fabricated.** The model most likely to take the bait on citation-trap prompts — prompts specifically designed to elicit confident fabrication. Nearly half the URLs it produced in response to these traps return HTTP 404.

**GPT-4o on adversarial traps: 4% engaged.** The most conservative model under citation pressure. High refusal is safer at deployment; GPT-4o cited on only 4% of adversarial prompts vs GPT-4.1's 76%.

**Policy / regulatory citations had the highest fabrication rate by category: 43%.** EU AI Act, ICO guidance, Colorado SB-205 and similar policy texts have unstable URL patterns and frequent path drift — 28 of 65 cited policy URLs resolved (43% fabricated). This is the strongest argument for canonical-ID schemes rather than URL-based citation.

---

## Breakdown by category (aggregated across all 3 models)

| Category | Prompt × model runs | Cited on | Total cites | Verified (HTTP 200) | Fab (HTTP 404) |
|---|---:|---:|---:|---:|---:|
| US case citations | 75 | 71% | 105 | 24% | 13% |
| Adversarial traps | 75 | 29% | 68 | 29% | **47%** |
| Brazil (Portuguese) | 60 | 47% | 66 | **3%** | 9% |
| US statutory interpretation | 45 | 76% | 65 | 43% | 18% |
| Policy / regulatory | 45 | 67% | 65 | 48% | **43%** |
| Academic claims | 45 | 62% | 63 | **67%** | 11% |
| US contract law | 45 | 47% | 51 | 39% | 22% |
| UK / Commonwealth | 60 | 63% | 41 | **76%** | 5% |
| **Total** | **450** | — | **524** | — | — |

*Prompt × model runs = number of prompts in the category × 3 models. "Cited on" = % of those runs where the model produced at least one citation. "Total cites" = sum of all citations across the 3 models on this category. Bolded values mark the highest and lowest in each metric column.*

---

## Metrics

### Existence rate

The fraction of citations that resolve to a live document. Broken down by HTTP status:

- **HTTP 200** — verified real. Cited URL resolves.
- **HTTP 403** — blocked by server (anti-scraping, geo-block). Likely real but unverifiable.
- **HTTP 404** — confirmed fabrication. The URL does not exist.
- **Other / network** — indeterminate. Could be real or fabricated.

Reporting `existence_score=0.0` as "fabricated" without the 404 breakdown overclaims. See [METHODOLOGY.md](../../METHODOLOGY.md) for the policy.

### Support scoring

Each citation that resolves is scored by the judge model (`claude-3-5-haiku-20241022`):

- `supported` — cited source directly supports the claim
- `partial` — cited source supports a weaker or qualified version
- `unsupported` — cited source does not support the claim
- `unverifiable` — judge ran but could not extract relevant text (PDF landing page, auth gate, etc.)

In this run all citations scored `unverifiable`. This is a fetch-pipeline limitation: many resolved URLs return PDF landing pages or auth-gated HTML from which the judge cannot extract text. It does not mean citations are correct — it means the pipeline could not determine support either way.

### Confirmed fabrication (HTTP 404)

The count of cited URLs that return HTTP 404. This is the narrowest, most defensible definition of fabrication: the model invented a URL that resolves to nothing. The broader `existence_score=0.0` bucket includes 403s and network errors and should not be called fabrication.

---

## Limitations

1. **Support scores are uniformly unverifiable** in this run due to fetch-pipeline depth (PDF landing pages, auth-gated sources). The existence pipeline works; the content-extraction layer needs deeper fetching for support scoring to be meaningful.
2. **Brazil fetch failures may be infrastructure, not fabrication.** Several planalto.gov.br and stf.jus.br paths that returned 0% existence may be geo-blocked or robots.txt-restricted from the benchmark runner's IP. Manual browser verification recommended before citing "Brazil = 0%" as a fabrication finding.
3. **N=150 prompts per model, one run each.** No temperature averaging. Results are indicative, not statistically powered for small differences.
4. **Scorer is Claude 3.5 Haiku** — adequate for existence-vs-support classification but conservative on `unverifiable`. A deeper fetch + richer judge prompt is planned for v1.

---

## How to reproduce

### Requirements

```
python >= 3.11
OPENAI_API_KEY      (for GPT models)
ANTHROPIC_API_KEY   (for support scorer — Claude 3.5 Haiku)
```

### Run

```bash
git clone https://github.com/yenk/Dali.git
cd Dali
pip install -r requirements.txt

# Full 3-model run (150 prompts each)
python runners/run_synthetic.py \
  --models openai_fast openai_quality openai_production \
  --output results/v0.2/$(date +%Y-%m-%d)/

# Single model
python runners/run_synthetic.py \
  --models openai_quality \
  --output results/v0.2/$(date +%Y-%m-%d)/

# Adversarial only (smoke run, ~25 prompts)
python runners/run_synthetic.py \
  --models openai_fast \
  --prompt-filter adversarial \
  --output results/v0.2/smoke-$(date +%Y-%m-%d)/
```

Model aliases are defined in `runners/model_registry.py`. To add a new model, add an entry there.

Results are written per-model to `results/v0.2/<date>/`:
- `<alias>.json` — 150 per-prompt result records (schema: `results/v0.2/schema.json`)
- `methodology.json` — run metadata: git SHA, scorer model, provider reliability, pipeline versions

### Schema

Per-prompt result records conform to `results/v0.2/schema.json` (JSON Schema Draft 2020-12).

---

## Corpus breakdown

| File | Category | Count | Notes |
|---|---|---|---|
| `synthetic/legal/case_citations.jsonl` | US case law | 25 | Landmark cases + recent decisions |
| `synthetic/legal/statutory_interpretation.jsonl` | US statutes | 15 | CFAA, ADA, ACA, ERISA, FHA, CDA §230 |
| `synthetic/legal/contract_law.jsonl` | Contract law | 15 | Restatement, UCC, CISG, leading cases |
| `synthetic/legal/uk_commonwealth.jsonl` | UK / Commonwealth | 20 | UK, AU, CA, NZ — 12/3/3/2 split |
| `synthetic/legal/brazil.jsonl` | Brazil | 20 | STF, LGPD, CDC, Civil Code — Portuguese |
| `synthetic/research/policy_citations.jsonl` | Policy / regulatory | 15 | EU AI Act, EO 14110, GDPR Art. 22, Colorado AI Act |
| `synthetic/research/academic_claims.jsonl` | Academic / empirical | 15 | Landmark papers + adversarial fabrication probes |
| `synthetic/adversarial/hallucination_prone.jsonl` | Adversarial | 25 | Designed to elicit confident fabrication |
| **Total** | | **150** | |

---

## Citation

If you use these results in research:

```bibtex
@misc{dali-2026,
  title   = {Dali: Open Citation Integrity and Evidentiary Infrastructure for Legal AI},
  author  = {Kha, Yen},
  year    = {2026},
  version = {0.2},
  url     = {https://github.com/yenk/Dali}
}
```
