# For software engineers

You are here because you saw a benchmark repo and want to know if it's worth contributing to. This doc is the 2-hour on-ramp — enough to land a first PR.

---

## What the code actually does

Dali is a Python project. The core flow is:

```
benchmarks/tier1/corpus/citation_failure_cases.json   ← canonical court-documented cases
       │
       ▼
corpus/                                                ← validator, anonymizer, taxonomy, lineage, policy
       │
       ▼
runners/run_integrity.py                               ← deterministic Tier 1 evaluator (no API keys)
       │
       ▼
results/<run>/integrity.json                          ← CitationIntegrityResult artifacts, hash-sealed
```

Tier 2 adds live model evaluation:

```
benchmarks/tier2/**/*.jsonl                           ← synthetic probe prompts across jurisdictions
       │
       ▼
runners/run_synthetic.py + runners/model_registry.py  ← provider abstraction (OpenAI, Anthropic, etc.)
       │
       ▼
scoring/{existence,support,verification}.py           ← URL fetch + verification + support scoring
       │
       ▼
results/v0.2/<date>/openai_*.json                     ← per-model run output
```

The MCP server in `dali_mcp/` exposes corpus validation and prompt scaffolding tools so contributors can work from Claude Desktop, VS Code, or Cursor without leaving their editor.

---

## Get the project running in 10 minutes

```bash
git clone https://github.com/yenk/Dali && cd Dali
python -m venv .venv && source .venv/bin/activate    # activate.fish on Fish
pip install -r requirements.txt
pytest tests/                                          # should be green
python runners/run_integrity.py \
  --corpus benchmarks/tier1/corpus/citation_failure_cases.json \
  --output results/demo/integrity.json
```

If `pytest tests/` is green and `results/demo/integrity.json` exists, you're set up.

---

## Codebase tour (15 min read)

| Path | What's in it | Notes |
|---|---|---|
| `corpus/` | Python package: schema, validator, anonymizer, taxonomy, policy, lineage, loader | Pure-Python, no external deps for Tier 1 |
| `runners/` | Canonical CLI entrypoints: `run_integrity.py` (Tier 1, offline), `run_synthetic.py` (Tier 2, live), `model_registry.py` (provider config) | |
| `dali_cli/` | Short-verb dispatcher mirroring the MCP tool vocabulary (`lint`, `score`, `replay`, `probe`, `draft`, `pack`). Thin wrapper over the runners + MCP impl modules. | Invoke via `python -m dali_cli <verb>` |
| `scoring/` | Scoring modules: `existence` (URL fetch), `verification` (HTTP-level), `support` (semantic) | Tier 2 only |
| `schemas/` | JSON schemas: canonical citation, evidence bundle, integrity result | Schema-first; changes need spec proposal |
| `specs/` | RFCs: currently RFC-001 (Evidence JSON v1) | Spec contributions live here |
| `dali_mcp/` | MCP server exposing six short-verb tools (`lint`, `score`, `replay`, `probe`, `draft`, `pack`) | Editor-integrated contributor workflow; same code path as the CLI |
| `benchmarks/tier1/corpus/` | Canonical court-documented JSON corpus + `internal/` blocklist for anonymizer | The `internal/` folder is gitignored from public except for the anonymizer input |
| `benchmarks/tier2/` | JSONL prompt corpora by category (`legal/`, `research/`, `adversarial/`) | |
| `results/v0.2/` | Versioned, immutable run artifacts | Immutable once merged |
| `tests/` | pytest suite | Should stay green |
| `scripts/generate_benchmark_snapshot.py` | Regenerates the hero chart from v0.2 results | One-off rendering |

---

## Good first issues (ranked by impact)

The repo's `good first issue` label is the canonical source — these are representative.

