# Which Agent `.md` Files Are Actually Loaded — Runtime Truth

Verified by reading source in `chiper/agent/prompt_builder.py`, `chiper/agent/system_prompt.py`,
and `chiper/tools/memory_tool.py` (2026-11-08). Use this whenever an operator asks "which file
should I edit?" or after auditing a pack and finding many `.md` files that *look* authoritative.

## The authoritative list — only 3 files affect behaviour

| File | Path | Loader | Tier |
|---|---|---|---|
| `SOUL.md` | `~/.chiper/SOUL.md` | `prompt_builder.load_soul_md()` → identity slot | **stable** (cached) |
| `MEMORY.md` | `~/.chiper/memories/MEMORY.md` | `memory_tool.format_for_system_prompt("memory")` | **volatile** (frozen snapshot) |
| `USER.md` | `~/.chiper/memories/USER.md` | `memory_tool.format_for_system_prompt("user")` | **volatile** (frozen snapshot) |

Plus **exactly one** project-context file, first match wins, from the CWD:

| Priority | Name | Scope |
|---|---|---|
| 1 | `.chiper.md` / `CHIPER.md` | walks to git root |
| 2 | `AGENTS.md` / `agents.md` | cwd only |
| 3 | `CLAUDE.md` / `claude.md` | cwd only |
| 4 | `.cursorrules` / `.cursor/rules/*.mdc` | cwd only |

`prompt_builder.build_context_files_prompt()` uses `or` chaining — **only one** of those four is
loaded. Loading `AGENTS.md` means `CLAUDE.md` is silently ignored, not merged.

## Source evidence

`agent/prompt_builder.py`:

```python
soul_path = get_chiper_home() / "SOUL.md"          # line ~1656
project_context = (
    _load_chiper_md(cwd_path, context_length)
    or _load_agents_md(cwd_path, context_length)
    or _load_claude_md(cwd_path, context_length)
    or _load_cursorrules(cwd_path, context_length)
)
```

`agent/system_prompt.py`:

```python
if agent._memory_store:
    if agent._memory_enabled:
        mem_block  = agent._memory_store.format_for_system_prompt("memory")
    if agent._user_profile_enabled:
        user_block = agent._memory_store.format_for_system_prompt("user")
```

`tools/memory_tool.py`:

```python
def get_memory_dir() -> Path:
    return get_chiper_home() / "memories"        # line ~57

self.memory_entries = self._read_file(mem_dir / "MEMORY.md")
self.user_entries   = self._read_file(mem_dir / "USER.md")
```

## `TOOLS.md` is not loaded by the runtime

```
grep -rn 'TOOLS.md' chiper/agent/ chiper/tools/ chiper/cli/ --include=*.py   → 0 hits
```

It is referenced only by *prose* in skill-pack docs (`AGENTS.md` startup sequences, `SKILL.md`
architecture diagrams). An operator who edits `~/.chiper/TOOLS.md` expecting behaviour change gets
nothing — and a poisoned `TOOLS.md` never actually reaches the model unless something else quotes it.

Same for the rest of the CHIPER_HOME tree:

| Path | Status |
|---|---|
| `~/.chiper/souls/<id>.md` | ⚪ source only — copied **to** `~/.chiper/SOUL.md` on `switch_soul()` |
| `~/.chiper/memories/souls/<id>.md` | ⚪ source only — copied **to** `~/.chiper/memories/MEMORY.md` |
| `~/.chiper/sessions/*.md` | ❌ archive (can be hundreds of KB of transcript) |
| `~/.chiper/cache/documents/*_SOUL.md` | ❌ cache snapshots, often stale |
| `~/.chiper/skills/**/*.md` | ❌ only via explicit `skill_view()` |

## The snapshot trap — edits do not apply mid-session

`memory_tool.format_for_system_prompt()` (line ~589) returns the state captured at
`load_from_disk()` time, **not** live state. Documented in the code itself:

> "This returns the state captured at load_from_disk() time, NOT the live state. Mid-session
> writes do not affect this. This keeps the system prompt stable across all turns, preserving
> the prefix cache."

Consequence: after patching `USER.md` or `MEMORY.md`, the change **only lands in a new session**.
Tell the operator to `/new` or restart the gateway; do not claim the edit is already in effect.
This is deliberate (cache preservation), not a bug — do not try to "fix" it.

`SOUL.md` is read at prompt-build time per the `stable` tier, so that one does apply on rebuild.

## Audit recipe

```bash
# 1. Which files exist at CHIPER_HOME root
find ~/.chiper -maxdepth 1 -name '*.md'

# 2. All .md outside skills/ and node_modules (the real config surface)
find ~/.chiper -type f -name '*.md' \
  -not -path '*/lsp/node_modules/*' -not -path '*/skills/*' | sort

# 3. Prove TOOLS.md is dead
grep -rn 'TOOLS.md' chiper/agent/ chiper/tools/ --include=*.py

# 4. Prove the memory dir path
grep -n 'def get_memory_dir' -A 3 chiper/tools/memory_tool.py

# 5. Which project context wins in this CWD
for f in .chiper.md CHIPER.md AGENTS.md agents.md CLAUDE.md claude.md .cursorrules; do
  [ -f "$f" ] && echo "PRESENT $f"
done
```

## Reporting shape that worked

Present a two-column verdict table rather than a tree — operators act on it immediately:

| File | Runtime status |
|---|---|
| `~/.chiper/SOUL.md` | ✅ active, stable tier |
| `~/.chiper/memories/MEMORY.md` | ✅ active, volatile |
| `~/.chiper/memories/USER.md` | ✅ active, volatile |
| `~/.chiper/TOOLS.md` | ❌ dead — 0 code references |
| `~/.chiper/souls/*.md` | ⚪ copy source |
| `~/.chiper/sessions/*.md` | ❌ archive |

Then state explicitly which file the operator must edit for the change they want. The recurring
failure mode is an operator (or a previous agent) editing the in-pack `USER.md` / `TOOLS.md` under
`skills/<pack>/` and assuming it takes effect — those are copies, and the runtime copy lives under
`~/.chiper/memories/`.
