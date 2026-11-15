---
name: ai-scanner-detection
description: "Blue-team view of autonomous AI-driven scanning and exploitation: what a defender can observe on the wire (target view) and on a host where such a framework ran (forensic view), our own behavioural detection rules, and what OUR scans look like to a client SOC. Use when asked to detect/defend against AI scanners, write detection rules, brief a client on scan visibility, or triage a suspected host."
category: security
metadata:
  hermes:
    tags: [security, blue-team, detection, sigma, suricata, ioc, ai-scanner, defence, triage]
---

# AI Scanner Detection (blue team)

The counterpart to our offensive work. Two questions matter equally:

1. **Defence:** how does a defender spot an autonomous, LLM-driven attacker that does not carry a
   stable signature?
2. **Self-awareness:** when WE scan a client, what does their SOC see? That is a deliverable, and it
   protects the engagement.

> **Provenance & license.** This skill is a **clean-room re-expression** of the ideas in ARTEX's
> defence guide (github.com/jiwoochris/artex-ko, AGPL-3.0). No ARTEX text, rule body, identifier, or
> IOC value was copied. Where a technique is theirs in origin it is credited as "inspired by ARTEX
> (AGPL-3.0), clean-room re-implementation". See `references/05-provenance.md`.

## When to load

- Asked to detect, block, or write rules against AI/agent-driven scanning
- Asked "what will the client's SOC see when we scan?" or preparing a scope/rules-of-engagement brief
- Writing Sigma / Suricata / WAF / SIEM rules for scan-and-exploit behaviour
- Triaging a suspected host for an agent framework footprint
- Any mention of: blue team, detection engineering, IOC, threat hunting, AI scanner, autonomous
  attacker, SOC visibility, scan fingerprint

## Core thesis (read this first)

**Static signatures are disposable; behaviour is not.** A UA string, a payload, a port — an operator
can change any of them in one line. What an autonomous attacker cannot easily hide is the *shape* of
its activity:

- one source chaining **recon -> enumeration -> parameter probing -> auth/injection** inside one
  coherent session, at short intervals;
- requests that **mutate in response to status code and body length** (adaptive, not random fuzzing);
- a session that **keeps going long past human fatigue**, and **keeps trying bypasses after 401/403/429**.

So: anchor on behaviour. Treat every static indicator as a supporting clue only, and always state the
limitation — **absence of a signature is not evidence of safety.**

## Trigger -> reference

| when | read |
|---|---|
| what traffic aimed at a target reveals | `references/01-target-view.md` |
| what a host that RAN such a framework reveals | `references/02-forensic-view.md` |
| writing the actual detection rules (ours, ready to adapt) | `references/03-behavioural-rules.md` |
| what OUR OWN scans look like to a client SOC | `references/04-our-own-footprint.md` |
| hardening guidance + incident triage order | `references/05-provenance.md` + `references/01` §hardening |
| why IP blocklists fail here | `references/01-target-view.md` §ip-blocklists |

## The two views must not be mixed

- **Target view** = what the victim's logs/proxy/WAF see. Mostly behavioural; static strings are few
  and changeable.
- **Forensic view** = what an incident responder sees on a host where the framework ran. This is where
  static artefacts DO help (a listening port, a proxy CA file, injected proxy env vars, a distinctive
  DB schema).

Confusing the two produces bad rules and bad reports. Keep them apart.

## Deliverable habit

When we brief a client on scan visibility, produce: (a) the static fingerprints we will emit,
(b) the behavioural pattern their SIEM will see, (c) explicit "this is changeable / this is not"
labelling, (d) suggested tuning so we do not trip their production alerting. That is a
differentiator, not overhead.
