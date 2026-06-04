from __future__ import annotations

from pathlib import Path

from tools.scripts.release_from_changelog import (
    SemVer,
    build_release_plan,
    finalize_changelog,
    infer_bump_kind,
    run_release,
)


CHANGELOG_TEMPLATE = """# Changelog

## [Unreleased]

### {section}
- {body}

## [1.2.3] - 2026-06-01

### Fixed
- Previous release note.
"""


CITATION_TEMPLATE = """cff-version: 1.2.0
title: "Dali"
version: "1.2.3"
date-released: "2026-06-01"
preferred-citation:
  version: "1.2.3"
"""


README_TEMPLATE = """```bibtex
@software{dali-2026,
  version      = {1.2.3},
}
```"""


def _write_repo(root: Path, changelog_text: str) -> None:
    (root / "data" / "results" / "v0.2").mkdir(parents=True)
    (root / "CHANGELOG.md").write_text(changelog_text, encoding="utf-8")
    (root / "CITATION.cff").write_text(CITATION_TEMPLATE, encoding="utf-8")
    (root / "README.md").write_text(README_TEMPLATE, encoding="utf-8")
    (root / "data" / "results" / "v0.2" / "README.md").write_text(
        README_TEMPLATE,
        encoding="utf-8",
    )


def test_infer_bump_major_on_breaking_marker():
    unreleased = "### Changed\n- BREAKING for MCP users: renamed public verbs.\n"
    assert infer_bump_kind(unreleased) == "major"


def test_infer_bump_major_on_removed_section():
    unreleased = "### Removed\n- Deleted deprecated endpoint.\n"
    assert infer_bump_kind(unreleased) == "major"


def test_infer_bump_minor_on_added_section():
    unreleased = "### Added\n- New runner.\n"
    assert infer_bump_kind(unreleased) == "minor"


def test_infer_bump_patch_on_fixed_only():
    unreleased = "### Fixed\n- Corrected broken citation link.\n"
    assert infer_bump_kind(unreleased) == "patch"


def test_build_release_plan_uses_latest_released_version():
    changelog = CHANGELOG_TEMPLATE.format(section="Fixed", body="Bug fix.")
    plan = build_release_plan(changelog, bump="auto", release_date="2026-06-04")
    assert plan.current_version == SemVer(1, 2, 3)
    assert plan.bump_kind == "patch"
    assert plan.next_version == SemVer(1, 2, 4)


def test_finalize_changelog_promotes_unreleased_block():
    changelog = CHANGELOG_TEMPLATE.format(section="Added", body="New tool.")
    plan = build_release_plan(changelog, bump="auto", release_date="2026-06-04")
    updated = finalize_changelog(changelog, plan)
    assert "## [Unreleased]\n\n## [1.3.0] - 2026-06-04" in updated
    assert "### Added\n- New tool." in updated


def test_run_release_updates_all_release_surfaces(tmp_path):
    _write_repo(
        tmp_path,
        CHANGELOG_TEMPLATE.format(section="Changed", body="Expanded public docs."),
    )

    plan = run_release(
        repo_root=tmp_path,
        bump="auto",
        release_date="2026-06-04",
        dry_run=False,
    )

    assert str(plan.next_version) == "1.3.0"
    assert 'version: "1.3.0"' in (tmp_path / "CITATION.cff").read_text(encoding="utf-8")
    assert 'date-released: "2026-06-04"' in (tmp_path / "CITATION.cff").read_text(encoding="utf-8")
    assert "version      = {1.3.0}," in (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "version      = {1.3.0}," in (
        tmp_path / "data" / "results" / "v0.2" / "README.md"
    ).read_text(encoding="utf-8")
    changelog = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [1.3.0] - 2026-06-04" in changelog


def test_run_release_dry_run_leaves_files_unchanged(tmp_path):
    changelog_text = CHANGELOG_TEMPLATE.format(section="Fixed", body="Patch only.")
    _write_repo(tmp_path, changelog_text)

    plan = run_release(
        repo_root=tmp_path,
        bump="auto",
        release_date="2026-06-04",
        dry_run=True,
    )

    assert str(plan.next_version) == "1.2.4"
    assert (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8") == changelog_text
