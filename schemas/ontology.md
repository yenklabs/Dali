# Dali Ontology Definitions v1

This document is the normative reference for all ontology enum values used in
Evidence JSON contracts and Dali-compatible systems.

> **Scope note:** This document covers `AuthorityType`, `Verdict`,
> `ResolutionMethod`, and `JurisdictionHierarchy`. The **citation failure-class
> taxonomy** (`CitationFailureClass`, `MutationType`, `ActualStatus`) is defined
> in [`corpus/taxonomy.py`](../corpus/taxonomy.py) (normative Python enum) and
> documented in the [METHODOLOGY.md Failure class taxonomy](../METHODOLOGY.md#failure-class-taxonomy)
> table. Changes to failure classes require a `taxonomy` sub-version bump per
> [docs/policy-versioning.md](../docs/policy-versioning.md).

Ontology definitions are **public**. The scoring heuristics, classifier weights,
and ranking logic that produce values for these enums are **private** to
implementing systems. This is the governing principle of the project.

Changes to this document go through a lightweight proposal — open an issue
with label `spec-change`. The minimalism rule applies: a new category is added
only when an existing one demonstrably collapses two distinct legal behaviors
into the same bucket.

---

## AuthorityType

Classifies the type of legal authority cited.

| Value | Definition |
|-------|-----------|
| `federal_case` | A US federal court opinion. Includes SCOTUS, circuit courts of appeal, district courts, and bankruptcy courts. |
| `state_case` | A US state court opinion. Includes state supreme courts, intermediate appellate courts, and trial courts. |
| `federal_statute` | US federal statutory law, including the United States Code (USC) and Code of Federal Regulations (CFR). |
| `state_statute` | US state statutory law or administrative code. |
| `international` | A foreign court opinion, international tribunal decision, or treaty. |
| `secondary` | A non-primary authority: law review article, treatise, restatement, or practice guide. |
| `unknown` | The authority type could not be determined from available metadata. |

**Classification note:** The boundary between `federal_case` and `state_case` is
the issuing court, not the subject matter of the dispute. A state court ruling on
a federal constitutional question is `state_case`.

---

## Verdict

Categorical result of an existence check for a cited source.

| Value | Definition |
|-------|-----------|
| `verified` | The source was fetched with HTTP 200–299 at the cited URL. Content was archived. |
| `redirected` | The source was fetched with HTTP 200–299 but at a different URL than cited. Content was archived. |
| `dead` | The fetch returned HTTP 4xx or 5xx. The cited URL is definitively non-functional. |
| `unreachable` | The fetch timed out or returned a network-level error. The URL may be transiently unavailable. |
| `unresolvable` | No URL could be derived from the citation. Applies to case citations without CourtListener resolution. |

**Scoring:** `verified` and `redirected` → `existence_score = 1.0`. `unreachable` → `0.5`. `dead` and `unresolvable` → `0.0`.

---

## ResolutionMethod

How a citation was extracted from LLM output.

| Value | Definition |
|-------|-----------|
| `url_explicit` | An http(s):// URL appeared verbatim in the LLM output. Highest confidence. |
| `case_pattern` | A legal case citation extracted via structured parser (e.g. eyecite `FullCaseCitation`). Includes party names and reporter. |
| `statute_pattern` | A statutory citation extracted (e.g. `42 U.S.C. § 1983` via eyecite `FullLawCitation`). |
| `doi` | A DOI (10.x/…) found; URL constructed as `https://doi.org/<id>`. |
| `unresolvable` | A citation-like pattern detected but not resolvable to a URL or canonical ID. |

---

## AuthorityTreatment (v2 — forthcoming)

**Status:** Reserved. Not part of v1.

The v2 treatment ontology will launch with exactly 3 values:

| Value | Definition |
|-------|-----------|
| `cited_approvingly` | The citing document relies on the cited authority to support its reasoning. |
| `contradicted` | The citing document disagrees with, distinguishes, or limits the cited authority. |
| `neutral_reference` | The citing document mentions the cited authority without alignment or disagreement. |

Values `distinguished`, `overruled`, `questioned`, `criticized`, `limited`,
and `clarified` are reserved for v2.5 or v3, after the 3-category baseline
is proven against CourtListener annotations.

---

## PropositionSupport (v3a — forthcoming)

**Status:** Reserved. Not part of v1.

The v3a proposition ontology will launch with exactly 3 values:

| Value | Definition |
|-------|-----------|
| `supported` | The cited authority directly says the proposition as stated. |
| `partially_supported` | The cited authority says a weaker or qualified version of the proposition. |
| `not_supported` | The cited authority does not say the proposition. Covers LLM hallucination and misattribution. |

Multi-hop support, statutory interplay, and cross-authority synthesis are
reserved for v3b.

---

## JurisdictionHierarchy (v1)

| Code | Meaning |
|------|---------|
| `us-scotus` | US Supreme Court |
| `us-fed` | US federal courts (circuit, district, bankruptcy — below SCOTUS) |
| `us-state` | US state courts (generic when specific state is not resolved) |
| `uk` | United Kingdom |
| `br` | Brazil |

State-specific codes (e.g. `us-ny`, `us-ca`) are reserved for future versions.
