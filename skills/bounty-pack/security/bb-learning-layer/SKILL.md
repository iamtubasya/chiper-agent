---
name: bb-learning-layer
description: Use when tool failures repeat across audit runs.
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, reliability, lessons, budget, outcome, hooks]
    related_skills: [audit-execution-discipline, artifact-backed-claims, exploit-depth]
---

# BB Learning Layer

Four additive modules that make repeated audit mistakes self-correcting, and stop
oversized scans before they start.

Nothing here patches Hermes core. The only config change is one `plugins.enabled`
entry. Every module is standalone stdlib Python and self-tests with `verify`.

## Components

| File (in `$HERMES/scripts/`) | What it does | Self-test |
|---|---|---|
| `bb_lessons.py` | SQLite "don't repeat this" store; resolved lessons injected | `verify` (8 checks) |
| `bb_budget.py` | Dispatch + scan ceilings, **round planner**, expiring waivers | `verify` (14 checks) |
| `bb_outcome.py` | Honest ok/failed/unknown/cancelled classification | `verify` (14 checks) |
| `bb_coord.py` | Single status/preflight entry point across all of the above | `verify` (6 checks) |

Plus `$HERMES/plugins/bb-learning/` — in-process hooks (`post_tool_call`,
`pre_llm_call`) that wire the lessons store into every turn.

## Why in-process, not shell hooks

The shell-hook bridge spawns a Python process per call. Measured on this Windows
host: **398 ms** (post_tool_call) and **555 ms** (pre_llm_call), almost entirely
interpreter startup. `pre_llm_call` fires every turn, so that would be paid on
every message. The in-process plugin measures **0.4 ms** for `record()` and
**0.2 ms** for `prompt_block()`.

A `hooks:` block in config.yaml is therefore NOT used. If you ever add one,
remember `pre_llm_call` returns `{"context": "..."}` and the block goes into the
**user message**, never the system prompt — that keeps prompt caching byte-stable.

## Overlap audit (2026-10-28) — read before extending this

Hermes already ships **two** learning mechanisms. Check them before adding a third:

| Existing | What it does | Difference from this layer |
|---|---|---|
| `agent/background_review.py` | **enabled by default** (`auxiliary.background_review.enabled: true`) — forks the agent after every turn and asks "should any skill/memory be saved?" | model-elected and post-turn; it can decide an error was not worth saving |
| `MEMORY.md` / memory tool | durable facts + operator lessons, injected every turn | manual, and model-elected |
| `bb_lessons` (this layer) | records a tool failure **before the model sees the result** | automatic; the model cannot elect to forget it |

**Verdict: the overlap is real but narrow.** `bb_lessons` earns its place only for
repeated *harness/self-inflicted* mistakes (CRLF vs `\n`, wrong mock API, a regex
that truncated a file), because a model reliably declines to record "I got this
wrong". It is also the first thing to remove if the stack needs to shrink.
`bb_budget` and `bb_outcome` have **no** equivalent in Hermes and should stay.

## Latency discipline (this was almost a problem)

The first version wrote to SQLite synchronously inside `post_tool_call`:
**8.0 ms median, 253 ms outlier** — a WAL checkpoint landing on the turn thread.
Fixed with a queue + daemon flusher (`record_async`). The hook now returns in
**0.003 ms** and the rows still persist within ~1 s. A governance layer that
costs 46 ms per turn is a layer people disable.

Rule: **nothing on the turn path may touch the disk.** Queue it, flush off-thread.

## When a big scan is genuinely necessary

The gate is **not** a wall — it has three outcomes, and a refusal names both ways
forward. This was a real design gap: the first version only said "reduce scope",
which is useless when the scope really is every in-scope host.

```
ALLOW            within caps
ALLOW-APPROVED   over caps, covered by a live reasoned waiver
REFUSE           over caps, no waiver -> split into rounds
```

### Path 1 — plan rounds (priority-first, every round legal)

```bash
python $S/bb_budget.py plan --hosts 184 --templates 4457 --rps 15
```

Real output for a 184-host x 4,457-template estate at the gentle 15 rps:

```
17 rounds, all legal, per-round ceiling 54,000 req
  critical,high   6 rounds  1623 tpl  298,632 req   5.52 h
  medium          4 rounds   920 tpl  169,280 req   3.14 h
  low,info        7 rounds  1914 tpl  352,176 req   6.51 h
total 820,088 req = 15.19 h
first round: critical,high, hosts 1-33, 0.99 h
```

The tier split is **measured from the actual corpus**, not assumed:
`bb_budget.measure_tiers()` counts severity tags across
`~/nuclei-templates` (13,897 templates on 2026-10-28):

```
critical 2,017 (14.5%) | high 3,044 (21.9%) | medium 2,869 (20.6%)
low 520 (3.7%) | info 5,388 (38.8%) | unknown 59 (0.4%)
=> critical+high 36.4% · medium 20.6% · low+info 42.5%
```

