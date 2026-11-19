"""Regression tests: bundled souls must survive a non-editable install.

Bug being locked down
---------------------
``agent/soul_manager.py:ensure_default_souls()`` used to source every persona
from the repo-relative ``skills/`` tree only. That tree is ~935 MB, is synced
into ``$CHIPER_HOME/skills`` by the installer, and is **not** part of the wheel
or any ``pip install`` of the package. Consequences on a wheel/PyPI/Nix/Homebrew
install:

* ``chiper-cyber.md`` — no source found, so a 3-line stub was written
  (``"Kamu adalah Chiper-cyber, bug bounty hunter."``). The agent booted with
  Chiper-Cyber's name and none of her persona: no Hukum Tunggal, no
  anti-bantah rules, no skill-loading discipline. ~12 KB -> 72 bytes.
* ``chiper-web3.md`` — no ``else`` branch at all, so the file was silently
  never created and the soul was simply absent.
* ``chiper-dev.md`` / ``chiper-hunt.md`` — survived only because they had an
  inline constant fallback, which is what made the inconsistency invisible.

Fix: the four personas are shipped as package-data (``agent/bundled_souls/*.md``),
which always lands next to the module that reads it, and ``_seed_soul()``
appends that packaged copy as the final candidate before any inline fallback.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGED_SOULS = REPO_ROOT / "agent" / "bundled_souls"

# A persona shorter than this is a stub, not a soul. The smallest real one
# (chiper-dev) is ~4.9 KB; the old Chiper-Cyber stub was 72 bytes.
_MIN_REAL_SOUL_BYTES = 2000


def test_packaged_soul_files_exist_and_are_not_stubs():
    expected = {"chiper-cyber", "chiper-dev", "chiper-hunt", "chiper-web3"}

    on_disk = {p.stem for p in PACKAGED_SOULS.glob("*.md")}
    assert expected <= on_disk, (
        f"agent/bundled_souls/ must bundle every built-in soul; missing "
        f"{sorted(expected - on_disk)}"
    )

    for soul_id in sorted(expected):
        path = PACKAGED_SOULS / f"{soul_id}.md"
        size = path.stat().st_size
        assert size >= _MIN_REAL_SOUL_BYTES, (
            f"{path.name} is {size} bytes — that is a stub, not a persona. "
            "The 72-byte Chiper-Cyber stub is the exact regression this guards."
        )


def test_pyproject_ships_packaged_souls_in_the_wheel():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    agent_pkg_data = data["tool"]["setuptools"]["package-data"].get("agent", [])

    assert any("soul" in glob for glob in agent_pkg_data), (
        "pyproject [tool.setuptools.package-data] 'agent' must declare the "
        "bundled_souls/*.md glob, otherwise the wheel ships the loader but not the "
        "data and ensure_default_souls() falls back to a stub."
    )

    # The glob must actually match files on disk, or the package-data entry is
    # decorative.
    assert list(PACKAGED_SOULS.glob("*.md")), "expected soul files under agent/bundled_souls/"


@pytest.fixture
def wheel_install(monkeypatch, tmp_path):
    """Simulate a wheel install: no ``skills/`` tree, packaged data present."""
    from agent import soul_manager

    absent_skills = tmp_path / "no-such-skills-tree"
    monkeypatch.setattr(soul_manager, "_repo_skills_dir", lambda: absent_skills)
    monkeypatch.setattr(soul_manager, "_PACKAGED_SOULS_DIR", PACKAGED_SOULS)
    return tmp_path


def test_cyber_soul_seeds_full_persona_without_skills_tree(wheel_install):
    """Chiper-Cyber must get her whole persona, not the 72-byte stub."""
    from agent import soul_manager

    soul_manager.ensure_default_souls()

    seeded = soul_manager.get_souls_dir() / "chiper-cyber.md"
    assert seeded.is_file(), "chiper-cyber.md was not created"

    content = seeded.read_text(encoding="utf-8")
    assert len(content.encode("utf-8")) >= _MIN_REAL_SOUL_BYTES
    assert "bug bounty hunter" not in content or len(content) > 5000

    expected = (PACKAGED_SOULS / "chiper-cyber.md").read_text(encoding="utf-8")
    assert content == expected, "seeded soul must be the packaged persona verbatim"


def test_web3_soul_is_created_without_skills_tree(wheel_install):
    """Chiper-Web3 used to be skipped entirely when skills/ was absent."""
    from agent import soul_manager

    soul_manager.ensure_default_souls()

    seeded = soul_manager.get_souls_dir() / "chiper-web3.md"
    assert seeded.is_file(), (
        "chiper-web3.md was never created — the old code had no fallback branch"
    )
    assert seeded.stat().st_size >= _MIN_REAL_SOUL_BYTES


def test_all_souls_present_after_seeding_without_skills_tree(wheel_install):
    from agent import soul_manager

    soul_manager.ensure_default_souls()

    souls_dir = soul_manager.get_souls_dir()
    for soul_id in ("chiper-cyber", "chiper-dev", "chiper-hunt", "chiper-web3"):
        path = souls_dir / f"{soul_id}.md"
        assert path.is_file(), f"{soul_id}.md missing after seeding"
        assert path.stat().st_size >= _MIN_REAL_SOUL_BYTES, (
            f"{soul_id}.md is only {path.stat().st_size} bytes — stub, not persona"
        )


def test_seeded_souls_are_not_overwritten(wheel_install):
    """User edits (or a switched soul) must survive a later ensure_default_souls()."""
    from agent import soul_manager

    souls_dir = soul_manager.get_souls_dir()
    custom = souls_dir / "chiper-cyber.md"
    custom.write_text("# custom persona the user wrote\n", encoding="utf-8")

    soul_manager.ensure_default_souls()

    assert custom.read_text(encoding="utf-8") == "# custom persona the user wrote\n"


# ---------------------------------------------------------------------------
# Fresh-install regression: the generic first-run SOUL.md must never be used as
# a persona source. chiper_cli.config._ensure_default_soul_md() writes a ~0.5 KB
# "You are Chiper Agent ..." stub into CHIPER_HOME/SOUL.md on the first CLI or
# gateway call — before scripts/install.sh seeds ~/.chiper/souls/. Because the
# stub used to be candidate #1 for chiper-cyber, souls/chiper-cyber.md was
# seeded with the stub, and every later switch copied the stub back onto
# SOUL.md. Symptom: "/new lalu ganti jiwa" never changes the personality.
# ---------------------------------------------------------------------------


def _generic_stub() -> str:
    from chiper_cli.default_soul import DEFAULT_SOUL_MD

    return DEFAULT_SOUL_MD


def test_generic_first_run_soul_does_not_poison_cyber_persona(wheel_install):
    from agent import soul_manager

    chiper_home = soul_manager.get_chiper_home()
    (chiper_home / "SOUL.md").write_text(_generic_stub(), encoding="utf-8")

    soul_manager.ensure_default_souls()

    seeded = soul_manager.get_souls_dir() / "chiper-cyber.md"
    expected = (PACKAGED_SOULS / "chiper-cyber.md").read_text(encoding="utf-8")
    assert seeded.read_text(encoding="utf-8") == expected, (
        "chiper-cyber.md was seeded from the generic first-run SOUL.md stub"
    )


def test_real_user_soul_still_wins_as_cyber_source(wheel_install):
    """A hand-edited (non-stub) CHIPER_HOME/SOUL.md must keep winning."""
    from agent import soul_manager

    chiper_home = soul_manager.get_chiper_home()
    persona = "# SOUL.md — My Own Persona\n\n" + ("rule line\n" * 400)
    (chiper_home / "SOUL.md").write_text(persona, encoding="utf-8")

    soul_manager.ensure_default_souls()

    seeded = soul_manager.get_souls_dir() / "chiper-cyber.md"
    assert seeded.read_text(encoding="utf-8") == persona


def test_switch_soul_repairs_stub_seeded_soul(wheel_install):
    """An install already broken by the stub must self-heal on the next switch."""
    from agent import soul_manager

    chiper_home = soul_manager.get_chiper_home()
    (chiper_home / "SOUL.md").write_text(_generic_stub(), encoding="utf-8")
    stale = soul_manager.get_souls_dir() / "chiper-cyber.md"
    stale.write_text(_generic_stub(), encoding="utf-8")

    ok, _, _ = soul_manager.switch_soul("chiper-cyber")
    assert ok

    expected = (PACKAGED_SOULS / "chiper-cyber.md").read_text(encoding="utf-8")
    assert (chiper_home / "SOUL.md").read_text(encoding="utf-8") == expected


def test_switching_between_souls_actually_changes_soul_md(wheel_install):
    from agent import soul_manager

    soul_manager.ensure_default_souls()
    chiper_home = soul_manager.get_chiper_home()

    assert soul_manager.switch_soul("chiper-dev")[0]
    dev = (chiper_home / "SOUL.md").read_text(encoding="utf-8")

    assert soul_manager.switch_soul("chiper-hunt")[0]
    hunt = (chiper_home / "SOUL.md").read_text(encoding="utf-8")

    assert hunt != dev, "switching souls must change SOUL.md"
    assert "Chiper-Hunt" in hunt
    assert dev != hunt
