"""Data classes for the Canonical Case Corpus and integrity result.

Field design follows the OPUS prompt schema with:
- workflow_context (Dali's moat: workflow attribution, not just outcome)
- mutation lineage (Tier 2 synthetic probes derive from Tier 1 cases)
- dali_pipeline_reproducibility_status (tri-state, not boolean)
- policy_version stamp on every result
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional, Union

from corpus.taxonomy import (
    ActualStatus,
    AnnotationConfidence,
    CitationFailureClass,
    CurationSource,
    DefensibilityRisk,
    MutationType,
    SourceType,
)

# ---------------------------------------------------------------------------
# Workflow attribution
# ---------------------------------------------------------------------------

UnknownableBool = Union[bool, Literal["unknown"]]


@dataclass
class WorkflowContext:
    """How the citation was produced and verified.

    Courts and insurers care about who touched the citation and whether
    verification occurred — not merely whether the citation was fake.
    All fields default to ``"unknown"`` when the sanctions order doesn't
    disclose them; that is a finding, not a failure.
    """

    retrieval_used: UnknownableBool = "unknown"
    human_review_present: UnknownableBool = "unknown"
    ai_system_type: Optional[str] = None
    source_chain_complete: UnknownableBool = "unknown"
    downstream_modified: UnknownableBool = "unknown"
    verification_step_present: UnknownableBool = "unknown"


# ---------------------------------------------------------------------------
# Corpus record
# ---------------------------------------------------------------------------

@dataclass
class CitationFailureCase:
    """One record in the Canonical Case Corpus.

    Required-for-scoring fields are enforced by ``validator.py``. Records
    lacking those fields are loadable for inspection but cannot count
    toward any scoring aggregate.
    """

    # Identity
    case_id: str
    incident_name: str
    year: int
    jurisdiction: str
    court: Optional[str] = None

    # Source provenance (required for scoring)
    source_type: Optional[SourceType] = None
    source_url: Optional[str] = None
    source_document_hash: Optional[str] = None
    retrieval_date: Optional[str] = None  # ISO 8601

    # Alleged generated citation
    alleged_generated_citation: Optional[str] = None
    claimed_case_name: Optional[str] = None
    claimed_reporter: Optional[str] = None
    claimed_court: Optional[str] = None
    claimed_year: Optional[int] = None

    # Ground truth
    actual_status: ActualStatus = ActualStatus.UNKNOWN
    failure_class: list[CitationFailureClass] = field(default_factory=list)
    judicial_response: Optional[str] = None
    sanctions_or_consequence: Optional[str] = None

    # Curation + confidence
    ground_truth_notes: str = ""
    annotation_confidence: AnnotationConfidence = AnnotationConfidence.MEDIUM
    curation_source: CurationSource = CurationSource.HAND_CURATED
    needs_verification: bool = False
    pre_canonical: bool = False  # year in 2021–2022

    # Dali workflow attribution
    workflow_context: Optional[WorkflowContext] = None
    dali_pipeline_reproducibility_status: Literal[
        "passed", "failed", "not_run"
    ] = "not_run"

    # Lineage (Tier 2 → Tier 1)
    parent_incident_id: Optional[str] = None
    mutation_type: Optional[MutationType] = None
    synthetic_derivative: bool = False

    # Privacy — never serialized to public artifact
    attorney_names_internal: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Run output
# ---------------------------------------------------------------------------

@dataclass
class CitationIntegrityResult:
    """Per-case output of the Tier 1 integrity runner.

    Cryptographic lineage fields:
      corpus_record_hash — SHA-256 over the canonical JSON of the input corpus
                           record. Tamper-detects silent mutation of the input.
      replay_hash        — SHA-256 over (corpus_record_hash, policy_version,
                           source_document_hash). Replay invariant: same input
                           under same policy produces the same hash forever.
                           This is what --verify-replay checks for equality.
      evidence_hash      — SHA-256 over (case_id, policy_version, run_timestamp).
                           Per-run tamper-evident seal; differs across runs by
                           design (the timestamp is part of the seal).
    """

    case_id: str
    citation_exists: bool
    authority_reachable: bool
    semantic_alignment: Literal[
        "aligned", "partially_aligned", "misaligned", "unknown"
    ]
    quote_fidelity: Literal["exact", "partial", "fabricated", "not_applicable"]
    temporal_validity: Literal["valid_at_time", "invalid_at_time", "unknown"]
    jurisdiction_match: Union[bool, Literal["unknown"]]
    provenance_complete: bool
    failure_classes_detected: list[CitationFailureClass]
    defensibility_risk: DefensibilityRisk

    # Workflow-centric additions
    workflow_reconstructable: UnknownableBool
    verification_recoverable: Literal["automatic", "manual", "infeasible"]
    mutation_lineage: list[str]

    # Stamps
    policy_version: str
    evidence_hash: str
    run_timestamp: str

    # Cryptographic lineage (replay-stable)
    corpus_record_hash: str = ""
    replay_hash: str = ""


# ---------------------------------------------------------------------------
# Canonical serialization + hashing
# ---------------------------------------------------------------------------

def _enum_safe(obj):
    """Convert dataclass-of-enums into JSON-safe primitives."""
    if hasattr(obj, "value"):
        return obj.value
    if isinstance(obj, dict):
        return {k: _enum_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_enum_safe(v) for v in obj]
    return obj


def canonical_json(record: CitationFailureCase) -> str:
    """Deterministic JSON serialization for hashing.

    attorney_names_internal is excluded — it must not influence the hash
    of a public artifact derived from the same record.
    """
    raw = asdict(record)
    raw.pop("attorney_names_internal", None)
    safe = _enum_safe(raw)
    return json.dumps(safe, sort_keys=True, separators=(",", ":"))


def evidence_hash(record: CitationFailureCase, policy_version: str) -> str:
    """sha256 over canonical record + policy version + source content hash.

    Replay-invariant: identical inputs under identical policy always yield
    the same hash. Surfaced on CitationIntegrityResult as ``replay_hash``.
    """
    base = canonical_json(record)
    content = record.source_document_hash or ""
    payload = f"{base}|policy={policy_version}|content={content}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def corpus_record_hash(record: CitationFailureCase) -> str:
    """sha256 over the canonical JSON of the corpus record alone.

    Detects silent mutation of the input corpus. Independent of policy
    version — changes only when the record content itself changes.
    """
    return hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()


def compute_replay_hash(record: CitationFailureCase, policy_version: str) -> str:
    """Replay-invariant hash for a single (record, policy) pair.

    Alias of :func:`evidence_hash` with the name that matches what is exposed
    on :class:`CitationIntegrityResult` as ``replay_hash``. Same inputs always
    produce the same hash; if two runs of the runner produce different
    ``replay_hash`` values for the same case, that is a determinism bug or
    silent corpus mutation.
    """
    return evidence_hash(record, policy_version)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
