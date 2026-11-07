"""
Tests for Soul-Scoped Skill Masking architecture.
Verifies that each soul persona only sees and accesses its designated skills,
while skills from other personas remain cleanly masked without physical file moves.
"""

import json
from pathlib import Path
from unittest.mock import patch

from agent.soul_manager import (
    SOUL_SKILL_SCOPES,
    is_skill_allowed_for_soul,
    get_soul_for_skill,
    switch_soul,
    get_active_soul,
)
from agent.prompt_builder import build_skills_system_prompt, clear_skills_system_prompt_cache
from tools.skills_tool import skills_list, skill_view


def test_is_skill_allowed_for_soul_matrix():
    # Chiper-Dev
    assert is_skill_allowed_for_soul("chiper-dev", "software-development", "test-driven-development")
    assert is_skill_allowed_for_soul("chiper-dev", "github", "github-pr-workflow")
    assert is_skill_allowed_for_soul("chiper-dev", "devops", "linux-server-ops")
    assert is_skill_allowed_for_soul("chiper-dev", "autonomous-ai-agents", "chiper-agent")
    assert not is_skill_allowed_for_soul("chiper-dev", "bounty-pack", "hunt-sqli")
    assert not is_skill_allowed_for_soul("chiper-dev", "chiper-cyber", "chiper-web-sqli")
    assert not is_skill_allowed_for_soul("chiper-dev", "chiper-web3", "chiper-airdrop-intelligence")

    # Chiper-Cyber
    assert is_skill_allowed_for_soul("chiper-cyber", "chiper-cyber", "chiper-web-sqli")
    assert is_skill_allowed_for_soul("chiper-cyber", "bounty-pack/tob", "semgrep")
    assert is_skill_allowed_for_soul("chiper-cyber", "software-development", "systematic-debugging")
    assert not is_skill_allowed_for_soul("chiper-cyber", "bounty-pack", "hunt-sqli")
    assert not is_skill_allowed_for_soul("chiper-cyber", "chiper-web3", "chiper-airdrop-intelligence")
    assert not is_skill_allowed_for_soul("chiper-cyber", "creative", "manim-video")

    # Chiper-Hunt
    assert is_skill_allowed_for_soul("chiper-hunt", "bounty-pack", "hunt-sqli")
    assert is_skill_allowed_for_soul("chiper-hunt", "bounty-pack/security", "smart-contract-audit")
    assert is_skill_allowed_for_soul("chiper-hunt", "software-development", "systematic-debugging")
    assert not is_skill_allowed_for_soul("chiper-hunt", "chiper-cyber", "chiper-web-sqli")
    assert not is_skill_allowed_for_soul("chiper-hunt", "chiper-web3", "chiper-airdrop-intelligence")

    # Chiper-Web3
    assert is_skill_allowed_for_soul("chiper-web3", "chiper-web3", "chiper-airdrop-intelligence")
    assert is_skill_allowed_for_soul("chiper-web3", "bounty-pack/tob", "solana-vulnerability-scanner")
    assert not is_skill_allowed_for_soul("chiper-web3", "chiper-cyber", "chiper-web-sqli")
    assert not is_skill_allowed_for_soul("chiper-web3", "bounty-pack", "hunt-sqli")

    # Unknown or default: everything allowed
    assert is_skill_allowed_for_soul("unknown", "chiper-cyber", "chiper-web-sqli")
    assert is_skill_allowed_for_soul(None, "chiper-cyber", "chiper-web-sqli")


def test_get_soul_for_skill():
    assert get_soul_for_skill("chiper-cyber", "chiper-web-sqli") == "chiper-cyber"
    assert get_soul_for_skill("bounty-pack", "hunt-sqli") == "chiper-hunt"
    assert get_soul_for_skill("chiper-web3", "chiper-airdrop-intelligence") == "chiper-web3"
    assert get_soul_for_skill("software-development", "fastapi-backend-architecture") == "chiper-dev"


