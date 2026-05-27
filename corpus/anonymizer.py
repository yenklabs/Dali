"""Internal → public artifact transformation.

The internal corpus stores full attorney names. The public artifact must
contain zero attorney names anywhere — including every free-text field.

We replace with neutral placeholders ("counsel of record", "filing
attorney") rather than redaction marks. Preserves narrative readability
and infrastructure-grade tone.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

from corpus.loader import load_corpus
from corpus.schema import CitationFailureCase, _enum_safe

# Fields whose string values must be swept for attorney names.
FREE_TEXT_FIELDS = (
    "incident_name",
    "judicial_response",
    "sanctions_or_consequence",
    "ground_truth_notes",
)

# WorkflowContext nested string fields to sweep.
WORKFLOW_TEXT_FIELDS = ("ai_system_type",)

PLACEHOLDER = "counsel of record"


def _build_pattern(names: list[str]) -> re.Pattern[str] | None:
    """Build a case-insensitive whole-word regex for an attorney-name list."""
    if not names:
        return None
    # Sort longest-first so multi-word names match before their substrings.
    parts = sorted({n.strip() for n in names if n and n.strip()}, key=len, reverse=True)
    escaped = [re.escape(p) for p in parts]
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)


def _scrub_string(s: str | None, pattern: re.Pattern[str] | None) -> str | None:
    if s is None or pattern is None:
        return s
    return pattern.sub(PLACEHOLDER, s)


def _scrub_record(rec: CitationFailureCase) -> dict:
    """Convert a record to a sanitized public dict."""
    names = rec.attorney_names_internal or []
    pattern = _build_pattern(names)

    raw = asdict(rec)
    raw.pop("attorney_names_internal", None)

    for fname in FREE_TEXT_FIELDS:
        raw[fname] = _scrub_string(raw.get(fname), pattern)

    wc = raw.get("workflow_context")
    if isinstance(wc, dict):
        for fname in WORKFLOW_TEXT_FIELDS:
            wc[fname] = _scrub_string(wc.get(fname), pattern)
        raw["workflow_context"] = wc

    # Walk every remaining string field (defensive — catches schema growth)
    for k, v in list(raw.items()):
        if isinstance(v, str) and k not in FREE_TEXT_FIELDS:
            raw[k] = _scrub_string(v, pattern)

    return _enum_safe(raw)


def anonymize_corpus(
    records: list[CitationFailureCase],
    extra_names: list[str] | None = None,
) -> list[dict]:
    """Return sanitized public dicts from internal records.

    extra_names — additional attorney names to scrub beyond each record's
    attorney_names_internal (e.g., loaded from a blocklist file).
    """
    if extra_names:
        # Merge blocklist names into each record's internal list so
        # _scrub_record picks them up without mutating the originals.
        merged_records = []
        for r in records:
            existing = list(r.attorney_names_internal or [])
            for n in extra_names:
                if n not in existing:
                    existing.append(n)
            # Shallow-copy with merged names
            import dataclasses
            merged_records.append(dataclasses.replace(r, attorney_names_internal=existing))
        records = merged_records
    return [_scrub_record(r) for r in records]


def detect_leaks(public_records: list[dict], names: list[str]) -> list[str]:
    """Return any attorney-name strings still present in public records."""
    pattern = _build_pattern(names)
    if pattern is None:
        return []
    leaks: list[str] = []

    def walk(obj, path: str):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")
        elif isinstance(obj, str):
            if pattern.search(obj):
                leaks.append(path)

    for i, rec in enumerate(public_records):
        walk(rec, f"records[{i}]")
    return leaks


def _collect_all_names(records: list[CitationFailureCase]) -> list[str]:
    out: list[str] = []
    for r in records:
        if r.attorney_names_internal:
            out.extend(r.attorney_names_internal)
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Anonymize an internal Canonical Case Corpus file."
    )
    parser.add_argument("--in", dest="src", required=True)
    parser.add_argument("--out", dest="dst", required=True)
    parser.add_argument(
        "--blocklist",
        help="Optional path to a newline-delimited attorney names blocklist; "
             "names in this file are scrubbed in addition to "
             "attorney_names_internal fields.",
    )
    args = parser.parse_args(argv)

    records = load_corpus(args.src)
    extra_names: list[str] = []
    if args.blocklist:
        with open(args.blocklist) as f:
            extra_names = [line.strip() for line in f if line.strip()]

    # Inject blocklist names into every record so detector picks them up.
    for r in records:
        merged = list(r.attorney_names_internal or [])
        for n in extra_names:
            if n not in merged:
                merged.append(n)
        r.attorney_names_internal = merged

    sanitized = anonymize_corpus(records)

    # Defensive: verify no leaks before writing.
    leaks = detect_leaks(sanitized, _collect_all_names(records))
    if leaks:
        print(f"REFUSED: {len(leaks)} attorney-name leaks detected:", file=sys.stderr)
        for path in leaks[:10]:
            print(f"  • {path}", file=sys.stderr)
        return 1

    Path(args.dst).parent.mkdir(parents=True, exist_ok=True)
    with open(args.dst, "w") as f:
        json.dump({"records": sanitized}, f, indent=2)
    print(f"wrote {len(sanitized)} records → {args.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
