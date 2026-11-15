# Living Report Loop — time-budgeted continuous engagements

For engagements where the user says *"keep digging for N hours, add every finding to the
report as you go"*. The deliverable **accretes**, and the hunt is long enough that a single
session will hit context limits. Hand-editing the report text each time drifts and loses
findings; a structured store + a renderer keeps it honest and lets a fresh session append
deterministically.

## Architecture (build once, reuse every tick)

```
findings.json   ──source of truth (findings, positives, coverage, queue)
     │
build_report.py ──renders draft_body.txt FROM findings.json   (never hand-edit the body)
     │
deliver.py      ──idempotent push of draft_body.txt to the delivery channel
     │
cron job        ──every N min × M ticks: investigate → append → rebuild → deliver
```

Nothing else touches `draft_body.txt` — if it isn't in `findings.json`, it isn't in the
report.

## findings.json schema (keep it small and rigid)

```json
{
  "subject": "...", "scope": "...", "headline": "...", "updated": "<iso8601>",
  "findings": [{"id":"F1","sev":"MEDIUM|LOW|INFO|HIGH|CRITICAL","title":"...",
                "obs":["evidence lines, exact URLs/headers/response snippets"],
                "impact":["..."], "fix":["..."], "refs":["..."]}],
  "positives": ["controls working — keeps the report credible and balanced"],
  "coverage": [{"status":"done|pending","area":"...","note":"one line"}],
  "queue": ["next areas to examine"]
}
```

`coverage[]` is the anti-repeat mechanism: a **documented negative** ("12 marketing JS
chunks fetched, no secrets/endpoints found") stops the next tick re-doing it. Always log
negatives — never invent findings to fill space.

## Idempotent delivery — Gmail draft (create-or-update)

The Google Workspace skill is bundled/protected; replicate the pattern in your own script.
Token lives at `$HERMES_HOME/google_token.json` (check `setup.py --check` → `AUTHENTICATED`).
Build the MIME body, `urlsafe_b64encode`, then **update the existing draft if you have its
id, else create**:

```python
state = Path(BASE)/"draft_state.json"          # {"draft_id": "..."}
did = json.loads(state.read_text()).get("draft_id") if state.exists() else None
if did: s.users().drafts().update(userId="me", id=did, body={"message":{"raw":raw}}).execute()
else:   d = s.users().drafts().create(userId="me", body={"message":{"raw":raw}}).execute()
        state.write_text(json.dumps({"draft_id": d["id"]}))
```

Set `To`/`Subject` as MIME headers and **do not** repeat them in the body — the renderer
should start at the greeting. Keep ONE draft per engagement; a fresh draft per tick
fragments the report.

## Cron continuation (the "for N hours" part)

You cannot hold a turn open for hours. Hand the continuation to cron with a
**self-contained prompt** (fresh session, no chat context):

- Point it at the state dir + each script's exact path/command.
- Give it the **program rules inline** (in-scope assets, and any bans: no scanners, no
  brute force, no authenticated testing, no touching other tenants' data) so an
  unsupervised tick can't drift out of authorization.
- Tell it to read `coverage[]`/`queue[]`, pick ONE–TWO areas, investigate with real
  tooling, append findings **or log negatives**, rebuild, deliver, and report what it did.
- `schedule` every ~15m, `repeat` = ticks (15m × 12 = 3h), `deliver: origin` so results
  land back in the chat.

Verify the first tick actually updated the draft (it prints `UPDATED draft=…` / `CREATED
draft=…`) — a silent render failure looks identical to "nothing found".

## Pitfalls

- **MSYS path trap (Windows host).** `curl -o /tmp/x` writes via git-bash, but a *native*
  Windows Python invoked from the same shell resolves `/tmp/x` to `C:\tmp\x` and fails
  with `FileNotFoundError`. Either use a native path (`D:\...`) or pipe the payload:
  `curl -s URL | python -c "import sys; h=sys.stdin.read(); ..."`. Inline heredocs
  (`python - <<'PY' … PY`) also work and avoid the quoting mess.
- **Single-quoted JSON.** When building `findings.json` by hand, JSON strings must use
  `"` with escaped inner quotes (`"{\"status\":\"healthy\"}"`). `'{"a":1}'` is invalid and
  the renderer will refuse. Validate with `python -c "import json;json.load(open(...))"`
  before rendering.
- **Keep the loop inside program rules.** If the target's policy bans automated scanners,
  the cron prompt must say so explicitly — an unsupervised tick is exactly where a
  scanner run would slip through and void the engagement.
- **Regenerate, never patch the body.** If a number in the report is wrong, fix
  `findings.json` and re-render; editing `draft_body.txt` guarantees drift on the next tick.
