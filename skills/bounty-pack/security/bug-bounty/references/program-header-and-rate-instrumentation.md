# Instrumenting program-mandated request headers + gentle mode (policy compliance layer)

Some policies make an identifying header a CONDITION of the authorization — finanzen.net
(`.well-known/bugbounty.txt`, v1.0): *"Researchers must add headers to requests identifying their
testing activity: `X-BugBounty-Researcher: <Pseudonym or E-Mail>`"*. Missing it can void the
engagement (other programs dock up to 50% for persistently unidentified traffic — see
`bot-protected-target-testing` section3.0). Every request must carry it, **including every
scanner invocation** — a hand-written curl list is easy; a 30-tool pipeline is not.

## Design: one in-process injector, installed additively

A module like `scripts/bbr_header.py` (pattern below) monkeypatches the TWO ways the pipeline
launches requests, inside the main process:

```python
install()  # idempotent:
#  subprocess.run / subprocess.Popen  -> inject the flag into the command (string or argv form)
#  urllib.request.Request.__init__    -> headers.setdefault(NAME, IDENT)
```

Wire it ADDITIVELY into every script that spawns tools (operator rule: old systems are modified
additively — never rewritten):

```python
# --- additive: vendor program rule: send X-BugBounty-Researcher on every request ---
try:
    import bbr_header as _bbr
    _bbr.install()
except Exception:
    pass
# --- end additive header hook ---
```

Insert right after the import block of the pipeline orchestrator, force-full-execution,
tool_router, scope_checker — and any child script that spawns its OWN subprocesses (the hook is
per-process, so a child that starts its own tools needs the same five lines). Scripts invoked as
`python <abs path>` get their own directory on `sys.path`, so the module only has to live there.
In-process urllib probes pick the header up for free through the `Request.__init__` hook.

## Injection rules for shell-string commands (all hit during live use)

- **Quoted exe path** (`"C:\go\bin\nuclei.exe" -tpl ...`): insert the flag AFTER the closing quote.
- **Bare token in command position only**; skip when the preceding word is
  `grep/echo/python/tee/cat/sed/...` — a pipe segment is not a launcher
  (`cat x | grep nuclei` must stay untouched).
- **Never double-inject** (skip when the header name already appears in the command).
- List-argv form: insert after `argv[0]` when its basename matches a known tool; skip when the
  previous element is `-m`.
- **Failure direction**: on any doubt run the command UNMODIFIED — a missing header is a policy
  miss, a broken command is a dead audit. Wrap injection in try/except; never raise.

## Verified flag syntax (check with `-version` / `--version` BEFORE wiring; a wrong flag kills the run)

| tools | flag |
|---|---|
| nuclei, ffuf, httpx, katana, dalfox, curl | `-H "Name: value"` |
| sqlmap, ghauri | `--headers="Name: value"` |
| passive / non-HTTP (subfinder, gau, waymore, amass, naabu SYN, interactsh) | N/A — they send no request to the target; list as skipped-by-design, never as missing |

## Manual probes

Every hand-run curl/python request carries the header too (keep it in the shared header dict, see
`bot-protected-target-testing`). Browser-driven flows are the gap: if the browser stack cannot be
made to send it, state that in the coverage ledger instead of silently omitting it.

## Gentle mode when the policy bans excessive traffic

finanzen.net prohibits *"Generate excessive traffic that could degrade platform performance"*.
Standing operator rule: automated tools still run — **GENTLE** (`-rl/-rate` low, `-c/-t 1..2`,
`--delay`, honour 429/Retry-After), never a downgrade to curl-only. Cost: ONE line in
`plans/scope-risk-log.md` quoting the clause + stating accepted risk, then run. Also log the
no-sandbox situation ("we do NOT provide a test environment" -> self-provisioned test accounts only).

## Report-side consequences of the policy read

Read the whole policy before drafting. This one (a) makes disclosure of AI/tool assistance plus a
manual-verification statement MANDATORY — include it in the body even where the generic template
avoids AI wording; (b) excludes scanner dumps, banner/version disclosure and "missing best
practices" — drop those candidates with a written reason instead of filing them; (c) is
code-based (reset mails contain a code and no URL -> reset-poisoning class is a recorded negative).
