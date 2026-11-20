"""Regression test: the soul-picker inline button must evict the cached agent.

Root cause of "ganti jiwa tapi SOUL.md tidak berubah": the `soul:set:` callback
called `switch_soul()` (which does rewrite SOUL.md correctly) but never evicted
the session's cached AIAgent.  SOUL.md lives in the prompt-cached stable tier,
so the running agent kept serving the OLD persona until `/new` rebuilt it.
`/soul <id>` evicted; the button did not.

These tests pin the button path to the runner hook so the two paths cannot
drift apart again.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest


class _FakeQuery:
    def __init__(self, chat_id: int = 5974432705) -> None:
        self.data = ""
        self.message = SimpleNamespace(chat_id=chat_id, message_id=1)
        self.answers: List[str] = []
        self.edits: List[str] = []

    async def answer(self, text: str = "", **kwargs: Any) -> None:
        self.answers.append(text)

    async def edit_message_text(self, text: str = "", **kwargs: Any) -> None:
        self.edits.append(text)


def _build_adapter() -> Any:
    """Build a TelegramAdapter without running __init__ (no network/bot)."""
    from gateway.platforms.telegram import TelegramAdapter

    adapter = TelegramAdapter.__new__(TelegramAdapter)
    adapter._soul_picker_hooks = {}
    adapter._pending_soul_prompt = {}
    adapter.format_message = lambda text, **kw: text
    return adapter


def test_send_soul_picker_stores_hook_per_session(monkeypatch):
    """send_soul_picker must remember the caller's hook keyed by session."""
    adapter = _build_adapter()
    adapter._bot = object()  # non-None so the early return doesn't fire

    async def _fake_send(**kwargs):
        return SimpleNamespace(message_id=42)

    adapter._send_message_with_thread_fallback = _fake_send
    adapter._reply_to_message_id_for_send = lambda *a, **k: None
    adapter._thread_kwargs_for_send = lambda *a, **k: {}
    adapter._link_preview_kwargs = lambda: {}
    adapter._reply_to_mode = None
    adapter._build_soul_keyboard = lambda: object()

    calls: List[str] = []

    def hook(soul_id: str) -> None:
        calls.append(soul_id)

    res = asyncio.run(
        adapter.send_soul_picker(
            chat_id="5974432705",
            session_key="telegram:5974432705",
            on_soul_selected=hook,
        )
    )

    assert res.success is True
    assert adapter._soul_picker_hooks["telegram:5974432705"] is hook


def test_soul_set_callback_fires_hook_and_pops_it(monkeypatch):
    """Clicking a soul button must invoke the hook exactly once."""
    adapter = _build_adapter()

    # Pretend switch_soul succeeded (the file rewrite is covered elsewhere).
    monkeypatch.setattr(
        "agent.soul_manager.switch_soul",
        lambda soul_id: (True, "ok", {"id": soul_id, "name": "Chiper-Cyber", "icon": "\U0001f3ad", "desc": "d"}),
    )

    evicted: List[str] = []
    adapter._soul_picker_hooks["5974432705"] = lambda soul_id: evicted.append(soul_id)

    query = _FakeQuery(chat_id=5974432705)
    asyncio.run(adapter._handle_soul_callback(query, "soul:set:chiper-cyber"))

    assert evicted == ["chiper-cyber"], "cached agent was NOT evicted -> persona won't change"
    assert "5974432705" not in adapter._soul_picker_hooks, "hook must be consumed (one-shot)"


def test_soul_set_callback_without_hook_still_succeeds(monkeypatch):
    """A picker rendered by an older path (no hook) must not crash."""
    adapter = _build_adapter()
    monkeypatch.setattr(
        "agent.soul_manager.switch_soul",
        lambda soul_id: (True, "ok", {"id": soul_id, "name": "X", "icon": "*", "desc": "d"}),
    )

    query = _FakeQuery()
    asyncio.run(adapter._handle_soul_callback(query, "soul:set:chiper-dev"))

    assert any("didi" not in a for a in query.answers)  # answered, no exception


def test_runner_hook_evicts_cached_agent():
    """_soul_selected_hook must route into the runner's eviction."""
    from gateway.slash_commands import GatewaySlashCommandsMixin

    evicted: List[str] = []

    class _FakeRunner(GatewaySlashCommandsMixin):
        def _evict_cached_agent(self, session_key: str) -> None:
            evicted.append(session_key)

    runner = _FakeRunner()
    hook = runner._soul_selected_hook("telegram:123")
    hook("chiper-cyber")

    assert evicted == ["telegram:123"]


def test_runner_hook_is_noop_for_empty_session_key():
    """An unknown session key must not evict anything (or raise)."""
    from gateway.slash_commands import GatewaySlashCommandsMixin

    evicted: List[str] = []

    class _FakeRunner(GatewaySlashCommandsMixin):
        def _evict_cached_agent(self, session_key: str) -> None:
            evicted.append(session_key)

    GatewaySlashCommandsMixin._soul_selected_hook(_FakeRunner(), "")("chiper-cyber")
    assert evicted == []
