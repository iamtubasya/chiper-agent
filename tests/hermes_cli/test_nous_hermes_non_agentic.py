"""Tests for the Nous-Chiper-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"chiper"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``chiper-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under the "chiper" tag namespace.

``is_nous_chiper_non_agentic`` should only match the actual Nous Research
Chiper-3 / Chiper-4 chat family.
"""

from __future__ import annotations

import pytest

from chiper_cli.model_switch import (
    _CHIPER_MODEL_WARNING,
    _check_chiper_model_warning,
    is_nous_chiper_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "NousResearch/Chiper-3-Llama-3.1-70B",
        "NousResearch/Chiper-3-Llama-3.1-405B",
        "chiper-3",
        "Chiper-3",
        "chiper-4",
        "chiper-4-405b",
        "chiper_4_70b",
        "openrouter/chiper3:70b",
        "openrouter/nousresearch/chiper-4-405b",
        "NousResearch/Chiper3",
        "chiper-3.1",
    ],
)
def test_matches_real_nous_chiper_chat_models(model_name: str) -> None:
    assert is_nous_chiper_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as Nous Chiper 3/4"
    )
    assert _check_chiper_model_warning(model_name) == _CHIPER_MODEL_WARNING


@pytest.mark.parametrize(
    "model_name",
    [
        # Kyle's local Modelfile — qwen3:14b under a custom tag
        "chiper-brain:qwen3-14b-ctx16k",
        "chiper-brain:qwen3-14b-ctx32k",
        "chiper-honcho:qwen3-8b-ctx8k",
        # Plain unrelated models
        "qwen3:14b",
        "qwen3-coder:30b",
        "qwen2.5:14b",
        "claude-opus-4-6",
        "anthropic/claude-sonnet-4.5",
        "gpt-5",
        "openai/gpt-4o",
        "google/gemini-2.5-flash",
        "deepseek-chat",
        # Non-chat Chiper models we don't warn about
        "chiper-llm-2",
        "chiper2-pro",
        "nous-chiper-2-mistral",
        # Edge cases
        "",
        "chiper",  # bare "chiper" isn't the 3/4 family
        "chiper-brain",
        "brain-chiper-3-impostor",  # "3" not preceded by /: boundary
    ],
)
def test_does_not_match_unrelated_models(model_name: str) -> None:
    assert not is_nous_chiper_non_agentic(model_name), (
        f"expected {model_name!r} NOT to be flagged as Nous Chiper 3/4"
    )
    assert _check_chiper_model_warning(model_name) == ""


def test_none_like_inputs_are_safe() -> None:
    assert is_nous_chiper_non_agentic("") is False
    # Defensive: the helper shouldn't crash on None-ish falsy input either.
    assert _check_chiper_model_warning("") == ""
