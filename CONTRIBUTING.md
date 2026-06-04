# Contributing to Dali

Thank you for contributing to Dali. This document covers how to get involved
and what kinds of contributions are most valuable to the project.

Dali is not a general-purpose legal AI framework.
It is evidentiary infrastructure focused on whether AI-generated legal
citations remain attributable, reconstructable, and defensible under scrutiny.
Contributions should strengthen reproducibility, provenance, verification, or
benchmark integrity.

---

## Philosophy

Dali is built on a simple assumption:
A legal citation is not trustworthy merely because it appears plausible or
resolves to a real case.

A citation becomes defensible only when the workflow that produced it can be
reconstructed, verified, and independently evaluated under a versioned
methodology.

Dali therefore prioritizes:
- Reproducibility over convenience
- Provenance over opacity
- Deterministic evidence over probabilistic confidence
- Public methodology over unverifiable claims
- Verifiable sourcing over benchmark scale

The project intentionally favors methodological rigor and evidentiary
traceability over feature velocity.
A benchmark that cannot itself be audited cannot function as citation
integrity infrastructure.

### Non-goals

Dali is not:
- a legal research engine
- a generative legal assistant
- a litigation platform
- a generalized LLM benchmark suite
- a replacement for judicial review

Its scope is evidentiary evaluation and citation integrity infrastructure.

---

## 15-minute quick start

```bash
git clone https://github.com/yenk/Dali.git
cd Dali
python -m venv .venv
```

Activate the environment:

```bash
# Bash / Zsh
source .venv/bin/activate

# Fish
source .venv/bin/activate.fish
```

```bash
pip install -r requirements.txt

# Run the Tier 1 deterministic evaluator (no API keys needed)
python -m tools.cli score

# Or with explicit args / additional flags:
python -m tools.cli score data/benchmark/tier1/corpus/citation_failure_cases.json \
  --output data/results/demo/integrity.json
```

The `python -m tools.cli` shim mirrors the six MCP verbs (`lint`, `score`, `replay`, `probe`, `draft`, `pack`) and wraps the underlying runners. `python -m dali.runners.run_integrity` continues to work as the canonical entry point.

Expected output:
```text
INFO run_integrity: loading corpus: data/benchmark/tier1/corpus/citation_failure_cases.json
INFO run_integrity: corpus: 4 total, 3 scoring-eligible, 0 pre-canonical, 1 needs-verification
INFO run_integrity: evaluating 3 record(s)
INFO run_integrity:   evaluating: mata-v-avianca-2023
INFO run_integrity:   evaluating: us-v-cohen-2023
INFO run_integrity:   evaluating: mata-derivative-reporter-swap-001
INFO run_integrity: wrote 3 result(s) to data/results/demo/integrity.json

--- Integrity Run Summary ---

  case_id:        mata-v-avianca-2023
  authority:      Mata v. Avianca, Inc.
  citation:       Varghese v. China Southern Airlines Co., 925 F.3d 1339 (11th Cir. 2019)
  source_url:     https://www.courtlistener.com/docket/63107798/mata-v-avianca-inc/
  verification:   FAILED
  recoverability: infeasible
  risk:           critical

  case_id:        us-v-cohen-2023
  authority:      United States v. Cohen (post-conviction motion citation incident)
  citation:       Three nonexistent federal decisions cited in a supervised-release termination mo...
  source_url:     https://www.courtlistener.com/docket/8009608/united-states-v-cohen/
  verification:   FAILED
  recoverability: infeasible
  risk:           critical
```

Tier 1 runs entirely offline. No API keys. No external services.

**Prefer working in an editor?** If you use Claude Desktop, VS Code, or Cursor, the `tools/mcp/` tools let you do the entire contribution workflow — validate, evaluate, verify replay determinism, scaffold prompts, bundle a PR — without touching the terminal. Six short verbs: `lint`, `score`, `replay`, `probe`, `draft`, `pack`. See [tools/mcp/README.md](tools/mcp/README.md) for the 5-minute setup.

---

## First 15 minutes

If you are new to the project, this is the fastest useful path:

1. Run the Tier 1 evaluator above.
2. Read [data/results/v0.2](data/results/v0.2/) to understand the public benchmark output.
3. Open one existing Tier 1 record in `data/benchmark/tier1/corpus/citation_failure_cases.json`.
4. Validate the corpus with `python -m dali.corpus.validator data/benchmark/tier1/corpus/citation_failure_cases.json`.
5. Choose a contribution track below.