def test_prompt_builder_soul_masking_integration(monkeypatch, tmp_path):
    monkeypatch.setenv("CHIPER_HOME", str(tmp_path))

    # Create dummy skills across categories
    skills_base = tmp_path / "skills"

    dev_skill = skills_base / "software-development" / "tdd"
    dev_skill.mkdir(parents=True)
    (dev_skill / "SKILL.md").write_text("---\nname: tdd\ndescription: TDD workflow\n---\nBody")

    cyber_skill = skills_base / "chiper-cyber" / "sqli-probe"
    cyber_skill.mkdir(parents=True)
    (cyber_skill / "SKILL.md").write_text("---\nname: sqli-probe\ndescription: SQLi probe\n---\nBody")

    hunt_skill = skills_base / "bounty-pack" / "hunt-sqli"
    hunt_skill.mkdir(parents=True)
    (hunt_skill / "SKILL.md").write_text("---\nname: hunt-sqli\ndescription: Hunt SQLi\n---\nBody")

    web3_skill = skills_base / "chiper-web3" / "airdrop"
    web3_skill.mkdir(parents=True)
    (web3_skill / "SKILL.md").write_text("---\nname: airdrop\ndescription: Airdrop scanner\n---\nBody")

    # In Chiper-Dev: bounty-pack and chiper-cyber must NOT appear
    clear_skills_system_prompt_cache(clear_snapshot=True)
    with patch("agent.soul_manager.get_active_soul", return_value={"id": "chiper-dev", "name": "Chiper-Dev"}):
        dev_prompt = build_skills_system_prompt()
        assert "tdd" in dev_prompt
        assert "hunt-sqli" not in dev_prompt
        assert "sqli-probe" not in dev_prompt
        assert "airdrop" not in dev_prompt

    # In Chiper-Cyber: chiper-cyber is present, but bounty-pack hunt-* is hidden
    clear_skills_system_prompt_cache(clear_snapshot=False)
    with patch("agent.soul_manager.get_active_soul", return_value={"id": "chiper-cyber", "name": "Chiper-Cyber"}):
        cyber_prompt = build_skills_system_prompt()
        assert "sqli-probe" in cyber_prompt
        assert "hunt-sqli" not in cyber_prompt
        assert "airdrop" not in cyber_prompt

    # In Chiper-Hunt: bounty-pack hunt-* is present, but chiper-cyber is hidden
    clear_skills_system_prompt_cache(clear_snapshot=False)
    with patch("agent.soul_manager.get_active_soul", return_value={"id": "chiper-hunt", "name": "Chiper-Hunt"}):
        hunt_prompt = build_skills_system_prompt()
        assert "hunt-sqli" in hunt_prompt
        assert "sqli-probe" not in hunt_prompt
        assert "airdrop" not in hunt_prompt

    # In Chiper-Web3: chiper-web3 is present
    clear_skills_system_prompt_cache(clear_snapshot=False)
    with patch("agent.soul_manager.get_active_soul", return_value={"id": "chiper-web3", "name": "Chiper-Web3"}):
        web3_prompt = build_skills_system_prompt()
        assert "airdrop" in web3_prompt
        assert "hunt-sqli" not in web3_prompt
        assert "sqli-probe" not in web3_prompt


def test_skill_view_masked_skill_feedback(monkeypatch, tmp_path):
    monkeypatch.setenv("CHIPER_HOME", str(tmp_path))

    skills_base = tmp_path / "skills"
    cyber_skill = skills_base / "chiper-cyber" / "chiper-test-probe"
    cyber_skill.mkdir(parents=True)
    (cyber_skill / "SKILL.md").write_text("---\nname: chiper-test-probe\ndescription: Test probe\n---\nBody")

    # Patch module SKILLS_DIR in skills_tool
    monkeypatch.setattr("tools.skills_tool.SKILLS_DIR", skills_base)

    with patch("agent.soul_manager.get_active_soul", return_value={"id": "chiper-dev", "name": "Chiper-Dev"}):
        raw_res = skill_view("chiper-test-probe", preprocess=False)
        res = json.loads(raw_res)
        assert res["success"] is False
        assert "chiper-cyber" in res["error"] or "chiper-cyber" in res.get("required_soul", "")
        assert "/soul" in res.get("hint", "") or "/soul" in res.get("error", "")
