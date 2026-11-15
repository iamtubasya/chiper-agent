---
name: bugbounty-playbook
description: >-
  External reference library mirrored from https://bugbounty.info/ ("The Bug Bounty
  Playbook") — 186 pages of TTPs, methodology, tradecraft, attack-surface deep-dives,
  pre-built exploit chains, recon playbooks, reporting templates and program/business
  notes. Use as a browsing/reading reference when you want a second opinion on a
  technique, need a step-by-step chain (XSS→ATO, SSRF→cloud RCE, IDOR→ATO, OAuth→ATO,
  race→financial, SSTI→RCE), want per-surface TTPs (Web/API/Cloud/CI-CD/AI-LLM/Mobile/
  Web3), recon playbook detail, or report-writing/structure guidance. Complements — does
  not replace — bb-methodology, security-arsenal, web2-vuln-classes, triage-validation,
  report-writing, security-recon and the hunt-* family. Read-only reference — pull a
  page, apply it, don't treat this as the orchestrator.
sources: external_reference, public_research
---

# BugBounty Playbook — External Reference Library

A vendored, read-only mirror of **bugbounty.info** (the "Bug Bounty Playbook" by
BugBounty.info). 186 pages, ~1.15 MB of TTPs, methodology and tradecraft.

This skill is a **reference shelf**, not an orchestrator. It does not own the hunt
workflow — `bb-methodology` / `bug-bounty` / `hunt-dispatch` do. Load this skill
when you want to *read a specific technique or chain in depth*, then go back to the
active hunt skill.

> Provenance: content mirrored from https://bugbounty.info/ via
> `static/contentIndex.json` (Quartz site content index). All pages preserved
> verbatim under `references/`. One file
> (`references/attack-surface/web/File-Operations/File-Upload.md`) has webshell
> payload tokens lightly defanged (`$_GET[cmd]` unquoted / `/*DOC*/` marker) to
> survive host AV — the technique and everything else is unchanged.

---

## When to use this skill

| You want… | Read |
|---|---|
| A **complete attack chain** for a low-impact finding you're sitting on | `references/chains/` |
| **Per-surface TTPs** for a target type you just fingerprinted | `references/attack-surface/<surface>/` |
| **Recon playbook** detail (what each source gives you, ordering, pipelines) | `references/recon/` |
| **Hunting discipline** (target selection, time-boxing, scoping, chain thinking) | `references/methodology/` |
| **Report structure / templates / impact statements** | `references/reporting/` |
| **Tool usage** notes (Burp, Nuclei, ffuf, DevTools, AI-assisted, automation) | `references/tooling/` |
| **Platform / program** selection and behaviour | `references/programs/` |
| Career / financial / running-a-program / org-side material | `references/business-of-bounties/` |
| A full catalogue of every page | `references/00-INDEX.md` |

---

## How to navigate

1. Start at `references/00-INDEX.md` — it lists every page and section with a one-line summary.
2. Or jump straight in by section:

```
references/
  00-INDEX.md                 full catalogue (186 pages)
  index.md                    site landing page
  recon/                      24 pages  — asset discovery playbook
  methodology/                10 pages  — target selection, scoping, chain thinking
  chains/                     20 pages  — pre-built exploit chains w/ diagrams
  attack-surface/
    web/                      47 pages  — auth, authz, injection, client-side, infra, file ops, biz-logic
    api/                       5 pages  — REST, GraphQL, gRPC, gateway bypass
    cloud/                     9 pages  — AWS, Azure, GCP, multi-cloud
    cicd/                      6 pages  — GH Actions, GitLab, Jenkins, secrets, supply chain
    AI-LLM/                    9 pages  — prompt injection, agents, MCP, RAG, output handling, DoS
    mobile/                    4 pages  — Android, iOS, shared
    web3/                     10 pages  — smart-contract / EVM attack surface
  reporting/                   6 pages  — writing, templates, impact, severity, disclosure
  tooling/                     7 pages  — Burp, Nuclei, ffuf, DevTools, automation, AI-assisted
  programs/                   14 pages  — platform selection + per-platform notes
  business-of-bounties/       12 pages  — career, financial, running a program, mental health
  resources/                   1 page
```

---

## How this integrates with the existing skill set

**Additive only.** Nothing here overrides your existing flow. Use it as a
cross-check and a source of step-by-step depth:

| Existing skill (owner) | This skill's role |
|---|---|
| `bb-methodology` (workflow owner) | Feed its Phase 1 recon from `references/recon/`; Phase 4 escalation from `references/chains/`; PART 0 scoping from `references/methodology/`. |
| `bug-bounty` / `hunt-dispatch` (orchestrators) | Route to `references/attack-surface/<surface>/` for the surface it fingerprints. |
| `web2-vuln-classes` | Per-class depth lives there; this skill adds the **chain** and **workflow** context. |
| `security-arsenal` | Payloads live there; this skill adds the **narrative + public report** for each technique. |
| `triage-validation` / `report-writing` | Report structure/templates/impact framing cross-check in `references/reporting/`. |
| `security-recon` / `web2-recon` | Recon playbook detail + ordering in `references/recon/`. |
| `exploit-cookbook` | `references/chains/` is a companion set of end-to-end chains with public-report evidence. |

**Precedence rule of thumb:** the vendored content here is opinionated and
"incomplete" by its own admission. When it conflicts with an owner skill's hard
rule (e.g. `triage-validation` always-rejected list, `bb-methodology` PART 0
engagement-type gate), the **owner skill wins**. This shelf is for depth, not for
overriding policy.

---

## Reading a page

Pages are plain markdown. To read one:

```
skill_view(name='bugbounty-playbook', file_path='references/chains/XSS-to-Account-Takeover.md')
```

Chains include `flowchart` blocks (Mermaid source), step-by-step exploitation,
a PoC report template, and links to public bug-bounty reports. Attack-surface
pages map validation → bypass → post-exploitation with checklists.


---

## Companion Reference — `poc-technique-atlas` (additive, never overrides)

Method-level technique shelf extracted from a 2,223-repo local PoC corpus (filtered of
malware/scam, deduped) + PortSwigger WSA. **Read ONE class file per phase** — it does NOT
count against the phase context budget (on-demand shelf).

- `references/00-INDEX.md` → 27 classes (RCE 357, IDOR/BOLA 87, SQLi 83, Crypto 75,
  Auth-bypass 68, XSS 59, Info-disclosure 48, LFI 47, Deserialization 22, SSRF 19,
  Cloud 14, SSTI 7, Race 5, XXE 5, Prototype-pollution 2, …). 1,901 techniques total.
- `skills/security/poc-technique-atlas/references/portswigger/00-INDEX.md` → 29 WSA topics.
- Use it to pick the *method* for the class you are testing; owner skill rules still win.
