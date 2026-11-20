"""Regression test: the soul-picker inline button must evict the cached agent.

Root cause of "ganti jiwa tapi SOUL.md tidak berubah": the `soul:set:` callback
called `switch_soul()` (which rewrites SOUL.md correctly) but never evicted the
session's cached AIAgent.  SOUL.md lives in the prompt-cached stable tier, so
the running agent kept serving the OLD persona until `/new` rebuilt it.
`/soul <id>` evicted; the button did not.

A second bug hid inside the first fix: the hook was stored under `session_key`
(`agent:main:telegram:dm:123`) but looked up with `chat_id` (`123`), so it never
matched.  The earlier version of this file missed that because it stored and
read the dict in two separate tests, each with its own key — the set/click pair
was never exercised end to end.  `test_picker_then_click_evicts_real_session`
below closes that hole and is the one that must fail if the keying regresses.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, List

import pytest

# Deliberately different strings: a callback query carries only the chat_id,
# while the agent cache is keyed by the full session key.
CHAT_ID = "5974432705"
SESSION_KEY = "agent:main:telegram:dm:5974432705"


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


def _stub_sending(adapter: Any) -> None:
    """Neutralise everything send_soul_picker touches besides the hook dict."""

    async def _fake_send(**kwargs):
        return SimpleNamespace(message_id=42)

    adapter._bot = object()  # non-None so the early return doesn't fire
    adapter._send_message_with_thread_fallback = _fake_send
    adapter._reply_to_message_id_for_send = lambda *a, **k: None
    adapter._thread_kwargs_for_send = lambda *a, **k: {}
    adapter._link_preview_kwargs = lambda: {}
    adapter._reply_to_mode = None
    adapter._build_soul_keyboard = lambda: object()


def _render_picker(adapter: Any, hook: Any) -> Any:
    return asyncio.run(
        adapter.send_soul_picker(
            chat_id=CHAT_ID,
            session_key=SESSION_KEY,
            on_soul_selected=hook,
        )
    )


def _stub_switch_soul(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent.soul_manager.switch_soul",
        lambda soul_id: (
            True,
            "ok",
            {"id": soul_id, "name": "Chiper-Cyber", "icon": "\U0001f3ad", "desc": "d"},
        ),
    )


# ---------------------------------------------------------------------------
# The end-to-end pair: render the picker, then click a button.
# ---------------------------------------------------------------------------


def test_picker_then_click_evicts_real_session(monkeypatch):
    """Render + click must evict the *session key*, not the chat id."""
    adapter = _build_adapter()
    _stub_sending(adapter)
    _stub_switch_soul(monkeypatch)

    evicted: List[str] = []
    hook = lambda session_key, soul_id: evicted.append(session_key)  # noqa: E731

    assert _render_picker(adapter, hook).success is True

    query = _FakeQuery(chat_id=int(CHAT_ID))
    asyncio.run(adapter._handle_soul_callback(query, "soul:set:chiper-cyber"))

    assert evicted == [SESSION_KEY], (
        "clicking the soul button did not evict the cached agent for its real "
        "session — the persona will stay stale until /new"
    )


def test_picker_hook_is_keyed_by_chat_id(monkeypatch):
    """The stored key must be the one a callback query can actually produce."""
    adapter = _build_adapter()
    _stub_sending(adapter)

    _render_picker(adapter, lambda *a: None)

    assert CHAT_ID in adapter._soul_picker_hooks
    assert SESSION_KEY not in adapter._soul_picker_hooks, (
        "hook stored under session_key is unreachable from a callback query"
    )
    stored_session_key, _hook = adapter._soul_picker_hooks[CHAT_ID]
    assert stored_session_key == SESSION_KEY


def test_click_consumes_the_hook_once(monkeypatch):
    """A second click must not fire the stale hook again."""
    adapter = _build_adapter()
    _stub_sending(adapter)
    _stub_switch_soul(monkeypatch)

    calls: List[str] = []
    _render_picker(adapter, lambda session_key, soul_id: calls.append(soul_id))

    query = _FakeQuery(chat_id=int(CHAT_ID))
    asyncio.run(adapter._handle_soul_callback(query, "soul:set:chiper-cyber"))
    asyncio.run(adapter._handle_soul_callback(query, "soul:set:chiper-dev"))

    assert calls == ["chiper-cyber"], "hook must be one-shot"
    assert adapter._soul_picker_hooks == {}


def test_click_from_unregistered_chat_does_not_evict(monkeypatch):
    """A picker from another chat must not evict this one's agent."""
    adapter = _build_adapter()
    _stub_sending(adapter)
    _stub_switch_soul(monkeypatch)

    evicted: List[str] = []
    _render_picker(adapter, lambda session_key, soul_id: evicted.append(session_key))

    other = _FakeQuery(chat_id=111222333)
    asyncio.run(adapter._handle_soul_callback(other, "soul:set:chiper-cyber"))

    assert evicted == [], "cross-chat click evicted the wrong session"


def test_click_without_hook_still_switches(monkeypatch):
    """A picker rendered by an older path (no hook) must not crash."""
    adapter = _build_adapter()
    _stub_switch_soul(monkeypatch)

    query = _FakeQuery()
    asyncio.run(adapter._handle_soul_callback(query, "soul:set:chiper-dev"))

    assert query.answers, "callback was not acknowledged"


# ---------------------------------------------------------------------------
# The runner side of the hook.
# ---------------------------------------------------------------------------


class _FakeRunner:
    def __init__(self) -> None:
        self.evicted: List[str] = []

    def _evict_cached_agent(self, session_key: str) -> None:
        self.evicted.append(session_key)


def _runner_hook(monkeypatch, captured_session_key: str):
    """Bind GatewaySlashCommandsMixin._soul_selected_hook to a fake runner."""
    from gateway.slash_commands import GatewaySlashCommandsMixin

    runner = _FakeRunner()
    monkeypatch.setattr("gateway.slash_commands.logger", SimpleNamespace(
        warning=lambda *a, **k: None
    ), raising=False)
    hook = GatewaySlashCommandsMixin._soul_selected_hook(runner, captured_session_key)
    return runner, hook


def test_runner_hook_evicts_captured_session(monkeypatch):
    runner, hook = _runner_hook(monkeypatch, SESSION_KEY)
    hook(SESSION_KEY, "chiper-cyber")
    assert runner.evicted == [SESSION_KEY]


def test_runner_hook_prefers_the_key_the_adapter_passes(monkeypatch):
    """The adapter's key is authoritative — the closure's is a fallback."""
    runner, hook = _runner_hook(monkeypatch, "stale:session")
    hook(SESSION_KEY, "chiper-cyber")
    assert runner.evicted == [SESSION_KEY], (
        "hook ignored the session key the adapter passed back"
    )


def test_runner_hook_is_noop_for_empty_session_key(monkeypatch):
    runner, hook = _runner_hook(monkeypatch, "")
    hook("", "chiper-cyber")
    assert runner.evicted == []
