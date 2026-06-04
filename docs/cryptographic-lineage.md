# Cryptographic lineage

Dali's determinism claim is not a slogan. It is a property the runner enforces, the schema requires, and CI verifies on every commit. This document explains the chain.

---

## The three hashes

Every `CitationIntegrityResult` carries three SHA-256 hashes. Each answers a different question.

| Hash | Inputs | What it proves |
|---|---|---|
| **`corpus_record_hash`** | Canonical JSON of the corpus record alone | The input was not silently mutated. Changes only when the record itself changes. Independent of policy version, timestamp, or runner. |
| **`replay_hash`** | (canonical corpus record · `policy_version` · `source_document_hash`) | The verdict is reproducible. Same inputs under same policy → byte-identical hash, forever. This is the load-bearing determinism invariant. |
| **`evidence_hash`** | (`case_id` · `policy_version` · `run_timestamp`) | A specific run actually happened. Per-run tamper-evident seal; differs across runs by design (the timestamp is part of the seal). |

The properties:

```
corpus_record_hash    →  function of (record)              →  stable until corpus changes
replay_hash           →  function of (record + policy)     →  stable forever for same inputs
evidence_hash         →  function of (record + policy + t) →  unique per run
```

If two runs against the same corpus under the same policy produce different `replay_hash` values for the same case, that is either a determinism bug in the runner or silent mutation of the corpus. The CI workflow `.github/workflows/replay-verification.yml` enforces this on every commit.

---

## Why three hashes, not one

A single hash would force a choice between two contradictory properties:

- **A per-run hash** seals "this evaluation happened at time T" — useful for non-repudiation but useless for reproducibility.
- **A replay-invariant hash** proves "the verdict is deterministic" — useful for reproducibility but cannot distinguish two real runs of the same evaluation.

We need both, plus a third (`corpus_record_hash`) that detects tampering with the *input* independently of policy. So we publish all three. Each is cheap to compute and each answers a question a verifier might ask.

---

## What a verifier can prove

Given a result file, an external verifier can independently establish:

1. **Input integrity.** Recompute `corpus_record_hash` from the published corpus record. If it matches, the input has not been altered.
2. **Verdict reproducibility.** Recompute `replay_hash` from the corpus record + policy version. If it matches the stored value, the verdict is reproducible under the published methodology.
3. **Run authenticity.** The `evidence_hash` ties the verdict to a specific run timestamp. Combined with a signed git commit or a future sigstore attestation (see roadmap), this establishes that *this specific output was produced by Dali at this point in time*.

No private keys. No trusted server. No dependency on the Dali maintainer being available later.

---

## The `--verify-replay` flag

```bash
python runners/run_integrity.py \
  --corpus benchmarks/tier1/corpus/citation_failure_cases.json \
  --output results/demo/integrity.json \
  --verify-replay
```

Runs the Tier 1 evaluator twice and asserts every `replay_hash` is byte-identical across the two runs. Exit code `4` on any mismatch.

This is the single test that proves the determinism claim. CI runs it on every PR. You can run it locally before submitting corpus or runner changes.

---

## What this protects against

| Failure mode | Detected by |
|---|---|
| Someone silently edits a corpus record after publication | `corpus_record_hash` mismatch on re-evaluation |
| A runner change introduces non-determinism | `--verify-replay` fails; CI blocks the PR |
| Two researchers report conflicting Tier 1 numbers under the same policy version | Compare `replay_hash` — only one can be correct, and the corpus record / runner state is recoverable |
| A regression in scoring logic changes verdicts without bumping policy version | `replay_hash` changes; existing CI results no longer match; visible in PR diff |
| A bad-faith actor publishes claimed Dali results that were never actually produced by the runner | `replay_hash` cannot be forged without running the actual evaluator on the actual corpus |

---

## What this does *not* protect against (yet)

These are open items, tracked for v0.3 and beyond.

| Gap | Future mitigation |
|---|---|
| Source URLs may change content underneath the citation | Add `source_content_hash` populated at retrieval time (v0.3) |
| Result files are not cryptographically signed | Sigstore signing with Rekor transparency log on release artifacts (v0.4) |
| Corpus membership cannot be proven to a verifier holding only a release tag | Merkle commitment over corpus per release (v0.4) |
| Runner environment (Python version, dependencies) is not pinned in the result | Run manifest with `pip freeze` hash and git commit SHA (v0.3) |

See [docs/roadmap.md](roadmap.md) for the broader v0.3–v0.5 plan.

---

## Schema reference

The three hash fields are required by [`schemas/integrity-result.schema.json`](../schemas/integrity-result.schema.json). All three are validated as 64-character lowercase hex strings (SHA-256 hexdigest).

```json
{
  "case_id": "mata-v-avianca-2023",
  "policy_version": "taxonomy=2.0.0;rubric=1.0.0;scoring=1.0.0;normalization=1.0.0;schema=1.0.0",
  "corpus_record_hash": "9c1e7d3a…",
  "replay_hash":        "4f2b8e9c…",
  "evidence_hash":      "a73fd1b2…",
  "run_timestamp": "2026-06-04T17:32:14Z"
}
```

---

## Why this matters beyond engineering

Most legal-AI evaluations cannot be independently reproduced. Closed vendors will not publish methodology; published academic results often cannot be re-run as models change. Courts, regulators, and journalists have no way to verify claims about model behavior.

Dali's cryptographic lineage is the property that makes claims about legal-AI citation behavior **falsifiable**. A vendor that contests a Dali result has to either produce a different `replay_hash` under the same policy (which is impossible if the verdict is deterministic) or acknowledge the result.

This is what evidentiary infrastructure means in practice.
