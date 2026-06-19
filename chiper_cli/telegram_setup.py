"""``chiper telegram`` and ``chiper platform`` command handlers.

Auto-detects gateway requirements and provides interactive setup.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from pathlib import Path
from typing import Optional


# ─── ANSI Colors ─────────────────────────────────────────────────────────────

def _c(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"

def _green(t): return _c(t, "32")
def _red(t): return _c(t, "31")
def _yellow(t): return _c(t, "33")
def _cyan(t): return _c(t, "36")
def _bold(t): return _c(t, "1")
def _dim(t): return _c(t, "2")
def _check(ok): return _green("✅") if ok else _red("❌")
def _warn(ok): return _green("✅") if ok else _yellow("⚠️")


# ─── Platform Definitions ────────────────────────────────────────────────────

PLATFORMS = {
    "telegram": {
        "name": "Telegram",
        "emoji": "📱",
        "description": "Telegram Bot Gateway",
        "package": "python-telegram-bot",
        "import_check": "telegram",
        "requirements": [
            {
                "key": "TELEGRAM_BOT_TOKEN",
                "label": "Bot Token",
                "description": "Token dari @BotFather",
                "required": True,
                "validate": lambda v: bool(re.match(r"^\d+:[A-Za-z0-9_-]{30,}$", v)),
                "hint": "Format: 123456789:ABCdefGHIjklMNOpqrSTUvwxYZ",
                "howto": [
                    "1. Buka Telegram, cari @BotFather",
                    "2. Kirim /newbot",
                    "3. Ikuti instruksi (nama bot, username)",
                    "4. Copy token yang diberikan",
                ],
            },
            {
                "key": "TELEGRAM_ALLOWED_USERS",
                "label": "Allowed Users",
                "description": "User ID yang diizinkan untuk chat bot",
                "required": True,
                "validate": lambda v: bool(re.match(r"^\d+(,\d+)*$", v.replace(" ", ""))),
                "hint": "Format: 123456789 atau 123,456,789",
                "howto": [
                    "1. Buka Telegram, cari @userinfobot",
                    "2. Kirim /start",
                    "3. Bot akan reply dengan user ID kamu",
                ],
            },
            {
                "key": "TELEGRAM_HOME_CHANNEL",
                "label": "Home Channel",
                "description": "Chat ID default untuk delivery",
                "required": False,
                "validate": lambda v: not v or bool(re.match(r"^-?\d+$", v)),
                "hint": "Kosongkan aja, nanti di-set dari chat /sethome",
            },
            {
                "key": "TELEGRAM_HOME_CHANNEL_THREAD_ID",
                "label": "Thread/Topic ID",
                "description": "Forum topic ID (opsional, untuk grup topik)",
                "required": False,
                "validate": lambda v: not v or bool(re.match(r"^\d+$", v)),
                "hint": "Kosongkan jika bukan grup topik",
            },
        ],
        "env_section": "telegram",
        "test_endpoint": "https://api.telegram.org/bot{token}/getMe",
    },
    "discord": {
        "name": "Discord",
        "emoji": "🎮",
        "description": "Discord Bot Gateway",
        "package": "discord.py",
        "import_check": "discord",
        "requirements": [
            {
                "key": "DISCORD_BOT_TOKEN",
                "label": "Bot Token",
                "description": "Discord bot token",
                "required": True,
                "validate": lambda v: len(v) > 50,
                "hint": "Dari Discord Developer Portal → Bot → Token",
                "howto": [
                    "1. Buka https://discord.com/developers/applications",
                    "2. Buat aplikasi baru → Bot",
                    "3. Copy token",
                    "4. Enable Message Content Intent",
                ],
            },
            {
                "key": "DISCORD_ALLOWED_USERS",
                "label": "Allowed Users",
                "description": "Discord user IDs yang diizinkan",
                "required": True,
                "validate": lambda v: bool(re.match(r"^\d+(,\d+)*$", v.replace(" ", ""))),
                "hint": "Klik kanan user → Copy ID (aktifkan Developer Mode)",
                "howto": [
                    "1. Settings → Advanced → Developer Mode (ON)",
                    "2. Klik kanan pada nama user → Copy User ID",
                ],
            },
        ],
        "env_section": "discord",
    },
    "slack": {
        "name": "Slack",
        "emoji": "💬",
        "description": "Slack Bot Gateway",
        "package": "slack_sdk",
        "import_check": "slack_sdk",
        "requirements": [
            {
                "key": "SLACK_BOT_TOKEN",
                "label": "Bot Token",
                "description": "Slack bot token (xoxb-...)",
                "required": True,
                "validate": lambda v: v.startswith("xoxb-"),
                "hint": "Format: xoxb-...",
                "howto": [
                    "1. Buka https://api.slack.com/apps",
                    "2. Buat app → OAuth & Permissions",
                    "3. Tambah scope: chat:write, channels:history, im:history",
                    "4. Install to workspace → Copy Bot Token",
                ],
            },
            {
                "key": "SLACK_APP_TOKEN",
                "label": "App Token",
                "description": "Slack app-level token (xapp-...)",
                "required": True,
                "validate": lambda v: v.startswith("xapp-"),
                "hint": "Format: xapp-...",
                "howto": [
                    "1. Basic Information → App-Level Tokens",
                    "2. Generate token dengan scope: connections:write",
                ],
            },
        ],
        "env_section": "slack",
    },
    "whatsapp": {
        "name": "WhatsApp",
        "emoji": "📞",
        "description": "WhatsApp Cloud API Gateway",
        "package": "requests",
        "import_check": "requests",
        "requirements": [
            {
                "key": "WHATSAPP_ACCESS_TOKEN",
                "label": "Access Token",
                "description": "WhatsApp Cloud API access token",
                "required": True,
                "validate": lambda v: len(v) > 20,
                "hint": "Dari Meta Business Suite",
                "howto": [
                    "1. Buka https://developers.facebook.com",
                    "2. Buat app → WhatsApp",
                    "3. Generate access token",
                ],
            },
            {
                "key": "WHATSAPP_PHONE_NUMBER_ID",
                "label": "Phone Number ID",
                "description": "WhatsApp phone number ID",
                "required": True,
                "validate": lambda v: bool(re.match(r"^\d+$", v)),
                "hint": "Numeric ID dari WhatsApp API settings",
            },
            {
                "key": "WHATSAPP_VERIFY_TOKEN",
                "label": "Verify Token",
                "description": "Webhook verify token (buat sendiri)",
                "required": True,
                "validate": lambda v: len(v) > 5,
                "hint": "Buat string random untuk verifikasi webhook",
            },
        ],
        "env_section": "whatsapp",
    },
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_env_path() -> Path:
    chiper_home = os.environ.get("CHIPER_HOME", os.path.expanduser("~/.hermes"))
    return Path(chiper_home) / ".env"


def _read_env() -> dict[str, str]:
    """Read current .env into dict."""
    path = _get_env_path()
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if "  #" in val:
                val = val[:val.index("  #")].strip()
            result[key] = val
    return result


def _save_env_value(key: str, value: str) -> None:
    """Save a value to .env (preserves comments and structure)."""
    try:
        from chiper_cli.config import save_env_value
        save_env_value(key, value)
    except ImportError:
        # Fallback: direct file manipulation
        path = _get_env_path()
        lines = []
        if path.exists():
            lines = path.read_text(encoding="utf-8").splitlines()

        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}=") or line.strip().startswith(f"# {key}="):
                lines[i] = f"{key}={value}"
                found = True
                break

        if not found:
            lines.append(f"{key}={value}")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _get_env_value(key: str) -> Optional[str]:
    """Get value from .env or environment."""
    # Check .env file first (more reliable than os.environ which may be sanitized)
    val = _read_env().get(key)
    if val:
        return val
    # Fallback to environment
    env_val = os.environ.get(key)
    return env_val if env_val else None


def _check_package(package_name: str, import_name: str) -> tuple[bool, str]:
    """Check if a Python package is installed."""
    try:
        import importlib.metadata as metadata
        try:
            ver = metadata.version(package_name)
            return True, ver
        except metadata.PackageNotFoundError:
            pass
    except ImportError:
        pass

    # Try import check
    try:
        spec = importlib.util.find_spec(import_name)
        if spec is not None:
            return True, "installed"
    except (ImportError, ModuleNotFoundError, ValueError):
        pass

    # Check if lazy-install is available
    try:
        from tools.lazy_deps import is_available
        if is_available(f"platform.{import_name}"):
            return True, "lazy (auto-install on first use)"
    except (ImportError, AttributeError):
        pass

    return False, "not installed"


def _test_telegram_token(token: str) -> tuple[bool, str]:
    """Test if a Telegram bot token is valid."""
    import urllib.request
    import json

    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "ChiperAgent/1.0")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("ok"):
                bot = data.get("result", {})
                name = bot.get("first_name", "Unknown")
                username = bot.get("username", "unknown")
                return True, f"@{username} ({name})"
            return False, data.get("description", "Invalid token")
    except Exception as e:
        return False, str(e)[:80]


def _input_with_validation(
    prompt_text: str,
    validate=None,
    hint: str = "",
    password: bool = False,
    default: str = "",
) -> Optional[str]:
    """Input with validation loop."""
    while True:
        suffix = f" [{_dim(default)}]" if default else ""
        hint_str = f" {_dim(f'({hint})')}" if hint else ""

        try:
            if password:
                import getpass
                value = getpass.getpass(f"  {prompt_text}{hint_str}{suffix}: ").strip()
            else:
                value = input(f"  {prompt_text}{hint_str}{suffix}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n" + _yellow("⚠️  Cancelled"))
            return None

        if not value and default:
            value = default

        if not value:
            return ""

        if validate and not validate(value):
            print(_red("  ❌ Format salah!"))
            if hint:
                print(_dim(f"     Hint: {hint}"))
            continue

        return value


def _print_header(title: str, emoji: str = "") -> None:
    """Print a section header."""
    print()
    print(_bold(f"{'─' * 50}"))
    print(_bold(f"  {emoji} {title}" if emoji else f"  {title}"))
    print(_bold(f"{'─' * 50}"))
    print()


# ─── Auto-Detection ──────────────────────────────────────────────────────────

def _detect_platform(platform_key: str) -> dict:
    """Auto-detect platform requirements and return status."""
    platform = PLATFORMS.get(platform_key)
    if not platform:
        return {"error": f"Unknown platform: {platform_key}"}

    env = _read_env()
    result = {
        "platform": platform["name"],
        "emoji": platform["emoji"],
        "description": platform["description"],
        "package_installed": False,
        "package_version": "unknown",
        "requirements": [],
        "all_configured": False,
        "all_required_met": False,
    }

    # Check package
    pkg_ok, pkg_ver = _check_package(platform["package"], platform["import_check"])
    result["package_installed"] = pkg_ok
    result["package_version"] = pkg_ver

    # Check requirements
    all_required = True
    all_any = True
    for req in platform["requirements"]:
        key = req["key"]
        value = env.get(key, "")
        is_set = bool(value)
        is_valid = req["validate"](value) if value else False

        if req["required"] and (not is_set or not is_valid):
            all_required = False
        if not is_set:
            all_any = False

        result["requirements"].append({
            "key": key,
            "label": req["label"],
            "description": req["description"],
            "required": req["required"],
            "is_set": is_set,
            "is_valid": is_valid,
            "value_preview": value[:8] + "***" if value and len(value) > 12 else value,
            "hint": req.get("hint", ""),
        })

    result["all_required_met"] = all_required
    result["all_configured"] = all_any

    return result


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_telegram_status(_args) -> None:
    """Show Telegram gateway status."""
    result = _detect_platform("telegram")

    _print_header("Telegram Gateway Status", "📱")

    # Package
    pkg_ok = result["package_installed"]
    print(f"  {_check(pkg_ok)} Package: python-telegram-bot {result['package_version']}")

    # Requirements
    print()
    for req in result["requirements"]:
        status = _check(req["is_set"] and req["is_valid"]) if req["required"] else _warn(req["is_set"])
        req_tag = f" {_red('(required)')}" if req["required"] else f" {_dim('(optional)')}"
        print(f"  {status} {req['label']}{req_tag}")
        if req["is_set"]:
            print(f"     {_dim(req['value_preview'])}")
        else:
            print(f"     {_dim('not set')}")

    print()
    if result["all_required_met"]:
        print(f"  {_green('🎉 Telegram gateway siap digunakan!')}")
        print(f"     Jalankan: {_cyan('chiper gateway run')}")
    else:
        print(f"  {_yellow('⚠️  Ada konfigurasi yang belum lengkap')}")
        print(f"     Jalankan: {_cyan('chiper telegram setup')}")


def cmd_telegram_test(_args) -> None:
    """Test Telegram bot connection."""
    _print_header("Testing Telegram Connection", "🔍")

    token = _get_env_value("TELEGRAM_BOT_TOKEN")
    if not token:
        print(_red("  ❌ TELEGRAM_BOT_TOKEN belum diset"))
        print(f"     Jalankan: {_cyan('chiper telegram setup')}")
        return

    print(f"  🔑 Token: {token[:8]}***{token[-4:]}")
    print(f"  🌐 Testing connection...")

    ok, info = _test_telegram_token(token)
    if ok:
        print(f"  {_green('✅ Connected!')}")
        print(f"     Bot: {info}")

        # Check allowed users
        allowed = _get_env_value("TELEGRAM_ALLOWED_USERS")
        if allowed:
            print(f"  👥 Allowed users: {allowed}")
        else:
            print(f"  {_yellow('⚠️  No allowed users — anyone can use your bot!')}")

        # Check home channel
        home = _get_env_value("TELEGRAM_HOME_CHANNEL")
        if home:
            print(f"  🏠 Home channel: {home}")
        else:
            print(f"  {_yellow('⚠️  No home channel set')}")
    else:
        print(f"  {_red('❌ Connection failed!')}")
        print(f"     Error: {info}")


def cmd_telegram_setup(_args) -> None:
    """Interactive Telegram setup with auto-detection."""
    platform_key = "telegram"
    platform = PLATFORMS[platform_key]

    _print_header(f"{platform['name']} Gateway Setup", platform["emoji"])

    # ── Step 1: Check package ──
    print(_bold("  📦 Step 1: Checking dependencies..."))
    print()
    pkg_ok, pkg_ver = _check_package(platform["package"], platform["import_check"])

    if pkg_ok:
        print(f"  ✅ {platform['package']}: {pkg_ver}")
    else:
        print(f"  ⏳ {platform['package']}: not installed yet")
        print(f"     {_dim('→ Akan di-install otomatis saat gateway pertama kali jalan')}")

    # ── Step 2: Auto-detect current config ──
    print()
    print(_bold("  🔍 Step 2: Auto-detecting current configuration..."))
    print()

    detection = _detect_platform(platform_key)
    env = _read_env()

    # Show current status
    has_existing = False
    for req in detection["requirements"]:
        status = _check(req["is_set"] and req["is_valid"]) if req["required"] else _warn(req["is_set"])
        print(f"  {status} {req['label']}: {req['value_preview'] if req['is_set'] else _dim('not set')}")
        if req["is_set"]:
            has_existing = True

    if detection["all_required_met"]:
        print()
        print(_green("  ✅ Semua konfigurasi sudah lengkap!"))
        try:
            choice = input(f"\n  Reconfigure? (y/N): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return
        if choice != "y":
            print(_dim("  Skipping setup."))
            return

    # ── Step 3: Interactive configuration ──
    print()
    print(_bold("  📝 Step 3: Configure Telegram Gateway"))
    print()

    values = dict(env)  # Start with current values
    bot_info = {}  # Store bot name/username after validation

    for req in platform["requirements"]:
        key = req["key"]
        current = values.get(key, "")
        required_tag = f" {_red('*')}" if req["required"] else ""

        # Special handling for BOT TOKEN
        if key == "TELEGRAM_BOT_TOKEN":
            # If token exists, get bot name first
            bot_label = req["label"]
            if current:
                ok, info = _test_telegram_token(current)
                if ok:
                    bot_label = f"{req['label']} ({info})"
                    bot_info["token"] = info

            print(_bold(f"  ── {bot_label}{required_tag} ──"))
            if not current and "howto" in req:
                print()
                for step in req["howto"]:
                    print(f"  {_cyan(step)}")
                print()

            # Show format hint
            print(f"  {_dim(req.get('hint', ''))}")
            print()

            # Prompt for token
            while True:
                try:
                    token_input = input(f"  {req['label']}: ").strip()
                except (KeyboardInterrupt, EOFError):
                    print("\n" + _yellow("⚠️  Cancelled"))
                    return

                if not token_input:
                    if current:
                        print(f"  {_dim('Keeping existing token')}")
                        break
                    if req["required"]:
                        print(_red("  ❌ Bot token wajib diisi!"))
                        continue
                    break

                # Validate format
                if not req["validate"](token_input):
                    print(_red("  ❌ Format salah!"))
                    print(_dim(f"     {req.get('hint', '')}"))
                    continue

                # Test token via Telegram API
                print(f"  {_dim('Verifikasi token...')}")
                ok, info = _test_telegram_token(token_input)
                if ok:
                    bot_info["token"] = info
                    print(f"  {_green(f'✅ Bot: {info}')}")
                    values[key] = token_input
                    _save_env_value(key, token_input)
                    break
                else:
                    print(_red(f"  ❌ Token tidak valid: {info}"))
                    continue
            print()

        # Special handling for ALLOWED USERS
        elif key == "TELEGRAM_ALLOWED_USERS":
            # Show label with current value if exists
            users_label = req["label"]
            if current:
                users_label = f"{req['label']} ({current})"

            print(_bold(f"  ── {users_label}{required_tag} ──"))
            print(f"  {req['description']}")
            if not current and "howto" in req:
                print()
                for step in req["howto"]:
                    print(f"  {_cyan(step)}")
                print()

            # Prompt for user IDs
            while True:
                try:
                    users_input = input(f"  {req['label']}: ").strip()
                except (KeyboardInterrupt, EOFError):
                    print("\n" + _yellow("⚠️  Cancelled"))
                    return

                if not users_input:
                    if current:
                        print(f"  {_dim('Keeping existing users')}")
                        break
                    if req["required"]:
                        print(_red("  ❌ User ID wajib diisi!"))
                        continue
                    break

                # Validate format
                if not req["validate"](users_input):
                    print(_red("  ❌ Format salah!"))
                    print(_dim(f"     {req.get('hint', '')}"))
                    continue

                values[key] = users_input
                _save_env_value(key, users_input)
                print(f"  {_green('✅ Saved!')}")
                break
            print()

        # Special handling for HOME CHANNEL
        elif key == "TELEGRAM_HOME_CHANNEL":
            home_label = req["label"]
            if current:
                home_label = f"{req['label']} ({current})"

            print(_bold(f"  ── {home_label}{required_tag} ──"))
            print(f"  {req['description']}")
            print()

            try:
                home_input = input(f"  {req['label']}: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n" + _yellow("⚠️  Cancelled"))
                return

            if home_input:
                if not req["validate"](home_input):
                    print(_red("  ❌ Format salah!"))
                    print(_dim("     Harus berupa angka"))
                else:
                    values[key] = home_input
                    _save_env_value(key, home_input)
                    print(f"  {_green('✅ Saved!')}")
            else:
                print(f"  {_dim('⬜ Kosong — set dari chat: /sethome')}")
            print()

        # Default handling for other fields (Thread/Topic ID etc)
        else:
            field_label = req["label"]
            if current:
                field_label = f"{req['label']} ({current})"

            print(_bold(f"  ── {field_label}{required_tag} ──"))
            print(f"  {req['description']}")

            value = _input_with_validation(
                req["label"],
                validate=req["validate"],
                hint=req.get("hint", ""),
                password="TOKEN" in key or "KEY" in key or "PASS" in key,
                default="",
            )

            if value is None:  # Ctrl+C
                return

            if value:
                values[key] = value
                _save_env_value(key, value)
                print(f"  {_green('✅ Saved!')}")
            elif not current and req["required"]:
                print(_red(f"  ❌ {req['label']} wajib diisi!"))
                print(f"     Jalankan lagi: {_cyan('chiper telegram setup')}")
                return
            print()

    # ── Step 4: Verify ──
    print(_bold("  🔍 Step 4: Verifikasi"))
    print()

    token = values.get("TELEGRAM_BOT_TOKEN", "")
    if token:
        ok, info = _test_telegram_token(token)
        if ok:
            print(f"  {_green(f'✅ Bot: {info}')}")
        else:
            print(f"  {_yellow(f'⚠️  Gagal verifikasi: {info}')}")
            print(f"     Token tersimpan, cek jika ada masalah")

    # ── Summary ──
    print()
    print(_bold("  ══════════════════════════════════════"))
    print(_bold(f"  {platform['emoji']} Telegram Gateway — Selesai!"))
    print(_bold("  ══════════════════════════════════════"))
    print()

    for req in platform["requirements"]:
        val = values.get(req["key"], "")
        if val:
            status = _green("✅")
            if req["key"] == "TELEGRAM_BOT_TOKEN" and bot_info.get("token"):
                display = bot_info["token"]
            else:
                display = req["label"]
        else:
            status = _dim("⬜")
            display = _dim("kosong")
        print(f"  {status} {req['label']}: {display}")

    print()
    print(f"  📄 Config: {_cyan(str(_get_env_path()))}")
    print()
    print(f"  {_bold('Steps:')}")
    print(f"    {_cyan('chiper telegram test')}     — Test koneksi")
    print(f"    {_cyan('chiper gateway')}           — Jalankan gateway (Telegram dll)")
    print(f"    {_cyan('chiper model')}             — Setup model AI")
    print(f"    {_cyan('chiper env check')}         — Cek konfigurasi .env")
    print(f"    {_cyan('chiper env wizard')}        — Setup .env interaktif")
    print(f"    {_cyan('chiper setup')}             — Setup wizard lengkap")
    print(f"    {_cyan('chiper status')}            — Cek status semua komponen")
    print(f"    {_cyan('chiper doctor')}            — Diagnosa masalah")
    print(f"    {_cyan('chiper platform detect')}   — Deteksi platform aktif")
    print(f"    {_cyan('chiper config show')}       — Lihat konfigurasi")
    print()


def cmd_platform_detect(_args) -> None:
    """Detect all configured platforms."""
    _print_header("Platform Detection", "🔍")

    env = _read_env()
    found = []

    for key, platform in PLATFORMS.items():
        result = _detect_platform(key)
        status = _check(result["all_required_met"])
        pkg = _check(result["package_installed"])

        print(f"  {platform['emoji']} {platform['name']}")
        print(f"     Package: {pkg} {result['package_version']}")
        print(f"     Config:  {status}")

        if result["all_required_met"]:
            found.append(platform["name"])

        for req in result["requirements"]:
            req_status = _check(req["is_set"] and req["is_valid"]) if req["required"] else _warn(req["is_set"])
            print(f"       {req_status} {req['label']}")
        print()

    if found:
        print(_green(f"  🎉 Active platforms: {', '.join(found)}"))
    else:
        print(_yellow("  ⚠️  No platforms fully configured"))
        print(f"     Run: {_cyan('chiper platform setup <name>')}")


def cmd_platform_setup(args) -> None:
    """Setup a platform gateway."""
    name = getattr(args, "name", None)

    if not name:
        # Interactive platform selection
        _print_header("Platform Setup", "🚀")
        print("  Pilih platform:\n")

        for i, (key, plat) in enumerate(PLATFORMS.items(), 1):
            result = _detect_platform(key)
            status = _green("✅") if result["all_required_met"] else _dim("⬜")
            print(f"  {status} [{i}] {plat['emoji']} {plat['name']} — {plat['description']}")

        print()
        try:
            choice = input("  Pilih nomor (atau nama platform): ").strip()
        except (KeyboardInterrupt, EOFError):
            return

        # Parse choice
        if choice.isdigit():
            idx = int(choice) - 1
            keys = list(PLATFORMS.keys())
            if 0 <= idx < len(keys):
                name = keys[idx]
            else:
                print(_red("  ❌ Pilihan tidak valid"))
                return
        elif choice.lower() in PLATFORMS:
            name = choice.lower()
        else:
            print(_red(f"  ❌ Platform '{choice}' tidak dikenal"))
            print(f"     Available: {', '.join(PLATFORMS.keys())}")
            return

    name = name.lower()
    if name not in PLATFORMS:
        print(_red(f"  ❌ Platform '{name}' tidak didukung"))
        print(f"     Available: {', '.join(PLATFORMS.keys())}")
        return

    # Route to platform-specific setup
    if name == "telegram":
        cmd_telegram_setup(args)
    else:
        _generic_platform_setup(name)


def _generic_platform_setup(platform_key: str) -> None:
    """Generic platform setup for non-telegram platforms."""
    platform = PLATFORMS[platform_key]
    _print_header(f"{platform['name']} Setup", platform["emoji"])

    # Check package
    pkg_ok, pkg_ver = _check_package(platform["package"], platform["import_check"])

    if pkg_ok:
        print(f"  ✅ {platform['package']}: {pkg_ver}")
    else:
        print(f"  ⏳ {platform['package']}: not installed yet")
        print(f"     {_dim('→ Akan di-install otomatis saat gateway pertama kali jalan')}")
    print()
    print(_bold("  📝 Konfigurasi:"))
    print()

    env = _read_env()
    values = dict(env)

    for req in platform["requirements"]:
        key = req["key"]
        current = values.get(key, "")
        required_tag = f" {_red('*')}" if req["required"] else ""

        print(f"  {req['label']}{required_tag}")
        print(f"  {req['description']}")

        if req["required"] and not current and "howto" in req:
            for step in req["howto"]:
                print(f"  {_cyan(step)}")
            print()

        value = _input_with_validation(
            req["label"],
            validate=req["validate"],
            hint=req.get("hint", ""),
            password="TOKEN" in key or "KEY" in key,
            default=current[:8] + "***" if current and len(current) > 12 else current,
        )

        if value is None:
            return

        if value:
            _save_env_value(key, value)
            values[key] = value
            print(f"  {_green('✅ Saved!')}")

        print()

    print(_green(f"\n  🎉 {platform['name']} configuration complete!"))
    print(f"     Jalankan: {_cyan('chiper gateway run')}")


def cmd_platform_list(_args) -> None:
    """List all supported platforms."""
    _print_header("Supported Platforms", "📋")

    for key, plat in PLATFORMS.items():
        result = _detect_platform(key)
        status = _green("✅") if result["all_required_met"] else _dim("⬜")
        pkg = _green("📦") if result["package_installed"] else _dim("📦")

        print(f"  {status} {plat['emoji']} {plat['name']}")
        print(f"     {plat['description']}")
        print(f"     {pkg} {plat['package']} ({result['package_version']})")

        reqs = [r for r in result["requirements"] if r["required"]]
        configured = sum(1 for r in reqs if r["is_set"] and r["is_valid"])
        print(f"     Config: {configured}/{len(reqs)} required vars")
        print()

    print(f"  Setup: {_cyan('chiper platform setup <name>')}")
    print(f"  Detect: {_cyan('chiper platform detect')}")


# ─── Main Handlers ───────────────────────────────────────────────────────────

def telegram_command(args) -> None:
    """Dispatch telegram subcommands."""
    cmd = getattr(args, "telegram_command", None)

    dispatch = {
        None: cmd_telegram_setup,
        "setup": cmd_telegram_setup,
        "status": cmd_telegram_status,
        "test": cmd_telegram_test,
    }

    handler = dispatch.get(cmd)
    if handler:
        handler(args)
    else:
        cmd_telegram_setup(args)


def platform_command(args) -> None:
    """Dispatch platform subcommands."""
    cmd = getattr(args, "platform_command", None)

    dispatch = {
        None: cmd_platform_detect,
        "detect": cmd_platform_detect,
        "setup": cmd_platform_setup,
        "list": cmd_platform_list,
    }

    handler = dispatch.get(cmd)
    if handler:
        handler(args)
    else:
        cmd_platform_detect(args)
