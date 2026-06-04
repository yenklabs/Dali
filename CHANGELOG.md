# Changelog

All notable changes to Dali are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed
- **MCP tool names shortened to action verbs** (BREAKING for any existing MCP users):
  - `check_case` → `lint`
  - `evaluate_case` → `score`
  - `verify_replay` → `replay`
  - `check_prompt` → `probe`
  - `new_prompt` → `draft`
  - `bundle_prompts` → `pack`
  Rationale: easier to remember, faster to invoke, consistent verb vocabulary.
  Private `_*_impl` implementation function names are unchanged — only the
  public MCP tool names rotated. All docs (`dali_mcp/README.md`,
  `CONTRIBUTING.md`, persona doorways, root README, `benchmarks/tier2/README.md`)
  updated.
- **Root README restructured around "Get started — pick your path"** with
  Path A (terminal) and Path B (MCP) as side-by-side first-class options.
  MCP install instructions now appear in the root README, not only in
  `dali_mcp/README.md`.

### Added
- **Two new MCP tools surface the demo to non-terminal contributors:**
  - `evaluate_case` — MCP equivalent of `python runners/run_integrity.py`.
    Runs the deterministic Tier 1 evaluator on a single record and returns
    the full `CitationIntegrityResult` including the three cryptographic
    hashes. Contributors can now run the demo by talking to Claude.
  - `verify_replay` — MCP equivalent of `--verify-replay`. Runs the
    evaluator twice and asserts replay_hash equality.
  Both live in `dali_mcp/tools/integrity_tools.py`; both share the exact
  code path the CLI uses, so MCP and terminal outputs are byte-identical.
- **`tests/test_mcp_tools.py`** — 20 unit tests covering all six MCP tool
  implementations (`check_case`, `evaluate_case`, `verify_replay`,
  `check_prompt`, `new_prompt`, `bundle_prompts`). Pure-Python tests; no
  MCP runtime required. The MCP layer is now testable like any other module.
- **`dali_mcp/README.md` rewritten value-first**: 5 ready-to-paste
  contributor prompts (the workflows people actually do), a 30-second
  smoke test, a CLI ↔ MCP mapping table, and troubleshooting. Setup demoted
  from the lede to a single 5-minute section.
- **No-terminal contribution path called out** in `README.md` and
  `docs/for-legal-practitioners.md`. Legal practitioners can now contribute
  a court-documented case entirely through their AI editor.
- **Cryptographic lineage on every Tier 1 result.** `CitationIntegrityResult`
  now carries three SHA-256 hashes:
  - `corpus_record_hash` — over the canonical JSON of the input corpus record.
    Detects silent mutation of the input.
  - `replay_hash` — over (canonical record, policy_version, source_document_hash).
    Replay-invariant: same inputs under same policy always yield the same hash.
  - `evidence_hash` — over (case_id, policy_version, run_timestamp). Per-run
    tamper-evident seal (docstring corrected; previously claimed replay-stability
    incorrectly).
- **`runners/run_integrity.py --verify-replay`** flag. Re-evaluates every case
  a second time and asserts every `replay_hash` is byte-identical. Exit code
  `4` on mismatch. Proves the determinism claim is testable, not merely asserted.
- **`.github/workflows/replay-verification.yml`** — CI workflow running
  `--verify-replay` on every PR and on `main`. A determinism regression now
  blocks merge.
- **`docs/cryptographic-lineage.md`** — full explanation of the three-hash
  chain, what each protects against, what a verifier can independently prove,
  and the v0.3+ roadmap items (source content hashing, sigstore signing,
  Merkle commitments).
- Demo summary in `run_integrity.py` now surfaces `policy_version`,
  `corpus_record_hash`, `replay_hash`, `evidence_hash`, and mutation lineage —
  previously computed but invisible in CLI output.
- Promotional surface: `LEADERBOARD.md`, `CASE-STUDIES.md`, and three
  persona doorways (`docs/for-legal-practitioners.md`, `docs/for-researchers.md`,
  `docs/for-engineers.md`) for clearer contributor on-ramps.
- New FAQ entries on `replay_hash`, `corpus_record_hash`, and why three hashes
  instead of one.

### Changed
- README rewritten top-to-fold: leads with the v0.2 GPT-4.1 fabrication and
  Portuguese civil-law verification findings; adds CI/release/license badges;
  three persona doorways; explicit Dali / GammaLex disclosure.
- `schemas/integrity-result.schema.json` requires `corpus_record_hash` and
  `replay_hash` (both 64-char hex). Existing field descriptions clarified.
- `evidence_hash` docstring corrected: it is a per-run tamper-evident seal,
  not a replay invariant. For replay-invariance see `replay_hash`.
- README hero visual upgraded: evidence pathway (attribution → reconstruction) plus
  verification-durability chart; title **Dali v0.2 Reproducibility & Attribution Benchmark**.
- Benchmark naming aligned across METHODOLOGY, policy-versioning, corpus, and
  `run_synthetic.py` runner strings.

