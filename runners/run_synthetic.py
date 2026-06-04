#!/usr/bin/env python3
"""Dali Reproducibility & Attribution Benchmark runner.

Usage:

    # Smoke test — 5 prompts, validate API access before a full run:
    python runners/run_synthetic.py \
        --models openai_fast \
        --limit 5

    # Full run — pinned model, versioned output directory:
    python runners/run_synthetic.py \
        --models openai_fast \
        --prompts benchmarks/tier2/ \
        --output results/v0.2/$(date +%Y-%m-%d)/

    # Multi-model comparison run:
    python runners/run_synthetic.py \
        --models openai_fast anthropic_fast \
        --output results/v0.2/$(date +%Y-%m-%d)/

    # With fallback if a provider is unavailable:
    python runners/run_synthetic.py \
        --models anthropic_fast \
        --fallback-model openai_fast

    # List all available model aliases and raw IDs:
    python runners/run_synthetic.py --list-models

Model aliases (recommended):
    openai_fast        → gpt-4o-mini-2024-07-18   pinned  ✓ public benchmark
    openai_fast_latest → gpt-4o-mini               latest  dev only
    openai_quality     → gpt-4.1                   latest  ✓ public benchmark
    anthropic_fast     → claude-3-5-haiku-20241022 pinned  ✓ public benchmark

Raw model IDs also work: gpt-4o-mini-2024-07-18, gpt-4o, etc.

Benchmark integrity principle
------------------------------
A provider billing or availability failure is NOT evidence of model
hallucination. Results with run_status != "completed" carry
scorable=False and are excluded from all citation metrics. They
contribute only to provider_reliability reporting.

Run status semantics
---------------------
  completed            model successfully evaluated
  provider_unavailable provider billing / model / account issue (non-retryable)
  rate_limited         transient 429 / throttle (retryable)
  api_error            unexpected API execution failure
  verification_failed  citation verification layer failed after model responded
  pipeline_error       internal framework exception
  skipped              intentionally excluded from this run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from runners.models import (
    assert_provider_ready,
    call_model_result,
    classify_model_error,
)
from runners.model_registry import resolve_model, list_models, DEFAULT_DEV_MODELS
from scoring.support import MAX_TOKENS, get_scorer_model, score_support
from scoring.verification import inspect_citation_extraction, verify_citations

_REPO_ROOT = Path(__file__).parent.parent
BENCHMARK_VERSION = "v0.2"
PARSER_VERSION = "v1.1.0"
POLICY_VERSION = "v1.0.0"

_REFUSAL_RE = re.compile(
    r"\b(i (?:can(?:not|'t)|won't|am unable to)\b|"
    r"i do not have access\b|"
    r"i can(?:not|'t) provide\b|"
    r"i can't help with that\b|"
    r"i don't know\b)\b",
    re.IGNORECASE,
)


def _looks_like_refusal(output: str, finish_reason: str | None) -> bool:
    if finish_reason == "refusal":
        return True
    return bool(_REFUSAL_RE.search(output.strip()))


def load_benchmark_env() -> dict[str, str]:
    """Load local .env overrides for benchmark runs."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None

    if load_dotenv is not None:
        local_env = _REPO_ROOT / ".env"
        if local_env.is_file():
            load_dotenv(local_env, override=False)

    return {k: v for k, v in os.environ.items() if k.endswith("_API_KEY")}


def preflight_api_keys(resolved: list[dict], sources: dict[str, str]) -> None:
    """Fail fast before burning prompts on missing API keys (env check only).

    Args:
        resolved: List of resolved registry entries (from resolve_model).
        sources:  Dict of env key → source label (from load_benchmark_env).
    """
    providers: set[str] = {e["provider"] for e in resolved}
    needed: dict[str, str] = {}
    if "anthropic" in providers:
        needed["ANTHROPIC_API_KEY"] = "anthropic"
    if "openai" in providers:
        needed["OPENAI_API_KEY"] = "openai"
    if "google" in providers:
        needed["GOOGLE_API_KEY"] = "google"

    problems: list[str] = []
    for secret_id, provider in sorted(needed.items()):
        value = os.environ.get(secret_id, "")
        source = sources.get(secret_id, "missing")
        if not value or value.startswith("placeholder"):
            problems.append(f"{secret_id} missing or placeholder (source={source})")

    if problems:
        print(
            "Benchmark blocked — live model calls need API keys in the local environment:",
            file=sys.stderr,
        )
        for line in problems:
            print(f"  • {line}", file=sys.stderr)
        sys.exit(2)


