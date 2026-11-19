"""Integration guard: the vendored chiper-dev design bundle must never ship half-way.

The bundle is a vendored copy of `nextlevelbuilder/ui-ux-pro-max-skill` (MIT),
merged into the Chiper-Dev soul as eight sub-skills under `skills/chiper-dev/`.

What this file locks down — every one of these was a real risk when vendoring:

1. **Every sub-skill present** with a matching frontmatter name.
2. **Catalog data present AND tracked by git.** The repo's global `.gitignore`
   has a bare `data/` rule that matches at any depth, so the ~55 CSVs the
   design engine reads were one `git add` away from being silently dropped —
   the scripts would ship, the data would not, and `search.py` would return
   empty results on every fresh install.
3. **No `${CLAUDE_PLUGIN_ROOT}` left.** Upstream paths point at the Claude
   plugin root; in Chiper they must resolve through `${CHIPER_HOME:-$HOME/.chiper}`.
4. **The engine actually runs** — a real subprocess call, not a mock.
5. **Soul wiring** — Chiper-Dev sees the bundle, the other souls do not, and
   ownership resolves to chiper-dev (not chiper-cyber via the `chiper-` prefix).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLE = REPO_ROOT / "skills" / "chiper-dev"
UIUX = BUNDLE / "chiper-dev-uiux"

# upstream skill dir -> vendored dir
EXPECTED_SKILLS = {
    "chiper-dev-uiux": "ui-ux-pro-max",
    "chiper-dev-design-system": "design-system",
    "chiper-dev-design-assets": "design",
    "chiper-dev-design-brand": "brand",
    "chiper-dev-design-banner": "banner-design",
    "chiper-dev-design-slides": "slides",
    "chiper-dev-ui-styling": "ui-styling",
}

# The 22 stack tables upstream ships; losing any of them silently disables
# stack-specific guidance for that framework.
EXPECTED_STACKS = {
    "angular", "astro", "avalonia", "flutter", "html-tailwind", "javafx",
    "jetpack-compose", "laravel", "nextjs", "nuxt-ui", "nuxtjs", "react",
    "react-native", "shadcn", "svelte", "swiftui", "threejs", "uno", "uwp",
    "vue", "winui", "wpf",
}


# --------------------------------------------------------------------------
# 1. Structure
# --------------------------------------------------------------------------


def test_every_bundled_skill_exists_with_matching_name():
    assert BUNDLE.is_dir(), f"missing bundle dir: {BUNDLE}"
    assert (BUNDLE / "SKILL.md").is_file(), "router SKILL.md missing"
    assert (BUNDLE / "SOUL.md").is_file(), "bundle SOUL.md missing"

    for skill_dir, upstream in EXPECTED_SKILLS.items():
        path = BUNDLE / skill_dir / "SKILL.md"
        assert path.is_file(), f"{skill_dir}/SKILL.md missing (upstream: {upstream})"
        text = path.read_text(encoding="utf-8")
        assert re.search(rf"(?m)^name:\s*{re.escape(skill_dir)}\s*$", text), (
            f"{skill_dir}/SKILL.md frontmatter name was not rewritten"
        )
        # upstream leftovers would point at a directory that does not exist here
        assert "CLAUDE_PLUGIN_ROOT" not in text


def test_scripts_and_assets_travel_with_the_skills():
    assert (UIUX / "scripts" / "search.py").is_file()
    assert (UIUX / "scripts" / "design_system.py").is_file()
    assert (BUNDLE / "chiper-dev-design-system" / "scripts" / "validate-tokens.cjs").is_file()
    assert (BUNDLE / "chiper-dev-design-assets" / "scripts" / "logo" / "generate.py").is_file()
    # ui-styling ships 54 canvas fonts used by the canvas design system
    fonts = list((BUNDLE / "chiper-dev-ui-styling" / "canvas-fonts").glob("*.ttf"))
    assert len(fonts) >= 50, f"expected the canvas font pack, found {len(fonts)} ttf files"


# --------------------------------------------------------------------------
# 2. Catalog data — present on disk AND tracked by git
# --------------------------------------------------------------------------


def test_catalog_csvs_present_on_disk():
    data = UIUX / "data"
    assert data.is_dir(), "ui-ux-pro-max data/ catalog missing"
    csvs = list(data.glob("*.csv"))
    assert len(csvs) >= 12, f"top-level catalog only has {len(csvs)} CSVs"

    stacks = {p.stem for p in (data / "stacks").glob("*.csv")}
    assert stacks == EXPECTED_STACKS, f"stack tables mismatch: {sorted(EXPECTED_STACKS ^ stacks)}"

    for required in ("colors.csv", "landing.csv", "products.csv", "google-fonts.csv", "icons.csv", "motion.csv"):
        assert (data / required).is_file(), f"catalog file missing: {required}"


def test_catalog_csvs_are_tracked_by_git():
    """The `.gitignore` `data/` rule must not swallow the catalog.

    Runs `git ls-files`; skipped when the test tree is not a git checkout
    (e.g. installed from a wheel) since there is nothing to track there.
    """
    if not (REPO_ROOT / ".git").exists():
        return

    out = subprocess.run(
        ["git", "ls-files", "skills/chiper-dev"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if out.returncode != 0:
        return  # not a usable git environment — nothing to assert

    tracked = out.stdout.splitlines()
    tracked_data = [p for p in tracked if "/data/" in p and p.endswith(".csv")]
    assert len(tracked_data) >= 40, (
        "the design catalog CSVs are not tracked by git "
        f"({len(tracked_data)} tracked) — the repo `.gitignore` `data/` rule is "
        "swallowing them and fresh installs will run search.py against an empty "
        "catalog. Add `!skills/chiper-dev/**/data/` + `!skills/chiper-dev/**/data/**`."
    )

    untracked = subprocess.run(
        ["git", "status", "--porcelain", "--ignored", "skills/chiper-dev"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    ).stdout
    assert "!! skills/chiper-dev/chiper-dev-uiux/data/" not in untracked, (
        "git reports the uiux data/ catalog as ignored"
    )


# --------------------------------------------------------------------------
# 3. Portability — no upstream plugin-root paths
# --------------------------------------------------------------------------


def test_no_claude_plugin_root_references_anywhere_in_bundle():
    offenders = []
    for path in BUNDLE.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".py", ".cjs", ".json", ".txt"}:
            continue
        try:
            if "CLAUDE_PLUGIN_ROOT" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(BUNDLE)))
        except UnicodeDecodeError:
            continue
    assert not offenders, f"upstream plugin paths survived in: {offenders[:5]}"


def test_hardcoded_home_paths_absent_from_docs():
    """Skills must stay server-agnostic: no /home/<someone>/ baked in."""
    offenders = []
    for path in BUNDLE.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"/home/[a-z_][a-z0-9_-]*/", text) or "/Users/" in text:
            offenders.append(str(path.relative_to(BUNDLE)))
    assert not offenders, f"hardcoded home paths in: {offenders[:5]}"


# --------------------------------------------------------------------------
# 4. The engine actually runs (real subprocess, real catalog)
# --------------------------------------------------------------------------


def test_search_py_design_system_returns_a_real_design_system():
    result = subprocess.run(
        [sys.executable, str(UIUX / "scripts" / "search.py"),
         "beauty spa wellness service", "--design-system", "-p", "Serenity Spa"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, f"search.py failed: {result.stderr[-800:]}"
    out = result.stdout
    assert re.search(r"#[0-9A-Fa-f]{6}", out), "no hex palette in design-system output"
    assert "Serenity Spa" in out
    assert len(out) > 800, "design-system output looks truncated"


def test_search_py_domain_and_stack_queries_work():
    for args in (["keyboard focus modal", "--domain", "ux"],
                 ["fintech dashboard", "--domain", "color"],
                 ["suspense streaming bundle", "--stack", "nextjs"]):
        result = subprocess.run(
            [sys.executable, str(UIUX / "scripts" / "search.py"), *args],
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, f"search.py {args} failed: {result.stderr[-500:]}"
        assert result.stdout.strip(), f"search.py {args} returned nothing"


# --------------------------------------------------------------------------
# 5. Soul wiring
# --------------------------------------------------------------------------


def test_dev_soul_sees_bundle_and_other_souls_do_not():
    from agent.soul_manager import is_skill_allowed_for_soul

    assert is_skill_allowed_for_soul("chiper-dev", "chiper-dev", "chiper-dev-uiux")
    assert is_skill_allowed_for_soul("chiper-dev", "chiper-dev", "chiper-dev-ui-styling")

    assert not is_skill_allowed_for_soul("chiper-cyber", "chiper-dev", "chiper-dev-uiux")
    assert not is_skill_allowed_for_soul("chiper-hunt", "chiper-dev", "chiper-dev-uiux")
    assert not is_skill_allowed_for_soul("chiper-web3", "chiper-dev", "chiper-dev-uiux")


def test_bundle_ownership_resolves_to_chiper_dev():
    from agent.soul_manager import get_soul_for_skill

    assert get_soul_for_skill("chiper-dev", "chiper-dev-uiux") == "chiper-dev"
    assert get_soul_for_skill("chiper-dev", "chiper-dev-design-brand") == "chiper-dev"


def test_dev_persona_documents_the_bundle():
    """The persona and the packaged copy must stay identical and mention design."""
    bundled = REPO_ROOT / "agent" / "bundled_souls" / "chiper-dev.md"
    canonical = BUNDLE / "SOUL.md"
    assert canonical.is_file() and bundled.is_file()

    text = canonical.read_text(encoding="utf-8")
    assert text == bundled.read_text(encoding="utf-8"), (
        "skills/chiper-dev/SOUL.md and agent/bundled_souls/chiper-dev.md diverged — "
        "fresh installs would seed a different persona than editable installs"
    )
    assert "Design Intelligence" in text
    for skill_dir in EXPECTED_SKILLS:
        assert skill_dir in text, f"persona routing table missing {skill_dir}"
    assert len(text.encode("utf-8")) >= 4000
