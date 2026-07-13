# Git Conventions

This is a public repository. Keep branch names and commit attribution vendor-neutral.

## Branch names

- Use conventional prefixes: `docs/`, `feat/`, `fix/`, `ci/`, etc.
- Do not use vendor or AI-tool prefixes in branch names.
- Example: `docs/eps-rfc` not `vendor/task-name`.

## Commit attribution

- Single human author per commit (name + email required).
- Do not add `Co-authored-by` trailers.
- AI agents must not appear as authors or co-authors.

CI enforces these rules in [commit-attribution-guard.yml](../.github/workflows/commit-attribution-guard.yml).
