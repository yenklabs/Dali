# Changelog

All notable changes to Dali are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.2.1] — 2026-05-27

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
  `validate_corpus_record`, `validate_prompt_jsonl`,
  `generate_prompt_template`, `create_contribution_bundle`.
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
- RFC status changed from `ACCEPTED` → `DRAFT — public review open`;
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

## [0.2.0] — 2026-05-26

### Added
- **Tier 2 synthetic probe corpus** — 150 prompts across 8 categories and
  5 jurisdictions (`synthetic/`).
- **First public benchmark run** — 450 evaluations across GPT-4o-mini,
  GPT-4.1, and GPT-4o, producing 524 citations with deterministic
  existence verification and HTTP-status-level fabrication distinction.
- **Cross-jurisdictional results** — US, UK/Commonwealth, Brazil (PT),
  adversarial traps, and research/policy tracks.
- **`runners/run_synthetic.py`** — Tier 2 runner with async model calls,
  model registry, provider-reliability tracking, and per-run
  `methodology.json` output.
- **`runners/model_registry.py`** — pinned model alias registry.
- **`runners/export.py`** — result export utilities.
- **`scoring/support.py`** — LLM-based support scorer with fallback chain.
- **`scoring/verification.py`** — URL existence verification with
  HTTP-status-level distinction (200/403/404/network).
- **`schemas/`** — JSON Schema files for `CitationIntegrityResult`,
  `EvidenceBundle`, and canonical citation.
- **`schemas/ontology.md`** — normative ontology definitions
  (AuthorityType, Verdict, ResolutionMethod, JurisdictionHierarchy).
- **`specs/RFC-001-evidence-json-v1.md`** — Evidence JSON v1.0 contract
  (EvidenceBundle, CitationIntegrityResult, ReplayState, taxonomies).
- **`docs/policy-versioning.md`** — composite policy version schema with
  five sub-dimensions and cross-version aggregation guard.
- **`docs/faq.md`**, **`docs/examples.md`**, **`docs/roadmap.md`**,
  **`docs/architecture.md`** — supporting documentation.
- **`results/v0.2/README.md`** — full v0.2 results with per-model
  leaderboard, per-jurisdiction breakdown, and methodology notes.
- **`.github/workflows/benchmark-validation.yml`** — CI pipeline: Tier 1
  evaluator, corpus quality gate, schema validation, JSONL validation.
- **`CITATION.cff`**, **`SECURITY.md`**, **`CODE_OF_CONDUCT.md`**.

### Changed
- Tier 1 failure-class taxonomy: renamed `non_reconstructable_workflow`
  → `reconstructability_failure` (taxonomy v2.0.0 bump).

---

## [0.1.0] — 2026-05-01

Initial internal release. Tier 1 canonical case corpus and deterministic
integrity evaluator. Not published publicly.
