"""Dali model registry — provider-agnostic aliases for benchmark runs.

Aliases decouple benchmark CLI invocations from raw provider model IDs.
A pinned alias resolves to a specific versioned model ID, ensuring runs
are reproducible across time without editing run commands.

Usage in CLI:
    # Alias (resolves to pinned model ID)
    python runners/run_synthetic.py --models openai_fast

    # Raw model ID still works
    python runners/run_synthetic.py --models gpt-4o-mini-2024-07-18

Alias resolution:
    openai_fast  →  gpt-4o-mini-2024-07-18  (pinned, recommended for public benchmarks)

Public benchmark policy:
    Use pinned=True aliases for any run committed to results/.
    Non-pinned aliases ("latest" variants) are for development only.
    Fallback results (fallback_used=True) are excluded from leaderboard aggregates.
"""

from __future__ import annotations

from typing import Any

# ── Registry ──────────────────────────────────────────────────────────────────
# Each alias maps to one concrete model configuration.
#
# Fields:
#   provider                      API provider (openai, anthropic, google)
#   model_id                      Exact provider model ID for API calls
#   display_name                  Human-readable label for reports
#   benchmark_role                Semantic role in the comparison matrix
#   pinned                        True = stable versioned ID; False = latest/alias
#   recommended_for_public_benchmark  Should appear in canonical leaderboard outputs
#   notes                         Optional implementation notes

MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    # ── OpenAI ─────────────────────────────────────────────────────────────
    "openai_fast": {
        "provider": "openai",
        "model_id": "gpt-4o-mini-2024-07-18",
        "display_name": "GPT-4o mini",
        "benchmark_role": "cheap_scale_baseline",
        "pinned": True,
        "recommended_for_public_benchmark": True,
        "notes": "Pinned to 2024-07-18 for reproducibility. Preferred for public runs.",
    },
    "openai_fast_latest": {
        "provider": "openai",
        "model_id": "gpt-4o-mini",
        "display_name": "GPT-4o mini (latest)",
        "benchmark_role": "cheap_scale_latest",
        "pinned": False,
        "recommended_for_public_benchmark": False,
        "notes": "Resolves to latest gpt-4o-mini. Use openai_fast for public runs.",
    },
    "openai_quality": {
        "provider": "openai",
        "model_id": "gpt-4.1",
        "display_name": "GPT-4.1",
        "benchmark_role": "frontier_quality_baseline",
        "pinned": False,
        "recommended_for_public_benchmark": True,
        "notes": "Frontier quality OpenAI model.",
    },
    "openai_production": {
        "provider": "openai",
        "model_id": "gpt-4o",
        "display_name": "GPT-4o",
        "benchmark_role": "production_baseline",
        "pinned": False,
        "recommended_for_public_benchmark": True,
    },
    # ── Anthropic ──────────────────────────────────────────────────────────
    "anthropic_fast": {
        "provider": "anthropic",
        "model_id": "claude-3-5-haiku-20241022",
        "display_name": "Claude 3.5 Haiku",
        "benchmark_role": "cross_vendor_fast_baseline",
        "pinned": True,
        "recommended_for_public_benchmark": True,
        "notes": (
            "Pinned to claude-3-5-haiku-20241022 — verified available. "
            "The ID 'claude-haiku-4-5-20251001' is invalid and returns 400."
        ),
    },
    "anthropic_production": {
        "provider": "anthropic",
        "model_id": "claude-3-5-sonnet-20241022",
        "display_name": "Claude 3.5 Sonnet",
        "benchmark_role": "cross_vendor_production_baseline",
        "pinned": True,
        "recommended_for_public_benchmark": True,
    },
    # ── Google ─────────────────────────────────────────────────────────────
    "gemini_quality": {
        "provider": "google",
        "model_id": "gemini-2.5-pro",
        "display_name": "Gemini 2.5 Pro",
        "benchmark_role": "cross_vendor_quality_baseline",
        "pinned": False,
        "recommended_for_public_benchmark": True,
        "notes": (
            "Google provider not yet wired in call_model(). "
            "Requires GOOGLE_API_KEY and google-generativeai SDK. Planned for v1."
        ),
    },
}

# ── Default run sets ──────────────────────────────────────────────────────────

# Minimum viable single-model run for smoke tests and dev validation
DEFAULT_DEV_MODELS: list[str] = ["openai_fast"]

# Full public comparison set (use when all providers have valid keys + billing)
DEFAULT_PUBLIC_MODELS: list[str] = [
    "openai_fast",
    "openai_quality",
    "anthropic_fast",
]


# ── Resolution helpers ────────────────────────────────────────────────────────

def resolve_model(alias_or_id: str) -> dict[str, Any]:
    """Resolve an alias or raw model ID to a full registry entry.

    Alias lookup is tried first. If not found, a synthetic entry is built
    from the raw model ID using the MODELS dict in models.py.

    Returns a dict with at minimum:
        provider, model_id, display_name, benchmark_role,
        pinned, recommended_for_public_benchmark, alias

    Raises ValueError if the alias or ID is not recognised.
    """
    # 1. Check registry aliases
    if alias_or_id in MODEL_REGISTRY:
        entry = dict(MODEL_REGISTRY[alias_or_id])
        entry["alias"] = alias_or_id
        return entry

    # 2. Fall through to raw model IDs registered in models.py
    from runners.models import MODELS
    if alias_or_id in MODELS:
        spec = MODELS[alias_or_id]
        return {
            "provider": spec["provider"],
            "model_id": alias_or_id,
            "display_name": alias_or_id,
            "benchmark_role": spec.get("category", "unspecified"),
            "pinned": False,
            "recommended_for_public_benchmark": False,
            "alias": alias_or_id,
            "notes": "Raw model ID (not a registry alias). Not pinned.",
        }

    raise ValueError(
        f"Unknown model alias or ID: {alias_or_id!r}.\n"
        f"Registry aliases: {list(MODEL_REGISTRY)}\n"
        f"Use 'python runners/run_synthetic.py --list-models' to see all options."
    )


def list_models() -> list[dict[str, Any]]:
    """Return all registry entries sorted by provider and role."""
    from runners.models import MODELS
    rows = []
    for alias, entry in MODEL_REGISTRY.items():
        rows.append({
            "alias": alias,
            **entry,
        })
    # Also list raw model IDs not covered by an alias
    alias_model_ids = {e["model_id"] for e in MODEL_REGISTRY.values()}
    for mid, spec in MODELS.items():
        if mid not in alias_model_ids:
            rows.append({
                "alias": mid,
                "provider": spec["provider"],
                "model_id": mid,
                "display_name": mid,
                "benchmark_role": spec.get("category", "unspecified"),
                "pinned": False,
                "recommended_for_public_benchmark": False,
            })
    return rows
