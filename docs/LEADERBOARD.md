# Dali Legal AI Citation Integrity Leaderboard

**Latest run: v0.2 · 2026-05-26 · 524 citations · 3 OpenAI models · 5 jurisdiction tracks**

This leaderboard ranks models on **evidence integrity**, not output fluency.
A model that refuses to cite cannot fabricate. A model that cites confidently and wrongly is the dangerous one. Read the table accordingly.

---

## How to read this

| Column | What it measures |
|---|---|
| **Citation rate** | % of prompts in which the model produced at least one citation. *Higher is not better.* |
| **Verified (HTTP 200)** | % of generated URLs that resolved successfully under deterministic fetch |
| **Fabricated (HTTP 404)** | % of generated URLs that returned 404 — the citation does not exist |
| **Adversarial trap rate** | % of adversarial trap prompts on which the model took the bait |
| **Defensibility verdict** | Qualitative — would this model's output survive Rule 11 scrutiny without human re-verification? |

The ideal model has a **moderate** citation rate, a **high** verified rate, and a **low** adversarial-trap rate. Citation-eagerness without verification is the failure mode courts are sanctioning.

---

## v0.2 results

| Rank | Model | Citation rate | Verified | Fabricated | Adversarial trap rate | Defensibility |
|---:|---|---:|---:|---:|---:|---|
| 1 | **GPT-4o** | 26% | — | 20% (of 56 cites) | — | Most cautious; needs human verification |
| 2 | **GPT-4o-mini** | 49% | — | 16% (of 94 cites) | — | Mid-tier; needs human verification |
| 3 | **GPT-4.1** | 94% | — | **23% (of 374 cites)** | **76%** | **Unsafe to deploy** without independent verification layer |

**Source:** `data/results/v0.2/2026-05-26/openai_*.json` · policy version pinned in `methodology.json`.

### Per-jurisdiction verification (aggregate across all 3 models)

| Jurisdiction track | Verified (HTTP 200) | Confirmed fabricated (HTTP 404) |
|---|---:|---:|
| UK / Commonwealth (UKSC, BAILII) | **76%** | 5% |
| Cross-jurisdictional policy / regulatory | 57% | 27% |
| US legal (cases, statutes, contracts) | 33% | 17% |
| Adversarial citation traps | 29% | 47% |
| Brazil / Civil Law (Portuguese) | **3%** | 9% |

The Portuguese civil-law result is the single most important data point in v0.2: a 25× verification gap between common-law English and civil-law Portuguese on the same underlying models. Any legal-AI product claiming multi-jurisdiction support should be required to publish their equivalent number.

---

## Submit a model

The leaderboard is open. To add your model:

1. Run Tier 2 against any OpenAI-compatible or Anthropic API endpoint:

   ```bash
   python -m dali.runners.run_synthetic \
     --models <your-model-id> \
     --prompts data/benchmark/tier2/ \
     --output data/results/v0.2/$(date +%Y-%m-%d)-<your-handle>/
   ```

2. Validate the output schema:

   ```bash
   python -m dali.corpus.validator data/results/v0.2/$(date +%Y-%m-%d)-<your-handle>/
   ```

3. Open a PR titled `leaderboard: add <model-id> v0.2 results` adding:
   - Your run directory under `data/results/v0.2/`
   - One row in the table above
   - The `policy_version` from your run output (required — runs across mismatched policy versions cannot be silently aggregated)

Reviewers verify deterministic replay before merge. Result files are immutable once merged.

See [docs/for-researchers.md](for-researchers.md) for the full submission protocol and what counts as a defensible row.

---

## Pinned questions for the community

- **Should we add a "refusal rate" column?** A model that refuses risky prompts may be safer than a model that cites confidently. Currently captured implicitly in citation rate. Discussion: open an issue with label `methodology`.
- **Should adversarial-trap results be weighted higher in ranking?** Arguably yes — that's where real-world citation failures originate. Discussion welcome.
- **What's the threshold below which a model should not be deployed in a non-anglophone jurisdiction?** v0.2 suggests **anything under 20% verified** is operationally unsafe. We'd like community input before formalizing this in v0.3.

---

## Versioning

The leaderboard is versioned with the benchmark. `v0.2` results are pinned to policy version `v0.2.*` and cannot be combined with v0.3+ runs without an explicit `--allow-cross-version` flag. See [docs/policy-versioning.md](policy-versioning.md).

Last updated: 2026-06-04.
