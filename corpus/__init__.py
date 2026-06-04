"""Canonical Case Corpus — v0.2 Tier 1 evidentiary citation infrastructure.

This package defines the data model, validators, and helpers for the
court-documented citation integrity failure corpus that anchors the
Dali Reproducibility & Attribution Benchmark.

Public entry points:
    schema     — CitationFailureCase, WorkflowContext, CitationIntegrityResult
    taxonomy   — CitationFailureClass, MutationType, ActualStatus enums
    policy     — POLICY_VERSION + cross-version comparison rules
    loader     — JSON → CitationFailureCase
    validator  — eligibility, provenance, lineage, anonymization checks
    anonymizer — internal → public artifact transformation
    lineage    — parent_incident_id resolution + mutation graph
"""
