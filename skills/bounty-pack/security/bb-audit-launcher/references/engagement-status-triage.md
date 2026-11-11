# Engagement Status Triage — "cek status audit / mana yang belum jalan"

Report-only procedure for the recurring user question: *which audits ran, which are
still alive, which never started*. Written 2026-09-29 after two identical asks in one
day ("cek status audit yg td berjalan apa aja?" 17:40, "cek proses audit apa td selain
rapyd an quarterwise yg blm jalan" 22:15).

## 0. Output contract (user expectation)

- Plain text, terminal-renderable. No markdown tables with pipes-as-decoration; a
  simple aligned block per engagement is what the user reads.
- **Lead with "YANG BELUM JALAN"** — that is the actual question when phrased
  "yg blm jalan". Then the rest as status, then "TIDAK ADA ANTREAN LAIN" proof.
- Indonesian, short, evidence-cited (paths + timestamps). One `→ Next` with concrete
  options at the end; do not ask permission for read-only triage.
- Honesty rules: BLOCKED ≠ clean. UNREACHABLE ≠ tested-negative. Work that stopped
  mid-scan is "MATI PREMATUR", not "SELESAI". Deliverable exists on disk = selesai.

## 1. Where engagement state actually lives (check ALL of these)

| Source | Command / path | What it proves |
|---|---|---|
| Per-engagement dirs | `ls -la --time-style=long-iso "/d/data hermes/bug-bounty/_progress/"` | which engagements exist + last touch time |
| Engagement log | `_progress/<slug>/ENGAGEMENT_LOG.md` (tail) | last session's NEXT / TODO list |
| Candidates | `_progress/<slug>/findings.json` | real vs lead-only findings |
| Scan health | `ls -la _progress/<slug>/scans/` (`.err`, result `.txt`, `~/.config/nuclei/resume.cfg`) | dead vs finished scans |
| Other target roots | `D:/data hermes/<target>/` (e.g. `monarcaproject`, `rapyd-idp`) | engagements that never got a `_progress/` dir |
| Scheduled work | `cronjob action=list` + `grep -o '"name": "[^"]*"' ~/.chiper/skills/bounty-pack/cron/jobs.json` | anything still queued |
| Kanban queue | `kanban.db` → table `tasks` (usually 0 rows) | no queued audit tasks |
| Live processes | `process action=list` (Hermes bg jobs) + `tasklist \| grep -iE "nuclei\|ffuf\|gobuster\|sqlmap\|dalfox"` | nothing running right now |
| Session history | `state.db` recipe in §4 | what the user actually ordered today |

## 2. Health signals (the ones that catch a fake "done")

- `nuclei_scope.err` mtime frozen (compare with `date`) + result `.txt` = **0 bytes**
  + no `~/.config/nuclei/resume.cfg` → scan **DIED**, must restart from scratch.
  Report the exact progress (e.g. "328.646 / 1.279.200 req = 25%, 0 match, 29.975 err").
- Scanner harness that crashed (Playwright `TargetClosedError`) is a crash, not a result.
- A run whose only "hit" is a catch-all 200 must be content-verified before it counts
  (`dashboard.rapyd.net/config.json` looked like SPA fallback but the 10 KB body was a
  real config: `REACT_APP_ENV`, `PhysicalEnvironments`, `baseUrl`).
- Absence of an expected file is a finding in itself: `pro/probe_api.py` ready but
  `pro/api_key.txt` missing → the Pro matrix **belum jalan**, not "clean".
- Plan/harness files present + `results.json` showing an ERROR baseline (e.g. `B1 = ERROR
  "Pro belum aktif"`) = harness OK, execution blocked on an input from the user.

## 3. Verdict taxonomy (use these words)

- `SELESAI` — deliverable on disk (report PDF/md, findings.json, verdict doc).
- `JALAN (in progress)` — files touched in last ~24 h, harness alive.
- `MATI PREMATUR` — stopped mid-scan; state files frozen; needs explicit restart.
- `BLOCKED (environment)` — edge/WAF/geo refused the egress; scope of testing impossible
  without a new egress or a user-supplied session. State the blocker chain per egress
  path, and state explicitly what was never touched.
- `BELUM JALAN` — set up (dir/scripts/plan exist) but no real run happened.
- `DIHAPUS ATAS PERMINTAAN` — engagement finished and the user ordered the artifacts
  purged; the empty/absent dir is not an unfinished audit.

## 4. Reconstructing "what ran today" from the session DB

`session_search` reliably returns only a few recent sessions (browse gave 3 when 20+
existed, and an AND-joined FTS query returned 0 hits). For a complete inventory, query
the DB directly:

```bash
PY="/usr/bin/python3"
"$PY" - <<'EOF'
import sqlite3, datetime
c = sqlite3.connect(os.path.expanduser("~/.chiper/state.db"))
c.row_factory = sqlite3.Row
ts0 = datetime.datetime(2026,9,29,0,0).timestamp()      # epoch seconds!
for r in c.execute("select id,title,source,message_count,started_at,last_activity_at"
                   " from sessions order by last_activity_at desc limit 15"):
    f = lambda v: datetime.datetime.fromtimestamp(float(v)).strftime("%Y-%m-%d %H:%M")
    print(f'{f(r["started_at"])} -> {f(r["last_activity_at"])} | {r["source"]:9} |'
          f' {r["message_count"]:>4} | {r["title"]} | {r["id"]}')
for r in c.execute("select session_id,content,timestamp from messages"
                   " where role='user' and timestamp >= ? order by timestamp", (ts0,)):
    t = (r["content"] or "").replace("\n"," ")
    print(datetime.datetime.fromtimestamp(r["timestamp"]).strftime("%H:%M"), "::", t[:300])
EOF
```

- Schema: `sessions(id, source, title, started_at, last_activity_at, message_count, ...)`,
  `messages(id, session_id, role, content, timestamp, ...)`.
- **Pitfall that silently returns 0 rows:** `started_at` / `timestamp` are REAL epoch
  seconds, so `where started_at >= '2026-09-29'` matches nothing. Always convert with
  `datetime.fromtimestamp` (or compare against `datetime(...).timestamp()`).
- User rows with `role='user'` include Hermes' own background-process notifications —
  filter those out when reconstructing the human's ordering timeline.

## 5. Reporting skeleton

```
YANG BELUM JALAN — cuma 1: <TARGET>
  Program / Dir / Perintah (jam) / Status / Bukti (blocker chain) / Butuh apa
AUDIT LAIN — status jujur
  <target> — <verdict>: <evidence line>, <what is pending + why>
TIDAK ADA ANTREAN LAIN:
  cron: ... | kanban: 0 task | bg process: kosong | scanner proses: tidak ada
→ Next (a)(b)(c)(d): concrete, highest-value first
```
