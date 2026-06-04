#!/usr/bin/env python3
"""Export and summarize benchmark results.

Usage:
    python -m dali.runners.export data/results/v0.2/2026-05-25/ --format table
    python -m dali.runners.export data/results/v0.2/2026-05-25/ --format csv
    python -m dali.runners.export data/results/v0.2/2026-05-25/ --format json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def load_results(results_dir: Path) -> dict[str, list[dict]]:
    """Load all model result files from a results directory."""
    results = {}
    for path in sorted(results_dir.glob("*.json")):
        if path.name == "methodology.json":
            continue
        model_id = path.stem.replace("_", "-", 2)  # rough reverse of safe_model_id
        with open(path) as f:
            results[path.stem] = json.load(f)
    return results


def per_prompt_rows(model_results: dict[str, list[dict]]) -> list[dict]:
    rows = []
    for model_file, results in model_results.items():
        for r in results:
            rows.append({
                "model": r.get("model_id", model_file),
                "prompt_id": r["prompt_id"],
                "run_status": r.get("run_status"),
                "citation_extraction_status": r.get("citation_extraction_status"),
                "citation_count": r["citation_count"],
                "citation_generation_rate": r.get("citation_generation_rate"),
                "citation_parse_rate": r.get("citation_parse_rate"),
                "malformed_citation_rate": r.get("malformed_citation_rate"),
                "existence_rate": r.get("existence_rate"),
                "semantic_support_rate": r.get("semantic_support_rate"),
                "unsupported_authority_rate": r.get("unsupported_authority_rate"),
                "finish_reason": r.get("finish_reason"),
                "latency_ms": r.get("latency_ms"),
                "prompt_tokens": r.get("prompt_tokens"),
                "completion_tokens": r.get("completion_tokens"),
                "total_tokens": r.get("total_tokens"),
                "error": r.get("error", ""),
            })
    return rows


def print_table(rows: list[dict]) -> None:
    print(
        f"\n{'Model':<28} {'Prompt':<20} {'Status':<12} {'Extract':<20} "
        f"{'Gen%':>6} {'Parse%':>7} {'Malformed%':>10} {'Exist%':>7} {'Support%':>9}"
    )
    print("─" * 130)
    for r in rows:
        gen = f"{r['citation_generation_rate']:.0%}" if r["citation_generation_rate"] is not None else "—"
        parse = f"{r['citation_parse_rate']:.0%}" if r["citation_parse_rate"] is not None else "—"
        malformed = f"{r['malformed_citation_rate']:.0%}" if r["malformed_citation_rate"] is not None else "—"
        ex = f"{r['existence_rate']:.0%}" if r["existence_rate"] is not None else "—"
        sup = f"{r['semantic_support_rate']:.0%}" if r["semantic_support_rate"] is not None else "—"
        err = f"  ERR: {r['error'][:30]}" if r["error"] else ""
        print(
            f"{r['model']:<28} {r['prompt_id']:<20} {str(r.get('run_status') or '—'):<12} "
            f"{str(r.get('citation_extraction_status') or '—'):<20} {gen:>6} {parse:>7} "
            f"{malformed:>10} {ex:>7} {sup:>9}{err}"
        )


def print_summary(model_results: dict[str, list[dict]]) -> None:
    print(f"\n── Aggregate Summary ─────────────────────────────────────────")
    print(
        f"{'Model':<30} {'Rows':>6} {'Gen%':>6} {'Parse%':>7} "
        f"{'Malformed%':>10} {'Exist%':>7} {'Support%':>9}"
    )
    print("─" * 85)
    for model_file, results in model_results.items():
        model_id = results[0].get("model_id", model_file) if results else model_file
        gen_rates = [r["citation_generation_rate"] for r in results if r.get("citation_generation_rate") is not None]
        parse_rates = [r["citation_parse_rate"] for r in results if r.get("citation_parse_rate") is not None]
        malformed_rates = [r["malformed_citation_rate"] for r in results if r.get("malformed_citation_rate") is not None]
        ex_rates = [r["existence_rate"] for r in results if r.get("existence_rate") is not None]
        sup_scores = [r["semantic_support_rate"] for r in results if r.get("semantic_support_rate") is not None]
        gen_mean = sum(gen_rates) / len(gen_rates) if gen_rates else None
        parse_mean = sum(parse_rates) / len(parse_rates) if parse_rates else None
        malformed_mean = sum(malformed_rates) / len(malformed_rates) if malformed_rates else None
        ex_mean = sum(ex_rates) / len(ex_rates) if ex_rates else None
        sup_mean = sum(sup_scores) / len(sup_scores) if sup_scores else None
        gen_str = f"{gen_mean:.0%}" if gen_mean is not None else "—"
        parse_str = f"{parse_mean:.0%}" if parse_mean is not None else "—"
        malformed_str = f"{malformed_mean:.0%}" if malformed_mean is not None else "—"
        ex_str = f"{ex_mean:.0%}" if ex_mean is not None else "—"
        sup_str = f"{sup_mean:.0%}" if sup_mean is not None else "—"
        print(
            f"{model_id:<30} {len(results):>6} {gen_str:>6} {parse_str:>7} "
            f"{malformed_str:>10} {ex_str:>7} {sup_str:>9}"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Export benchmark results")
    parser.add_argument("results_dir", type=Path, help="Results directory to export")
    parser.add_argument(
        "--format", choices=["table", "csv", "json"], default="table"
    )
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    if not args.results_dir.exists():
        print(f"Directory not found: {args.results_dir}", file=sys.stderr)
        sys.exit(1)

    model_results = load_results(args.results_dir)
    if not model_results:
        print("No result files found.", file=sys.stderr)
        sys.exit(1)

    rows = per_prompt_rows(model_results)

    if args.format == "table":
        if not args.summary_only:
            print_table(rows)
        print_summary(model_results)

    elif args.format == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    elif args.format == "json":
        json.dump(rows, sys.stdout, indent=2, default=str)
        print()


if __name__ == "__main__":
    main()
