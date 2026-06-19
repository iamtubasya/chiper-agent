"""``chiper env`` command handler.

Interactive .env file manager for Chiper Agent.
Supports: show, list, get, set, unset, edit, sections, wizard, check.
"""

from __future__ import annotations

import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Optional


# ─── Section definitions ─────────────────────────────────────────────────────
# Each section: (display_name, description, [(var_name, description, required)])
ENV_SECTIONS = [
    (
        "llm",
        "LLM Provider API Keys",
        [
            ("OPENROUTER_API_KEY", "OpenRouter API key (openrouter.ai/keys)", True),
            ("XIAOMI_API_KEY", "Xiaomi/MiMo API key", False),
            ("NOVITA_API_KEY", "NovitaAI API key (novita.ai)", False),
            ("GOOGLE_API_KEY", "Google AI Studio / Gemini key", False),
            ("GEMINI_API_KEY", "Gemini API key (alias for GOOGLE_API_KEY)", False),
            ("OLLAMA_API_KEY", "Ollama Cloud API key", False),
            ("GLM_API_KEY", "z.ai / ZhipuAI GLM key", False),
            ("KIMI_API_KEY", "Kimi / Moonshot API key", False),
            ("ARCEEAI_API_KEY", "Arcee AI key", False),
            ("MINIMAX_API_KEY", "MiniMax API key", False),
        ],
    ),
    (
        "telegram",
        "Telegram Gateway",
        [
            ("TELEGRAM_BOT_TOKEN", "Telegram bot token from @BotFather", True),
            ("TELEGRAM_ALLOWED_USERS", "Comma-separated Telegram user IDs", True),
            ("TELEGRAM_HOME_CHANNEL", "Default chat ID for delivery", True),
            ("TELEGRAM_HOME_CHANNEL_THREAD_ID", "Topic/thread ID (optional)", False),
        ],
    ),
    (
        "gateway",
        "Gateway & Platform",
        [
            ("TERMINAL_ENV", "Terminal environment (local/docker)", False),
        ],
    ),
    (
        "twitter",
        "X/Twitter Integration",
        [
            ("TWITTER_USER", "Twitter/X username", False),
            ("TWITTER_PASS", "Twitter/X password", False),
        ],
    ),
    (
        "email",
        "Email Integration",
        [
            ("GMAIL_USER", "Gmail address", False),
            ("GMAIL_PASS", "Gmail app password", False),
        ],
    ),
    (
        "rpc",
        "RPC Endpoints (Crypto)",
        [
            ("RPC_EVM_ETHEREUM", "Ethereum RPC URL", False),
            ("RPC_EVM_BASE", "Base RPC URL", False),
            ("RPC_SOLANA", "Solana RPC URL", False),
            ("RPC_ETH", "ETH RPC (alias)", False),
            ("RPC_BASE", "Base RPC (alias)", False),
            ("RPC_POLYGON", "Polygon RPC URL", False),
            ("RPC_ARB", "Arbitrum RPC URL", False),
            ("RPC_OP", "Optimism RPC URL", False),
            ("RPC_ZORA", "Zora RPC URL", False),
        ],
    ),
    (
        "governor",
        "Spend Governor (Crypto Safety)",
        [
            ("HERMES_MAX_TX_USD", "Max single transaction USD", False),
            ("HERMES_DAILY_CAP_USD", "Daily spending cap USD", False),
            ("HERMES_SESSION_CAP_USD", "Per-session spending cap USD", False),
            ("HERMES_MAX_SLIPPAGE_PCT", "Max slippage %", False),
            ("HERMES_MAX_GAS_MULTIPLE", "Max gas multiple", False),
            ("HERMES_MAX_TX_PER_MIN", "Max transactions per minute", False),
            ("HERMES_REQUIRE_SIM", "Require simulation (1=yes)", False),
        ],
    ),
    (
        "paths",
        "Paths & Models",
        [
            ("HERMES_GOVERNOR_DB", "Governor database path", False),
            ("HERMES_MEMORY_DB", "Memory database path", False),
            ("HERMES_MODELS_DB", "Models database path", False),
            ("HERMES_BROWSER_PROFILE", "Browser profile path", False),
            ("HERMES_WHISPER_MODEL", "Whisper model size", False),
        ],
    ),
]


