# Benchmark Expansion Strategy

This note reviews Dali's current jurisdiction structure and defines the next
benchmark expansion path. The goal is not raw prompt volume. The goal is to
make Dali more valuable because it measures evidentiary durability:
attribution, provenance, retrieval durability, reconstructability, evidence
replayability, and verification durability.

## Assessment of current tracks

The v0.2 benchmark currently uses five public-facing tracks:

| Current track | What it tests | Clarity assessment |
|---|---|---|
| UK / Commonwealth | Common-law transfer outside the US | Clear |
| Policy / Regulatory | Regulatory and policy citations across institutions | Clear |
| US Legal | US case, statutory, and contract citation behavior | Clear |
| Adversarial Traps | Citation pressure and hallucination-prone prompts | Clear |
| Brazil / Civil Law (Portuguese) | Portuguese-language civil-law citation behavior | Valuable, and now explicitly positioned |

The structure communicates common law, policy, and adversarial coverage well.
Civil-law coverage is present through Brazil. The important public-facing point
is that Brazil is not included as an arbitrary country sample; it is a
civil-law, Portuguese-language, non-English retrieval durability probe.

## Brazil naming recommendation

Use this public label:

**Brazil / Civil Law (Portuguese)**

Rationale:

- It explains why Brazil is present: civil-law structure and Portuguese-language
  source retrieval, not country selection for its own sake.
- It preserves the concrete jurisdiction so readers can inspect the source
  ecosystem.
- It avoids overclaiming that one country represents all civil-law systems.
- It makes the track more legible to researchers and evaluation platforms.

Avoid `Civil Law (Brazil)` as the primary label because it makes Brazil feel
like an example inside a larger civil-law category that does not yet exist.
Avoid `Portuguese Civil Law` because it can be confused with Portugal.

## EU expansion recommendation

Add an EU-focused track in v0.3.

Recommended label:

**EU / Regulatory**

Potential prompt sources:

- EU AI Act materials
- GDPR references
- European Commission guidance
- Court of Justice of the European Union materials
- European Court of Human Rights materials where citation format and source
  durability differ from US/UK patterns
- multilingual legal and policy citations

Benchmark value:

- EU regulatory materials are highly relevant to legal AI, AI governance, and
  evaluation platforms.
- EU sources stress multilingual retrieval, official-document stability,
  canonical identifier quality, and legal/policy citation conventions.
- The track complements Brazil / Civil Law without treating Brazil as the only
  non-US/non-UK legal-system probe.

Implementation effort:

- Moderate. The benchmark can start with a compact prompt set that focuses on
  official sources and stable identifiers.
- The initial goal should be clarity and source durability, not broad coverage.

Distribution relevance:

- High. EU AI Act and GDPR citations are immediately legible to AI evaluation
  companies, legal AI teams, researchers, and AI safety reviewers.

## Recommended coverage model

Use a hybrid structure.

| Track | Role |
|---|---|
| US Legal | Baseline US legal citation behavior |
| UK / Commonwealth | Common-law transfer outside the US |
| EU / Regulatory | Regulatory and multilingual legal-policy durability |
| Brazil / Civil Law (Portuguese) | Civil-law and Portuguese-language retrieval durability |
| Policy / Regulatory | Cross-institution policy citation behavior outside court systems |
| Adversarial Traps | Citation pressure and fabrication resistance |

This is stronger than a pure jurisdiction model because Dali is not trying to
be a world-law survey. It is trying to measure evidence durability across
different citation regimes, source ecosystems, languages, and pressure modes.

This is stronger than a pure legal-system model because concrete jurisdictions
make results inspectable and reproducible.

## v0.3 roadmap

Focus: clearer coverage model plus EU expansion.

- Use **Brazil / Civil Law (Portuguese)** consistently in public-facing docs.
- Add a compact **EU / Regulatory** Tier 2 prompt track.
- Use **Policy / Regulatory** instead of `Research / Policy` where the track is
  describing legal-policy source durability.
- Add explicit track purpose notes to benchmark docs so readers understand
  which evidentiary durability dimension each track stresses.
- Keep prompt count secondary to source quality and reproducibility.

## v0.4 roadmap

Focus: move beyond jurisdiction into evidence-pathway analysis.

- Add retrieval pathway fields to result artifacts where possible.
- Distinguish generated citation, retrieved source, verified state, evidence
  artifact, and reconstruction test more explicitly in outputs and docs.
- Improve attribution scoring: can the result explain which source, retrieval
  step, or citation pathway supports the finding?
- Expand failure taxonomy around provenance gaps, source mismatch, proposition
  drift, and reconstructability failure.
- Add clearer evidence artifact examples for reviewers.

## v0.5 roadmap

Focus: durability metrics.

- Introduce temporal drift checks for sources that change, move, block, or
  decay.
- Add source decay reporting: what previously resolved no longer resolves?
- Add reconstructability scoring: can the citation pathway be replayed from the
  recorded artifact?
- Add evidence replay tests against prior benchmark outputs.
- Add verification durability summaries alongside existence and fabrication
  metrics.

The long-term benchmark should answer not only whether a citation existed at
run time, but whether the evidence supporting it can still be attributed,
verified, and reconstructed later.
