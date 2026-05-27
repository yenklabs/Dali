"""Load CitationFailureCase records from JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from corpus.schema import CitationFailureCase, WorkflowContext
from corpus.taxonomy import (
    ActualStatus,
    AnnotationConfidence,
    CitationFailureClass,
    CurationSource,
    MutationType,
    SourceType,
)


def _opt_enum(enum_cls, value):
    if value is None:
        return None
    return enum_cls(value)


def _workflow_from_raw(raw: dict[str, Any] | None) -> WorkflowContext | None:
    if raw is None:
        return None
    return WorkflowContext(**raw)


def _case_from_raw(raw: dict[str, Any]) -> CitationFailureCase:
    raw = dict(raw)  # defensive copy
    raw["source_type"] = _opt_enum(SourceType, raw.get("source_type"))
    raw["actual_status"] = ActualStatus(raw.get("actual_status", "unknown"))
    raw["failure_class"] = [
        CitationFailureClass(c) for c in raw.get("failure_class", [])
    ]
    raw["annotation_confidence"] = AnnotationConfidence(
        raw.get("annotation_confidence", "medium")
    )
    raw["curation_source"] = CurationSource(
        raw.get("curation_source", "hand_curated")
    )
    raw["mutation_type"] = _opt_enum(MutationType, raw.get("mutation_type"))
    raw["workflow_context"] = _workflow_from_raw(raw.get("workflow_context"))
    raw.setdefault("ground_truth_notes", "")
    return CitationFailureCase(**raw)


def load_corpus(path: str | Path) -> list[CitationFailureCase]:
    """Load all records from a corpus JSON file.

    The file is expected to be either a top-level JSON array of records
    or a dict with a "records" key.
    """
    with open(path) as f:
        raw = json.load(f)
    records = raw["records"] if isinstance(raw, dict) else raw
    return [_case_from_raw(r) for r in records]
