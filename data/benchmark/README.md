# data/benchmark/

Benchmark assets for Dali, organized by evaluation tier.

```
data/benchmark/
  tier1/    Canonical court-documented citation failure cases (deterministic ground truth)
  tier2/    Synthetic probe prompts for live model evaluation
```

## Tiers at a glance

| Tier | Contents | Runner | API keys needed |
|---|---|---|---|
| **Tier 1** | `tier1/corpus/citation_failure_cases.json` | `dali/runners/run_integrity.py` | No |
| **Tier 2** | `tier2/{legal,research,adversarial}/` | `dali/runners/run_synthetic.py` | Yes |

Tier 1 is the evidentiary standard. Tier 2 extends evaluation to live model behavior.

## Quick start

```bash
# Tier 1 — no network, no API key:
python -m dali.runners.run_integrity \
  --corpus data/benchmark/tier1/corpus/citation_failure_cases.json \
  --output data/results/demo/integrity.json

# Tier 2 — requires model API access:
python -m dali.runners.run_synthetic \
  --models openai_fast \
  --prompts data/benchmark/tier2/ \
  --output data/results/v0.2/$(date +%Y-%m-%d)/
```

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for how to add corpus records or synthetic prompts.
