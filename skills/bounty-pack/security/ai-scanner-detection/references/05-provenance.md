# 05 — Provenance, licence, and hardening/IR summary

## Provenance

- **Source of the ideas:** ARTEX defence guide + `detections/` (github.com/jiwoochris/artex-ko),
  AGPL-3.0, copyright its authors.
- **What we did:** read for concepts, then wrote every rule, table, and sentence here ourselves.
  No ARTEX rule body, identifier (UUID), IOC value, framing string, or sentence was copied.
- **Credit line to use when reusing this material externally:**
  "Approach inspired by the ARTEX project (AGPL-3.0); clean-room re-implementation."
- **Why this matters:** copying their files into our kit would pull AGPL obligations onto our work
  and contaminate a kit we keep private. Ideas are free; expression is not.
- **Private-use carve-out:** if we ever want their *actual* rules for our own lab, that is private use
  and fine — just never ship them or merge them into a redistributable kit.

## Hardening summary (defender side, condensed)

Autonomous attackers exploit the same weaknesses humans do, only faster and without fatigue. Ranked:

1. **Shrink the exposed surface** — the single highest-value control. Fewer endpoints, no dev/admin
   panels on the internet, no verbose errors.
2. **Patch n-days fast** — version-based matching is the cheapest entry for a scanner; the window
   between disclosure and exploitation is now hours.
3. **MFA everywhere**, especially on identity-verification, recovery and one-time-code flows — these
   are precisely the flows an agent probes hardest.
4. **Fix object-level authorisation (IDOR/BOLA)** — the perennial top finding; enumerate the
   object-reference space of every authenticated endpoint.
5. **Rate-limit by *behaviour*, not by IP** — enforce on session/account, not source address.
6. **Watch the auth logs** for failure-rate shifts, slow distributed attempts across many accounts,
   and abnormal failure→success speed.
7. **Alert on the correlation, not the leg** — single 404 storms are noise; enumeration + probing +
   auth from one client in one window is not.

## Incident triage order (suspected host)

1. Listening sockets + owning processes (non-standard internal listeners first).
2. Process env for proxy + CA-trust variables together.
3. Presence of a generated proxy CA and the tool's own working directory.
4. Database/schema inspection for a framework-specific table set.
5. Egress logs for code-hosting calls with an updater UA.
6. Command-line audit for the destructive family (see `02-forensic-view.md`).

Each finding is a **lead**, not attribution. State that plainly in any report.
