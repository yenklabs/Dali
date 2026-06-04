# For legal researchers, law students, and practitioners

You are the most valuable contributor to Dali. The benchmark's evidentiary thesis depends on court-documented incidents, and identifying them requires legal training. Engineers can't replace this work.

This doc is the 30-minute on-ramp. No Python required.

---

## Why your contribution matters

Tier 1 of the Dali corpus contains 3 scoring-eligible cases: *Mata v. Avianca*, *United States v. Cohen*, *Park v. Kim*. The public record contains many more — sanctions orders, judicial findings, disciplinary referrals, court-documented retrieval failures, increasingly internationally.

Every additional case you contribute:

- Strengthens the benchmark's defensibility against the "n=3 is too small" critique
- Captures jurisdictional and procedural variation that single-case studies miss
- Becomes a permanently citable artifact (Zenodo DOI pending for v0.3)
- Earns named credit in the next release notes and the project's `CITATION.cff`

---

## What counts as a Tier 1 case

A scoring-eligible Tier 1 record is **court-documented** AI citation failure. Specifically:

| Required | Why |
|---|---|
| Public court document — sanctions order, judicial opinion, disciplinary referral, or filed court record | Anchors the incident in the public record |
| Verifiable URL — CourtListener, PACER, court website, official reporter | So the source can be independently retrieved |
| Retrieval date — ISO 8601, when you last verified the URL resolved | Tracks source decay over time |
| Stable case caption | Enables canonical identification |
| Documented AI involvement — the court itself, not media coverage, must establish AI was used | Removes anecdotal/speculative cases |
| Documented failure type — nonexistent authority, misattribution, fabricated quotation, etc. | Maps to the failure-class taxonomy |

**Not eligible:** Twitter threads, blog posts, podcast mentions, "I heard a lawyer say…" stories, media summaries without an underlying court document, incidents that cannot be independently re-verified.

This constraint is deliberate. See the explanation in [CONTRIBUTING.md § Tier 1 corpus sourcing standard](../CONTRIBUTING.md#tier-1-corpus-sourcing-standard).

---

## The 30-minute contribution path

### Step 1 — Find a case (10 min)

The fastest hunting grounds:

- [Damien Charlotin's AI hallucination tracker](https://www.damiencharlotin.com/hallucinations/) — canonical running list of court-documented incidents worldwide (HEC Paris)
- CourtListener full-text search for terms like *"hallucinated"*, *"fabricated citation"*, *"nonexistent case"*, *"ChatGPT"*, *"generative artificial intelligence"*
- Bar association disciplinary databases
- LexisNexis / Westlaw alerts for AI-related sanctions opinions

If you have one in mind already, skip ahead.

### Step 2 — Confirm eligibility (5 min)

Open the court document. Confirm it provides:

- A case caption and citation
- An explicit court finding that AI was involved (not just an attorney's later statement)
- Enough detail to identify the failure type (fabrication, misattribution, etc.)
- A public, retrievable URL

If any of these are missing, the case is not Tier 1 eligible. It may still be useful as Tier 2 background — open an issue with label `methodology` if you'd like to discuss.

### Step 3 — Open an issue (5 min)

Open a new issue using the **corpus contribution** template at:

[github.com/yenk/Dali/issues/new?template=corpus-contribution.md](https://github.com/yenk/Dali/issues/new?template=corpus-contribution.md)

Include:
- The case caption
- The public URL to the court document
- A 2-sentence summary of what the AI did wrong
- The failure type (your best guess; the maintainer will normalize against the taxonomy)

That is sufficient for the maintainer to begin canonicalization. You do not need to edit JSON or run any code.

### Step 4 — Optional: submit the record yourself (10 min)

If you are comfortable editing JSON, the record format is documented in [CONTRIBUTING.md § Tier 1: Canonical case records](../CONTRIBUTING.md#tier-1-canonical-case-records). Add your record to [`benchmarks/tier1/corpus/citation_failure_cases.json`](../benchmarks/tier1/corpus/citation_failure_cases.json), validate with `python -m corpus.validator benchmarks/tier1/corpus/citation_failure_cases.json`, and open a PR.

If your record contains attorney names from the original filing, the `corpus/anonymizer.py` script will strip them — public corpus records identify cases by case caption only.

---

## Other ways legal practitioners can help

| Task | What it looks like | Time |
|---|---|---|
| **Ontology review** | Read [`schemas/ontology.md`](../schemas/ontology.md) and comment on whether the failure-class taxonomy captures the legal-doctrinal distinctions that matter | 1 hr |
| **Jurisdiction adapter design** | If you practice in a non-U.S. jurisdiction, sketch what a "Tier 1 record" looks like in your system (UK, Canada, Australia, EU member states, Brazil, India, etc.) | 2 hr |
| **Reviewer guide critique** | Read [`docs/reviewer-guide.md`](reviewer-guide.md) and identify where a non-technical reviewer would get stuck | 30 min |
| **Methodology review** | Read [`METHODOLOGY.md`](../METHODOLOGY.md) and comment on whether the scoring rubric aligns with the standard of care a court would apply under Rule 11 | 2 hr |
| **Academic partnership** | If you are affiliated with a law school or legal research institute, open an issue with label `research-partner` | varies |

For ontology, methodology, or reviewer-guide work, open an issue with label `legal-review` so the maintainer can flag it for review before merging adjacent changes.

---

## What you get back

- Named credit in the next release notes
- Named contributor entry in [`CITATION.cff`](../CITATION.cff) for v0.3+
- Co-authorship eligibility on the v0.3 technical report (in progress) for substantial corpus or methodology contributions — this is a defensible academic-currency artifact
- Permanent attribution in the corpus record metadata (`contributed_by` field)
- A reproducible, citable artifact representing your contribution that you can list on a CV or in tenure materials

---

## Questions

- For corpus eligibility questions: open an issue with label `corpus-contribution`
- For taxonomy or methodology questions: open an issue with label `methodology`
- For partnership inquiries: open an issue with label `research-partner`
- For broader discussion not tied to a specific PR: use [GitHub Discussions](https://github.com/yenk/Dali/discussions) (enable when available)

The project's commitments to contributors are documented in [CONTRIBUTING.md](../CONTRIBUTING.md). The maintainer is responsive within 48 hours during the project's pre-1.0 phase.
