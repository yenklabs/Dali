# RFC-001: Evidence JSON v1.0

**Status:** DRAFT — public review open
**Created:** 2026-05-26
**Author:** Yen Kha

> This is the first public draft of the Evidence JSON contract. Breaking changes are still possible before the v1.0 freeze. Comments and conformance feedback are welcome via GitHub issues with label `spec-change`.

---

## Abstract

This RFC defines Evidence JSON v1.0 — the versioned contract format for
representing citation integrity verification results produced by AI-assisted
legal workflows.

Evidence JSON is the protocol primitive that allows legal AI systems, audit
tools, and compliance infrastructure to interoperate. A system that emits
conformant Evidence JSON is Dali-compatible.

---

## 1. Motivation

AI-assisted legal workflows produce citations. Those citations may be
fabricated, misattributed, or point to sources that no longer say what
the model claims. Today, every system that checks citations does so
differently, with no shared schema, no interoperable audit trail, and
no way to replay a verification result at a future date.

Evidence JSON solves this by defining:

1. **What a citation integrity result looks like** — a shared schema
   that any tool can emit or consume.
2. **What replay state must be preserved** — the version dimensions
   required to reconstruct a verification result years after the fact.
3. **What the ontology means** — normative definitions for authority
   types, verdict values, and support classifications.

---

## 2. Scope

This RFC defines:

- `EvidenceBundle` — the top-level container for a verification run
- `CitationIntegrityResult` — one result per cited source
- Authority type taxonomy (v1)
- Verdict taxonomy (v1)
- Replay state dimensions (v1)

Reserved for later RFCs:

- `SemanticSupportResult` — proposition-level support scoring (v3a)
- `ReplayArtifact` — deterministic replay package (v3a)
- Treatment classification schema (v2)

---

## 3. Schema

### 3.1 EvidenceBundle

