# Telemetry Sources — Paths, Schemas, Semantics

Verified against a live Chiper install on Linux (2026-11-08).

## 1. Lifetime counters — `~/.chiper/skills/.usage.json`

Written by `tools/skill_usage.py`, bumped from `tools/skills_tool.py::_skill_view_with_bump`
(view + use) and from `skill_manage` (patch). Atomic writes via tempfile + `os.replace`,
guarded by `fcntl` lock. ~20 KB for 51 records.

Record shape (one dict per skill name):

```json
{
  "agent-web-api-integration": {
    "archived_at": null,
    "created_at": "2026-11-06T14:27:54.182701+00:00",
    "created_by": null,
    "last_patched_at": "2026-11-08T10:25:41.205761+00:00",
    "last_used_at": "2026-11-08T10:25:25.394233+00:00",
    "last_viewed_at": "2026-11-08T10:25:25.391727+00:00",
    "patch_count": 7,
    "pinned": false,
    "state": "active",
    "use_count": 17,
    "view_count": 17
  }
}
```

Field semantics:

| Field | Meaning | Caveat |
|---|---|---|
| `view_count` | `skill_view` calls that returned success | lifetime, never decayed |
| `use_count` | bumped in the same call as `view_count` — **not** an independent signal | treat as duplicate of view_count |
| `patch_count` | `skill_manage` patch/edit calls | high count = unstable skill |
| `last_used_at` / `last_viewed_at` | ISO-8601 UTC | drives curator staleness |
| `state` | `active` / `stale` / `archived` | curator-managed only |
| `created_by` | `"agent"` opts into curator lifecycle | bundled/hub skills are `null` |

**Known defect — name forking.** Keys are whatever string was passed to `skill_view`.
Qualified plugin form (`plugin:skill`) produces a *separate* record from the bare name:

```
chiper-security-bounty-hunter                  view=27
chiper-cyber:chiper-security-bounty-hunter     view=1     <- same skill
```

Aggregate with `k.split(":")[-1]`. Do not delete the short record — it carries a
different `last_used_at`.

## 2. Executor log — `~/.chiper/logs/agent.log*`

Rotated at 5 MB. On a busy install expect `agent.log`, `.1`, `.2`, `.3` (~20 MB total).
Newest entries are in the file **without** a numeric suffix; the `.1` file is *older*
than `agent.log` but *newer* than `.2`. Always sort by parsed timestamp, never by filename.

Line format:

```
2026-11-08 20:01:11,228 INFO [20261108_193158_4597e646] agent.tool_executor: tool skills_list completed (0.21s, 51342 chars)
2026-11-08 20:02:12,242 WARNING [20261108_193158_4597e646] agent.tool_executor: Tool skill_view returned error (0.14s): {"success": false, "error": "File 'references/x.md' not found in skill 'y'."}
```

- Bracket group = session id, matching `state.db.messages.session_id`.
- `chars` = size of the tool result payload that entered context. **This is the only
  place token cost is measurable.** Tokens ≈ `chars / 4`.
- Success lines say `tool X completed`, failures say `Tool X returned error` — note the
  capital `T` on the failure form, which is why one regex misses them.
- Non-skill noise (gateway inbound messages, turn context) shares the file; filter on
  a case-insensitive `skill` substring *and* on the tool regexes.

Reference numbers from a real 5-day window: 636 skill-related lines → 515 parsed calls
(217 `skill_view`, 216 `skill_manage`, 67 `skills_list`), avg `skill_view` payload
13 284 chars, total 2.87 M chars ≈ 717 k tokens, avg duration 0.127 s.

## 3. Session store — `~/.chiper/state.db`

SQLite. Tables: `schema_version`, `sessions`, `messages`, plus FTS5 mirrors
(`messages_fts*`, `messages_fts_trigram*`).

`messages` columns that matter:

| Column | Type | Note |
|---|---|---|
| `id` | INTEGER PK | |
| `session_id` | TEXT | e.g. `20261108_193158_4597e646` |
| `role` | TEXT | `user` / `assistant` / `tool` |
| `content` | TEXT | tool result body for `role='tool'` |
| `tool_name` | TEXT | populated on `role='tool'` rows |
| `tool_calls` | TEXT | JSON array on `role='assistant'` rows |
| `timestamp` | REAL | unix epoch float |
| `active` | INTEGER | 1 = still in context |

Query for skill loads:

```sql
SELECT id, session_id, tool_calls, timestamp
FROM messages
WHERE role = 'assistant' AND tool_calls LIKE '%"skill_view"%'
ORDER BY timestamp;
```

Each row's `tool_calls` is a list of `{"function": {"name": ..., "arguments": "<json string>"}}`.
Arguments must be JSON-decoded **twice** (outer array, then the string).

### Traps

- `~/.chiper/sessions/sessions.db` **exists but has no tables** — an empty stub. Using it
  returns `[]` from `sqlite_master` and looks like "no data". The real store is `state.db`.
- `sqlite3` CLI is often not installed. Use Python's stdlib `sqlite3` instead of shelling
  out; there is no reason to apt-install it for a read-only audit.
- `state.db` is pruned by `chiper sessions prune`, so its counts are a **lower bound**
  on lifetime activity. That is exactly why `.usage.json` exists.

## Reconciling

| Question | Trust |
|---|---|
| Total lifetime loads per skill | `.usage.json` (after normalising forked keys) |
| Which session / what arguments | `state.db` |
| Cost per load, errors, durations | `agent.log` |

A `.usage.json` `view_count` higher than the log-derived count means history was pruned
or the log rotated away — both expected, neither is a bug. Report the delta, don't average.