def preflight_providers(resolved: list[dict]) -> dict[str, tuple[str, str]]:
    """Live preflight: ping each model with a minimal call.

    Args:
        resolved: List of resolved registry entries (from resolve_model).

    Returns a dict of model_id → (run_status, failure_reason) for models
    confirmed as provider_unavailable (billing/auth/invalid model).

    api_error on the ping is treated as a warning — the ping itself may be
    flaky. Only provider_unavailable is a hard block on all prompts for
    that provider.
    """
    failures: dict[str, tuple[str, str]] = {}
    seen_providers: set[str] = set()

    for entry in resolved:
        provider = entry["provider"]
        model_id = entry["model_id"]
        alias = entry.get("alias", model_id)

        if provider in seen_providers:
            continue  # one ping per provider is enough
        seen_providers.add(provider)

        label = f"{alias} → {model_id}" if alias != model_id else model_id
        print(f"   ↳ preflight {label} ({provider}) ... ", end="", flush=True)
        try:
            assert_provider_ready(model_id)
            print("✓ ready")
        except RuntimeError as exc:
            msg = str(exc)
            run_status, failure_reason = classify_model_error(msg)
            if run_status == "provider_unavailable":
                print(f"✗ {run_status} ({failure_reason})")
                # Block all models on this provider
                for e in resolved:
                    if e["provider"] == provider:
                        failures[e["model_id"]] = (run_status, failure_reason)
            else:
                # api_error / rate_limited on ping — warn, let prompts decide
                print(f"⚠ ping inconclusive ({run_status}: {failure_reason}) — proceeding")
        except Exception as exc:
            run_status, failure_reason = classify_model_error(str(exc))
            if run_status == "provider_unavailable":
                print(f"✗ {run_status} ({failure_reason})")
                for e in resolved:
                    if e["provider"] == provider:
                        failures[e["model_id"]] = (run_status, failure_reason)
            else:
                print(f"⚠ ping inconclusive ({run_status}: {failure_reason}) — proceeding")
    return failures