def _get_env_path() -> Path:
    """Get the .env file path."""
    chiper_home = os.environ.get("CHIPER_HOME", os.path.expanduser("~/.chiperflux"))
    return Path(chiper_home) / ".env"


def _read_env(path: Path) -> list[str]:
    """Read .env file lines."""
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _write_env(path: Path, lines: list[str]) -> None:
    """Write .env file."""
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_env(lines: list[str]) -> dict[str, str]:
    """Parse active (uncommented) KEY=VALUE pairs."""
    result = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Remove inline comments
            if "  #" in value:
                value = value[: value.index("  #")].strip()
            result[key] = value
    return result


def _mask_value(key: str, value: str) -> str:
    """Mask sensitive values."""
    sensitive_suffixes = ("_KEY", "_TOKEN", "_SECRET", "_PASS", "_PASSWORD")
    if any(key.endswith(s) for s in sensitive_suffixes):
        if len(value) <= 8:
            return "***"
        return value[:4] + "***" + value[-4:]
    return value


def _find_var_line(lines: list[str], key: str) -> Optional[int]:
    """Find the line index of a var (active or commented)."""
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Active: KEY=...
        if stripped.startswith(f"{key}="):
            return i
        # Commented: # KEY=... or #KEY=...
        if stripped.startswith(f"# {key}=") or stripped.startswith(f"#{key}="):
            return i
    return None


def _get_section_for_key(key: str) -> Optional[str]:
    """Get the section name for a given key."""
    for section_name, _, vars_list in ENV_SECTIONS:
        for var_name, _, _ in vars_list:
            if var_name == key:
                return section_name
    return None


def _color(text: str, code: str) -> str:
    """ANSI color wrapper."""
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def _green(text: str) -> str:
    return _color(text, "32")


def _red(text: str) -> str:
    return _color(text, "31")


def _yellow(text: str) -> str:
    return _color(text, "33")

def _cyan(text: str) -> str:
    return _color(text, "36")

def _bold(text: str) -> str:
    return _color(text, "1")


# ─── Commands ────────────────────────────────────────────────────────────────


def cmd_env_show(_args) -> None:
    """Show all env vars with secrets masked."""
    path = _get_env_path()
    if not path.exists():
        print(_red(f"❌ .env not found: {path}"))
        print(f"   Run {_cyan('chiper env wizard')} to create one")
        return

    lines = _read_env(path)
    env = _parse_env(lines)

    if not env:
        print(_yellow("⚠️  No active env vars found"))
        return

    print(_bold(f"📋 Environment Variables ({len(env)} active)\n"))

    # Group by section
    section_vars: dict[str, list[tuple[str, str]]] = {}
    other_vars = []

    for key, value in sorted(env.items()):
        section = _get_section_for_key(key)
        if section:
            section_vars.setdefault(section, []).append((key, value))
        else:
            other_vars.append((key, value))

    for section_name, desc, _ in ENV_SECTIONS:
        if section_name in section_vars:
            print(_bold(f"── {desc} ──"))
            for key, value in section_vars[section_name]:
                masked = _mask_value(key, value)
                print(f"  {_green(key)}={masked}")
            print()

    if other_vars:
        print(_bold("── Other ──"))
        for key, value in other_vars:
            masked = _mask_value(key, value)
            print(f"  {_green(key)}={masked}")
        print()


def cmd_env_list(_args) -> None:
    """List all env var names."""
    path = _get_env_path()
    if not path.exists():
        print(_red(f"❌ .env not found: {path}"))
        return

    env = _parse_env(_read_env(path))
    for key in sorted(env.keys()):
        print(key)
    print(f"\nTotal: {len(env)} vars")


