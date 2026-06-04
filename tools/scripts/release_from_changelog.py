#!/usr/bin/env python3
"""Finalize a Dali release from the changelog.

This script treats ``CHANGELOG.md`` as the source of truth for the next release.
It reads the ``[Unreleased]`` section, infers a semver bump when requested,
promotes that section into a dated release entry, and updates release-facing
metadata in ``CITATION.cff`` plus the repo's citation snippets.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
CITATION_PATH = REPO_ROOT / "CITATION.cff"
README_PATH = REPO_ROOT / "README.md"
RESULTS_README_PATH = REPO_ROOT / "data" / "results" / "v0.2" / "README.md"

BREAKING_MARKERS = (
    "breaking",
    "backward-incompatible",
    "backwards-incompatible",
)
MINOR_HEADINGS = ("added", "changed", "deprecated")
PATCH_HEADINGS = ("fixed", "security")


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value.strip())
        if not match:
            raise ValueError(f"invalid semver: {value!r}")
        return cls(*(int(part) for part in match.groups()))

    def bump(self, kind: str) -> "SemVer":
        if kind == "major":
            return SemVer(self.major + 1, 0, 0)
        if kind == "minor":
            return SemVer(self.major, self.minor + 1, 0)
        if kind == "patch":
            return SemVer(self.major, self.minor, self.patch + 1)
        raise ValueError(f"unsupported bump kind: {kind}")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class ReleasePlan:
    current_version: SemVer
    next_version: SemVer
    bump_kind: str
    release_date: str


def _extract_unreleased_block(changelog_text: str) -> tuple[str, int, int]:
    match = re.search(
        r"^## \[Unreleased\]\n(?P<body>.*?)(?=^## \[|\Z)",
        changelog_text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise ValueError("CHANGELOG.md does not contain a [Unreleased] section")
    body = match.group("body")
    if not body.strip():
        raise ValueError("[Unreleased] is empty; nothing to release")
    return body, match.start(), match.end()


def _latest_released_version(changelog_text: str) -> SemVer:
    match = re.search(
        r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}$",
        changelog_text,
        flags=re.MULTILINE,
    )
    if not match:
        raise ValueError("CHANGELOG.md does not contain a released version entry")
    return SemVer.parse(match.group(1))


def infer_bump_kind(unreleased_text: str) -> str:
    lowered = unreleased_text.lower()
    if any(marker in lowered for marker in BREAKING_MARKERS):
        return "major"
    if re.search(r"^### Removed$", unreleased_text, flags=re.MULTILINE):
        return "major"

    headings = [
        heading.lower()
        for heading in re.findall(r"^### ([^\n]+)$", unreleased_text, flags=re.MULTILINE)
    ]
    if any(heading in MINOR_HEADINGS for heading in headings):
        return "minor"
    if any(heading in PATCH_HEADINGS for heading in headings):
        return "patch"
    return "patch"


def build_release_plan(
    changelog_text: str,
    *,
    bump: str,
    release_date: str,
) -> ReleasePlan:
    current = _latest_released_version(changelog_text)
    unreleased, _, _ = _extract_unreleased_block(changelog_text)
    bump_kind = infer_bump_kind(unreleased) if bump == "auto" else bump
    return ReleasePlan(
        current_version=current,
        next_version=current.bump(bump_kind),
        bump_kind=bump_kind,
        release_date=release_date,
    )


def finalize_changelog(changelog_text: str, plan: ReleasePlan) -> str:
    unreleased_body, start, end = _extract_unreleased_block(changelog_text)
    release_header = f"## [{plan.next_version}] - {plan.release_date}\n"
    new_block = f"## [Unreleased]\n\n{release_header}{unreleased_body}"
    return changelog_text[:start] + new_block + changelog_text[end:]


def update_citation_cff(citation_text: str, plan: ReleasePlan) -> str:
    version = str(plan.next_version)
    text = re.sub(
        r'(?m)^version: "\d+\.\d+\.\d+"$',
        f'version: "{version}"',
        citation_text,
        count=1,
    )
    text = re.sub(
        r'(?m)^date-released: "\d{4}-\d{2}-\d{2}"$',
        f'date-released: "{plan.release_date}"',
        text,
        count=1,
    )
    text = re.sub(
        r'(?m)^(\s+version: ")\d+\.\d+\.\d+(")$',
        rf'\g<1>{version}\2',
        text,
        count=1,
    )
    return text


def update_bibtex_version(text: str, plan: ReleasePlan) -> str:
    version = str(plan.next_version)
    return re.sub(
        r'(?m)^(\s*version\s*=\s*\{)\d+\.\d+\.\d+(\},)$',
        rf"\g<1>{version}\2",
        text,
    )


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def run_release(
    *,
    repo_root: Path,
    bump: str,
    release_date: str,
    dry_run: bool,
) -> ReleasePlan:
    changelog_path = repo_root / "CHANGELOG.md"
    citation_path = repo_root / "CITATION.cff"
    readme_path = repo_root / "README.md"
    results_readme_path = repo_root / "data" / "results" / "v0.2" / "README.md"

    changelog_text = changelog_path.read_text(encoding="utf-8")
    citation_text = citation_path.read_text(encoding="utf-8")
    readme_text = readme_path.read_text(encoding="utf-8")
    results_readme_text = results_readme_path.read_text(encoding="utf-8")

    plan = build_release_plan(changelog_text, bump=bump, release_date=release_date)

    if dry_run:
        return plan

    write_text(changelog_path, finalize_changelog(changelog_text, plan))
    write_text(citation_path, update_citation_cff(citation_text, plan))
    write_text(readme_path, update_bibtex_version(readme_text, plan))
    write_text(results_readme_path, update_bibtex_version(results_readme_text, plan))
    return plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bump",
        choices=("auto", "major", "minor", "patch"),
        default="auto",
        help="Semver bump to apply. Defaults to inferring from CHANGELOG.md [Unreleased].",
    )
    parser.add_argument(
        "--date",
        default=str(date.today()),
        help="Release date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root. Defaults to the current Dali checkout.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the inferred release plan without modifying files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = run_release(
        repo_root=args.repo_root.resolve(),
        bump=args.bump,
        release_date=args.date,
        dry_run=args.dry_run,
    )
    print(
        f"current={plan.current_version} "
        f"bump={plan.bump_kind} "
        f"next={plan.next_version} "
        f"date={plan.release_date}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
