"""``chiper telegram`` and ``chiper platform`` subcommand parsers.

Provides platform-specific gateway setup with auto-detection.
"""

from __future__ import annotations

from typing import Callable


def build_telegram_parser(subparsers, *, cmd_telegram: Callable) -> None:
    """Attach the ``telegram`` subcommand to ``subparsers``."""
    telegram_parser = subparsers.add_parser(
        "telegram",
        help="Telegram gateway management",
        description="Setup and manage Telegram gateway",
    )
    telegram_subparsers = telegram_parser.add_subparsers(dest="telegram_command")

    # telegram setup
    telegram_subparsers.add_parser(
        "setup", help="Interactive Telegram gateway setup with auto-detection"
    )

    # telegram status
    telegram_subparsers.add_parser(
        "status", help="Show Telegram gateway status"
    )

    # telegram test
    telegram_subparsers.add_parser(
        "test", help="Test Telegram bot connection"
    )

    telegram_parser.set_defaults(func=cmd_telegram)


def build_platform_parser(subparsers, *, cmd_platform: Callable) -> None:
    """Attach the ``platform`` subcommand to ``subparsers``."""
    platform_parser = subparsers.add_parser(
        "platform",
        help="Platform gateway setup (Telegram, Discord, etc.)",
        description="Auto-detect and configure messaging platform gateways",
    )
    platform_subparsers = platform_parser.add_subparsers(dest="platform_command")

    # platform detect
    platform_subparsers.add_parser(
        "detect", help="Detect all configured platforms"
    )

    # platform setup
    platform_setup = platform_subparsers.add_parser(
        "setup", help="Setup a platform gateway"
    )
    platform_setup.add_argument(
        "name",
        nargs="?",
        help="Platform name (telegram, discord, slack, whatsapp, etc.)",
    )

    # platform list
    platform_subparsers.add_parser(
        "list", help="List all supported platforms"
    )

    platform_parser.set_defaults(func=cmd_platform)
