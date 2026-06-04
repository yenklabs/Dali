# data/benchmark/tier1/

Tier 1 canonical corpus: court-documented AI citation failure cases.

```
tier1/
  corpus/
    citation_failure_cases.json   Scoring-eligible and pre-canonical records
```

## What qualifies as a Tier 1 record

Scoring-eligible Tier 1 records require:

- a verifiable `source_url` pointing to a public court document, sanctions order, or regulatory filing
- a `retrieval_date` in ISO 8601 format
- an `actual_status` of `nonexistent_authority`, `misattributed`, `real_authority_wrong_proposition`, or `other`
- one or more `failure_class` values from the taxonomy in `../../../dali/schemas/ontology.md`

Records with `needs_verification: true` load for inspection but are excluded from scoring aggregates.

## Validator

```bash
python -m dali.corpus.validator data/benchmark/tier1/corpus/citation_failure_cases.json
```

## Runner

```bash
python -m dali.runners.run_integrity \
  --corpus data/benchmark/tier1/corpus/citation_failure_cases.json \
  --output data/results/demo/integrity.json
```

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for the full field reference and sourcing standard.
