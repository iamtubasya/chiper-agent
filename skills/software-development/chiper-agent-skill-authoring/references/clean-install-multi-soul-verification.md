# Clean-Install Multi-Soul and Memory Architecture

This reference documents the pitfalls, architecture, and verification protocol for ensuring that Multi-Soul personas and isolated soul memories initialize out-of-the-box on clean installations.

## The Problem: The Lazy Initialization Trap

When persona switching (`switch_soul`) and memory isolation are implemented as runtime features:
1. Systems often register initialization helpers (`ensure_default_souls`, `ensure_default_soul_memories`) inside user-facing commands (e.g. `/soul` or `/new`).
2. On a fresh installation (`curl ... | bash` or `./setup-chiper.sh`), the installer copies bundled skills via `tools/skills_sync.py` and creates a default config.
3. However, if the installer does not explicitly trigger soul initialization, the directory `~/.chiper/souls/` and `~/.chiper/memories/souls/` remain uncreated.
4. If the installer falls back to writing a dummy template into `~/.chiper/SOUL.md` (e.g. 15-line `# Chiper Agent Persona` stub), the agent boots into a generic identity rather than the intended default persona (`chiper-cyber.md`).
5. Furthermore, `~/.chiper/memories/MEMORY.md` remains unpopulated with the default curated operational context.

## The Solution: Two-Layer Defense

### 1. Installer-Level Provisioning (`setup-chiper.sh` & `scripts/install.sh`)
At the conclusion of the setup script (after venv creation and skill sync), run an explicit Python one-liner:

```bash
"$SCRIPT_DIR/venv/bin/python" -c "
from agent.soul_manager import ensure_default_souls, ensure_default_soul_memories, switch_soul
ensure_default_souls()
ensure_default_soul_memories()
switch_soul('chiper-cyber')
" 2>/dev/null || true
```

This guarantees that:
- `~/.chiper/souls/` contains `chiper-cyber.md`, `chiper-dev.md`, and `chiper-web3.md`.
- `~/.chiper/memories/souls/` contains the pre-curated memory files for each persona.
- `~/.chiper/SOUL.md` is populated with the complete Chiper-Cyber identity (~12.7 KB).
- `~/.chiper/memories/MEMORY.md` is initialized with Chiper-Cyber's active memory (~1.3 KB).

### 2. Runtime Self-Healing Fallbacks

Never assume the filesystem remains untouched post-install. Users or automated scripts may delete `~/.chiper/SOUL.md` or clear memory.

**In `agent/prompt_builder.py` (`load_soul_md()`):**
```python
soul_path = get_chiper_home() / "SOUL.md"
if not soul_path.exists():
    try:
        from agent.soul_manager import ensure_default_souls, switch_soul
        ensure_default_souls()
        switch_soul("chiper-cyber")
    except Exception:
        pass
```

**In `tools/memory_tool.py` (`MemoryStore.load_from_disk()`):**
```python
mem_dir = get_memory_dir()
mem_dir.mkdir(parents=True, exist_ok=True)
if not (mem_dir / "MEMORY.md").exists():
    try:
        from agent.soul_manager import ensure_default_soul_memories, get_active_soul, get_soul_memory_path
        ensure_default_soul_memories()
        active = get_active_soul()
        s_id = active.get("id", "chiper-cyber")
        s_path = get_soul_memory_path(s_id)
        if s_path.exists():
            shutil.copy2(s_path, mem_dir / "MEMORY.md")
    except Exception:
        pass
```

## Clean Installation Verification Script

Run this test in a temporary mock environment to verify that a fresh install initializes all souls, isolated memories, and bundled skills without error:

```python
import tempfile, os, subprocess, sys
from pathlib import Path

mock_home = Path(tempfile.mkdtemp())
os.environ['CHIPER_HOME'] = str(mock_home)

env = os.environ.copy()
env['PYTHONPATH'] = '/path/to/chiper-repo'

# 1. Sync skills
subprocess.check_call([sys.executable, '/path/to/chiper-repo/tools/skills_sync.py'], env=env)

# 2. Init souls & memories
subprocess.check_call([sys.executable, '-c', '''
from agent.soul_manager import ensure_default_souls, ensure_default_soul_memories, switch_soul
ensure_default_souls()
ensure_default_soul_memories()
switch_soul("chiper-cyber")
'''], env=env)

# 3. Assertions
assert (mock_home / "SOUL.md").stat().st_size > 5000
assert len(list((mock_home / "souls").glob("*.md"))) >= 3
assert len(list((mock_home / "memories" / "souls").glob("*.md"))) >= 3
assert (mock_home / "memories" / "MEMORY.md").stat().st_size > 500
```
