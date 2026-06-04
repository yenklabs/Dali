# Dali Platform MCP Contract

The public `yenk/Dali` repository includes MCP contributor tools for benchmark records and prompt scaffolding. Dali Platform exposes a separate prompt-audit contract for live legal AI risk evidence.

This document describes the public contract only. It intentionally omits implementation, deployment, authentication, persistence, and operational details.

## Tool

`audit_prompt`

## Purpose

Audit user-submitted prompts, attachments, or PDF text for legal AI risk before the content is sent to external models or downstream systems.

The tool is a live inspection hook. It reviews only content explicitly passed to the tool; it does not scan a workspace, crawl files, or monitor all model usage.

## Input Contract

| Field | Type | Required | Notes |
|---|---|---|---|
| `content` | string | Optional | Exact prompt, log line, or document text to audit. Required unless `pdf_base64` is provided. |
| `pdf_base64` | string | Optional | Base64-encoded PDF. Required unless `content` is provided. |
| `pdf_filename` | string | Optional | Original filename for PDF audits. |
| `framework` | string | Optional | `auto` or `legal`; default `auto`. |
| `blocking_mode` | boolean | Optional | When true, high-risk findings can return a blocked envelope. |
| `context` | object | Optional | Caller metadata such as `source`, `model`, and `user_id`. |

## Output Contract

Dali Platform returns a legal audit envelope with deterministic evidence fields:

| Field | Meaning |
|---|---|
| `audit.audit_id` | Run identifier for the audit session. |
| `audit.source` | Canonical source channel, usually `mcp`. |
| `audit.framework` | Resolved legal audit lens. |
| `audit.policy_version` | Policy and pack lineage. |
| `evidence.canonical_input_hash` | Hash of normalized audited input. |
| `evidence.finding_fingerprint` | Corpus-level finding fingerprint. |
| `evidence.evidence_hash` | Canonical evidence hash over input, findings, framework, and policy version. |
| `evidence_id` | Canonical evidence ID derived from `evidence_hash`. |
| `display_id` | Reviewer-facing evidence alias. |
| `findings` | Structured legal risk findings using the Dali taxonomy. |

## Legal Risk Categories

Platform findings map to the six Dali legal risk categories:

- Privilege Risk
- Confidential Data Exposure
- Citation Integrity
- Public Data Risk
- Redaction Integrity
- FOIA Disclosure

## Determinism

MCP output must not depend on LLM paraphrasing. The platform computes evidence hashes in the backend from canonicalized inputs and normalized findings. Tool callers should display the returned envelope verbatim when evidence review or replay is required.
