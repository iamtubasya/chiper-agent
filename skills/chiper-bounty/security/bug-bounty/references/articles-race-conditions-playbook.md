# Race Conditions — Research Articles Compendium

> Consolidated from 3 PortSwigger Research articles (2019–2023, James Kettle): true potential of web race conditions (sub-states, single-packet attack), reCAPTCHA race reuse, and single-packet adaptation across protocols. Reference playbook for bug bounty testing/triage.

## Article Map

| Article | Year | Focus |
|---|---|---|
| smashing-the-state-machine | 2023 | Beyond limit-overrun: sub-states, single-packet attack, multi-endpoint/deferred races |
| cracking-recaptcha-turbo-intruder-style | 2019 | Last-byte sync; racing reCAPTCHA token reuse via target server |
| the-single-packet-attack-making-remote-race-conditions-local | 2023 | Protocol adaptation: HTTP/3, HTTP/1.1, WebSocket, SMTP |

## Key Techniques

**Concept shift** — race conditions ≠ only limit-overrun. "With race conditions, everything is multi-step": every request passes through fleeting **sub-states** (~1ms race window) between check and commit (TOCTOU generalized). Exploit = second request interacting with same resource DURING the sub-state.
- Classic case study: session initialized with admin privileges, downgraded when `GET /role` fetched → skip redirect chain in parallel with login = super-admin
- Facebook 2016 email case: racing two email-change requests → single email contains TWO confirmation codes (one per address)

**Single-packet attack (jitter killer)** — 20-30 requests arrive <1ms apart, 17,000km Melbourne→Dublin benchmark:
1. All requests over ONE HTTP/2 connection, withhold tiny fragment of each (server can't start processing)
2. Wait for packets to arrive at target
3. Send final fragments together — OS coalesces into ONE TCP packet
- Tooling: Burp Repeater tab-group "send group in parallel (single-packet attack)"; Turbo Intruder (open source)
- Needs HTTP/2. HTTP/1.1 fallback: parallel connections + last-byte sync (Repeater does this automatically)

**Last-byte sync (HTTP/1.1 era)** — pre-send all requests except last byte, hold on a gate, release together: 5-thread 2.7ms → full-connection-first 1.4ms → last-byte 0.7ms window. `engine.queue(request, gate='race1'); engine.openGate('race1')`

**reCAPTCHA token reuse (second-order race)** — validation happens target↔Google; race the target's validation endpoint with the SAME token N times in one packet batch. Google declined to fix (2019, "attack not plausible in the wild" — it is); burden on sites. Affects token-gated registration/posting/voting; ~2-3x token reuse typical. Chain with captcha-solving services.

**Methodology (state machine probing)** — plot every state transition incl. GETs (GETs change state!). Then race: parallel requests hitting different endpoints in the same flow (multi-endpoint race), single-endpoint parallel, or deferred execution (partial requests held open, released in chosen order) to re-order server-side steps.

**Protocol adaptation (single-packet availability)**
- HTTP/2: YES (fragment trick, TCP 64KB packet)
- HTTP/3/QUIC: possible (single UDP datagram ~1500B soft limit) — rarely worth it
- HTTP/1.1: NO true single-packet (head-of-line blocking, in-order responses) → use parallel-connection last-byte sync
- SMTP pipelining: same in-order limitation
- WebSocket: promising (no response ordering) but no multi-fragment interleaving (RFC6455); RFC 8441 (WS over H2) unlocks full power; under-tooled area
- 30+ connections needed? Bundle multiple requests per connection with pipelining INSIDE the single-packet batch

## High-Value Target List

- Gift card / discount code / store credit reuse; transfer/withdrawal over balance
- One-account-per-email registration bypass; email confirm code confusion (race two addresses)
- Password reset / email change token single-use races (use token twice in parallel)
- 2FA/OTP single-use races; voting/rating multi-count
- Session role init sub-states (admin-by-default then downgrade)
- Captcha token reuse (reCAPTCHA/hCaptcha validation endpoints)
- Rate-limit bypass on auth-bruteforce protection

## By-Design / SKIP Filters

- Single request success + retries blocked cleanly = no race; need ≥2 wins in one batch to claim
- Server uses DB row locks/transactions/idempotency keys and both responses agree = not vulnerable
- Race window demonstrated only via artificial `sleep` endpoints = [THEORETICAL] on real flow
- Limit-overrun on free/no-impact counter (view count) = INFO
- Only 1-of-20 batch succeeds once, unreproducible = INFORMATIONAL (jitter artifact)

## Severity Guide

- Fund transfer/withdrawal overrun, gift card/cashout reuse: CRITICAL/HIGH
- Auth bypass via sub-state (role init, session downgrade race): HIGH/CRITICAL
- Registration/account-creation bypass, OTP/2FA reuse: HIGH
- Email confirm confusion (code for attacker-chosen address): HIGH
- Captcha reuse: MEDIUM (spam-rate multiplier; chain-dependent)
- Vote/rating overrun, no financial/auth impact: LOW–MEDIUM
- Suspected race, blocked by jitter/tooling, unproven: INFORMATIONAL

## Reporting Checklist

- [ ] Batch of 20-30 requests via Repeater single-packet attack or Turbo Intruder; show ≥2 exploitable responses in ONE batch
- [ ] Repeat batch ≥5-10x; report hit-rate (race windows are probabilistic)
- [ ] Show state change persisted (balance, second account, second code) — not just 2xx codes
- [ ] HTTP/1.1 targets: state last-byte sync used; note jitter caveat
- [ ] Impact quantified (max extractable value / accounts created)
- [ ] No DoS: batch sizes 20-30, no sustained flood
- [ ] Blocked/unproven (e.g. only intermittently, no state change) ⇒ INFORMATIONAL per master KB

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