Good first contributions usually improve corpus evidence, prompt coverage,
schema clarity, or methodology explanations. Code changes are useful when they
make those artifacts easier to reproduce or review.

---

## Contribution tracks

Dali is evidentiary infrastructure, not a traditional application framework or
SDK. The project prioritizes reproducibility, provenance, deterministic
evaluation, and public benchmark integrity over feature velocity.
Contributions are valued across seven tracks:

| Track | What's needed | Where to start |
|---|---|---|
| **Corpus expansion** | Annotated real-world AI citation failure cases: especially UK/Commonwealth, Brazil, adversarial | `data/benchmark/tier1/corpus/citation_failure_cases.json` |
| **Synthetic prompts** | New Tier 2 probe prompts across legal domains | `data/benchmark/tier2/` + `tools/mcp/` contributor tools |
| **Ontology review** | Legal practitioners reviewing treatment and proposition ontology definitions | [dali/schemas/ontology.md](dali/schemas/ontology.md) + open a discussion issue |
| **Parser coverage** | eyecite wrapper improvements, jurisdiction adapters | Roadmap: see [docs/roadmap.md](docs/roadmap.md). `dali/corpus/parsers/` will land with eyecite integration. |
| **Spec authorship** | Drafting and reviewing changes to schemas and the Evidence JSON contract | `docs/specs/` |
| **Benchmark replication** | Running Tier 2 against new models and sharing results | `dali/runners/run_synthetic.py` |
| **Academic partnerships** | Law schools and court data projects: structured dataset contributions, co-authored methodology | Open issue with label `partnership` |

Code contributions are welcome but secondary to corpus quality, ontology
correctness, and specification rigor.

---

## Corpus contributions

### Tier 1: Canonical case records

Court-documented AI citation failure incidents. These live in:

```
data/benchmark/tier1/corpus/citation_failure_cases.json
```

Each scoring-eligible record requires these fields:

| Field | Description |
|---|---|
| `case_id` | Unique slug (e.g. `mata-v-avianca-2023`) |
| `incident_name` | Human-readable name |
| `year` | Year of the incident (2021–2026) |
| `jurisdiction` | Court jurisdiction code |
| `source_url` | Public URL to the court document or sanctions order |
| `retrieval_date` | ISO 8601 date the source_url was last verified |
| `source_type` | `sanctions_order`, `judicial_opinion`, `court_filing`, or `other` |
| `alleged_generated_citation` | The fabricated or hallucinated citation string |
| `actual_status` | `nonexistent_authority`, `misattributed`, `real_authority_wrong_proposition`, or `other` |
| `failure_class` | Array of failure taxonomy values (see `dali/schemas/ontology.md`) |
| `ground_truth_notes` | Human-readable explanation of what actually happened |

Validate your record before submitting:

```bash
python -m tools.cli lint data/benchmark/tier1/corpus/citation_failure_cases.json
# or, the underlying canonical command:
python -m dali.corpus.validator data/benchmark/tier1/corpus/citation_failure_cases.json
```

Optional: the `tools/mcp/` contributor interface exposes the same validation via the `lint` MCP tool for editor-integrated workflows.

Records with `needs_verification: true` load for inspection but are excluded
from scoring aggregates.

Attorney names must be removed from public records. Run `dali/corpus/anonymizer.py`
if your record contains names from the original filing.

### Tier 2: Synthetic prompt probes

Model-facing prompts for live Tier 2 evaluation. These live in:

```
data/benchmark/tier2/
  legal/
    case_citations.jsonl
    statutory_interpretation.jsonl
    contract_law.jsonl
    uk_commonwealth.jsonl
    brazil.jsonl
  research/
    academic_claims.jsonl
    policy_citations.jsonl
  adversarial/
    hallucination_prone.jsonl
```

Each record requires `id` (lowercase alphanumeric + underscore), `category`,
`subcategory`, `prompt` (≥ 30 chars), and `difficulty`.

**Easiest path:** use the `draft` and `pack` MCP tools to scaffold,
validate, and package prompts. See [tools/mcp/README.md](tools/mcp/README.md)
for setup.

**Taxonomy values:**

