# 01 — Target view (what the victim sees)

Split by confidence, not by neatness.

## High-signal statics (changeable → supporting only)

Our tooling, like any tooling, leaves default fingerprints: scanner User-Agents, default header
ordering, default `Accept` sets, TLS fingerprints (JA3/JA4), and absence of normal browser
behaviours (no cookie jar evolution, no Referer, no static-asset fetches).

Rules that match these are **cheap and useful, but brittle**: the operator changes one string and
they stop firing. Never write a rule whose only leg is a UA.

> Compare with ARTEX: their enrichment prober emits a fixed UA and their SDK leaves another; both are
> documented as "supporting clue, absence ≠ safety". Same principle, our own implementation.

## Behavioural signals (the durable part)

Rank these above any static match:

1. **Single-source multi-stage chain** — one client, one session, doing enumeration *then* parameter
   probing *then* authentication attempts within a short window. Individually each leg is noise; the
   co-occurrence is the signal.
2. **Adaptive mutation** — consecutive requests to the same endpoint whose parameters change in
   response to the previous status code / body length. Random fuzzing looks different from
   "read the error, adjust the payload, retry".
3. **Fatigue-free persistence** — a session that continues for hours, including outside the service's
   normal traffic hours, without the pauses a human takes.
4. **Bypass persistence after refusal** — 401/403/429 does not end the attempt; the source returns
   with variants.
5. **Concurrency without coordination** — several distinct "angles" against one target at once
   (multiple workers), which does not match a single human using one browser.

## What the attacker's attack-phase traffic actually looks like

Important and counter-intuitive: the *exploitation* traffic usually carries **whatever the invoked
CLI tool's default fingerprint is** — not the framework's own UA. Frameworks route tool traffic
through a proxy and inject env vars, but they typically do NOT force a custom UA onto the tools. So:

- You will most often see `curl` / `sqlmap` / `nuclei` / `ffuf` / Python-requests defaults.
- If the operator *did* customise, the traffic may look like an ordinary browser — and your static
  rule is blind.
- Therefore: **static rules are a bonus; behaviour rules are the plan.**

## IP blocklists are a weak first line

Do not advise a client to blackhole a community-shared "attacker IP" list.

- provenance is unverifiable (who collected it, over what window, with what else mixed in);
- it is stale on arrival — autonomous operators rotate through VPNs, cloud instances and relays;
- false-positive risk is real (shared ranges, CDN edges) and automatic blocking amplifies the damage.

IP blocking earns its place only with **official** indicators from a response agency or trusted intel,
applied with a validity window and a false-positive review. It is a stopgap; behaviour and reduced
attack surface are the durable controls.