def load_prompts(prompts_dir: Path, limit: int | None = None) -> list[dict]:
    """Load .jsonl files from prompts_dir recursively, optionally capped."""
    prompts = []
    for jsonl_file in sorted(prompts_dir.rglob("*.jsonl")):
        with open(jsonl_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    prompts.append(json.loads(line))
                    if limit and len(prompts) >= limit:
                        return prompts
    return prompts


async def run_prompt(
    prompt: dict,
    model_entry: dict,
    *,
    upload_snapshots: bool = True,
    fallback_entry: dict | None = None,
    provider_unavailable: bool = False,
    debug_parser: bool = False,
) -> dict:
    """Run a single prompt through the full verification pipeline.

    Args:
        prompt:             Prompt dict with 'id' and 'prompt' fields.
        model_entry:        Resolved registry entry (from resolve_model).
        upload_snapshots:   Whether to upload citation snapshots.
        fallback_entry:     Resolved registry entry for fallback model.
        provider_unavailable: True if preflight already confirmed this provider down.
    """
    prompt_id = prompt["id"]
    prompt_text = prompt["prompt"]
    prompt_category = prompt.get("category")
    run_at = datetime.now(timezone.utc).isoformat()

    model_id = model_entry["model_id"]
    provider = model_entry["provider"]
    alias = model_entry.get("alias", model_id)
    model_pinned = model_entry.get("pinned", False)

    requested_alias = alias
    executed_model = model_id
    executed_provider = provider
    fallback_used = False
    fallback_from: str | None = None

    llm_output = ""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    finish_reason: str | None = None
    provider_finish_reason: str | None = None
    latency_ms: int | None = None

    def _failed(
        run_status: str,
        failure_reason: str,
        error: str,
        *,
        extraction_status: str = "empty_response",
        extraction_debug: dict | None = None,
    ) -> dict:
        return {
            "prompt_id": prompt_id,
            "prompt_text": prompt_text,
            "category": prompt_category,
            "model_id": executed_model,
            "provider": executed_provider,
            "requested_model": requested_alias,
            "executed_model": executed_model,
            "model_pinned": model_pinned,
            "benchmark_version": BENCHMARK_VERSION,
            "parser_version": PARSER_VERSION,
            "policy_version": POLICY_VERSION,
            "fallback_used": fallback_used,
            "fallback_from": fallback_from,
            "run_status": run_status,
            "failure_reason": failure_reason,
            "scorable": False,
            "error": error,
            "output": llm_output if llm_output else None,
            "parsed_citations": [],
            "citation_extraction_status": extraction_status,
            "citation_extraction_debug": extraction_debug if debug_parser else None,
            "citations": [],
            "citation_count": 0,
            "malformed_citation_count": 0,
            "citation_generation_attempted": False,
            "citation_generation_rate": 0.0,
            "citation_parse_rate": 0.0,
            "malformed_citation_rate": 0.0,
            "unsupported_authority_rate": None,
            "existence_rate": None,
            "mean_support_score": None,
            "semantic_support_rate": None,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "finish_reason": finish_reason,
            "provider_finish_reason": provider_finish_reason,
            "latency_ms": latency_ms,
            "run_at": run_at,
        }

    if provider_unavailable:
        return _failed("provider_unavailable", "preflight_failed", "provider failed preflight check")

    model_call_started = time.perf_counter()
    try:
        model_result = call_model_result(model_id, prompt_text)
        llm_output = model_result.output or ""
        prompt_tokens = model_result.prompt_tokens
        completion_tokens = model_result.completion_tokens
        total_tokens = model_result.total_tokens
        finish_reason = model_result.finish_reason
        provider_finish_reason = model_result.provider_finish_reason
    except KeyError:
        latency_ms = int((time.perf_counter() - model_call_started) * 1000)
        return _failed("provider_unavailable", "missing_api_key", "API key env var not set")
    except Exception as exc:
        run_status, failure_reason = classify_model_error(str(exc))
        fb_id = fallback_entry["model_id"] if fallback_entry else None
        if run_status == "provider_unavailable" and fb_id and fb_id != model_id:
            try:
                fb_started = time.perf_counter()
                model_result = call_model_result(fb_id, prompt_text)
                latency_ms = int((time.perf_counter() - fb_started) * 1000)
                llm_output = model_result.output or ""
                prompt_tokens = model_result.prompt_tokens
                completion_tokens = model_result.completion_tokens
                total_tokens = model_result.total_tokens
                finish_reason = model_result.finish_reason
                provider_finish_reason = model_result.provider_finish_reason
                fallback_from = model_id
                executed_model = fb_id
                executed_provider = fallback_entry["provider"]
                fallback_used = True
                model_pinned = False
            except Exception as fb_exc:
                latency_ms = int((time.perf_counter() - model_call_started) * 1000)
                fb_status, fb_reason = classify_model_error(str(fb_exc))
                return _failed(
                    fb_status,
                    fb_reason,
                    f"primary: {exc}; fallback ({fb_id}): {fb_exc}",
                )
        else:
            latency_ms = int((time.perf_counter() - model_call_started) * 1000)
            return _failed(run_status, failure_reason, str(exc))

    if latency_ms is None:
        latency_ms = int((time.perf_counter() - model_call_started) * 1000)

    try:
        extraction_debug = inspect_citation_extraction(llm_output)
    except Exception as exc:
        return _failed(
            "verification_failed",
            "parser_failure",
            str(exc),
            extraction_debug={
                "stage": "inspect_citation_extraction",
                "exception": str(exc),
            },
        )

    parsed_candidates = extraction_debug.get("parsed_candidates", [])
    malformed_candidates = extraction_debug.get("malformed_candidates", [])
    parsed_citations = [item["raw_text"] for item in parsed_candidates]

    output_stripped = llm_output.strip()
    if not output_stripped:
        extraction_status = "empty_response"
    elif _looks_like_refusal(llm_output, finish_reason):
        extraction_status = "refusal"
    elif parsed_candidates:
        extraction_status = "citations_found"
    elif malformed_candidates:
        extraction_status = "malformed_citations"
    else:
        extraction_status = "no_citations_generated"

    citations = []
    support_scores = []
    if parsed_candidates:
        try:
            verified = await verify_citations(
                llm_output,
                evidence_id=f"benchmark:{prompt_id}:{executed_model}",
                audit_id="benchmark",
                upload=upload_snapshots,
            )
        except Exception as exc:
            print(f"  ⚠️  verify_citations failed for {prompt_id}: {exc}", file=sys.stderr)
            return _failed(
                "verification_failed",
                "verification_error",
                str(exc),
                extraction_status=extraction_status,
                extraction_debug={
                    **extraction_debug,
                    "stage": "verify_citations",
                    "exception": str(exc),
                },
            )

        for vc in verified:
            snap = vc.snapshot
            support_score = None
            support_verdict = None

            if snap and snap.exists_verified and snap.extracted_text:
                try:
                    from scoring.support import extract_claim_for_citation
                    claim = extract_claim_for_citation(vc.raw_text, llm_output)
                    if claim:
                        scored = score_support(claim, snap.extracted_text)
                        support_score = scored.score
                        support_verdict = scored.verdict
                        support_scores.append(support_score)
                except Exception as exc:
                    print(f"  ⚠️  scoring failed for {vc.source_ref}: {exc}", file=sys.stderr)

            citations.append({
                "citation_text": vc.raw_text,
                "source_url": vc.source_ref,
                "resolution_method": vc.resolution_method,
                "existence_verified": vc.verdict in ("verified", "redirected"),
                "existence_score": vc.existence_score,
                "http_status": snap.http_status if snap else 0,
                "content_hash": snap.content_hash if snap else None,
                "storage_path": snap.storage_path if snap else None,
                "support_score": support_score,
                "support_verdict": support_verdict,
                "verdict": vc.verdict,
                "captured_at": snap.captured_at.isoformat() if snap else run_at,
            })

    existence_rate = (
        sum(1 for c in citations if c["existence_verified"]) / len(citations)
        if citations else None
    )
    mean_support = (
        sum(support_scores) / len(support_scores)
        if support_scores else None
    )

    malformed_count = len(malformed_candidates)
    parse_attempts = len(parsed_candidates) + malformed_count
    citation_generation_attempted = parse_attempts > 0
    citation_generation_rate = 1.0 if citation_generation_attempted else 0.0
    citation_parse_rate = (len(parsed_candidates) / parse_attempts) if parse_attempts else 0.0
    malformed_citation_rate = (malformed_count / parse_attempts) if parse_attempts else 0.0

    unsupported = [
        c for c in citations
        if c.get("support_verdict") in {"unsupported", "partial", "unverifiable"}
    ]
    unsupported_authority_rate = (len(unsupported) / len(citations)) if citations else None

    scorable = not fallback_used

    return {
        "prompt_id": prompt_id,
        "prompt_text": prompt_text,
        "category": prompt_category,
        "model_id": executed_model,
        "provider": executed_provider,
        "requested_model": requested_alias,
        "executed_model": executed_model,
        "model_pinned": model_pinned,
        "benchmark_version": BENCHMARK_VERSION,
        "parser_version": PARSER_VERSION,
        "policy_version": POLICY_VERSION,
        "fallback_used": fallback_used,
        "fallback_from": fallback_from,
        "run_status": "completed",
        "failure_reason": None,
        "scorable": scorable,
        "output": llm_output,
        "parsed_citations": parsed_citations,
        "citation_extraction_status": extraction_status,
        "citation_extraction_debug": extraction_debug if debug_parser else None,
        "citations": citations,
        "citation_count": len(citations),
        "malformed_citation_count": malformed_count,
        "citation_generation_attempted": citation_generation_attempted,
        "citation_generation_rate": round(citation_generation_rate, 4),
        "citation_parse_rate": round(citation_parse_rate, 4),
        "malformed_citation_rate": round(malformed_citation_rate, 4),
        "unsupported_authority_rate": (
            round(unsupported_authority_rate, 4)
            if unsupported_authority_rate is not None else None
        ),
        "existence_rate": round(existence_rate, 4) if existence_rate is not None else None,
        "mean_support_score": round(mean_support, 4) if mean_support is not None else None,
        "semantic_support_rate": round(mean_support, 4) if mean_support is not None else None,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "finish_reason": finish_reason,
        "provider_finish_reason": provider_finish_reason,
        "latency_ms": latency_ms,
        "run_at": run_at,
    }


async def run_model(
    model_entry: dict,
    prompts: list[dict],
    output_dir: Path,
    *,
    upload_snapshots: bool = True,
    fallback_entry: dict | None = None,
    provider_unavailable: bool = False,
    debug_parser: bool = False,
) -> list[dict]:
    """Run all prompts for one model and save results."""
    n = len(prompts)
    model_id = model_entry["model_id"]
    alias = model_entry.get("alias", model_id)
    label = f"{alias} → {model_id}" if alias != model_id else model_id
    pinned_tag = " [pinned]" if model_entry.get("pinned") else ""
    unavail_tag = " [PROVIDER UNAVAILABLE — results will be non-scorable]" if provider_unavailable else ""
    print(f"\n▶  {label}  ({n} prompts){pinned_tag}{unavail_tag}")

    results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"   [{i:02d}/{n}] {prompt['id']} ... ", end="", flush=True)
        try:
            result = await run_prompt(
                prompt,
                model_entry,
                upload_snapshots=upload_snapshots,
                fallback_entry=fallback_entry,
                provider_unavailable=provider_unavailable,
                debug_parser=debug_parser,
            )
            status = result["run_status"]
            if status == "completed":
                fb = " [fallback]" if result.get("fallback_used") else ""
                parsed = len(result.get("parsed_citations", []))
                malformed = result.get("malformed_citation_count", 0)
                extraction_status = result.get("citation_extraction_status", "unknown")
                ex = result.get("existence_rate")
                sup = result.get("semantic_support_rate")
                ex_str = f"{ex:.0%}" if ex is not None else "n/a"
                sup_str = f"{sup:.2f}" if sup is not None else "n/a"
                print(
                    f"{parsed} citations extracted ({extraction_status})  "
                    f"exist={ex_str}  support={sup_str}{fb}"
                )
                for citation in result.get("parsed_citations", []):
                    print(f"      - {citation}")
                if malformed:
                    print(f"      malformed candidates: {malformed}")
                if debug_parser and result.get("citation_extraction_debug"):
                    debug = result["citation_extraction_debug"]
                    raw = debug.get("raw_matches", {})
                    print("      debug parser:")
                    print(
                        f"        raw matches url={len(raw.get('url_explicit', []))} "
                        f"doi={len(raw.get('doi', []))} case={len(raw.get('case_pattern', []))}"
                    )
                    print(
                        f"        selected={len(debug.get('parsed_candidates', []))} "
                        f"malformed={len(debug.get('malformed_candidates', []))}"
                    )
                    for step in debug.get("normalization_steps", []):
                        print(f"        normalize: {step}")
                    for item in debug.get("malformed_candidates", []):
                        print(f"        malformed[{item.get('type')}]: {item.get('raw_text')}")
            else:
                reason = result.get("failure_reason", "unknown")
                print(f"SKIP ({status}: {reason})  [non-scorable]")
                if debug_parser:
                    extraction_status = result.get("citation_extraction_status")
                    if extraction_status:
                        print(f"      extraction_status={extraction_status}")
                    debug = result.get("citation_extraction_debug") or {}
                    if debug.get("stage") or debug.get("exception"):
                        stage = debug.get("stage", "unknown")
                        exc = debug.get("exception", "unknown")
                        print(f"      debug parser exception ({stage}): {exc}")
        except Exception as exc:
            print(f"ERROR: {exc}")
            traceback.print_exc()
            result = {
                "prompt_id": prompt["id"],
                "model_id": model_id,
                "category": prompt.get("category"),
                "provider": model_entry.get("provider", "unknown"),
                "requested_model": alias,
                "executed_model": model_id,
                "model_pinned": model_entry.get("pinned", False),
                "benchmark_version": BENCHMARK_VERSION,
                "parser_version": PARSER_VERSION,
                "policy_version": POLICY_VERSION,
                "fallback_used": False,
                "fallback_from": None,
                "run_status": "pipeline_error",
                "failure_reason": "unknown",
                "scorable": False,
                "error": str(exc),
                "output": None,
                "parsed_citations": [],
                "citation_extraction_status": "parser_failure",
                "citation_extraction_debug": None,
                "citations": [],
                "citation_count": 0,
                "malformed_citation_count": 0,
                "citation_generation_attempted": False,
                "citation_generation_rate": 0.0,
                "citation_parse_rate": 0.0,
                "malformed_citation_rate": 0.0,
                "unsupported_authority_rate": None,
                "existence_rate": None,
                "mean_support_score": None,
                "semantic_support_rate": None,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "finish_reason": None,
                "provider_finish_reason": None,
                "latency_ms": None,
                "run_at": datetime.now(timezone.utc).isoformat(),
            }
        results.append(result)

    output_dir.mkdir(parents=True, exist_ok=True)
    # Use alias as filename when available (e.g. openai_fast.json)
    safe_name = alias.replace("/", "_").replace(":", "_")
    out_path = output_dir / f"{safe_name}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"   → saved {out_path}")

    return results


