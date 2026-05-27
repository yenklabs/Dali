# Examples

This page collects the most common ways to use Dali from the public repo.

## 1. Run the deterministic Tier 1 evaluator

Use the canonical case corpus to verify the workflow-centric benchmark locally without external services.

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

What this does:
- loads the public canonical corpus
- applies the deterministic Tier 1 rubric
- writes a reproducible JSON artifact under `results/demo/`

## 2. Check source reachability

If you want to see which sources are currently reachable, add `--check-reachability`.

```bash
python runners/run_integrity.py \
  --corpus data/public/citation_failure_cases.json \
  --output results/demo/integrity.json \
  --check-reachability
```

## 3. Run the shipped Tier 2 synthetic probes

Tier 2 uses the built-in 150-prompt synthetic corpus under `synthetic/`.

```bash
python runners/run_synthetic.py \
  --models openai_fast \
  --output results/v0.2/$(date +%Y-%m-%d)/
```

What this does:
- runs every prompt under `synthetic/` against the selected models
- writes one result file per model plus a `methodology.json`
- prints a live per-prompt summary and a citation-metrics table at the end

### Reading the per-prompt output

```
[06/25] adversarial_006 ... 3 citations extracted (citations_found)  exist=33%  support=0.00
   │      │                  │                       │                  │          │
   │      │                  │                       │                  │          └─ % of citations whose source text actually supports the prompt's claim
   │      │                  │                       │                  └─ % of citation URLs that resolve to a real source
   │      │                  │                       └─ response classification (see table below)
   │      │                  └─ how many citations the extractor found in the model's response
   │      └─ prompt ID from synthetic/ corpus
   └─ progress counter
```

**Response classifications:**

| Classification | Meaning | Interpretation |
|---|---|---|
| `refusal` | Model explicitly declined to cite ("I'm not confident about recent cases…") | Often the right behavior on adversarial prompts |
| `no_citations_generated` | Model answered but didn't include any citations | Neutral: answered without making things up |
| `citations_found` | Model produced citations that the extractor parsed | Now we check existence and support |

**Existence and support scoring:**

```
                Model generates citation
                          │
                          v
                  Does URL resolve?
                  ┌───────┴───────┐
                NO                YES
                  │                 │
                  v                 v
         existence = 0.0     Fetch source → Run support scorer
         support = None              │
         (skipped)                   v
                          ┌──────────────────────────┐
                          │  Verdict and score:      │
                          │   supported    → 0.5–1.0 │
                          │   partial      → 0.3–0.6 │
                          │   unsupported  → 0.0–0.3 │
                          │   unverifiable → 0.0     │
                          └──────────────────────────┘
```

`unverifiable` means the URL fetched but the scorer couldn't determine support, e.g. the page was a PDF that didn't extract, the source was blocked, or the content didn't contain the prompt's topic. It is a legitimate verdict, not a scorer error.

## 4. Run your own prompt set

You can point `--prompts` at any directory of JSONL prompts that follow the same schema as the shipped probes.

```bash
python runners/run_synthetic.py \
  --models <model-a> <model-b> \
  --prompts path/to/your/prompts/ \
  --output results/v0.2/$(date +%Y-%m-%d)/custom-synthetic.json
```

Use this for local experimentation or extended evaluation. If you want your prompts to become part of the benchmark standard, add them through the contribution path in [CONTRIBUTING.md](../CONTRIBUTING.md).

## 5. Add a new synthetic prompt

Create a JSONL entry under `synthetic/` that matches the repo schema:

```json
{
  "id": "legal_case_009",
  "category": "legal",
  "subcategory": "case_citations",
  "prompt": "...",
  "difficulty": "known_case",
  "notes": "Optional. What this prompt is testing."
}
```

Then follow the prompt contribution rules in [CONTRIBUTING.md](../CONTRIBUTING.md):
- keep the prompt neutral
- explain the failure mode it exercises
- choose the appropriate difficulty tier

## 6. Inspect a result file

The benchmark writes plain JSON, so you can inspect the output directly:

```bash
jq '.[] | {prompt_id, model_id, citation_count, existence_rate, mean_support_score}' results/v0.2/$(date +%Y-%m-%d)/*.json
```

## 7. Verify the repo

Run the test suite:

```bash
pytest tests/ -q
```

Expected: tests covering the corpus validator, anonymizer, lineage tracker, taxonomy, schema, and the deterministic Tier 1 runner.
