"""``chiper env`` subcommand parser.

Provides an interactive CLI to manage .env configuration.
"""

from __future__ import annotations

from typing import Callable


def build_env_parser(subparsers, *, cmd_env: Callable) -> None:
    """Attach the ``env`` subcommand to ``subparsers``."""
    env_parser = subparsers.add_parser(
        "env",
        help="Manage .env configuration (API keys, tokens, settings)",
        description="Interactive .env file manager for Chiper Agent",
    )
    env_subparsers = env_parser.add_subparsers(dest="env_command")

    # env show (default)
    env_subparsers.add_parser("show", help="Show all env vars (secrets masked)")

    # env list
    env_subparsers.add_parser("list", help="List all env var names (no values)")

    # env get
    env_get = env_subparsers.add_parser("get", help="Get value of an env var")
    env_get.add_argument("key", help="Environment variable name")

    # env set
    env_set = env_subparsers.add_parser("set", help="Set an env var value")
    env_set.add_argument("key", help="Environment variable name")
    env_set.add_argument("value", help="Value to set")

    # env unset
    env_unset = env_subparsers.add_parser("unset", help="Remove an env var")
    env_unset.add_argument("key", help="Environment variable name")

    # env edit
    env_subparsers.add_parser("edit", help="Open .env in $EDITOR")

    # env sections
    env_subparsers.add_parser("sections", help="List all config sections")

    # env section
    env_section = env_subparsers.add_parser(
        "section", help="Show vars in a specific section"
    )
    env_section.add_argument("name", help="Section name (e.g., telegram, gateway)")

    # env wizard
    env_subparsers.add_parser("wizard", help="Interactive setup wizard for .env")

    # env path
    env_subparsers.add_parser("path", help="Print .env file path")

    # env check
    env_subparsers.add_parser("check", help="Check for missing/empty required vars")

    env_parser.set_defaults(func=cmd_env)