| # | What | Why it matters | Skills |
|---|---|---|---|
| 1 | **Canonicalization layer for legal citations** | Issue [#5](https://github.com/yenk/Dali/issues/5). Eyecite integration is on the roadmap; this is the foundational normalization layer. Highest infrastructure impact. | Python, regex, schema design |
| 2 | **Non-OpenAI providers in model registry** | Issue [#8](https://github.com/yenk/Dali/issues/8). Currently only OpenAI is tested; Anthropic and open-weight providers are the gap. | Python, API integration |
| 3 | **Reproducibility verification workflow** | Issue [#11](https://github.com/yenk/Dali/issues/11). CI workflow that re-runs Tier 1 and verifies deterministic hash equality across commits. | GitHub Actions, pytest |
| 4 | **Interactive benchmark visualization dashboard** | Issue [#9](https://github.com/yenk/Dali/issues/9). v0.2 results are currently a static PNG + JSON; an interactive view dramatically increases shareability. | Frontend (suggest: Observable, Streamlit, or static HTML+d3) |
| 5 | **Deep-fetch support extraction pipeline** | Issue [#6](https://github.com/yenk/Dali/issues/6). Move from URL existence (HTTP 200/404) to semantic support (does the page actually support the cited proposition?). | Python, HTML parsing, NLP |

Pick one, comment on the issue with your approach before coding, then open a PR. Pre-PR discussion is preferred over drive-by PRs because schema and methodology changes have non-obvious downstream constraints.

---

## Architecture decisions worth knowing about

These are calls the maintainer has made deliberately. Engaging with them is welcome; ignoring them produces PRs that won't merge.

1. **Tier 1 is offline by design.** No network, no API keys, no external services. Anything that requires network access goes in Tier 2. The boundary is enforced.
2. **Policy versioning is enforced at the runner level.** Runs across mismatched policy versions cannot be silently aggregated. If you change scoring, you bump policy version. See [docs/policy-versioning.md](policy-versioning.md).
3. **Result files are immutable once merged.** A new run goes in a new dated directory. No overwriting. This is what makes long-horizon replay credible.
4. **Schemas are first-class.** Changes to `schemas/` or the Evidence JSON contract require an issue with label `spec-change`. See [CONTRIBUTING.md § Specification contributions](../CONTRIBUTING.md#specification-contributions).
5. **Anonymization is non-optional.** Public corpus records identify cases by case caption only. Attorney names go through `corpus/anonymizer.py`. The `benchmarks/tier1/corpus/internal/` blocklist is the input to that pipeline.
6. **Minimalism rule on ontology.** A new failure-class category is added only when an existing one demonstrably collapses two distinct legal behaviors into the same bucket. See [CONTRIBUTING.md § What we do not accept](../CONTRIBUTING.md#what-we-do-not-accept).
7. **Determinism is a load-bearing property, not a quality-of-life feature.** SHA-256 evidence hashes are tested. Replays that produce non-equal hashes are a regression, not flakiness.

---

## PR checklist

The full list lives in [CONTRIBUTING.md § Pull request checklist](../CONTRIBUTING.md#pull-request-checklist). The non-obvious items:

- `pytest tests/` is green locally before pushing
- New corpus records pass `python -m dali_cli lint <path>` (terminal) or `lint` (MCP)
- New synthetic prompts pass `python -m dali_cli probe <path>` (terminal) or `probe` (MCP)
- Schema changes have an accompanying `spec-change` issue
- No PII in corpus records — `corpus/anonymizer.py` has been run if any attorney names appear in source text
- Commit authorship accurately represents the contributor

The `commit-attribution-guard.yml` workflow enforces the last item.

---

## What you get back

- Named credit in release notes and `CITATION.cff` contributor roll
- Your contribution becomes part of an MIT-licensed, citable, deterministically reproducible artifact
- For substantive infrastructure work (canonicalization, model registry, viz dashboard): co-authorship eligibility on the v0.3 technical report

---

## Contact

- Bug reports: use the [bug issue template](../.github/ISSUE_TEMPLATE/bug.md)
- Spec or schema proposals: use the [spec-change template](../.github/ISSUE_TEMPLATE/spec-change.md)
- Open methodology questions: open an issue with label `methodology`
- General discussion: [GitHub Discussions](https://github.com/yenk/Dali/discussions) (enable when available)
