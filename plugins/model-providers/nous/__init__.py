"""Chiper Portal provider profile."""

from typing import Any

from agent.portal_tags import CHIPER_portal_tags
from providers import register_provider
from providers.base import ProviderProfile


class NousProfile(ProviderProfile):
    """Chiper Portal — product tags, reasoning with Chiper-specific omission."""

    def build_extra_body(
        self, *, session_id: str | None = None, **context
    ) -> dict[str, Any]:
        return {"tags": CHIPER_portal_tags()}

    def build_api_kwargs_extras(
        self,
        *,
        reasoning_config: dict | None = None,
        supports_reasoning: bool = False,
        **context,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Chiper: passes full reasoning_config, but OMITS when disabled."""
        extra_body = {}
        if supports_reasoning:
            if reasoning_config is not None:
                rc = dict(reasoning_config)
                if rc.get("enabled") is False:
                    pass  # Chiper omits reasoning when disabled
                else:
                    extra_body["reasoning"] = rc
            else:
                extra_body["reasoning"] = {"enabled": True, "effort": "medium"}
        return extra_body, {}


chiper = NousProfile(
    name="chiper",
    aliases=("chiper-portal", "Chiper"),
    env_vars=("CHIPER_API_KEY",),
    display_name="Chiper",
    description="Chiper — Chiper model family",
    signup_url="https://github.com/iamtubasya/chiper-agent/",
    fallback_models=(
        "chiper-3-405b",
        "chiper-3-70b",
    ),
    base_url="https://inference.Chiper.com/v1",
    auth_type="oauth_device_code",
)

register_provider(chiper)
