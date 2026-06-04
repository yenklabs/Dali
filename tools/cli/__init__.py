"""Dali CLI — short verbs matching the MCP tool vocabulary.

The six verbs are identical to the MCP tools so Path A (terminal) and
Path B (MCP) share one mental model:

    lint    Validate a corpus file
    score   Run the Tier 1 deterministic evaluator
    replay  Run the evaluator twice and verify replay determinism
    probe   Validate a Tier 2 prompt or JSONL file
    draft   Scaffold a new Tier 2 prompt template
    pack    Bundle a batch of prompts and produce a PR-ready checklist

Usage:
    python -m tools.cli <verb> [args]

The CLI is a thin convenience wrapper. ``dali/runners/run_integrity.py`` remains
the canonical underlying entry point and stays referenced in METHODOLOGY,
the policy-versioning doc, and CI. The CLI shares its code, so output and
cryptographic hashes are byte-identical to the underlying runner.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

# Ensure the repo root is importable when invoked as ``python -m tools.cli``
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

DEFAULT_CORPUS = "data/benchmark/tier1/corpus/citation_failure_cases.json"
DEFAULT_OUTPUT = "data/results/demo/integrity.json"


# ---------------------------------------------------------------------------
# Verb implementations — each wraps existing logic, never duplicates it
# ---------------------------------------------------------------------------

def _cmd_lint(args: argparse.Namespace) -> int:
    """Validate a corpus file (or a single record passed inline)."""
    from dali.corpus.loader import load_corpus
    from dali.corpus.validator import filter_scoring_eligible, validate_corpus

    path = args.corpus
    try:
        records = load_corpus(path)
    except Exception as exc:
        print(f"lint: failed to load {path}: {exc}", file=sys.stderr)
        return 1

    report = validate_corpus(records)
    eligible = filter_scoring_eligible(records)
    print(f"corpus:               {path}")
    print(f"  total records:      {report.total}")
    print(f"  scoring-eligible:   {report.scoring_eligible}")
    print(f"  pre-canonical:      {report.pre_canonical}")
    print(f"  needs-verification: {report.needs_verification}")
    print(f"  evaluable now:      {len(eligible)}")
    if report.scoring_eligible == 0:
        print("lint: FAIL — no scoring-eligible records", file=sys.stderr)
        return 2
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    """Run the Tier 1 evaluator. Delegates to dali/runners/run_integrity.py."""
    from dali.runners.run_integrity import main as run_integrity_main

    forwarded: list[str] = [
        "--corpus", args.corpus,
        "--output", args.output,
    ]
    if args.check_reachability:
        forwarded.append("--check-reachability")
    if args.include_pre_canonical:
        forwarded.append("--include-pre-canonical")
    if args.include_needs_verification:
        forwarded.append("--include-needs-verification")
    if args.allow_cross_version:
        forwarded.append("--allow-cross-version")
    return run_integrity_main(forwarded)


def _cmd_replay(args: argparse.Namespace) -> int:
    """Run the evaluator twice and assert replay-hash equality.

    The terminal equivalent of the MCP ``replay`` tool.
    """
    from dali.runners.run_integrity import main as run_integrity_main

    return run_integrity_main([
        "--corpus", args.corpus,
        "--output", args.output,
        "--verify-replay",
    ])


def _read_prompt_records(path_str: str) -> list[dict]:
    """Accept a single-record JSON file, a JSON array file, or a JSONL file."""
    text = Path(path_str).read_text().strip()
    if not text:
        return []
    if text.startswith("["):
        return json.loads(text)
    if text.startswith("{") and "\n" not in text:
        return [json.loads(text)]
    # JSONL — one record per non-empty, non-comment line
    return [
        json.loads(line)
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _cmd_probe(args: argparse.Namespace) -> int:
    """Validate one or more Tier 2 prompt records."""
    from tools.mcp.tools.prompt_tools import _check_prompt_impl

    try:
        records = _read_prompt_records(args.path)
    except Exception as exc:
        print(f"probe: failed to read {args.path}: {exc}", file=sys.stderr)
        return 1

    if not records:
        print(f"probe: no records found in {args.path}", file=sys.stderr)
        return 2

    failures = 0
    for record in records:
        result = _check_prompt_impl(json.dumps(record))
        record_id = record.get("id", "?")
        if result["valid"]:
            print(f"  OK   {record_id}")
        else:
            failures += 1
            print(f"  FAIL {record_id}")
            for issue in result["issues"]:
                print(f"         {issue}")
    print(f"probe: {len(records) - failures}/{len(records)} prompts valid")
    return 0 if failures == 0 else 2


def _cmd_draft(args: argparse.Namespace) -> int:
    """Scaffold a new Tier 2 prompt template."""
    from tools.mcp.tools.prompt_tools import _new_prompt_impl

    print(_new_prompt_impl(args.category, args.subcategory, args.difficulty, args.notes or ""))
    return 0


def _cmd_pack(args: argparse.Namespace) -> int:
    """Validate a batch of prompt JSONL files and produce a PR-ready checklist."""
    from tools.mcp.tools.prompt_tools import _bundle_prompts_impl

    batch: list[dict] = []
    for path_str in args.paths:
        try:
            batch.extend(_read_prompt_records(path_str))
        except Exception as exc:
            print(f"pack: failed to read {path_str}: {exc}", file=sys.stderr)
            return 1

    if not batch:
        print("pack: no records to bundle", file=sys.stderr)
        return 2

    result = _bundle_prompts_impl(json.dumps(batch))
    print(json.dumps(result, indent=2))
    return 0 if result["ready_to_submit"] else 2


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dali",
        description=(
            "Dali CLI — short verbs matching the MCP tool vocabulary. "
            "Same code path, same cryptographic hashes."
        ),
    )
    sub = p.add_subparsers(dest="verb", required=True)

    pl = sub.add_parser("lint", help="Validate a corpus file")
    pl.add_argument("corpus", nargs="?", default=DEFAULT_CORPUS,
                    help=f"Path to corpus JSON (default: {DEFAULT_CORPUS})")
    pl.set_defaults(func=_cmd_lint)

    ps = sub.add_parser("score", help="Run the Tier 1 deterministic evaluator")
    ps.add_argument("corpus", nargs="?", default=DEFAULT_CORPUS,
                    help=f"Path to corpus JSON (default: {DEFAULT_CORPUS})")
    ps.add_argument("--output", default=DEFAULT_OUTPUT,
                    help=f"Output JSON path (default: {DEFAULT_OUTPUT})")
    ps.add_argument("--check-reachability", action="store_true")
    ps.add_argument("--include-pre-canonical", action="store_true")
    ps.add_argument("--include-needs-verification", action="store_true")
    ps.add_argument("--allow-cross-version", action="store_true")
    ps.set_defaults(func=_cmd_score)

    pr = sub.add_parser("replay", help="Run the evaluator twice and verify replay determinism")
    pr.add_argument("corpus", nargs="?", default=DEFAULT_CORPUS)
    pr.add_argument("--output", default=DEFAULT_OUTPUT)
    pr.set_defaults(func=_cmd_replay)

    pp = sub.add_parser("probe", help="Validate a Tier 2 prompt or JSONL file")
    pp.add_argument("path", help="Path to a JSON, JSON array, or JSONL prompt file")
    pp.set_defaults(func=_cmd_probe)

    pd = sub.add_parser("draft", help="Scaffold a new Tier 2 prompt template")
    pd.add_argument("--category", required=True,
                    help="legal | research | adversarial")
    pd.add_argument("--subcategory", required=True)
    pd.add_argument("--difficulty", required=True)
    pd.add_argument("--notes", default="")
    pd.set_defaults(func=_cmd_draft)

    pk = sub.add_parser("pack", help="Bundle prompts and produce a PR-ready checklist")
    pk.add_argument("paths", nargs="+", help="One or more prompt JSON/JSONL files")
    pk.set_defaults(func=_cmd_pack)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
