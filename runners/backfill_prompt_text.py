#!/usr/bin/env python3
"""Backfill prompt_text into existing Tier 2 result files.

For result files produced before runners/run_synthetic.py started
embedding prompt_text per record. Reads the source synthetic/*.jsonl
prompts, builds a prompt_id → prompt_text map, then injects prompt_text
into each result record in-place.

Idempotent — re-running is safe. Skips records that already have
prompt_text.

Usage:
    python runners/backfill_prompt_text.py results/v0.2/2026-05-26/

    # Or specific files:
    python runners/backfill_prompt_text.py results/v0.2/2026-05-26/openai_fast.json
"""

from __future__ import annotations

import json
import pathlib
import sys


def load_prompt_map() -> dict[str, str]:
    """Build {prompt_id: prompt_text} from every synthetic/*.jsonl file."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    synthetic_dir = repo_root / "synthetic"
    if not synthetic_dir.is_dir():
        raise SystemExit(f"synthetic/ not found at {synthetic_dir}")

    prompts: dict[str, str] = {}
    for jsonl in synthetic_dir.rglob("*.jsonl"):
        for line_no, line in enumerate(jsonl.read_text().splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"  ⚠️  {jsonl}:{line_no} unparseable JSON: {exc}", file=sys.stderr)
                continue
            pid = rec.get("id")
            ptext = rec.get("prompt")
            if not pid or not ptext:
                continue
            if pid in prompts and prompts[pid] != ptext:
                print(f"  ⚠️  duplicate prompt_id {pid!r} with differing text — keeping first", file=sys.stderr)
                continue
            prompts[pid] = ptext
    return prompts


def backfill_file(path: pathlib.Path, prompts: dict[str, str]) -> tuple[int, int, int]:
    """Inject prompt_text into each record in `path`.

    Returns (updated, already_present, missing) counts.
    """
    raw = path.read_text()
    data = json.loads(raw)
    if not isinstance(data, list):
        print(f"  ⚠️  {path}: not a list of records, skipping")
        return 0, 0, 0

    updated = 0
    already = 0
    missing = 0
    for rec in data:
        pid = rec.get("prompt_id")
        if not pid:
            continue
        if rec.get("prompt_text"):
            already += 1
            continue
        ptext = prompts.get(pid)
        if ptext is None:
            missing += 1
            continue
        # Insert prompt_text right after prompt_id for readability
        new_rec = {}
        for k, v in rec.items():
            new_rec[k] = v
            if k == "prompt_id":
                new_rec["prompt_text"] = ptext
        rec.clear()
        rec.update(new_rec)
        updated += 1

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return updated, already, missing


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2

    targets: list[pathlib.Path] = []
    for arg in argv[1:]:
        p = pathlib.Path(arg)
        if p.is_dir():
            targets.extend(sorted(p.glob("*.json")))
        elif p.is_file():
            targets.append(p)
        else:
            print(f"  ⚠️  not found: {p}", file=sys.stderr)

    if not targets:
        print("No files to process.")
        return 1

    print(f"Loading prompts from synthetic/ ...")
    prompts = load_prompt_map()
    print(f"  loaded {len(prompts)} prompts")
    print()

    total_updated = 0
    for path in targets:
        # Skip non-result files (methodology, schema)
        name = path.name.lower()
        if name.startswith("methodology") or name.startswith("schema") or name == "readme.md":
            continue
        try:
            updated, already, missing = backfill_file(path, prompts)
        except json.JSONDecodeError as exc:
            print(f"  ⚠️  {path}: invalid JSON — {exc}", file=sys.stderr)
            continue
        total_updated += updated
        status = "✓" if missing == 0 else "⚠"
        print(f"  {status} {path}")
        print(f"      updated={updated}  already_present={already}  missing_prompt={missing}")

    print()
    print(f"Done. Total records updated: {total_updated}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
