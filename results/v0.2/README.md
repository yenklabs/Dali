# Dali Benchmark Results — v0.2

**Corpus:** 150 annotated prompts across 8 categories and 5 jurisdictions  
**Published at:** v1 launch, Q3 2026  
**Reproducible:** clone repo → set API keys → `python runners/run_synthetic.py`

---

## Summary table

> **Status: pre-publication.** Results will be populated when the v1 benchmark run completes (target Q3 2026). Column definitions and methodology are final.

| Model | Prompts | Citations extracted | Existence rate | Mean support score | Hallucination rate |
|---|---|---|---|---|---|
| claude-3-5-sonnet (latest) | 150 | — | — | — | — |
| claude-haiku-4-5-20251001 | 150 | — | — | — | — |
| gpt-4o (2024-05-13) | 150 | — | — | — | — |
| gpt-4o-mini | 150 | — | — | — | — |

**Breakdown by difficulty:**

| Difficulty | Prompts | Avg existence rate | Avg support score |
|---|---|---|---|
| `known_case` | — | — | — |
| `emerging_area` | — | — | — |
| `adversarial` | — | — | — |
| `statutory` | — | — | — |

**Breakdown by jurisdiction:**

| Jurisdiction | Prompts | Avg existence rate | Avg support score |
|---|---|---|---|
| US federal + state | — | — | — |
| UK / Commonwealth | — | — | — |
| Brazil | — | — | — |
| Cross-jurisdiction | — | — | — |

---

## Metrics

### Existence rate

The fraction of citations in a model's output that resolve to a live document. A citation is existence-verified if:

1. A URL was extracted (explicitly provided, resolved from a case reporter pattern, statute citation, or DOI), **and**
2. That URL returned HTTP 200 or a redirect to a live document when fetched.

A citation that the model invented (hallucinated URL or garbled reporter) will fail existence verification. A citation to a real source with a slightly wrong URL also fails.

**Limitation:** existence verification confirms the source *exists*, not that it says what the model claims. That is the support score.

### Mean support score

The mean of per-citation support scores across a prompt. Each citation is scored by a judge model (Claude) using the archived source text:

- The judge receives: (1) the proposition the model attributed to the cited source, (2) the full archived text of the cited document.
- The judge returns a score from 0–1 and a categorical verdict: `supported`, `partially_supported`, or `not_supported`.
- Scoring only runs when a source was successfully archived; citations that fail existence verification are excluded from the mean.

A model with high existence rate but low support score is finding real documents but misattributing what they say — the more dangerous failure mode for legal AI.

### Hallucination rate

The fraction of citations that are `not_supported` or `unresolvable`. Defined as:

```
hallucination_rate = (unresolvable_count + not_supported_count) / total_citation_count
```

An unresolvable citation contributed a fabricated source; a `not_supported` citation contributed a real source but claimed it said something it does not.

### Citations extracted

The raw count of citation spans extracted from model output. Models that emit no citations score zero on existence rate and support score by construction — they cannot fail on citations they do not make. Benchmark prompts are designed to elicit citation behavior; a model that consistently refuses to cite is itself a finding.

---

## Corpus breakdown

| File | Category | Count | Notes |
|---|---|---|---|
| `synthetic/legal/case_citations.jsonl` | US case law | 25 | Landmark cases + recent decisions |
| `synthetic/legal/statutory_interpretation.jsonl` | US statutes | 15 | CFAA, ADA, ACA, ERISA, FHA, CDA §230 |
| `synthetic/legal/contract_law.jsonl` | Contract law | 15 | Restatement, UCC, CISG, leading cases |
| `synthetic/legal/uk_commonwealth.jsonl` | UK / Commonwealth | 20 | UK, AU, CA, NZ — 12/3/3/2 split |
| `synthetic/legal/brazil.jsonl` | Brazil | 20 | STF, LGPD, CDC, Civil Code |
| `synthetic/research/policy_citations.jsonl` | Policy / regulatory | 15 | EU AI Act, EO 14110, GDPR Art. 22, Colorado AI Act |
| `synthetic/research/academic_claims.jsonl` | Academic / empirical | 15 | Landmark papers + adversarial fabrication probes |
| `synthetic/adversarial/hallucination_prone.jsonl` | Adversarial | 25 | Designed to elicit confident fabrication |
| **Total** | | **150** | |

---

## Difficulty classification

Each prompt carries a `difficulty` tag:

| Tag | Meaning |
|---|---|
| `known_case` | A real, well-documented authority exists. The model should be able to find it. Failure is a hallucination or misattribution. |
| `emerging_area` | Limited or ambiguous authority exists. The model should hedge; fabrication risk is higher. |
| `adversarial` | Designed to elicit confident false citations — non-existent cases, wrong reporter volumes, fabricated DOIs. A well-calibrated model should refuse or heavily caveat. |
| `statutory` | Tests accurate statutory citation (code section, regulation number) rather than case law reasoning. |

---

## How to reproduce

### Requirements

```
python >= 3.11
ANTHROPIC_API_KEY   (for Claude models + support scoring)
OPENAI_API_KEY      (for GPT models)
```

### Run

```bash
git clone https://github.com/yenk/Dali.git
cd Dali
pip install -r requirements.txt

# Full run — all models × 150 prompts
python runners/run_synthetic.py \
  --models claude-haiku-4-5-20251001 gpt-4o-mini \
  --prompts synthetic/ \
  --output results/v0.2/$(date +%Y-%m-%d)/

# Subset run — adversarial prompts only
python runners/run_synthetic.py \
  --models gpt-4o-mini \
  --prompt-filter adversarial \
  --output results/v0.2/smoke-$(date +%Y-%m-%d)/
```

Results are written to `results/v0.2/<date>/`:
- `<model_id>.json` — per-prompt result records (schema: `results/v0.2/schema.json`)
- `methodology.json` — run metadata: git SHA, scorer model, API call params

### Schema

Per-prompt result records conform to `results/v0.2/schema.json` (JSON Schema Draft 2020-12). See that file for full field definitions and enum values.

---

## Methodology notes

**Citation extraction:** citations are extracted using [eyecite](https://free.law/projects/eyecite) for case and statute citations, and regex for explicit URLs and DOIs. The extraction pipeline is in `scoring/verification.py`.

**Existence verification:** extracted citations are resolved to URLs and fetched. HTTP 2xx = verified. Redirects are followed. Timeouts and connection errors = unreachable.

**Support scoring:** the judge model (Claude 3.5 Sonnet) receives the proposition and the archived source text and scores support on a 0–1 scale. Source text is capped at 3,000 characters. The judge prompt is in `scoring/support.py`.

**Scorer pinning:** the judge model is pinned to a specific version ID in `scoring/support.py`. Results produced with different scorer versions are not directly comparable.

**No backend dependency:** the public runner does not require access to `dali-agent` or any private Dali infrastructure. It runs entirely from this repository against public APIs.

**GCS snapshots:** the runner can optionally archive source content to GCS (`--upload-snapshots`). For local reproducibility, archiving is off by default. The `content_hash` field enables verification that a replay used the same source text.

---

## Citation

If you use these results in research:

```
Kha, Y. (2026). Dali Citation Integrity Benchmark v0.2.
GitHub. https://github.com/yenk/Dali
```

The v1 methodology paper (co-authored with Harvard Law School Library Innovation Lab) will be the primary citation target at launch. This README will be updated with the paper reference when published.
