---
name: security-lab-range-practice
description: "Drill exploit technique on a lab range — PortSwigger/DVWA web apps, or build a Foundry contract lab to verify a web3 probe."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [security, training, lab, exploit, portswigger, verification]
    platforms: [linux, macos, windows]
---

# Security Lab Range Practice

Deliberate practice against intentionally-vulnerable lab ranges (PortSwigger Web Security
Academy, DVWA, Juice Shop, HTB) to build **verified** exploit technique. Trigger: "pelajari &
kerjakan lab ini satu per satu", "latihan exploit di PortSwigger", or any request to work
through a lab curriculum.

The output of a practice session is NOT a report — it is a **tested payload, proven against a
live target, with the platform's own solved-banner as evidence**.

## Core loop (one lab at a time)

```
1. PICK one lab (never batch-exploit several at once — you lose track of which payload worked)
2. SPAWN its instance → capture the INSTANCE URL (not the description URL)
3. READ the sink/source from the live app (JS bundle, HTML, error text) — never guess the payload
4. EXPLOIT with the technique the sink implies
5. VERIFY via the platform's own solved indicator (banner / "Congratulations")
6. RECORD: lab id, technique, exact payload, solved bool → progress JSON on disk
7. Only then move to the next lab
```

**Never claim a lab solved from a reflected payload alone.** Many labs reflect your input yet
stay unsolved — the platform requires *execution* (JS alert fires) or *data leakage* (stolen
value shown in the response). Read the platform's status, not your assumption.

## Harness (this is where time gets wasted if you get it wrong)

**Use Playwright's sync API directly** (from `execute_code` / terminal). The generic browser
tool can fail with CDP WS handshake errors on these sites; Playwright driving its own Chromium
is reliable.

Build once per range, reuse for every lab:

- **Login** → save `ctx.cookies()` to JSON; reload with `ctx.add_cookies(...)` next time.
  If the site uses a hosted IdP (Auth0/Okta) a plain `requests`/curl login will NOT work — the
  flow needs a JS session and a fresh state token. Use the browser, then reuse cookies.
- **Spawn** → click the "ACCESS THE LAB" button inside `expect_popup()`; if the popup times out
  (instance already exists), fall back to reading the `.../launch/<hash>` href and navigating
  there directly. Instance host matches the range pattern (e.g. `*.web-security-academy.net`).
- **Provisioning delay** → the instance root may return 200 while deeper routes (e.g.
  `/filter?category=`) still 404/500. Wait 10–15 s and retry before concluding anything broke.
- **Exploit** → once provisioned, plain HTTP requests are faster and more stable than the
  browser. Use the browser ONLY where JS must actually execute (XSS) or a dialog must fire.
- **Verify** → GET instance root, look for the platform's solved marker. An error from a dialog
  handler (`TargetClosedError` while accepting an alert) is a *hint* the alert fired — confirm
  via the banner anyway.

## Payload hygiene rules (learned the hard way)

1. **Enumerate, don't guess.** Column-count-dependent bugs (UNION SQLi): iterate until the
   response changes. A wrong count looks exactly like "not vulnerable".
2. **Detect the dialect before writing extraction logic.** One probe per dialect
   (`pg_sleep` / `DBMS_PIPE.RECEIVE_MESSAGE` / `SLEEP` / `WAITFOR DELAY`). The wrong dialect
   silently no-ops and reads as "not injectable".
3. **Put a boolean, not a string, in a conditional.** `CASE WHEN (<subquery returning text>)`
   is a SQL error → nothing delays/fires → the loop reads zero characters. Wrap in `EXISTS(...)`.
4. **Whitespace inside a cookie value can be truncated by the server.** A manually assembled
   `Cookie:` header mangles the payload (`Unterminated string literal started at position N`).
   Send cookies via your HTTP client's cookie parameter (auto-encodes) or URL-encode the value.
5. **Long blind extractions belong in a background process with a per-character checkpoint.**
   Hundreds of timed probes exceed any synchronous cell/command budget. Write partial results to
   disk each iteration and resume from that file.
6. **Read the sink before choosing an XSS payload.** `<script>` does not execute via
   `innerHTML` → use an event handler (`<img src=x onerror=...>`). In an attribute context, break
   out with `">` first. `javascript:`-capable href sinks accept a URI payload. Grep the page's
   inline `<script>` — the sink is often on a **secondary page** (post detail, feedback form),
   not the landing page.

## Evidence & progress

Keep a progress JSON on disk (`D:/data hermes/<range>-progress.json` style): one entry per lab
with `{id, topic, name, payload|technique, solved, ts}`. This survives session/context loss so
the next session resumes at the right lab instead of restarting the curriculum.

Report progress as a table: solved/total grouped by topic, plus an explicit list of what is
still open. Never round up or imply completion of an unsolved lab.

## What NOT to write up as guidance

- A sequence of attempts that never produced a solve is **not** a workflow. Omit it, or mark it
  clearly as unresolved ("belum tembus — ide berikutnya: ...").
- Do not record environment/transient failures (popup timeouts, provisioning races) as
  "the tool doesn't work" — record the *retry pattern* that fixed it.

## When NOT to build a lab (operator correction, 2026-10-27)

A lab calibrates a **probe**. It does not raise a **severity ceiling**. Those are different
asks, and answering the second with the first burns a whole session.

Verbatim: *"sy butuh nya bukan lab lab gkkaruan, yg sy butuh, skill ny dmaksimalkan agar sy
bs kejar dan olah lead candidate ug menjadi bug dgn tingkat tertinggi yaitu critical atau
high"* — I do not need more labs; maximise the skills so I can chase half-formed lead
candidates up to Critical/High.

Decision rule before proposing a new range:

| The ask is… | Right move |
|---|---|
| "prove this probe/template actually fires" | build or reuse a lab (this skill) |
| "turn my lead candidates into Critical/High" | `lead-to-critical` (ceiling scoring + per-class climb plays), `exploit-depth`, `exploit-chain-graph` |
| "the target's class X has no sink anywhere for me to practise" | extend an existing range only for that class — never a fresh multi-service stack |
| "I don't know if my probe transfers" | prefer a **paired control already in the product** (DVWA `low` vs `impossible`, old vs fixed library version) over authoring a new app |

Corollary: when a lab is genuinely needed, it must ship a **negative control** (a patched
sibling that must REFUSE) — otherwise the session produces a demo, not calibration. And say
plainly that a control you authored yourself proves internal consistency, **not** transfer.

## References

- `references/portswigger-labs-verified.md` — per-lab verified payload matrix (SQLi + XSS),
  harness snippets, and the time-wasting traps with their fixes.

## Related

- For **product/appliance** labs (a real NAS OS, firewall, router firmware) — i.e. when the target
  is a hardware/OS product rather than a web app — use the `vm-appliance-lab` skill instead: it
  stands the product up locally under QEMU (headless) so you can fuzz/RE it with no authorization
  limits. That is also the correct redirect when the operator pushes "max attack variants / run a
  scanner" against a live third-party host.

## Absorbed playbooks (complete sub-packages under `references/`)
- `references/portswigger-labs/PLAYBOOK.md` — the PortSwigger Web Security Academy harness: stored
  account/session, logging in with the Playwright sync API (not the browser-use daemon), spawning a
  lab from the all-labs list, driving the instance with plain `requests`, the SQLi solution pattern
  distilled from 11 solved labs, and the progress/output files.
