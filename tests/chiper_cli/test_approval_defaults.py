"""Contract tests for the shipped approvals defaults.

Policy (deliberate, see the DEFAULT_CONFIG comment in chiper_cli/config.py):
a fresh install must not block on a prompt nobody can answer.  Gateways,
containers and cron jobs run unattended, so "manual" there does not read as
"safety" — it reads as "the agent is broken".

The hardline floor is a separate, unconditional layer and is NOT weakened by
these defaults.  These tests pin both halves of that contract so a future edit
cannot quietly flip the default back (or, worse, make the floor bypassable).
"""

from __future__ import annotations

import importlib
import os

import pytest

from chiper_cli.config import DEFAULT_CONFIG


# ---------------------------------------------------------------------------
# Shipped template
# ---------------------------------------------------------------------------


def test_default_approval_mode_is_off():
    """A fresh install must not require a human to approve commands."""
    assert DEFAULT_CONFIG["approvals"]["mode"] == "off"


def test_default_cron_mode_is_approve():
    """Scheduled jobs run unattended — "deny" turns them into silent no-ops."""
    assert DEFAULT_CONFIG["approvals"]["cron_mode"] == "approve"


def test_confirmations_stay_on():
    """Interactive-only confirmations keep their safe default."""
    assert DEFAULT_CONFIG["approvals"]["mcp_reload_confirm"] is True
    assert DEFAULT_CONFIG["approvals"]["destructive_slash_confirm"] is True


# ---------------------------------------------------------------------------
# End-to-end: a real fresh CHIPER_HOME
# ---------------------------------------------------------------------------

CTX_VARS = (
    "CHIPER_INTERACTIVE",
    "CHIPER_GATEWAY_SESSION",
    "CHIPER_CRON_SESSION",
    "CHIPER_EXEC_ASK",
    "CHIPER_YOLO_MODE",
)

# Built from pieces so this file never contains a literal destructive command.
FLAGGED = "rm" + " -rf ./build"
HARDLINE = "shut" + "down -h now"
BENIGN = "git " + "status"


@pytest.fixture
def fresh_home(tmp_path, monkeypatch):
    """A brand-new CHIPER_HOME, plus a clean approval-context environment."""
    for var in CTX_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("CHIPER_HOME", str(tmp_path / ".chiper"))

    import chiper_cli.config as cfg_mod
    import tools.approval as approval_mod

    importlib.reload(cfg_mod)
    importlib.reload(approval_mod)
    cfg_mod.ensure_chiper_home()
    yield tmp_path
    importlib.reload(cfg_mod)
    importlib.reload(approval_mod)


def _guards(cmd: str, ctx: dict):
    """Run the guard exactly as terminal_tool does, in the requested context."""
    for var in CTX_VARS:
        os.environ.pop(var, None)
    os.environ.update(ctx)

    import tools.approval as approval_mod

    importlib.reload(approval_mod)
    return approval_mod.check_all_command_guards(cmd, env_type="local")


def test_fresh_install_writes_the_new_defaults(fresh_home):
    """The file written to disk carries the new policy, not just the dict."""
    from chiper_cli.config import load_config

    approvals = load_config().get("approvals", {})
    assert approvals.get("mode") == "off"
    assert approvals.get("cron_mode") == "approve"


@pytest.mark.parametrize(
    "label,ctx",
    [
        ("cli", {"CHIPER_INTERACTIVE": "1"}),
        ("gateway", {"CHIPER_GATEWAY_SESSION": "1"}),
        ("cron", {"CHIPER_CRON_SESSION": "1"}),
        ("non-interactive", {}),
    ],
)
def test_flagged_command_never_waits_for_a_human(fresh_home, label, ctx):
    """Every execution context auto-approves under the shipped default."""
    result = _guards(FLAGGED, ctx)
    assert result.get("approved") is True, f"{label} still blocked: {result}"


@pytest.mark.parametrize(
    "label,ctx",
    [
        ("cli", {"CHIPER_INTERACTIVE": "1"}),
        ("gateway", {"CHIPER_GATEWAY_SESSION": "1"}),
        ("cron", {"CHIPER_CRON_SESSION": "1"}),
    ],
)
def test_benign_command_runs(fresh_home, label, ctx):
    """Sanity: nothing prompts for a plainly safe command."""
    assert _guards(BENIGN, ctx).get("approved") is True


def test_hardline_still_refused_under_mode_off(fresh_home):
    """The unconditional floor must survive the new default."""
    import tools.approval as approval_mod

    for var in CTX_VARS:
        os.environ.pop(var, None)
    os.environ["CHIPER_INTERACTIVE"] = "1"
    importlib.reload(approval_mod)

    result = approval_mod.check_all_command_guards(HARDLINE, env_type="local")
    assert result.get("approved") is not True
    assert "hardline" in str(result.get("message", "")).lower()
