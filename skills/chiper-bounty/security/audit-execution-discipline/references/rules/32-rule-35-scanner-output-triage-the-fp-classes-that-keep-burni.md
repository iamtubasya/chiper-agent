## ⛔ RULE 35: Scanner-output triage — the FP classes that keep burning report time

Five mechanical false-positive classes, all hit on live targets (worked example + platform map:
`references/session-lessons/forexfactory-posture-2026-09-30.md`). Clear each before a scanner result
reaches `findings.json`:

1. **Malformed input list ⇒ VOID coverage, not "0 findings".** A URL-list file whose lines carry a label
   (`url1=https://…`) makes the tool treat the *whole line* as the URL. The run "completes" with an empty
   output and proves nothing about the target. Keep scanner inputs to bare URLs; if you spot a label,
   re-run and state in the log that the first run was void. Never quote coverage from the broken run.
2. **Catch-all / `/<username>` routes.** Path scanners report 200 on `/admin`, `/manager`, `/swagger`,
   `/debug`, `/upload` — on a site whose URL scheme is `/<username>`, those are **member-profile pages**
   (`/<username>` = "username", "manager", "debug" …). Always resolve what a 200 *is* (title + body +
   the app's `content_group`-style marker) before triaging. Same trap for `/api/` → a profile page.
3. **A parameter "found" by mining may not be consumed at all.** dalfox's miner injects into every name
   it discovers (`image_url`, `panel`, …); if the app echoes the whole query string into `og:url` —
   URL-encoded and HTML-escaped — the "reflection" is cosmetic. Confirm the app *uses* the parameter
   (behaviour changes with value, or a sink is reached) before treating a hit as real.
4. **dalfox JSON `{"type":"G","poc_type":"plain","evidence":""}` is grep-class, not XSS.** No `evidence`
   field plus a `message_str` mentioning a built-in grep rule = the scanner pattern-matched the response
   body. Severity "Low" on such a record is not a finding — verify by hand or drop it.
5. **A step that dies on a timeout is ENVIRONMENT, not a negative.** `subprocess.TimeoutExpired … timed
   out after 2400 seconds` on a pipeline stage means that stage produced **NO RESULT (re-run pending)** —
   the RULE 2c DNS sub-case in a different costume. And a pipeline that aborts there **without generating
   a report is the gate behaving correctly**, not a failed audit. Record `NO RESULT / re-run pending`,
   re-run the stage standalone with a longer timeout, and never write "negative" for it.

Also enforce while triaging: a tool that ran against a **root/asset URL** (e.g. sqlmap pointed at
`/resources/svg/icons.svg?<hash>` harvested from page JS) has tested nothing — see RULE 2c/2d. The
pipeline's `status:EXECUTED` and its "evidence ≥100B" threshold both pass on a file that contains only
the tool's own error banner.