def cmd_env_get(args) -> None:
    """Get value of a specific env var."""
    path = _get_env_path()
    if not path.exists():
        print(_red(f"❌ .env not found: {path}"))
        return

    env = _parse_env(_read_env(path))
    key = args.key.upper()

    if key in env:
        value = env[key]
        masked = _mask_value(key, value)
        print(f"{key}={masked}")
    else:
        print(_red(f"❌ {key} not found in .env"))


def cmd_env_set(args) -> None:
    """Set an env var value."""
    path = _get_env_path()
    if not path.exists():
        print(_red(f"❌ .env not found: {path}"))
        print(f"   Run {_cyan('chiper env wizard')} to create one")
        return

    key = args.key.upper()
    value = args.value

    lines = _read_env(path)
    idx = _find_var_line(lines, key)

    new_line = f"{key}={value}"

    if idx is not None:
        old_line = lines[idx].strip()
        if old_line.startswith("#"):
            # Uncomment and set
            lines[idx] = new_line
            print(_green(f"✅ Enabled: {key}"))
        else:
            # Update
            lines[idx] = new_line
            print(_green(f"✅ Updated: {key}"))
    else:
        # Add new - find the right section
        section = _get_section_for_key(key)
        if section:
            # Find the section header and add after last var in section
            inserted = False
            in_section = False
            for i, line in enumerate(lines):
                if line.strip().startswith("# ===") and section.upper() in line.upper():
                    in_section = True
                    continue
                if in_section and line.strip().startswith("# ==="):
                    # End of section, insert before this
                    lines.insert(i, new_line)
                    inserted = True
                    break
            if not inserted:
                # Fallback: append at end
                lines.append(new_line)
        else:
            lines.append(new_line)
        print(_green(f"✅ Added: {key}"))

    _write_env(path, lines)
    print(f"   {_cyan(str(path))}")


def cmd_env_unset(args) -> None:
    """Remove (comment out) an env var."""
    path = _get_env_path()
    if not path.exists():
        print(_red(f"❌ .env not found: {path}"))
        return

    key = args.key.upper()
    lines = _read_env(path)
    idx = _find_var_line(lines, key)

    if idx is not None:
        old_line = lines[idx]
        if not old_line.strip().startswith("#"):
            lines[idx] = f"# {old_line}"
            _write_env(path, lines)
            print(_yellow(f"⚠️  Commented out: {key}"))
        else:
            print(_yellow(f"⚠️  Already commented: {key}"))
    else:
        print(_red(f"❌ {key} not found in .env"))


def cmd_env_edit(_args) -> None:
    """Open .env in editor."""
    path = _get_env_path()
    if not path.exists():
        print(_red(f"❌ .env not found: {path}"))
        return

    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))
    print(f"📝 Opening .env in {editor}...")
    subprocess.run([editor, str(path)])


def cmd_env_sections(_args) -> None:
    """List all config sections."""
    print(_bold("📂 Configuration Sections\n"))
    for name, desc, vars_list in ENV_SECTIONS:
        required = sum(1 for _, _, req in vars_list if req)
        total = len(vars_list)
        req_str = f" ({required} required)" if required else ""
        print(f"  {_cyan(name):20s} {desc} — {total} vars{req_str}")
    print(f"\nUse: {_cyan('chiper env section <name>')}")


