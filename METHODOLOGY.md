# Methodology — Dali Citation Integrity Benchmark v0.2

Dali evaluates whether AI-assisted legal citation workflows remain reconstructable, attributable, and defensible under judicial scrutiny.

The public benchmark repo, `Dali`, defines the standard. Tier 1 is deterministic and runs locally. Tier 2 evaluates live model behavior against the shipped probe corpus.

---

## Tier 1 — Canonical Case Corpus Methodology

### Overview

Tier 1 evaluates real, court-documented AI-assisted citation failures against a workflow-centric defensibility rubric. Each record in the Canonical Case Corpus represents a case where the public court record provides ground truth: the citation was fabricated, wrong, or otherwise integrity-compromised, and a judge documented it.

The scoring premise differs from traditional output-centric evaluations. We do not ask whether the model produced an incorrect citation — the court record already establishes that it did. We already know it did — the court record says so. We ask: **at the time this citation was filed, could the workflow that produced it have been audited and defended?**

### Scoring pipeline

```
Corpus record (CitationFailureCase)
  → Workflow context extraction (was retrieval used? was there human review?)
  → Defensibility rubric application (critical / high / medium / low)
  → Verification recoverability assessment (automatic / manual / infeasible)
  → CitationIntegrityResult with policy_version + evidence_hash
```

### Defensibility rubric

The rubric is workflow-centric, not output-centric. Two records can have the same `actual_status: nonexistent_authority` but different risk levels based on whether the workflow that produced the citation is reconstructable.

| Risk level | Criteria |
|---|---|
| `critical` | Nonexistent authority **and** workflow gaps (no verification step, source chain incomplete, reconstructability failure) — would fail Rule 11 scrutiny if undetected at filing |
| `high` | Material citation misrepresentation recoverable only through manual investigation; or nonexistent authority without critical workflow gaps |
| `medium` | Citation mutation (reporter swap, page drift, year drift) with reconstructable lineage — automatic verification tools can detect |
| `low` | Formatting or non-material drift; full provenance intact |

### Verification recoverability

| Level | Meaning |
|---|---|
| `infeasible` | The workflow cannot be audited post-hoc; nonexistent authority with reconstructability failure |
| `manual` | Verification is possible but requires human investigation (e.g., pulling the original filing, checking Westlaw) |
| `automatic` | Verification tools (cite-check, reporter parsers) could have detected the failure automatically |

### Failure class taxonomy

12-class closed vocabulary from `corpus/taxonomy.py`:

| Class | Description |
|---|---|
| `nonexistent_authority` | The cited case, statute, or authority does not exist in any verifiable form |
| `fabricated_quote` | A quoted passage is attributed to a real source but does not appear in that source |
| `real_case_wrong_holding` | The cited case exists but the stated holding misrepresents what the court actually held |
| `wrong_jurisdiction` | Authority cited as binding when it is from a non-binding jurisdiction |
| `wrong_court_level` | Case attributed to the wrong court |
| `overruled_authority` | Cited as good law when the case has been overruled, reversed, or vacated |
| `temporal_validity_failure` | Authority not yet decided or no longer valid at the relevant time |
| `parallel_citation_mismatch` | Parallel citations do not match the same case |
| `semantic_misalignment` | Source exists but does not support the claim made about it |
| `citation_mutation` | Reporter, volume, page, or year of a real citation has been altered |
| `provenance_gap` | Citation lacks the lineage data needed to reconstruct how it was generated |
| `reconstructability_failure` | The pipeline that produced the citation cannot be audited or replayed |

### Policy versioning

Every `CitationIntegrityResult` records a composite `policy_version` string covering five sub-dimensions. Results from different policy versions cannot be silently aggregated. See [docs/policy-versioning.md](docs/policy-versioning.md) for the full versioning schema.

### Scoring eligibility

Records must carry a verifiable `source_url` and seven other required fields to be scoring-eligible. `annotation_confidence` does not substitute for a verifiable source. See `corpus/validator.py` for the complete gate.

### Mutation lineage

Tier-2 synthetic probes derive from Tier-1 canonical cases via `parent_incident_id` + `mutation_type`. Example: a reporter-swap probe derived from Mata v. Avianca tests whether downstream verification distinguishes `F.2d` from `F.3d` mutations from total fabrication.

Lineage resolution walks the `parent_incident_id` chain to produce a `mutation_lineage` list in each result. Cycles and depth > 16 are caught by the resolver.

---

