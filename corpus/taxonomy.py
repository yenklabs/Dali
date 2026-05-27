"""Closed taxonomies — CitationFailureClass, MutationType, ActualStatus.

These enums are the canonical vocabulary for the Canonical Case Corpus.
Adding a new value bumps POLICY_VERSION (see policy.py).
"""

from __future__ import annotations

from enum import Enum


class CitationFailureClass(str, Enum):
    """12-class taxonomy of citation integrity failures."""

    NONEXISTENT_AUTHORITY = "nonexistent_authority"
    FABRICATED_QUOTE = "fabricated_quote"
    REAL_CASE_WRONG_HOLDING = "real_case_wrong_holding"
    WRONG_JURISDICTION = "wrong_jurisdiction"
    WRONG_COURT_LEVEL = "wrong_court_level"
    OVERRULED_AUTHORITY = "overruled_authority"
    TEMPORAL_VALIDITY_FAILURE = "temporal_validity_failure"
    PARALLEL_CITATION_MISMATCH = "parallel_citation_mismatch"
    SEMANTIC_MISALIGNMENT = "semantic_misalignment"
    CITATION_MUTATION = "citation_mutation"
    PROVENANCE_GAP = "provenance_gap"
    RECONSTRUCTABILITY_FAILURE = "reconstructability_failure"


class ActualStatus(str, Enum):
    """What the cited authority actually is, post-verification."""

    NONEXISTENT_AUTHORITY = "nonexistent_authority"
    REAL_AUTHORITY_WRONG_HOLDING = "real_authority_wrong_holding"
    FABRICATED_QUOTE = "fabricated_quote"
    WRONG_JURISDICTION = "wrong_jurisdiction"
    OVERRULED_OR_INVALID = "overruled_or_invalid"
    UNREACHABLE_SOURCE = "unreachable_source"
    PARALLEL_CITATION_MISMATCH = "parallel_citation_mismatch"
    UNKNOWN = "unknown"


class MutationType(str, Enum):
    """How a Tier-2 synthetic probe was derived from a Tier-1 case."""

    REPORTER_SWAP = "reporter_swap"
    FABRICATED_QUOTATION = "fabricated_quotation"
    JURISDICTION_SUBSTITUTION = "jurisdiction_substitution"
    YEAR_DRIFT = "year_drift"
    HOLDING_INVERSION = "holding_inversion"
    PARTY_NAME_PERMUTATION = "party_name_permutation"
    PAGE_NUMBER_DRIFT = "page_number_drift"
    OVERRULED_AS_GOOD = "overruled_as_good"


class SourceType(str, Enum):
    """What kind of public document anchors this record."""

    SANCTIONS_ORDER = "sanctions_order"
    JUDICIAL_OPINION = "judicial_opinion"
    MOTION = "motion"
    DISCIPLINARY_RECORD = "disciplinary_record"
    NEWS_REPORT = "news_report"
    OTHER = "other"


class CurationSource(str, Enum):
    """Where the record came from."""

    CHARLOTIN_DB = "charlotin_db"
    HAND_CURATED = "hand_curated"
    USER_SUBMISSION = "user_submission"


class AnnotationConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DefensibilityRisk(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


FAILURE_CLASS_DESCRIPTIONS: dict[CitationFailureClass, str] = {
    CitationFailureClass.NONEXISTENT_AUTHORITY: (
        "The cited case, statute, or authority does not exist in any verifiable form."
    ),
    CitationFailureClass.FABRICATED_QUOTE: (
        "A quoted passage is attributed to a real source but does not appear in that source."
    ),
    CitationFailureClass.REAL_CASE_WRONG_HOLDING: (
        "The cited case exists but the stated holding misrepresents what the court actually held."
    ),
    CitationFailureClass.WRONG_JURISDICTION: (
        "Authority cited as binding when it is from a non-binding jurisdiction."
    ),
    CitationFailureClass.WRONG_COURT_LEVEL: (
        "Case attributed to the wrong court (e.g., Supreme Court vs. circuit court)."
    ),
    CitationFailureClass.OVERRULED_AUTHORITY: (
        "Cited as good law when the case has been overruled, reversed, or vacated."
    ),
    CitationFailureClass.TEMPORAL_VALIDITY_FAILURE: (
        "Authority that was not yet decided or was no longer valid at the relevant time."
    ),
    CitationFailureClass.PARALLEL_CITATION_MISMATCH: (
        "Parallel citations (e.g., F.3d and S.Ct.) do not match the same case."
    ),
    CitationFailureClass.SEMANTIC_MISALIGNMENT: (
        "Source exists but does not support the claim made about it."
    ),
    CitationFailureClass.CITATION_MUTATION: (
        "Reporter, volume, page, or year of a real citation has been altered."
    ),
    CitationFailureClass.PROVENANCE_GAP: (
        "Citation lacks the lineage data needed to reconstruct how it was generated."
    ),
    CitationFailureClass.RECONSTRUCTABILITY_FAILURE: (
        "The pipeline that produced the citation cannot be audited or replayed."
    ),
}
