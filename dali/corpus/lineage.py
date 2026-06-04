"""Mutation lineage — Tier 2 synthetic probes derive from Tier 1 cases.

This module is the structural connector between the Canonical Case Corpus
and the synthetic probes. Without it, the tiers would live in separate
silos and the platform claim ("synthetic probes systematically extend
canonical-case insight") would be hollow.
"""

from __future__ import annotations

from dali.corpus.schema import CitationFailureCase


def resolve_parent(
    record: CitationFailureCase, by_id: dict[str, CitationFailureCase]
) -> CitationFailureCase | None:
    """Return the parent record if parent_incident_id is set and resolves."""
    if not record.parent_incident_id:
        return None
    return by_id.get(record.parent_incident_id)


def mutation_chain(
    record: CitationFailureCase, by_id: dict[str, CitationFailureCase]
) -> list[str]:
    """Return the ordered list of parent case_ids walking up to the root.

    Catches cycles and bounds depth at 16 to prevent runaway recursion if
    a malformed corpus has self-referential lineage.
    """
    chain: list[str] = []
    seen: set[str] = set()
    cur = record
    for _ in range(16):
        parent = resolve_parent(cur, by_id)
        if parent is None or parent.case_id in seen:
            break
        chain.append(parent.case_id)
        seen.add(parent.case_id)
        cur = parent
    return chain


def derivatives_of(
    parent_id: str, all_records: list[CitationFailureCase]
) -> list[CitationFailureCase]:
    """Return all synthetic derivatives whose parent_incident_id == parent_id."""
    return [
        r for r in all_records
        if r.parent_incident_id == parent_id and r.synthetic_derivative
    ]
