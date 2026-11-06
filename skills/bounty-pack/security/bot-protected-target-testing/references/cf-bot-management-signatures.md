# Cloudflare edge signatures — recognizing blocks, false positives, and hard walls

Field notes from hitting Cloudflare-fronted estates (verified 2026-10, Byte Federal engagement).
Companion to `references/cloudflare-challenge-and-local-dns-failure.md`.

## 1. CF Bot Management blocks scanners by UA — the uniform-403 signature

- ffuf with its DEFAULT user-agent against a CF-Bot-Managed host returns the SAME status AND
  byte size for every path (e.g. all 403, all 5863 bytes). That uniformity is the block
  signature — it is NOT the app answering. Fix: rerun with a browser UA
  (`-H "User-Agent: Mozilla/5.0 ... Chrome/131..."`). Always sanity-check a 0-hit ffuf run for
  this before concluding "no endpoints".
- nuclei with default settings stalls on CF-challenged hosts (runs 30+ min with no output).
  Run it per-host, kill and document partial coverage when a host wedges; never present a
  killed scan as a completed sweep.
- Plain curl probes with a browser UA generally pass; the block is UA/fingerprint-based, not
  path-based.

## 2. CF Turnstile on form/API steps

- Server-side validation is real: dummy token -> 403 "bot verification required", empty ->
  400, malformed -> 400. Report nothing about the gate itself.
- Automation status (2026-10): Playwright headless AND headed Chromium both fail managed
  Turnstile (token input never populates; widget iframe appears then detaches). The stealth
  Firefox REST server can wedge on tab creation. Treat a Turnstile-walled flow as a coverage
  limit with a concrete ask (test account/number), NOT as "target clean" and NOT as a finding.
- The Turnstile SITE KEY is public by design (`0x4AAAA...` in page data/`__data.json`) — not a
  finding.

## 3. subzy / takeover false positives on CF-proxied hostnames

- subzy flagged three hostnames as "Cargo Collective" takeovers; all three resolved to
  Cloudflare proxy IPs and the fingerprint had matched the generic CF 404 page. A CF-proxied
  hostname CANNOT be taken over (the zone is owned by the target).
- Manual verification recipe before believing any takeover flag: (1) resolve the host — CF
  ranges mean no takeover; (2) fetch the body and compare against the claimed service's real
  fingerprint; (3) for bare-IP hosts, check SSH/ports — a live SSH banner means an owned
  server, not a dangling record.

## 4. Malformed framing at the edge

- CL.TE / TE.CL smuggling probes against CF-fronted origins get a clean 400 from Cloudflare
  (framing normalized at the edge). That is a verified negative, not an inconclusive result —
  record it as such.