## Tier 2 — Synthetic Probes Methodology

Tier 2 is the public/supporting synthetic track for the benchmark standard.

Tier 1 records are canonical cases, such as Mata v. Avianca, stored as structured corpus records. Tier 2 records are prompt probes stored under `synthetic/` and used to test model or retrieval behavior against controlled citation tasks.

## Overview

Tier 2 evaluates live citation-generation behavior under controlled synthetic conditions. Unlike Tier 1, which operates from court-documented ground truth, Tier 2 measures how models and retrieval systems perform against mutation and verification stress tests in real time. The existence and support dimensions here are probabilistic — they depend on live model output and source reachability at run time, rather than established judicial record.

This section describes the exact scoring methodology used for Tier-2 synthetic probes. It is intended to allow independent reproduction and peer review.

---

## Pipeline

```
Prompt -> Model -> LLM output -> Citation extraction -> URL fetch -> Support scoring -> Result JSON
```

Each step is logged. The text fetched from a reachable source URL is hashed and used for support scoring in that run.

---

## Step 1: Citation Extraction

Citations are extracted from raw model output via three regex-based methods applied in confidence order:

### Method 1: `url_explicit`
Regex: `https?://[^\s\])\>\"']+` with trailing punctuation stripped.

### Method 2: `case_pattern`
Matches legal case citations in the format `Party v. Party, <volume> <reporter> <page> (year)`.

Reporters covered: U.S., S.Ct., L.Ed.(2d), F., F.2d, F.3d, F.Supp., F.Supp.2d, F.Supp.3d, N.E., N.E.2d, N.W., N.W.2d, S.E., S.E.2d, S.W., S.W.2d, A., A.2d, A.3d, P., P.2d, P.3d, So., So.2d, So.3d, Cal., Cal.2d–5th, N.Y., N.Y.2d–3d.

Party names may include lowercase connectors: `of`, `the`, `and`, `a`, `an`, `for`, `in`, `on`, `to`, `de`, `la`, `von`, `van`.

**URL derivation for case patterns:** None in the current synthetic track. Case pattern citations are recorded with `resolution_method='case_pattern'` and `existence_score=0.0`. CourtListener URL resolution is planned post-Week 12.

### Method 3: `doi`
Regex: `\b10\.\d{4,9}/[-._;/:A-Z0-9]+` (case-insensitive). URL constructed as `https://doi.org/{doi}`.

### Deduplication
Span-based: a citation from a later method is dropped if its character span overlaps with a higher-confidence match. Identical URLs are deduplicated across methods regardless of span.

---

## Step 2: URL Fetch

For each resolvable URL, an HTTP GET is issued and the response body is normalized into text for scoring.

| Parameter | Value |
|---|---|
| HTTP client | Python standard-library URL fetch |
| User-Agent | `Dali-Benchmark-Runner/1.0` |
| Timeout | 10 seconds |
| Text extraction | HTML tag stripping with whitespace normalization |
| Hash algorithm | SHA-256 of extracted UTF-8 text |

The `content_hash` in the result JSON is the SHA-256 of exactly what was scored.

---

## Step 3: Existence Scoring

| Condition | `existence_score` | `verdict` |
|---|---|---|
| HTTP 200–299 | 1.0 | `verified` or `redirected` |
| Timeout or connect error | 0.5 | `unreachable` |
| HTTP 4xx/5xx | 0.0 | `dead` |
| No resolvable URL | 0.0 | `unresolvable` |

`redirected` is used when `http_status` is 200–299 but `redirect_chain` is non-empty.

### Interpretation of `existence_score = 0.0`

A zero existence score does not mean the cited URL was fabricated. Aggregate result interpretation must distinguish three sub-cases by `http_status`:

| HTTP status | Likely meaning | Counts as fabrication? |
|---|---|---|
| `404` | URL path does not exist | **Yes** — confirmed fabrication or wrong path |
| `403` | Source server blocked verification | **No** — URL likely real but anti-scraper protection prevents verification (common on `supreme.justia.com`, `supremecourt.gov`, `stf.jus.br`) |
| `0` / network error | Connection failed | Indeterminate — could be DNS, timeout, geo-block |

When reporting an aggregate "fabrication rate" externally, distinguish:

- **Confirmed fabrication** = share of citations returning HTTP 404
- **Verification blocked** = share returning HTTP 403 (URL probably real)
- **Verified existing** = share returning HTTP 2xx
- **Network noise** = share with status 0 / timeout

