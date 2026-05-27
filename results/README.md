# Results

Benchmark outputs are generated locally and are not required for cloning or testing the repository.

Use `results/demo/` for quick local smoke runs:

```bash
python runners/run_integrity.py \
  --corpus data/public/citation_failure_cases.json \
  --output results/demo/integrity.json
```

Use `results/v0.2/<date>/` for dated benchmark runs that you intend to review or publish.

The old `results/v0.1/` snapshot has been removed from the public repo because the current public benchmark contract is v0.2.
