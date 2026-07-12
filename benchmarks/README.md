# Dali Benchmarks

Reproducible evaluation workflows, cross-jurisdiction benchmark suites, and versioned benchmark releases.

## In this repository

| Asset | Location |
|-------|----------|
| Tier 1 canonical corpus | [`data/benchmark/tier1/`](../data/benchmark/tier1/) |
| Tier 2 evaluation prompts | [`data/benchmark/tier2/`](../data/benchmark/tier2/) |
| Published run artifacts | [`data/results/`](../data/results/) |
| Deterministic Tier 1 runner | [`dali/runners/run_integrity.py`](../dali/runners/run_integrity.py) |
| Tier 2 synthetic runner | [`dali/runners/run_synthetic.py`](../dali/runners/run_synthetic.py) |
| Leaderboard | [`docs/LEADERBOARD.md`](../docs/LEADERBOARD.md) |

## Hugging Face

- [Dali Citation Benchmark](https://huggingface.co/datasets/yenklabs/dali-citation-benchmark)
- [Organization profile](https://huggingface.co/yenklabs)

## Reproduce a run

```bash
pip install -r requirements.txt
python -m tools.cli replay
```

See [docs/quickstart.md](../docs/quickstart.md).