```json
{
  "$schema": "https://raw.githubusercontent.com/yenk/Dali/main/schemas/evidence-bundle.schema.json",
  "schema_version": "1.0.0",
  "bundle_id": "<uuid>",
  "created_at": "<ISO 8601 timestamp>",
  "evidence_id": "<string>",
  "audit_id": "<string | null>",
  "citations": ["<CitationIntegrityResult>"],
  "replay_state": "<ReplayState>",
  "summary": {
    "total": "<integer>",
    "verified": "<integer>",
    "dead": "<integer>",
    "unresolvable": "<integer>",
    "mean_existence_score": "<float 0–1>"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | yes | Must be `"1.0.0"` for v1 bundles. |
| `bundle_id` | string (UUID) | yes | Globally unique identifier for this bundle. |
| `created_at` | string (ISO 8601) | yes | Timestamp of bundle creation. |
| `evidence_id` | string | yes | Links this bundle to the source workflow artifact. |
| `audit_id` | string \| null | no | Parent audit session identifier. |
| `citations` | array | yes | One `CitationIntegrityResult` per extracted citation. |
| `replay_state` | object | yes | Version dimensions required for deterministic replay. |
| `summary` | object | yes | Aggregate statistics over the citations array. |

---

### 3.2 CitationIntegrityResult

```json
{
  "citation_id": "<uuid>",
  "raw_text": "<string>",
  "source_ref": "<string (URL) | null>",
  "resolution_method": "<ResolutionMethod>",
  "canonical_id": "<string | null>",
  "authority_type": "<AuthorityType>",
  "jurisdiction": "<string | null>",
  "court": "<string | null>",
  "decision_year": "<integer | null>",
  "existence_score": "<float 0–1>",
  "verdict": "<Verdict>",
  "fetch_error": "<string | null>",
  "content_hash": "<string | null>",
  "storage_path": "<string | null>",
  "captured_at": "<ISO 8601 | null>"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `citation_id` | string (UUID) | yes | Unique identifier within the bundle. |
| `raw_text` | string | yes | Citation as extracted from LLM output (includes party names for case citations). |
| `source_ref` | string \| null | no | Resolved URL. Null for unresolved case citations. |
| `resolution_method` | ResolutionMethod | yes | How the citation was extracted. |
| `canonical_id` | string \| null | no | CourtListener opinion ID when resolved. |
| `authority_type` | AuthorityType | yes | Classification of the cited authority. |
| `jurisdiction` | string \| null | no | Jurisdiction code (see §4.4). |
| `court` | string \| null | no | Human-readable court name. |
| `decision_year` | integer \| null | no | Year of the cited decision. |
| `existence_score` | float | yes | 1.0 = verified, 0.5 = unreachable, 0.0 = dead/unresolvable. |
| `verdict` | Verdict | yes | Categorical existence verdict. |
| `fetch_error` | string \| null | no | Error description if existence check failed. |
| `content_hash` | string \| null | no | SHA-256 of archived text content (for replay). |
| `storage_path` | string \| null | no | Content-addressable archive path (for replay). |
| `captured_at` | string \| null | no | ISO 8601 timestamp of content archival. |

---

### 3.3 ReplayState

```json
{
  "parser_version": "<semver>",
  "normalization_version": "<semver>",
  "policy_version": "<semver>",
  "model_id": "<string | null>",
  "prompt_template_version": "<string | null>"
}
```

`parser_version`, `normalization_version`, and `policy_version` are required
at v1. `model_id` and `prompt_template_version` are null in v1 when semantic
scoring is not performed; they become required at v3a.

---

## 4. Taxonomies

### 4.1 ResolutionMethod

| Value | Description |
|-------|-------------|
| `url_explicit` | An http(s):// URL appeared verbatim in the LLM output. |
| `case_pattern` | A legal case citation extracted via structured parser (e.g. eyecite). |
| `statute_pattern` | A statutory citation extracted (e.g. 42 U.S.C. § 1983). |
| `doi` | A DOI (10.x/…) extracted; URL constructed as `https://doi.org/<id>`. |
| `unresolvable` | Detected but could not be resolved to a URL. |

### 4.2 Verdict

| Value | Description |
|-------|-------------|
| `verified` | Source exists at the cited URL with HTTP 200–299. |
| `redirected` | Source exists but at a different URL than cited. |
| `dead` | Source returned HTTP 4xx/5xx. |
| `unreachable` | Fetch timed out or network error; may be transient. |
| `unresolvable` | No URL could be derived from the citation. |

### 4.3 AuthorityType

| Value | Description |
|-------|-------------|
| `federal_case` | US federal court opinion (SCOTUS, circuit, district). |
| `state_case` | US state court opinion. |
| `federal_statute` | US federal statutory law (USC, CFR). |
| `state_statute` | US state statutory law. |
| `international` | International treaty, tribunal, or foreign court. |
| `secondary` | Law review, treatise, or other secondary authority. |
| `unknown` | Could not classify from available metadata. |

### 4.4 Jurisdiction codes (v1)

| Code | Meaning |
|------|---------|
| `us-scotus` | US Supreme Court |
| `us-fed` | US federal courts (circuit, district, bankruptcy) |
| `us-state` | US state courts (generic) |
| `uk` | United Kingdom |
| `br` | Brazil |

---

## 5. Backwards compatibility

Evidence JSON v1.0 is the initial version. Minor versions (1.1.0, 1.2.0) may
add optional fields. Required fields will not be removed or renamed within v1.x.
A v2.0 bump requires a migration guide and 90-day deprecation window.

---

## 6. Conformance

A system is **Dali-compatible at v1** if it:

1. Emits `EvidenceBundle` objects with all Required fields present and correctly
   typed per §3.
2. Uses only values from the §4 taxonomies for `resolution_method`, `verdict`,
   and `authority_type`.
3. Populates `replay_state.parser_version`, `replay_state.normalization_version`,
   and `replay_state.policy_version` with SemVer strings.

Additional fields may be added under a namespaced key (e.g. `"x-vendor-field"`).
Unknown fields must be ignored by conformant consumers.

---

## 7. Reference implementation

The reference evaluator in `runners/run_integrity.py` emits per-citation
`CitationIntegrityResult` records (see [schemas/integrity-result.schema.json](../schemas/integrity-result.schema.json)).
Wrapping these into a full `EvidenceBundle` with `replay_state` and `summary`
fields is part of the v1.0 freeze work — currently tracked under the v1
roadmap item in [docs/roadmap.md](../docs/roadmap.md). Until then, conformant
producers should construct the bundle envelope from the documented schema
in §3.1.

Machine-readable schemas:
- [`schemas/evidence-bundle.schema.json`](../schemas/evidence-bundle.schema.json) — bundle envelope
- [`schemas/integrity-result.schema.json`](../schemas/integrity-result.schema.json) — per-citation record