- `category`: `legal` | `research` | `adversarial`
- `subcategory`: `case_citations` | `statutory_interpretation` | `contract_law` | `uk_commonwealth` | `brazil` | `academic_claims` | `policy_citations` | `hallucination_prone`
- `difficulty`: `known_case` | `obscure_case` | `fabricated_likely` | `ambiguous` | `adversarial` | `standard`

---

## Result contributions

External run results are welcome.

**Tier 1 results** (no API key required):

```bash
python -m dali.runners.run_integrity \
  --corpus data/benchmark/tier1/corpus/citation_failure_cases.json \
  --output data/results/v0.2/{your-run-date}/integrity.json
```

**Tier 2 results** (requires model API access):

```bash
python -m dali.runners.run_synthetic \
  --models <model-id> \
  --prompts data/benchmark/tier2/ \
  --output data/results/v0.2/{your-run-date}/
```

Open a PR adding the output JSON to `data/results/v0.2/{your-run-date}/`. Include the `policy_version` field from the output and the `methodology.json` produced by the runner. Result files are immutable once merged.

## Specification contributions

Schema and ontology changes go through a lightweight proposal, open an issue with label `spec-change` describing the motivation, the breaking impact (if any), and a migration note. Documentation and clarification changes do not need a proposal.

---

## Issue labels

The repository uses labels to route contributions by review path:

| Label | Use |
|---|---|
| `good first issue` | Small, self-contained contribution suitable for first-time contributors |
| `help wanted` | Maintainer wants outside input or implementation help |
| `corpus-contribution` | New or improved Tier 1 court-documented case record |
| `synthetic-prompt` | New or improved Tier 2 prompt probe |
| `methodology` | Rubric, scoring, policy-versioning, or documentation question |
| `spec-change` | Schema, ontology, or Evidence JSON contract proposal |
| `benchmark-result` | External run artifact or reproducibility report |
| `research-partner` | Law school, research group, or dataset partnership |
| `legal-review` | Legal-domain review requested before merging |
| `bug` | Runner, validator, schema, or documentation defect |

---

## Pull request checklist

- [ ] Tests pass: `pytest tests/`
- [ ] New corpus records pass `lint` (MCP) or `python -m tools.cli lint <path>` (terminal)
- [ ] New synthetic prompts pass `probe` (MCP) or `python -m tools.cli probe <path>` (terminal)
- [ ] Schema changes have an accompanying `spec-change` issue
- [ ] No PII in corpus records: run `dali/corpus/anonymizer.py` if needed
- [ ] Commit authorship must accurately represent the contributor responsible for the change

---

## What we do not accept

- Changes to Evidence JSON contract semantics without a `spec-change` proposal
- New ontology categories that do not meet the minimalism rule (a new category is added only when an existing one demonstrably collapses two distinct legal behaviors into the same bucket)
- Corpus entries with unannotated or unverified citations
- Synthetic prompts covering non-public or unpublished matters
- Dependencies on proprietary data sources that cannot be redistributed

### Tier 1 corpus sourcing standard

Scoring-eligible Tier 1 records require canonical retrieval evidence: a verifiable `source_url`, a `retrieval_date`, and a publicly accessible court document or regulatory filing as the anchor.

The following are not acceptable as scoring-eligible Tier 1 sources:

- Unverified anecdotes or social-media reports
- Media summaries without an underlying judicial or regulatory document
- "People said a model hallucinated" accounts without a retrievable authority
- Incidents that cannot be independently re-verified by a third party

This constraint is intentional. A benchmark built on unverifiable incidents
cannot itself function as evidentiary infrastructure.

---

## Academic partnerships

Dali welcomes collaboration with law schools, legal research institutes,
court transparency organizations, and public legal data projects interested in:

- Citation integrity evaluation
- Reproducible legal AI benchmarking
- Corpus development and annotation
- Legal citation ontology review
- Methodology replication and peer review

If your institution is interested in contributing datasets, evaluation methods,
or benchmark review, please open an issue with the label `partnership`.

Areas of particular interest include:

- U.S. federal and state court citation datasets
- UK/Commonwealth legal citation systems
- Brazilian legal and regulatory citation structures
- Public court transparency and access initiatives
- Empirical legal studies involving AI-generated citations

---

## Code of conduct

Be precise. Be reproducible. Be evidence-oriented.
Dali handles legal citation integrity infrastructure. Accuracy, traceability,
and methodological rigor matter more than velocity or opinion.

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

Dali is operated by GammaLex AI Inc. Contributions are licensed under MIT unless explicitly stated otherwise.
