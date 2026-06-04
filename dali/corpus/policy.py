"""Policy version semantics.

Every CitationIntegrityResult records the active POLICY_VERSION. The version
is composed of five sub-versions — bumping any one of them bumps the whole.

Cross-version aggregation is refused by default; runners must pass
--allow-cross-version to opt in. This keeps longitudinal comparisons honest:
you cannot quietly compare results scored under different rubrics.
"""

from __future__ import annotations

from dataclasses import dataclass


# Sub-version constants — bump on material change.
TAXONOMY_VERSION = "2.0.0"        # CitationFailureClass + MutationType enums
RUBRIC_VERSION = "1.0.0"          # defensibility_risk thresholds
SCORING_VERSION = "1.0.0"         # existence / support / integrity scoring logic
NORMALIZATION_VERSION = "1.0.0"   # text + URL normalization rules
SCHEMA_VERSION = "1.0.0"          # CitationFailureCase + CitationIntegrityResult shape


@dataclass(frozen=True)
class PolicyVersion:
    taxonomy: str
    rubric: str
    scoring: str
    normalization: str
    schema: str

    def as_string(self) -> str:
        return (
            f"taxonomy={self.taxonomy};"
            f"rubric={self.rubric};"
            f"scoring={self.scoring};"
            f"normalization={self.normalization};"
            f"schema={self.schema}"
        )


POLICY_VERSION = PolicyVersion(
    taxonomy=TAXONOMY_VERSION,
    rubric=RUBRIC_VERSION,
    scoring=SCORING_VERSION,
    normalization=NORMALIZATION_VERSION,
    schema=SCHEMA_VERSION,
)


def is_same_version(a: str, b: str) -> bool:
    """Strict equality across all five sub-versions."""
    return a == b


def assert_same_version_or_raise(results_versions: list[str], allow_cross: bool) -> None:
    """Refuse cross-version aggregation unless explicitly allowed.

    Raises ValueError if results carry mixed policy versions and the caller
    has not passed allow_cross=True.
    """
    distinct = set(results_versions)
    if len(distinct) <= 1:
        return
    if allow_cross:
        return
    raise ValueError(
        "Results from different POLICY_VERSIONs cannot be aggregated silently. "
        f"Found {len(distinct)} distinct versions: {sorted(distinct)}. "
        "Re-run all records under one policy or pass --allow-cross-version."
    )
