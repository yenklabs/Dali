---
name: Corpus contribution
about: Submit a new court-documented AI citation failure case for Tier 1
labels: corpus-contribution
assignees: ''
---

## Case summary

**Case name / docket:** 
**Jurisdiction:** 
**Year:** 
**Court:** 

## What was the citation failure?

<!-- Describe in plain terms what AI-generated citation failed and how the court or sanctions record documents it. -->

## Source URL

<!-- Public URL to the sanctions order, judicial opinion, or docket entry that documents the failure. -->

**source_url:**
**retrieval_date:** <!-- ISO 8601, e.g. 2026-05-26 -->

## Failure class(es)

<!-- Check all that apply -->
- [ ] `nonexistent_authority`
- [ ] `fabricated_quote`
- [ ] `real_case_wrong_holding`
- [ ] `wrong_jurisdiction`
- [ ] `wrong_court_level`
- [ ] `overruled_authority`
- [ ] `temporal_validity_failure`
- [ ] `parallel_citation_mismatch`
- [ ] `semantic_misalignment`
- [ ] `citation_mutation`
- [ ] `provenance_gap`
- [ ] `reconstructability_failure`

## Workflow context

<!-- What is known about how the citation was produced? -->
- Retrieval system used? 
- Human review present?
- AI system: 
- Verification step before filing?

## Checklist before submitting

- [ ] Source URL is publicly accessible
- [ ] Attorney names removed (run `corpus/anonymizer.py` if needed)
- [ ] Record passes `python -m corpus.validator data/public/citation_failure_cases.json`
- [ ] `annotation_confidence` set appropriately (high / medium / low)
