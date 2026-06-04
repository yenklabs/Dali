# Reviewer Guide

This guide is for researchers, legal AI teams, AI evaluation platforms,
benchmark contributors, and diligence reviewers who need to decide quickly
whether Dali is a serious project.

## What Dali is

Dali is open evidentiary infrastructure for legal AI. The public repository
defines a citation-integrity benchmark, reproducible evaluation workflows,
schemas, methodology, and published evidence artifacts.

It is not a hosted product repo and it is not a general legal assistant.

## What to inspect first

| Question | Evidence |
|---|---|
| Is there a real benchmark? | [results/v0.2](../results/v0.2/) |
| Can I reproduce anything locally? | [Quick start](../README.md#quick-start) |
| Are the scoring rules documented? | [METHODOLOGY.md](../METHODOLOGY.md) |
| Are results versioned and schema-backed? | [schemas](../schemas/) and [docs/policy-versioning.md](policy-versioning.md) |
| Can contributors extend the corpus? | [CONTRIBUTING.md](../CONTRIBUTING.md) |

## Proof points

- Tier 1 runs locally without API keys.
- v0.2 includes 450 prompt evaluations across 3 OpenAI models.
- v0.2 evaluates 524 citations across 5 jurisdiction tracks.
- Published results separate confirmed HTTP 404 fabrication from blocked or
  indeterminate verification.
- Results include methodology metadata and policy-versioning rules.
- The repository includes schemas, tests, CI, issue templates, and contribution
  paths.

## Current limitations

Dali is early. The public corpus is intentionally small where only
court-documented incidents are scoring-eligible. Tier 2 support scoring is
limited by source extraction depth, blocked endpoints, and live model behavior.

Those limitations are documented because the goal is reviewable evidence, not
inflated benchmark claims.

## Best-fit reviewers

| Reviewer | Relevant entry point |
|---|---|
| AI evaluation platforms | v0.2 result artifacts, schemas, policy versioning |
| Legal AI companies | methodology, failure taxonomy, jurisdiction breakdowns |
| Researchers and law schools | corpus contribution path, citation metadata, reproducible runner |
| AI safety organizations | adversarial citation traps and fabrication distinctions |
| Prospective design partners | v0.2 results, methodology, and contribution path |

## What would strengthen the project next

- Expanded Tier 1 court-documented corpus
- CourtListener-backed canonical citation resolution
- More cross-jurisdiction prompt tracks
- Independent replication runs from external model providers
- Public review of Evidence JSON v1.0
