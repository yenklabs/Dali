# Contributing to Dali

Thank you for contributing to Dali. This document covers how to get involved
and what kinds of contributions are most valuable to the project.

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
python runners/run_integrity.py \
  --corpus data/public/citation_failure_cases.json \
  --output results/demo/integrity.json
```

Expected output:
```text
INFO run_integrity: loading corpus: data/public/citation_failure_cases.json
INFO run_integrity: corpus: 4 total, 3 scoring-eligible, 0 pre-canonical, 1 needs-verification
INFO run_integrity: evaluating 3 record(s)
INFO run_integrity:   evaluating: mata-v-avianca-2023
INFO run_integrity:   evaluating: us-v-cohen-2023
INFO run_integrity:   evaluating: mata-derivative-reporter-swap-001
INFO run_integrity: wrote 3 result(s) to results/demo/integrity.json

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

**Prefer working in an editor?** If you use Claude Desktop, VS Code, or Cursor, the `dali_mcp/` tools let you validate corpus records and scaffold prompts without touching the terminal. See [dali_mcp/README.md](dali_mcp/README.md) for setup. The `check_case` and `check_prompt` tools cover the same validation logic as the CLI commands above.

---

## Contribution tracks

Dali is benchmark and evidence infrastructure, not a typical library.
Contributions are valued across seven tracks:

| Track | What's needed | Where to start |
|---|---|---|
| **Corpus expansion** | Annotated real-world AI citation failure cases: especially UK/Commonwealth, Brazil, adversarial | `data/public/citation_failure_cases.json` |
| **Synthetic prompts** | New Tier 2 probe prompts across legal domains | `synthetic/` + `dali_mcp/` contributor tools |
| **Ontology review** | Legal practitioners reviewing treatment and proposition ontology definitions | [schemas/ontology.md](schemas/ontology.md) + open a discussion issue |
| **Parser coverage** | eyecite wrapper improvements, jurisdiction adapters | Roadmap: see [docs/roadmap.md](docs/roadmap.md). `corpus/parsers/` will land with eyecite integration. |
| **Spec authorship** | Drafting and reviewing changes to schemas and the Evidence JSON contract | `specs/` |
| **Benchmark replication** | Running Tier 2 against new models and sharing results | `runners/run_synthetic.py` |
| **Academic partnerships** | Law schools and court data projects: structured dataset contributions, co-authored methodology | Open issue with label `partnership` |

Code contributions are welcome but secondary to corpus quality, ontology
correctness, and specification rigor.

---

## Corpus contributions

### Tier 1: Canonical case records

Court-documented AI citation failure incidents. These live in:

```
data/public/citation_failure_cases.json
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
| `failure_class` | Array of failure taxonomy values (see `specs/ontology/`) |
| `ground_truth_notes` | Human-readable explanation of what actually happened |

Validate your record before submitting:

```bash
python -m corpus.validator data/public/citation_failure_cases.json
```

Optional: the `dali_mcp/` contributor interface exposes the same validation as an MCP tool (`check_case`) for editor-integrated workflows.

Records with `needs_verification: true` load for inspection but are excluded
from scoring aggregates.

Attorney names must be removed from public records. Run `corpus/anonymizer.py`
if your record contains names from the original filing.

### Tier 2: Synthetic prompt probes

Model-facing prompts for live Tier 2 evaluation. These live in:

```
synthetic/
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

**Easiest path:** use the `new_prompt` and `bundle_prompts`
MCP tools to scaffold, validate, and package prompts. See
[dali_mcp/README.md](dali_mcp/README.md) for setup.

**Taxonomy values:**

- `category`: `legal` | `research` | `adversarial`
- `subcategory`: `case_citations` | `statutory_interpretation` | `contract_law` | `uk_commonwealth` | `brazil` | `academic_claims` | `policy_citations` | `hallucination_prone`
- `difficulty`: `known_case` | `obscure_case` | `fabricated_likely` | `ambiguous` | `adversarial` | `standard`

---

## Result contributions

External run results are welcome.

**Tier 1 results** (no API key required):

```bash
python runners/run_integrity.py \
  --corpus data/public/citation_failure_cases.json \
  --output results/v0.2/{your-run-date}/integrity.json
```

**Tier 2 results** (requires model API access):

```bash
python runners/run_synthetic.py \
  --models <model-id> \
  --prompts synthetic/ \
  --output results/v0.2/{your-run-date}/
```

Open a PR adding the output JSON to `results/v0.2/{your-run-date}/`. Include the `policy_version` field from the output and the `methodology.json` produced by the runner. Result files are immutable once merged.

## Specification contributions

Schema and ontology changes go through a lightweight proposal, open an issue with label `spec-change` describing the motivation, the breaking impact (if any), and a migration note. Documentation and clarification changes do not need a proposal.

---

## Pull request checklist

- [ ] Tests pass: `pytest tests/`
- [ ] New corpus records pass `check_case`
- [ ] New synthetic prompts pass `check_prompt`
- [ ] Schema changes have an accompanying `spec-change` issue
- [ ] No PII in corpus records: run `corpus/anonymizer.py` if needed
- [ ] Commit author matches your real identity

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

This constraint is not a limitation. It is what makes the corpus defensible. A benchmark built on unverifiable sources cannot itself serve as evidentiary infrastructure.

---

## Academic partnerships

If you are affiliated with a law school, legal research institute, or court
data project and want to contribute corpus data or co-author evaluation
methodology, please open an issue with the label `partnership`.

We are particularly interested in structured collaborations with:
- Harvard Law School Library / Caselaw Access Project
- Stanford CodeX
- Free Law Project / CourtListener
- Legal data projects focused on UK/Commonwealth or Brazilian jurisdictions

---

## Code of conduct

Be direct, be specific, be accurate. This project handles legal information ,
precision matters more than enthusiasm.

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