def compute_provider_reliability(all_results: dict[str, list[dict]]) -> dict:
    """Aggregate provider-level availability metrics across all model runs."""
    provider_stats: dict[str, dict] = defaultdict(lambda: defaultdict(int))

    for alias, results in all_results.items():
        for r in results:
            provider = r.get("provider", "unknown")
            provider_stats[provider]["total"] += 1
            status = r.get("run_status", "unknown")
            provider_stats[provider][status] += 1

    reliability: dict[str, dict] = {}
    for provider, stats in provider_stats.items():
        total = stats["total"]
        completed = stats.get("completed", 0)
        unavailable = stats.get("provider_unavailable", 0)
        reliability[provider] = {
            "total_prompts": total,
            "completed": completed,
            "provider_unavailable": unavailable,
            "rate_limited": stats.get("rate_limited", 0),
            "api_error": stats.get("api_error", 0),
            "verification_failed": stats.get("verification_failed", 0),
            "pipeline_error": stats.get("pipeline_error", 0),
            "availability_rate": round(completed / total, 4) if total else 0.0,
            "billing_failure": unavailable == total and total > 0,
        }
    return reliability


def write_methodology(
    output_dir: Path,
    resolved: list[dict],
    prompt_count: int,
    git_sha: str,
    provider_reliability: dict,
    fallback_entry: dict | None,
) -> None:
    """Write methodology.json alongside results."""
    try:
        scorer_model = get_scorer_model()
    except EnvironmentError:
        scorer_model = None

    methodology = {
        "benchmark_version": BENCHMARK_VERSION,
        "parser_version": PARSER_VERSION,
        "policy_version": POLICY_VERSION,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha,
        "models": [
            {
                "alias": e.get("alias", e["model_id"]),
                "model_id": e["model_id"],
                "provider": e["provider"],
                "display_name": e.get("display_name", e["model_id"]),
                "benchmark_role": e.get("benchmark_role", ""),
                "pinned": e.get("pinned", False),
                "recommended_for_public_benchmark": e.get("recommended_for_public_benchmark", False),
            }
            for e in resolved
        ],
        "fallback_model": fallback_entry["model_id"] if fallback_entry else None,
        "scorer": {
            "model_id": scorer_model,
            "max_tokens": MAX_TOKENS,
            "temperature": 0.0,
            "source_char_limit": 3000,
        },
        "prompt_count": prompt_count,
        "pipeline": {
            "extraction": "public citation extraction",
            "source_fetch": "public URL fetch",
            "verifier": "scoring.verification.verify_citations",
            "inspector": "scoring.verification.inspect_citation_extraction",
            "scorer": "scoring.support.score_support",
        },
        "provider_reliability": provider_reliability,
        "benchmark_integrity_note": (
            "Rows with scorable=False (provider_unavailable, rate_limited, api_error, "
            "verification_failed, pipeline_error, fallback_used) are excluded from "
            "citation metrics. They contribute only to provider_reliability reporting."
        ),
    }

    out_path = output_dir / "methodology.json"
    with open(out_path, "w") as f:
        json.dump(methodology, f, indent=2)
    print(f"\n📋 methodology → {out_path}")