A claim like *"X% of citations were fabricated"* without this breakdown is overclaiming. The Dali result schema preserves `http_status` per citation so any aggregation can be re-derived from the raw artifact.

The longer-term mitigation for 403 blocking is content-addressable archival (Wayback Machine, archive.is, or first-party snapshots stored under content hashes) — planned for a future release.

---

## Step 4: Support Scoring

**Model:** LLM-based verification scorer, configurable via `DALI_SCORER_MODEL`. Use a cross-vendor model (different provider than your subject models) to avoid self-evaluation bias. The scorer model used in each run is recorded in `methodology.json`.
**Parameters:** `temperature=0.0`, `max_tokens=256`
**Source input:** first 3,000 characters of the fetched source text

System prompt (exact):

> You are a citation integrity auditor. Given a legal or factual CLAIM and the SOURCE TEXT it is supposed to be grounded in, evaluate whether the source actually supports the claim.
>
> Respond with JSON only — no preamble, no explanation outside the JSON object.
>
> Response schema: `{"score": float 0.0–1.0, "verdict": "supported"|"partial"|"unsupported"|"unverifiable", "reasoning": "one sentence"}`

The `claim_text` passed to the scorer is the sentence or clause from the model output that directly references the cited source.

**Fallback chain:** source < 50 chars → `unverifiable` (no API call); API error or parse failure → `unverifiable`.

**Score thresholds:**

| Score | Verdict |
|---|---|
| ≥ 0.6 | `supported` |
| 0.3–0.59 | `partial` |
| < 0.3 | `unsupported` |
| — | `unverifiable` |

---

## Result Schema

Each result file (`results/v0.2/{date}/{model_id}.json`) contains one JSON object per prompt:

```json
{
  "prompt_id": "legal_case_001",
  "model_id": "hosted-verification-model",
  "output": "[raw model output]",
  "citations": [
    {
      "citation_text": "Smith v. Jones, 123 F.3d 456",
      "source_url": "https://...",
      "resolution_method": "case_pattern",
      "existence_verified": false,
      "existence_score": 0.0,
      "http_status": 0,
      "content_hash": null,
      "storage_path": null,
      "support_score": null,
      "support_verdict": null,
      "verdict": "unresolvable",
      "captured_at": "2026-05-25T..."
    }
  ],
  "citation_count": 1,
  "existence_rate": 0.0,
  "mean_support_score": null,
  "run_at": "2026-05-25T..."
}
```

A `methodology.json` file is written alongside each run recording exact model versions, scorer model, params, and the git SHA of the benchmark runner used.

---

## Model Version Pinning

Every run records exact dated model version strings:
- benchmark subject models recorded in run metadata

If a provider deprecates a model version, a new versioned results directory is created. Old results are never modified.

---

## Scorer Bias Disclosure

The scorer model is recorded in `methodology.json` per run. For any published run, the scorer must be from a different provider than the subject models being evaluated. This cross-vendor requirement is the primary guard against self-evaluation bias. The v0.2 public run satisfies this requirement; the specific scorer identity is recorded in the run artifacts rather than in this document to keep the methodology provider-neutral.

---

## Reproducibility

To reproduce any result:

1. Re-run the same benchmark version against the same prompt and model version.
2. Pass the `claim_text` and fetched source text to the hosted LLM-based verification scorer with the exact system prompt above.
3. Compare the `content_hash` in the result with the SHA-256 of the fetched text used for scoring.

Tier 1 results are fully deterministic from corpus annotations. Tier 2 results depend on live model responses and currently reachable source URLs, so they should be interpreted as versioned run artifacts rather than immutable ground truth.

---

## Limitations

The current benchmark is a credible, well-scoped public standard. A few methodological constraints are worth stating up front:

- **Corpus size.** Tier 1 results at the current corpus size should be treated as exploratory rather than population-level. Aggregate claims should stay tied to corpus size and the versioned methodology.
- **Scorer overlap.** When the support scorer and the subject model are from the same model family, support scores should be interpreted with self-evaluation bias in mind. Future versions will use an independent scorer.
- **Confidence reporting.** Aggregate summaries do not yet carry explicit confidence intervals. This is intentional at v0.2 corpus size — re-introducing them is part of the v0.3 / v1 roadmap as the corpus expands.
- **URL reachability drift.** Tier 2 source-URL fetching is live. Source reachability can drift over time independently of the benchmark — versioned snapshots are the longer-term path.
