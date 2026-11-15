# Cloudflare `error code: 1015` — the zone-level rate-limit ban

Measured 2026-10-25 on betterteam.com (careers.betterteam.com), Windows/git-bash, all traffic already
throttled to the program's own `<5 req/s` ceiling.

## Fingerprint — three different walls, three different readings

| signal | meaning | what to do |
|---|---|---|
| `error code: 1015`, body **17 bytes**, `text/plain` | Cloudflare account/zone **rate-limit ban** | stop hitting that hostname entirely |
| `Cf-Mitigated: challenge`, ~5.5 KB `Just a moment...` HTML, 200/403 | managed JS challenge | escalate to a real browser profile (see `cloudflare-challenge-and-local-dns-failure.md`) |
| `Access blocked — <Brand>` branded page, 17 KB HTML with inline CSS | the app's own WAF rule fired on the payload | treat as "payload rejected", not as a block on the host |

The three are routinely confused. A WAF deny still lets clean requests through; 1015 does not — it
answers the same 17 bytes for **every** path, including `/robots.txt`, which is the tell.

## What triggered it here
Gentle automated passes were still enough: `nuclei -rl 3 -c 1`, `ffuf -rate 3 -t 1` across a 167-entry
wordlist, plus a handful of `python urllib` probes. Time from first request to 1015 on that hostname:
**~25 minutes**. Sibling hostnames on the same zone (`www`, `dashboard`, `app`, `s`, `srp`) kept
answering 200/403/404 normally the whole time — the ban is **per-hostname**, not per-zone, so you can
still work the other hosts of the same program.

## It does not clear inside the session
Retested at +5 min, +10 min, +40 min: still 1015. Treat it as lost for the rest of the run.

## Operating rules
1. **Order by value, not by convenience.** Whatever host holds the highest-value surface (the authed
   API, the career/apply flow) gets scanned FIRST while the budget is fresh. A pass you scheduled for
   the end is a pass you may never run.
2. **1015 is REWORK, never N/A.** Record `host, timestamp, trigger (which scanner), coverage lost` in
   the run notes and the report's coverage section, and retry the host in a later session after a
   cooldown (≥ hours, not minutes). "Vendor blocked me" does not mean "no bug there".
3. **Never "work around" it by hand.** Switching to curl-only after a 1015 is exactly the manual
   fallback the operator forbids; wait out the cooldown and re-run automated.
4. **Do not report it.** A rate limit that a published rate rule asked you to respect is not a
   finding — and on most programs "missing rate limits" only pays when it enables password/code
   guessing, which brute force is prohibited anyway.
5. Keep the OOB/listener alive across the gap (interactsh `-n 3` in background) — the ban is on the
   target's edge, not on your callbacks.

## Cheap pre-flight that avoids it
Before pointing the scanner set at a host, spend 2 requests:
`httpx -u https://<host>/ -status-code -rl 2 -t 1` twice ~10 s apart. A 1015 on either means the host
was already banned (by you or by a previous run) — skip it and note the cooldown instead of burning the
run on a host that will answer 17 bytes forever.
