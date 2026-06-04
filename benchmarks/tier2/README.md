# benchmarks/tier2/

Tier 2 synthetic probe corpus: model-facing prompts for live citation integrity evaluation.

```
tier2/
  legal/
    case_citations.jsonl           US case law citations
    statutory_interpretation.jsonl US statutes and regulatory text
    contract_law.jsonl             Contract law
    uk_commonwealth.jsonl          UK / Commonwealth authorities
    brazil.jsonl                   Brazil / Civil Law (Portuguese)
  research/
    academic_claims.jsonl          Academic and empirical claims
    policy_citations.jsonl         Policy and regulatory citations
  adversarial/
    hallucination_prone.jsonl      Adversarial citation-trap prompts
```

## Schema

Each JSONL record requires:

| Field | Description |
|---|---|
| `id` | Lowercase alphanumeric + underscore |
| `category` | `legal`, `research`, or `adversarial` |
| `subcategory` | Matches the file name (e.g. `case_citations`) |
| `prompt` | The model-facing prompt text (minimum 30 characters) |
| `difficulty` | `known_case`, `obscure_case`, `fabricated_likely`, `ambiguous`, `adversarial`, or `standard` |

## Runner

```bash
python runners/run_synthetic.py \
  --models openai_fast \
  --prompts benchmarks/tier2/ \
  --output results/v0.2/$(date +%Y-%m-%d)/
```

## Adding prompts

Use the MCP contributor tools (`new_prompt`, `check_prompt`, `bundle_prompts`) or follow the manual path in [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Track strategy

Tier 2 uses a hybrid coverage model. Tracks are concrete enough to reproduce
and inspect, but selected because they stress different evidence-durability
dimensions:

| Track | Evidence-durability dimension |
|---|---|
| US Legal | Baseline US legal citation behavior |
| UK / Commonwealth | Common-law transfer outside the US |
| Brazil / Civil Law (Portuguese) | Civil-law, Portuguese-language, non-English retrieval durability |
| Policy / Regulatory | Cross-institution regulatory and policy citation stability |
| Adversarial Traps | Citation pressure and fabrication resistance |

Future expansion should prioritize differentiated evidence behavior over raw
prompt count. See [docs/benchmark-expansion-strategy.md](../../docs/benchmark-expansion-strategy.md).