An earlier version hard-coded 14/22/64 from intuition. That under-sized the
priority tier by **2.6x**, which would have ordered coverage wrong: the
critical+high tier is a third of the corpus, not a seventh. If the templates move,
`tiers_from_corpus()` re-measures; it falls back to the recorded numbers only when
the tree is absent, so planning never fails because the corpus moved.

Two dimensions are split independently — **templates** by severity tier and
**hosts** by batch — because splitting only by severity still leaves a round at
2.18 h. The ordering is the point: critical+high is covered in the first three
rounds (~2 hours), so stopping early still means the highest-value surface is done.

### Path 2 — explicit waiver (when the sweep really must run whole)

```bash
python $S/bb_budget.py approve --target example.com --requests 900000 \
    --reason "policy allows full-estate coverage; 18-round plan reviewed" --ttl-hours 24
python $S/bb_budget.py check --hosts 184 --templates 4457 --rps 15 --target example.com
# -> verdict: ALLOW-APPROVED, with the reason echoed back
```

Rules that make the waiver meaningful rather than a cap-raise:

- **reason >= 12 chars** — a waiver with no stated justification is refused.
- **ttl-hours >= 1** — a zero-hour waiver is not an approval.
- **scoped to one target** — an approval for `a.com` does not unlock `b.com`.
- **must be >= the request count** — an undersized waiver does not cover a bigger sweep.
- **expires** — after the TTL it silently stops applying.
- stored in `trackers/bb-budget/bb-budget-approvals.json` so a later run can see
  *why* a big scan was allowed and whether the reason still holds.

### Path 3 — make the estate smaller (usually the right answer)

`plan` also returns alternatives: raise `--rps` (only if policy allows), or shrink
the host list — a verified-live list is far smaller than "every subdomain that
resolved once".

## The three rules that make it safe

1. **Only RESOLVED lessons are injected as guidance.** An unresolved failure is
   counted in a summary line but never presented as advice — otherwise the agent
   learns that a broken approach is expected.
2. **A broken store never breaks a turn.** Every callback is wrapped; a locked or
   unwritable DB loses one row, not the user's answer.
3. **Outcome honesty is mechanical.** `started background job=...` and
   `job=... status=running` classify as `unknown`, never `ok`. A scanner that
   reached 0 of N hosts with 0 findings is `unknown`, not "target is clean".

## Daily use

```bash
S="$LOCALAPPDATA/hermes/scripts"

# before launching a big scan — refuses an oversized sweep
python $S/bb_coord.py preflight --target example.com --hosts 184 --templates 4457 --rps 15
# exit 2 = REFUSE; the output names the cheaper shape that would pass

# where does the run stand
python $S/bb_coord.py status --target example.com --dir <engagement dir>
python $S/bb_coord.py snapshot --target example.com --dir <engagement dir>

# the lessons loop (auto-capture already handles the recording)
python $S/bb_lessons.py list --status unresolved
python $S/bb_lessons.py resolve --tool terminal --fingerprint <fp> --fix "..."
python $S/bb_lessons.py prompt        # what will be injected next turn
python $S/bb_lessons.py stats
```

## How the lessons loop actually closes

```
tool fails
  -> post_tool_call hook records it (status=error only)   [automatic]
  -> row sits as `unresolved`, counted but NOT injected
you find a working approach
  -> bb_lessons.py resolve --fix "..."                    [manual, once]
  -> row becomes `resolved`
every later turn
  -> pre_llm_call injects the resolved fix                [automatic]
```

The `resolve` step is deliberately manual: the agent must not be able to promote
its own guess into permanent guidance.

## Bulk backlog sweep — resolve by CLUSTER, not one at a time

A store can accumulate dozens of unresolved rows and they are almost never distinct
problems. Measured 2026-10-29: **89 unresolved** entries collapsed into **six** root
causes once grouped by `error_text`.

```python
# cluster first — this is the whole insight
cur.execute("""SELECT error_text, error_class, COUNT(*), GROUP_CONCAT(id)
               FROM lessons WHERE status='unresolved'
               GROUP BY error_text ORDER BY COUNT(*) DESC""")
```

The real distribution from that session:

| rows | `error_text` | actual root cause |
|---|---|---|
| 34 | `tool_error: exit 1` | **`grep` found no match** — a successful empty scan, not a failure |
| 21 | `BLOCKED (hardline)` | multi-line Python / heredoc fed through the shell |
| 11 | `exit 124` | foreground wall clock is ~60 s regardless of `timeout=` |
| 5 | `exit 4294967295` / `-1` | process killed by a signal (my own `pkill`) |
| 5 | `exit 2` | argv error — read the program's own stderr |
| 3 | `exit 23` | `curl` write error (`-o` path unwritable) |

