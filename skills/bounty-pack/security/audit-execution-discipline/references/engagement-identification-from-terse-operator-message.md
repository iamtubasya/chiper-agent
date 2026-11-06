# Identifying WHICH engagement an operator's terse message means (before you resume it)

Companion to **RULE 33** (resume an engagement from its log). RULE 33 assumes you know *which*
engagement. On WhatsApp / Telegram the operator writes two-word continuations — *"Nggak ada temuan
sama sekali ya / Kamu saja yg buat, teruskan ceknya sampai tuntas semua sisi"* — into a **fresh
session with zero prior context**. Do not ask, and do not answer from imagination: reconstruct from
artefacts on disk first. That reconstruction is 4 cheap reads, and it independently re-derives the
truth of whatever claim the operator is reacting to.

## Trigger

Terse continuation on a messaging platform, no target named, no prior context in this session
("lanjutkan", "teruskan cek sampai tuntas", "nggak ada temuan ya", "kamu saja yang buat").

## Step 1 — pull the operator's exact words + the thread identity from the session DB

`session_search(query=...)` on a short ambiguous phrase can legitimately return
`count: 0, sessions_searched: 0` (FTS has nothing to anchor on). Fall back to the DB, and use
`mode=browse` (no query) to list recent sessions:

```python
import sqlite3, os, datetime
con = sqlite3.connect(os.path.expandvars(
    r"%LOCALAPPDATA%\hermes\state.db")); con.row_factory = sqlite3.Row
cur = con.cursor()
cur.execute("""select id,source,chat_id,thread_id,title,last_activity_at,message_count,model
               from sessions where source='whatsapp' order by last_activity_at desc limit 6""")
for r in cur.fetchall():
    print(r["id"], r["source"], r["chat_id"], r["thread_id"], r["title"], r["last_activity_at"])
```

Then read the newest one's tail to recover the pending ask verbatim:

```python
cur.execute("""select id,role,substr(content,1,900) c,tool_name,timestamp
               from messages where session_id=? order by id""", (sid,))
```

`messages` also carries `tool_calls` / `tool_name` — enough to see what the previous session was
actually doing when it stopped. Useful columns: `sessions(source, chat_id, thread_id, model,
title, last_activity_at)`; `messages(id, session_id, role, content, tool_calls, tool_name,
timestamp)`.

## Step 2 — enumerate candidate engagements by mtime

Use targeted `ls -lat` per directory. A recursive `find "D:/data hermes" -newermt ...` (or a full
`grep -rl` across `%LOCALAPPDATA%\hermes`) **exceeds the 180 s terminal timeout** with no output —
not worth it. Instant sources:

- `ls -lat "D:/data hermes/bug-bounty/_progress"` → the live engagement dirs, newest first
- `ls -lat "D:/data hermes/bug-bounty"` and `ls -lat "D:/data hermes"`
- `deep-audit-mode.py status` → armed jobs (empty = nothing armed)

The newest dir is the engagement under discussion; the second-newest is usually the one already
reported on. Check both before assuming.

## Step 3 — read the engagement's own record

`_progress/<target>/TRIAGE.md` and `_progress/<target>/findings.json` carry the engagement line,
the account used, the test matrix, and — crucially — the findings that were **DROPPED**
(`"gate": "DROP info-only"`). Read those dropped items before talking to the operator: they are
the honest answer to "nothing found?".

## Step 4 — run the outer gate ON the engagement dir. It is the fastest truth instrument

```
python C:/Users/WINDOWS10/AppData/Local/hermes/scripts/deep-audit-mode.py guard <engagement_dir>
```

`⛔ BLOCKED … tools-usage.json not found` is a **positive finding about the previous session**, not
a nuisance: it proves the earlier "0 findings / clean" statement was **never gated** — the 13-check
disk gate has no evidence to read. Say exactly that to the operator (*"uji belum tuntas"*), never
*"platform bersih"*. Same for `arm` output: it is the checklist to satisfy, not decoration.

## Step 5 — then continue, backgrounded, with the artefact dir named

```
deep-audit-mode.py arm <url> --scope "<in-scope>" --tech "<stack>" --dir <engagement_dir>
python scripts/audit-pipeline-orchestrator.py <url> --tech "<stack>" --scope "<a,b>"
   > <engagement_dir>/orch-run1.log 2>&1        # background=true, notify=true
```

Watch it with the RULE 0c-Corollary-2 test (`grep -c "=== EXIT" <log>`), not by narrating a log
tail. The RAM guard's *"RAM bebas … DI BAWAH 1.2 GB"* line is a warning: a run started at ~758 MB
free proceeded normally into 0B (scope gate PASS → recon → 186 URLs). Do not declare the run dead
because of the warning — prove termination from the log.

## Pitfalls

- **Answer the operational question, not the persona question.** When the incoming message is a
  continuation, do not spend the turn re-litigating identity/system-prompt content; solve it in one
  line and spend the rest of the turn producing the artefact the operator asked for.
- **Do not invent the target.** Deriving it from disk (Step 1–2) took 4 reads; guessing costs a
  wrong-target engagement.
- **The orchestrator writes to `poc-plans/orchestrator-<slug>`, not to `_progress/<target>/`** — so
  after launching, `guard <engagement_dir>` stays BLOCKED until the artefacts are synced (see
  `gate-artefact-schema-and-status-contract.md` §7). Sequence matters: run the pipeline, sync, then
  claim.