def print_category_summary(all_results: dict[str, list[dict]]) -> None:
    """Print category-level aggregates for scorable completed rows."""
    bucket: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for results in all_results.values():
        for row in results:
            if not row.get("scorable") or row.get("run_status") != "completed":
                continue
            category = row.get("category") or "uncategorized"
            stats = bucket[category]
            stats["rows"] += 1
            stats["citations"] += row.get("citation_count", 0)
            ex = row.get("existence_rate")
            sup = row.get("semantic_support_rate")
            if ex is not None:
                stats["existence_sum"] += ex
                stats["existence_n"] += 1
            if sup is not None:
                stats["support_sum"] += sup
                stats["support_n"] += 1

    if not bucket:
        return

    print("\n── Category Summary (scorable runs only) ───────────────────────")
    print(f"{'Category':<18} {'Citations':>10} {'Exist%':>8} {'Support%':>10}")
    print("─" * 55)
    for category in sorted(bucket):
        stats = bucket[category]
        ex = (
            stats["existence_sum"] / stats["existence_n"]
            if stats.get("existence_n") else None
        )
        sup = (
            stats["support_sum"] / stats["support_n"]
            if stats.get("support_n") else None
        )
        ex_str = f"{ex:.0%}" if ex is not None else "—"
        sup_str = f"{sup:.0%}" if sup is not None else "—"
        print(f"{category:<18} {int(stats['citations']):>10} {ex_str:>8} {sup_str:>10}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dali Reproducibility & Attribution Benchmark runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Model aliases (recommended for public runs):\n"
            "  openai_fast        → gpt-4o-mini-2024-07-18  pinned\n"
            "  openai_fast_latest → gpt-4o-mini              latest\n"
            "  openai_quality     → gpt-4.1\n"
            "  anthropic_fast     → claude-3-5-haiku-20241022 pinned\n\n"
            "Raw model IDs also work: gpt-4o-mini-2024-07-18, gpt-4o, etc.\n"
            "Use --list-models to see all options."
        ),
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_DEV_MODELS,
        help="Model aliases or raw IDs (default: openai_fast). Use --list-models to see all.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print all available model aliases and raw IDs, then exit.",
    )
    parser.add_argument(
        "--prompts",
        type=Path,
        default=Path("benchmarks/tier2"),
        help="Path to synthetic prompt directory (default: benchmarks/tier2/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(f"results/v0.2/{datetime.now().strftime('%Y-%m-%d')}"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap prompts per run (smoke test mode). Example: --limit 5",
    )
    parser.add_argument(
        "--fallback-model",
        default=None,
        help=(
            "If a model's provider is unavailable, reroute prompts to this alias/ID. "
            "Fallback results carry fallback_used=true and scorable=false."
        ),
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Retained for compatibility; the public runner does not upload snapshots",
    )
    parser.add_argument(
        "--prompt-filter",
        help="Only run prompts whose ID contains this string",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip API key and live provider preflight checks",
    )
    parser.add_argument(
        "--debug-parser",
        action="store_true",
        help=(
            "Print parser diagnostics: raw matches, selected citations, malformed candidates, "
            "and extraction status."
        ),
    )
    args = parser.parse_args()

    # --list-models: print registry and exit
    if args.list_models:
        print(f"\n{'Alias':<25} {'Model ID':<35} {'Provider':<12} {'Pinned':<7} {'Public'}")
        print("─" * 95)
        for row in list_models():
            pin = "✓" if row.get("pinned") else ""
            pub = "✓" if row.get("recommended_for_public_benchmark") else ""
            print(f"{row['alias']:<25} {row['model_id']:<35} {row['provider']:<12} {pin:<7} {pub}")
        print()
        return

    key_sources = load_benchmark_env()

    # Resolve all aliases/IDs to full registry entries
    resolved: list[dict] = []
    for alias_or_id in args.models:
        try:
            resolved.append(resolve_model(alias_or_id))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)

    fallback_entry: dict | None = None
    if args.fallback_model:
        try:
            fallback_entry = resolve_model(args.fallback_model)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)

    prompts = load_prompts(args.prompts, limit=args.limit)
    if args.prompt_filter:
        prompts = [p for p in prompts if args.prompt_filter in p["id"]]
    if not prompts:
        print("No prompts found.", file=sys.stderr)
        sys.exit(1)

    if not args.skip_preflight:
        preflight_api_keys(resolved, key_sources)

    upload = not args.no_upload
    smoke = args.limit is not None

    model_labels = [
        f"{e.get('alias', e['model_id'])} → {e['model_id']}"
        if e.get("alias") != e["model_id"] else e["model_id"]
        for e in resolved
    ]
    print(f"Dali Reproducibility & Attribution Benchmark {BENCHMARK_VERSION}")
    print(f"Models:  {model_labels}")
    print(f"Prompts: {len(prompts)}{' (smoke test)' if smoke else ''}")
    print(f"Output:  {args.output}")
    if fallback_entry:
        print(f"Fallback: {fallback_entry.get('alias', fallback_entry['model_id'])} → {fallback_entry['model_id']}")

    # Live provider preflight — fail fast before wasting 150+ calls
    provider_failures: dict[str, tuple[str, str]] = {}
    if not args.skip_preflight:
        print("\nProvider preflight checks:")
        provider_failures = preflight_providers(resolved)
        if provider_failures:
            failed_labels = [
                f"{e.get('alias', e['model_id'])} ({e['model_id']})"
                for e in resolved if e["model_id"] in provider_failures
            ]
            print(f"\n  ⚠️  {len(failed_labels)} model(s) failed preflight: {', '.join(failed_labels)}")
            if not fallback_entry:
                print(
                    "  Their prompts will be recorded as provider_unavailable (non-scorable).\n"
                    "  Use --fallback-model to reroute them."
                )

    # Get git SHA for methodology
    try:
        import subprocess
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_REPO_ROOT
        ).decode().strip()
    except Exception:
        git_sha = "unknown"

    all_results: dict[str, list[dict]] = {}
    for entry in resolved:
        model_id = entry["model_id"]
        alias = entry.get("alias", model_id)
        unavailable = model_id in provider_failures
        results = await run_model(
            entry,
            prompts,
            args.output,
            upload_snapshots=upload,
            fallback_entry=fallback_entry,
            provider_unavailable=unavailable,
            debug_parser=args.debug_parser,
        )
        all_results[alias] = results

    provider_reliability = compute_provider_reliability(all_results)
    write_methodology(
        args.output,
        resolved,
        len(prompts),
        git_sha,
        provider_reliability,
        fallback_entry,
    )

    # ── Summary table ─────────────────────────────────────────────────────
    print("\n── Citation Metrics (scorable runs only) ────────────────────────")
    print(
        f"{'Model':<26} {'Scored':>6} {'Gen%':>6} {'Parse%':>7} "
        f"{'Malformed%':>11} {'Exist%':>7} {'Support%':>9} {'Unsup%':>8}"
    )
    print("─" * 90)
    for alias, results in all_results.items():
        scorable = [r for r in results if r.get("scorable") and r.get("run_status") == "completed"]
        gen_rates = [r.get("citation_generation_rate", 0.0) for r in scorable]
        parse_rates = [r.get("citation_parse_rate", 0.0) for r in scorable]
        malformed_rates = [r.get("malformed_citation_rate", 0.0) for r in scorable]
        ex_rates = [r["existence_rate"] for r in scorable if r.get("existence_rate") is not None]
        sup_scores = [r["semantic_support_rate"] for r in scorable if r.get("semantic_support_rate") is not None]
        unsup_rates = [r["unsupported_authority_rate"] for r in scorable if r.get("unsupported_authority_rate") is not None]
        gen_mean = sum(gen_rates) / len(gen_rates) if gen_rates else None
        parse_mean = sum(parse_rates) / len(parse_rates) if parse_rates else None
        malformed_mean = sum(malformed_rates) / len(malformed_rates) if malformed_rates else None
        ex_mean = sum(ex_rates) / len(ex_rates) if ex_rates else None
        sup_mean = sum(sup_scores) / len(sup_scores) if sup_scores else None
        unsup_mean = sum(unsup_rates) / len(unsup_rates) if unsup_rates else None
        gen_str = f"{gen_mean:.0%}" if gen_mean is not None else "—"
        parse_str = f"{parse_mean:.0%}" if parse_mean is not None else "—"
        malformed_str = f"{malformed_mean:.0%}" if malformed_mean is not None else "—"
        ex_str = f"{ex_mean:.0%}" if ex_mean is not None else "—"
        sup_str = f"{sup_mean:.0%}" if sup_mean is not None else "—"
        unsup_str = f"{unsup_mean:.0%}" if unsup_mean is not None else "—"
        print(
            f"{alias:<26} {len(scorable):>6} {gen_str:>6} {parse_str:>7} "
            f"{malformed_str:>11} {ex_str:>7} {sup_str:>9} {unsup_str:>8}"
        )

    print_category_summary(all_results)

    print("\n── Provider Reliability ─────────────────────────────────────────")
    print(f"{'Provider':<15} {'Total':>6} {'OK':>6} {'Unavail':>8} {'RateLimit':>10} {'Avail%':>7}")
    print("─" * 55)
    for provider, stats in provider_reliability.items():
        billing_tag = " ⚠️ billing" if stats.get("billing_failure") else ""
        print(
            f"{provider:<15} {stats['total_prompts']:>6} {stats['completed']:>6} "
            f"{stats['provider_unavailable']:>8} {stats['rate_limited']:>10} "
            f"{stats['availability_rate']:>6.0%}{billing_tag}"
        )
    print()


if __name__ == "__main__":
    asyncio.run(main())
