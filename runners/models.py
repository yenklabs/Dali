"""Low-level model call layer for the benchmark runner.

This module provides:
  - MODELS: raw provider model ID registry (used by call_model + model_registry.py)
  - classify_model_error: converts SDK exceptions to (run_status, failure_reason)
  - call_model: dispatches to the right provider SDK
  - assert_provider_ready: preflight ping before a full run

For alias-based model selection (openai_fast, anthropic_fast, etc.)
see runners/model_registry.py. The registry sits on top of this module
and resolves aliases → model_id before call_model() is invoked.

Provider support:
  anthropic — requires ANTHROPIC_API_KEY
  openai    — requires OPENAI_API_KEY
  google    — planned (v1); requires GOOGLE_API_KEY + google-generativeai

Do not change existing MODELS entries after a run has been committed.
Add a new entry with a new versioned ID instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ── Error classification ──────────────────────────────────────────────────────

# Non-retryable: the provider is structurally unavailable for this model/account.
# Retrying 150+ prompts against these will never succeed.
NON_RETRYABLE_PROVIDER_ERRORS: list[str] = [
    "credit balance is too low",
    "insufficient_quota",
    "billing_hard_limit",
    "billing",
    "payment required",
    "payment_required",
    "account suspended",
    "account has been disabled",
    "account deactivated",
    "model not found",
    "does not exist",
    "unknown model",
    "no such model",
    "invalid model",
    "model_not_found",
    "invalid x-api-key",
    "invalid api key",
    "authentication",
    "unauthorized",
]

# Retryable: transient throttle or timeout — may succeed on retry.
RETRYABLE_PROVIDER_ERRORS: list[str] = [
    "rate limit",
    "rate_limit_error",
    "too many requests",
    "429",
    "timeout",
    "timed out",
    "temporarily unavailable",
    "overloaded",
    "529",
    "503",
    "502",
]


def classify_model_error(error: str) -> tuple[str, str]:
    """Classify a model call exception into (run_status, failure_reason).

    Returns:
      ("provider_unavailable", "billing")        credit/payment/quota issue
      ("provider_unavailable", "invalid_model")  model ID rejected by provider
      ("provider_unavailable", "auth_error")     bad or missing API key
      ("provider_unavailable", "account_issue")  account suspended/disabled
      ("rate_limited",         "rate_limit")      429 / transient throttle
      ("api_error",            "api_error")       unexpected API failure
    """
    text = error.lower()

    # Billing / quota — always non-retryable
    if any(e in text for e in [
        "credit balance is too low", "insufficient_quota",
        "billing", "payment required", "payment_required",
    ]):
        return "provider_unavailable", "billing"

    # Account issues
    if any(e in text for e in [
        "account suspended", "account has been disabled", "account deactivated",
    ]):
        return "provider_unavailable", "account_issue"

    # Auth errors
    if any(e in text for e in [
        "invalid x-api-key", "invalid api key", "incorrect api key",
        "incorrect_api_key", "authentication", "unauthorized",
        "you didn't provide an api key", "no api key provided",
    ]):
        return "provider_unavailable", "auth_error"

    # Invalid / unknown model name — non-retryable
    if any(e in text for e in [
        "model not found", "does not exist", "unknown model",
        "no such model", "invalid model", "model_not_found",
    ]):
        return "provider_unavailable", "invalid_model"

    # Rate limiting — retryable
    if any(e in text for e in RETRYABLE_PROVIDER_ERRORS):
        return "rate_limited", "rate_limit"

    return "api_error", "api_error"


# ── Model registry ────────────────────────────────────────────────────────────
# Verified current model IDs as of 2026-05.
# Category labels match the recommended benchmark matrix.

MODELS: dict[str, dict[str, Any]] = {
    # ── Anthropic ──────────────────────────────────────────────────────────
    "claude-3-5-haiku-20241022": {
        "provider": "anthropic",
        "category": "cheap_scale",
        "params": {"temperature": 0.0, "max_tokens": 1024},
    },
    "claude-3-5-sonnet-20241022": {
        "provider": "anthropic",
        "category": "production_baseline",
        "params": {"temperature": 0.0, "max_tokens": 1024},
    },
    # ── OpenAI ─────────────────────────────────────────────────────────────
    "gpt-4o-mini-2024-07-18": {
        "provider": "openai",
        "category": "cheap_scale",
        "params": {"temperature": 0.0, "max_tokens": 1024},
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "category": "cheap_scale",
        "params": {"temperature": 0.0, "max_tokens": 1024},
    },
    "gpt-4.1": {
        "provider": "openai",
        "category": "frontier_reasoning",
        "params": {"temperature": 0.0, "max_tokens": 1024},
    },
    "gpt-4o": {
        "provider": "openai",
        "category": "production_baseline",
        "params": {"temperature": 0.0, "max_tokens": 1024},
    },
}

# Default smoke-test set — use pinned aliases where possible
DEFAULT_SMOKE_MODELS = ["openai_fast"]

_BENCHMARK_SYSTEM_PROMPT = (
    "You are a legal research assistant. When asked about cases, statutes, "
    "or academic papers, provide accurate citations including full case names, "
    "reporters, page numbers, years, and URLs where available. "
    "If you are not confident about a citation, say so rather than guessing."
)


@dataclass
class ModelCallResult:
    """Normalized model call output with provider metadata."""

    output: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    finish_reason: str | None
    provider_finish_reason: str | None


def _normalize_finish_reason(provider: str, raw_reason: str | None) -> str | None:
    """Map provider-native finish reasons into benchmark-friendly labels."""
    if raw_reason is None:
        return None

    if provider == "anthropic":
        mapping = {
            "end_turn": "stop",
            "max_tokens": "length",
            "stop_sequence": "stop",
            "tool_use": "tool_calls",
            "refusal": "refusal",
            "pause_turn": "tool_calls",
        }
        return mapping.get(raw_reason, raw_reason)

    return raw_reason


def call_model_result(model_id: str, prompt: str, *, max_tokens: int | None = None) -> ModelCallResult:
    """Call a model and return text + usage metadata."""
    spec = MODELS.get(model_id)
    if spec is None:
        raise ValueError(f"Unknown model: {model_id!r}. Add it to MODELS in models.py.")

    provider = spec["provider"]
    params = dict(spec["params"])
    if max_tokens is not None:
        params["max_tokens"] = max_tokens

    if provider == "anthropic":
        import os
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model=model_id,
            system=[
                {
                    "type": "text",
                    "text": _BENCHMARK_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
            **params,
        )
        text_blocks = [
            block.text for block in response.content
            if getattr(block, "type", "") == "text" and getattr(block, "text", None)
        ]
        output = "\n".join(text_blocks).strip()

        input_tokens = getattr(getattr(response, "usage", None), "input_tokens", None)
        output_tokens = getattr(getattr(response, "usage", None), "output_tokens", None)
        total_tokens = None
        if input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens

        provider_finish_reason = getattr(response, "stop_reason", None)
        return ModelCallResult(
            output=output,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=total_tokens,
            finish_reason=_normalize_finish_reason(provider, provider_finish_reason),
            provider_finish_reason=provider_finish_reason,
        )

    if provider == "openai":
        import os
        import openai

        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": _BENCHMARK_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            **params,
        )
        output = response.choices[0].message.content or ""
        provider_finish_reason = response.choices[0].finish_reason
        usage = response.usage
        return ModelCallResult(
            output=output,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            finish_reason=_normalize_finish_reason(provider, provider_finish_reason),
            provider_finish_reason=provider_finish_reason,
        )

    raise ValueError(
        f"No call_model handler for provider {provider!r}. "
        f"Wire it in runners/models.py."
    )


def call_model(model_id: str, prompt: str, *, max_tokens: int | None = None) -> str:
    """Call a model and return its raw text output.

    Args:
        model_id:   Must be a key in MODELS.
        prompt:     User-facing prompt text.
        max_tokens: Override the registry default (useful for preflight pings).

    Raises:
        ValueError:  Unknown model_id or provider.
        Exception:   SDK-level API errors — callers classify with classify_model_error().
    """
    return call_model_result(model_id, prompt, max_tokens=max_tokens).output


def assert_provider_ready(model_id: str) -> None:
    """Preflight check: send a minimal prompt to confirm the model is reachable.

    Raises RuntimeError with a structured reason if the provider is unavailable.
    Silently returns on success.
    """
    try:
        call_model(model_id, "Return OK.", max_tokens=5)
    except ValueError:
        raise  # unknown model / provider — propagate as-is
    except Exception as exc:
        run_status, failure_reason = classify_model_error(str(exc))
        raise RuntimeError(
            f"Provider preflight failed for {model_id!r}: "
            f"status={run_status} reason={failure_reason} — {exc}"
        ) from exc
