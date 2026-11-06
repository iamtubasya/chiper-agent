# 05 — Blue-team detections (Item 5) — LICENSE-GATED

ARTEX ships `detections/`: Sigma rules (atomic + correlation), Suricata rules, a MITRE ATT&CK
Navigator layer, a MISP event + CSV of indicators, and a read-only host triage script.

## Why it matters to us (two ways)

1. **Blue-team / advisory-intel feed.** Their rules describe what autonomous AI scanning looks like in
   logs/on the wire — grist for our `advisory-intel` work.
2. **Defence against our own reflection.** When we scan a client, their SOC sees *something*. Knowing
   the published fingerprints of AI-scanner behaviour tells us what we will trip, so we can warn the
   client (or adjust) — and it is a genuinely useful deliverable.

## LICENSE GATE — read before touching

ARTEX is **AGPL-3.0**. The detection files are copyrightable expression.

- **Private use (our own defence/lab):** fine. Study them, learn the patterns.
- **Redistribution (shipping them in a kit, a client deliverable, a public repo):** AGPL obligations
  follow. Also, if we are building a "clean" kit, copying them *contaminates* it.
- **Recommended path:** read -> understand the *idea* -> write our OWN rules/indicators in our idiom.
  Ideas are not copyrightable; the concrete rule text is.

## Suggested first cut (if we build our own)

- Sigma: "AI-scanner user-agent", "rapid sequential 4xx/5xx from one source", "high-rate directory probes".
- Suricata: User-Agent + scan-velocity signatures.
- Keep a private IOC list; never ship it without deciding the license question first.


---

## ✅ EXECUTED 2026-10-09 — built as the skill `ai-scanner-detection`

This item is no longer deferred. It was delivered as a **separate blue-team skill** (thin SKILL.md +
`references/01..05`), because the blue-team purpose is distinct from `advisory-intel` (which ingests
advisories into *offence*). Contents: target view, forensic view, our own behavioural Sigma rules,
our-own-footprint brief template, provenance/licence, and a hardening + IR triage summary.

**Nothing from this item is copied.** No ARTEX rule text, rule UUID, IOC value, framing string, or
sentence appears in the new skill — verified by grep (0 hits on their identifiers). Port numbers are
mentioned exactly once, inside an explicit attribution sentence saying we do **not** reuse their values.