def cmd_env_section(args) -> None:
    """Show vars in a specific section."""
    name = args.name.lower()
    found = False

    for section_name, desc, vars_list in ENV_SECTIONS:
        if section_name == name:
            found = True
            path = _get_env_path()
            env = _parse_env(_read_env(path)) if path.exists() else {}

            print(_bold(f"📂 {desc}\n"))
            for var_name, var_desc, required in vars_list:
                status = ""
                if var_name in env:
                    val = env[var_name]
                    if val:
                        status = _green("✅ set")
                    else:
                        status = _yellow("⚠️  empty")
                else:
                    if required:
                        status = _red("❌ missing (required)")
                    else:
                        status = "⬜ not set"

                req_tag = " *" if required else ""
                print(f"  {_cyan(var_name)}{req_tag}")
                print(f"    {var_desc}")
                print(f"    Status: {status}")
                print()
            break

    if not found:
        print(_red(f"❌ Section '{name}' not found"))
        print(f"   Run {_cyan('chiper env sections')} to see available sections")


def cmd_env_wizard(_args) -> None:
    """Interactive setup wizard for .env."""
    path = _get_env_path()

    print(_bold("🧙 Chiper .env Setup Wizard\n"))
    print("Press Enter to skip, Ctrl+C to quit\n")

    # Read existing
    lines = _read_env(path) if path.exists() else []
    env = _parse_env(lines)

    changes = 0

    for section_name, desc, vars_list in ENV_SECTIONS:
        print(_bold(f"\n── {desc} ──"))
        for var_name, var_desc, required in vars_list:
            current = env.get(var_name, "")
            req_tag = " (required)" if required else ""

            if current:
                masked = _mask_value(var_name, current)
                prompt = f"  {var_name}{req_tag} [{masked}]: "
            else:
                prompt = f"  {var_name}{req_tag}: "

            try:
                value = input(prompt).strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\n" + _yellow("⚠️  Wizard cancelled"))
                return

            if value:
                # Set the value
                args = type("Args", (), {"key": var_name, "value": value})()
                cmd_env_set(args)
                changes += 1

    print(f"\n{_green(f'✅ Wizard complete! {changes} vars updated.')}")
    print(f"   Config: {_cyan(str(path))}")


def cmd_env_path(_args) -> None:
    """Print .env file path."""
    print(_get_env_path())


def cmd_env_check(_args) -> None:
    """Check for missing/empty required vars."""
    path = _get_env_path()
    if not path.exists():
        print(_red(f"❌ .env not found: {path}"))
        return

    env = _parse_env(_read_env(path))

    print(_bold("🔍 Checking .env configuration...\n"))

    missing = []
    empty = []
    ok = []

    for section_name, desc, vars_list in ENV_SECTIONS:
        for var_name, var_desc, required in vars_list:
            if not required:
                continue
            if var_name not in env:
                missing.append((var_name, desc))
            elif not env[var_name]:
                empty.append((var_name, desc))
            else:
                ok.append(var_name)

    if ok:
        print(_green(f"  ✅ {len(ok)} required vars configured"))

    if empty:
        print(_yellow(f"\n  ⚠️  {len(empty)} required vars are empty:"))
        for key, section in empty:
            print(f"     {key} ({section})")

    if missing:
        print(_red(f"\n  ❌ {len(missing)} required vars missing:"))
        for key, section in missing:
            print(f"     {key} ({section})")

    if not missing and not empty:
        print(_green("\n  🎉 All required vars are configured!"))
    else:
        print(f"\n  Run {_cyan('chiper env wizard')} to fix")


# ─── Main handler ────────────────────────────────────────────────────────────


def env_command(args) -> None:
    """Dispatch env subcommands."""
    cmd = getattr(args, "env_command", None)

    dispatch = {
        None: cmd_env_show,
        "show": cmd_env_show,
        "list": cmd_env_list,
        "get": cmd_env_get,
        "set": cmd_env_set,
        "unset": cmd_env_unset,
        "edit": cmd_env_edit,
        "sections": cmd_env_sections,
        "section": cmd_env_section,
        "wizard": cmd_env_wizard,
        "path": cmd_env_path,
        "check": cmd_env_check,
    }

    handler = dispatch.get(cmd)
    if handler:
        handler(args)
    else:
        cmd_env_show(args)
