# Pull request

## Summary

<!-- What does this PR change? One paragraph or bullet list. -->

## Contribution track

<!-- Which track from CONTRIBUTING.md does this fall under? -->
- [ ] Corpus expansion (Tier 1 canonical cases)
- [ ] Synthetic prompts (Tier 2 probes)
- [ ] Ontology / spec change (has `spec-change` issue linked below)
- [ ] Parser coverage
- [ ] Benchmark replication (external model run)
- [ ] Documentation / fix
- [ ] Other:

## Checklist

- [ ] `pytest tests/` passes
- [ ] New corpus records pass `python -m corpus.validator data/public/citation_failure_cases.json`
- [ ] New synthetic prompts pass `validate_prompt_jsonl` (CLI or MCP)
- [ ] Schema / ontology changes have a linked `spec-change` issue: #
- [ ] No PII in corpus records — `corpus/anonymizer.py` run if needed
- [ ] Result files (if any) include `methodology.json` and are in `results/v0.2/<date>/`
- [ ] Commit author has a real name and email

## Related issues

<!-- Closes # / Refs # -->