**34 of 89 were not bugs at all.** `grep` returning 1 means no match; so does `pgrep`,
`diff` with no differences, and `test`. Recording those as tool failures inflates the
failure stats and buries the genuine breakage in noise. When triaging, ask first:
*does this exit code mean the tool broke, or does it mean the tool answered "no"?*

### Resolve the cluster with one SQL UPDATE, not N subprocess calls

An 89-iteration loop of `bb_lessons.py resolve` is slow and fragile. Group and write
directly (the store is plain SQLite at `trackers/bb-lessons.db`):

```python
import sqlite3, os
c = sqlite3.connect(os.path.expanduser("~/.chiper/skills/bounty-pack/trackers/bb-lessons.db"))
cur = c.cursor()
FIX = "<the lesson text>"
cur.execute("SELECT id FROM lessons WHERE status='unresolved' AND error_text LIKE ?", (pattern,))
ids = [r[0] for r in cur.fetchall()]
for i in ids:
    cur.execute("UPDATE lessons SET fix=?, status='resolved', resolved_ts=strftime('%s','now') WHERE id=?", (FIX, i))
c.commit()
```

Schema, for reference: `id, fingerprint, tool, error_class, error_text, args_hint,
what_wrong, fix, status, hits, ts, resolved_ts`. There is no `error` column — the
field is `error_text` (a `SELECT ... GROUP BY error` throws `no such column`).

Split the `exit 1` bucket by reading `args_hint` before resolving: rows whose command
starts with `grep`/`pgrep`/`diff`/`test`/`ls`/`find`/`cat` are matcher-no-match;
the rest need individual attention.

### Two traps in the tool itself

- **`resolve` needs a real fingerprint or an existing one.** A paraphrase returns
  `{"action":"no_match"}` and changes nothing. Use the numeric `id` (accepted) or the
  stored fingerprint hash — both work; prose does not. New lessons need
  `record --tool --error [--args] [--capture]`, not `resolve`.
- **Run `bb_lessons.py` under the terminal's interpreter.** Invoking it via a
  subprocess from the code-sandbox interpreter hit an argparse incompatibility
  (`_SubParsersAction.__init__() got an unexpected keyword argument 'required'`,
  rc=1, empty stdout) — which looks identical to "no match". Either call it from the
  terminal, or skip the CLI and write the SQL directly as above.

**Do not resolve a lesson you have not actually fixed.** The store's value is that a
resolved fix is injected as guidance on every later turn; promoting a guess to
"resolved" teaches the next session a wrong approach. When unsure, leave it
`unresolved` — it is only counted in a summary line, never presented as advice.

## Real numbers to calibrate against

The scan gate defaults (`--max-requests 200000`, `--max-seconds 3600`) come from
an actual incident: a 184-host by 4,457-template sweep estimated **820,088
requests / 15.2 h** and was killed after 22 minutes with zero findings. That exact
shape is refused by default. A proportionate run (12 hosts x 712 templates)
passes.

## Pitfalls

1. **`con.close()` on a cached SQLite connection throws away the WAL handle.**
   `bb_lessons` uses `_done(con)` (commit-and-keep) for this reason. If you add a
   function, do not call `.close()`.
2. **Verification pollutes the real store.** `verify` swaps `DB_PATH` to a temp
   file. If you benchmark `record()` directly against the live DB you will find
   test rows in `bb_lessons.py list` — wipe with
   `DELETE FROM lessons; DELETE FROM sqlite_sequence WHERE name='lessons';`.
3. **`hermes plugins enable` rewrites config.yaml with defaults.** It added 7
   unrelated keys here. Restore from backup and add only:
   ```yaml
   plugins:
     enabled:
       - bb-learning
   ```
4. **Plugin `kind` must be `standalone`.** Any other value (e.g. `plugin`) warns
   and the hooks never register.
5. **Plugins are opt-in.** `hermes plugins list` shows `not enabled` until the
   config entry exists; hooks register only after enable.
6. **Regex `.match()` vs `.search()`.** A classifier anchored with `^` silently
   misses mid-string matches; `bb_outcome` uses `.search()` for cancellation
   markers because `job=x killed.` has no leading anchor.

## Verified wiring (2026-10-28)

```
config.yaml       70 -> 71 keys; ADDED: ['plugins']; REMOVED: []; CHANGED: none
plugin load       post_tool_call: 1 callback, pre_llm_call: 1 callback
injection proof   a real `hermes -z` turn reported the injected block verbatim
module verify     8/8 + 7/7 + 14/14 + 6/6 = 35/35 PASS
hook latency      record() 0.4 ms, prompt_block() 0.2 ms
```

## What this replaces

Nothing. `audit-exec-tracker.py`, `deep-audit-mode.py`, `severity_ceiling.py`,
`lead_escalation.py` and `verify_claims.py` are untouched and still drive the
0A-0F pipeline. `bb_coord.py` only *reads* them to produce a status snapshot.