---

## [0.2.1] - 2026-05-27

### Fixed
- Repo URL standardised to `github.com/yenk/Dali` across all files (was
  drifting between `Dali` and `Dali-Foundation` in CITATION.cff, README
  bibtex, and the RFC schema ref).
- `runners/run_synthetic.py` docstring used fish-shell `(date)` syntax;
  corrected to bash `$(date +%Y-%m-%d)`.
- `specs/RFC-001-evidence-json-v1.md` `$schema` URL pointed at a non-existent
  host; corrected to GitHub raw URL.
- Synthetic corpus Mata derivative record had a broken `source_url` pointing
  at a non-existent repo (`dali-citation-benchmark`); corrected to current
  repo path.
- `commit-attribution-guard.yml` was hard-coded to reject all commits not
  authored by a single named maintainer, blocking external contributions.
  Rewritten to accept any human author and reject AI agent co-author trailers
  (Claude, Cursor, Copilot, ChatGPT, Gemini, `[bot]` patterns).

### Added
- `dali_mcp/` MCP contributor tools server with four tools:
  `check_case`, `check_prompt`, `new_prompt`, `bundle_prompts`.
  Setup instructions for Claude Desktop, Cursor, and VS Code in
  `dali_mcp/README.md`.
- `.github/ISSUE_TEMPLATE/` with three templates: corpus-contribution,
  spec-change, bug.
- `.github/PULL_REQUEST_TEMPLATE.md` mirroring the CONTRIBUTING.md checklist.
- `.github/CODEOWNERS` assigning `@yenk` as default reviewer with explicit
  gates on specs/, schemas/, data/, corpus/, and CI workflows.
- `CHANGELOG.md` (this file).

### Changed
- `specs/evidence-json-v1.md` renamed to `specs/RFC-001-evidence-json-v1.md`
  to surface the RFC numbering.
- RFC status changed from `ACCEPTED` → `DRAFT: public review open`;
  §7 reference implementation section updated to reflect actual repo state.
- README `Latest Results` section now discloses Tier 1 corpus size (3
  scoring-eligible cases) directly above the v0.2 headline numbers.
- CONTRIBUTING.md parser-coverage track now correctly scoped to the
  eyecite integration roadmap item.
- v0.2 run artifacts (`results/v0.2/2026-05-26/`,
  `results/v0.2/smoke-2026-05-26/`) committed to the public tree for
  reproducibility. `.gitignore` updated so versioned runs are committed
  by default.

---

## [0.2.0] - 2026-05-26

### Added
- **Tier 2 synthetic probe corpus**: 150 prompts across 8 categories and
  5 jurisdictions (`benchmarks/tier2/`).
- **First public benchmark run**: 450 evaluations across GPT-4o-mini,
  GPT-4.1, and GPT-4o, producing 524 citations with deterministic
  existence verification and HTTP-status-level fabrication distinction.
- **Cross-jurisdictional results**: US, UK/Commonwealth, Brazil (PT),
  adversarial traps, and research/policy tracks.
- **`runners/run_synthetic.py`**: Tier 2 runner with async model calls,
  model registry, provider-reliability tracking, and per-run
  `methodology.json` output.
- **`runners/model_registry.py`**: pinned model alias registry.
- **`runners/export.py`**: result export utilities.
- **`scoring/support.py`**: LLM-based support scorer with fallback chain.
- **`scoring/verification.py`**: URL existence verification with
  HTTP-status-level distinction (200/403/404/network).
- **`schemas/`**: JSON Schema files for `CitationIntegrityResult`,
  `EvidenceBundle`, and canonical citation.
- **`schemas/ontology.md`**: normative ontology definitions
  (AuthorityType, Verdict, ResolutionMethod, JurisdictionHierarchy).
- **`specs/RFC-001-evidence-json-v1.md`**: Evidence JSON v1.0 contract
  (EvidenceBundle, CitationIntegrityResult, ReplayState, taxonomies).
- **`docs/policy-versioning.md`**: composite policy version schema with
  five sub-dimensions and cross-version aggregation guard.
- **`docs/faq.md`**, **`docs/examples.md`**, **`docs/roadmap.md`**,
  **`docs/architecture.md`**, supporting documentation.
- **`results/v0.2/README.md`**: full v0.2 results with per-model
  leaderboard, per-jurisdiction breakdown, and methodology notes.
- **`.github/workflows/benchmark-validation.yml`**: CI pipeline: Tier 1
  evaluator, corpus quality gate, schema validation, JSONL validation.
- **`CITATION.cff`**, **`SECURITY.md`**, **`CODE_OF_CONDUCT.md`**.

### Changed
- Tier 1 failure-class taxonomy: renamed `non_reconstructable_workflow`
  → `reconstructability_failure` (taxonomy v2.0.0 bump).

---

## [0.1.0] - 2026-05-01

Initial internal release. Tier 1 canonical case corpus and deterministic
integrity evaluator. Not published publicly.
