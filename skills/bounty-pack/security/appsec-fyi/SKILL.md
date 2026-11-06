---
name: appsec-fyi
description: Use for source-cited per-class web2 attack techniques.
version: 1.0.0
author: RESEARCHER_NAME
sources: external_reference, public_research
metadata:
  hermes:
    tags: [security, reference, web2, techniques, appsec]
    related_skills: [web2-vuln-classes, security-arsenal, bugbounty-playbook, poc-technique-atlas, attack-surface-index, hunt-dispatch]
---

# appsec.fyi — External Reference Mirror

A vendored, read-only mirror of **appsec.fyi** — Carl Sampson's curated application
security resource library. Each of the 25 classes is a long-form *practical guide*
auto-synthesized from 1,000+ source-cited resources (PortSwigger, OWASP, Wiz, Intigriti,
Detectify, individual researcher blogs, conference archives), so the content is dense,
current (fresh 2026 CVEs), and backs every technique with a citation trail.

This skill is a **reference shelf**, not an orchestrator. It does not own the hunt
workflow — `bb-methodology` / `bug-bounty` / `hunt-dispatch` / `attack-surface-index` do.
Load this skill when you want to *read a specific class's attack techniques in depth*,
then return to the active hunt skill.

> Provenance: technique sections extracted from `https://appsec.fyi/guide/<class>.html`
> ("Notable Techniques [and Attack Patterns/Vectors/Vulnerabilities]" H2 sections),
> rendered to clean markdown under `references/`. Citation fragments `[N]` were dropped
> (they point at the source list on the live page, not at local files). Technique
> substance is preserved verbatim.

---

## When to use this skill

| You want… | Read |
|---|---|
| A **fresh, source-cited attack-technique list** for a class you're about to test | `references/<class>.md` |
| Bypass variations for a specific defense (IP-encoding, SameSite, alg-confusion, filter-evasion) | the matching class file |
| Real-world CVE/practice cases chained to impact (IMDS theft, container escape, gadget chain) | `references/ssrf.md`, `references/rce.md`, `references/deser.md` |
| 2026 trends: AI/LLM pipeline abuse, agent swarms, AI-assisted fuzzing | `references/ai.md`, `references/fuzzing.md` |
| The full class → file catalogue | `references/00-INDEX.md` |

## Class → file map

| Class | File | Class | File |
|---|---|---|---|
| RCE | `references/rce.md` | SSRF | `references/ssrf.md` |
| SQLi | `references/sqli.md` | XSS | `references/xss.md` |
| XXE | `references/xxe.md` | IDOR/BOLA | `references/idor.md` |
| JWT | `references/jwt.md` | CSRF | `references/csrf.md` |
| SSTI | `references/ssti.md` | Deserialization | `references/deser.md` |
| GraphQL | `references/graphql.md` | API Security | `references/apisec.md` |
| Authentication | `references/authn.md` | Authorization | `references/authz.md` |
| AI / LLM | `references/ai.md` | Mobile | `references/mobile.md` |
| OSINT | `references/osint.md` | Recon | `references/recon.md` |
| Secrets | `references/secrets.md` | Supply Chain | `references/supplychain.md` |
| Fuzzing | `references/fuzzing.md` | Burp Suite | `references/burp.md` |
| Python | `references/python.md` | Bug Bounty methodology | `references/bugbounty.md` |
| Talks (attack-surface) | `references/talks.md` | | |

Full technique-level breakdown of every class: `references/00-INDEX.md`.

---

## WEB3 honesty note (do not over-claim)

appsec.fyi has **no dedicated smart-contract / web3 vulnerability class.** The library
covers web2 + adjacent surfaces (AI/LLM, mobile, OSINT, recon, fuzzing, supply-chain).
The only web3-adjacent material is tangential:

- `supplychain.md` — Web3 C2 infrastructure (smart contracts as botnet C2, dynamic dead-drop/update)
- `fuzzing.md` — smart-contract fuzzing (Medusa/Echidna passing mention)
- passing `defi`/`blockchain` references elsewhere are mostly the words "define/defined"

For actual web3 attack classes, route to the existing `hunt-*` web3 family
(`hunt-aa-modular`, `hunt-permit2-signature`, `hunt-amm-hooks`, `hunt-restaking-lrt`,
`hunt-intent-settlement`, `hunt-oracle-l2`, `hunt-vault-inflation`, `hunt-diamond-proxy`)
and `web3-audit/references/web3-hunt-dispatcher.md`.

---

## How this integrates with the existing skill set (additive only)

Nothing here overrides your existing flow. Use it as a cross-check and a source of
step-by-step depth:

| Existing skill (owner) | This skill's role |
|---|---|
| `web2-vuln-classes` (per-class owner) | Second, source-cited opinion; fills gaps where a class file is thin. |
| `security-arsenal` (payload owner) | Adds the **narrative + real CVE/practice cases** behind each payload. |
| `attack-surface-index` (master map) | Wired into the master map as an alternate per-class variant source (see its "Master map" section). |
| `hunt-*` family (technique executor) | Route a fingerprint here for a dense per-class technique list before firing probes. |
| `bugbounty-playbook` / `poc-technique-atlas` (sibling mirrors) | Sibling reference shelves; this adds **source-cited practical-guide prose** not present in either. |
| `bb-methodology` / `hunt-dispatch` (orchestrators) | Feed per-class depth during 0C when a class is fingerprinted but not yet probed. |

**Precedence rule:** the vendored content is opinionated but source-cited. When it
conflicts with an owner skill's hard rule (e.g. `triage-validation` always-rejected list,
`bb-methodology` PART 0 scope gate), the **owner skill wins**. This shelf is for depth
and breadth, not for overriding policy.

---

## Reading a class

```
skill_view(name='appsec-fyi', file_path='references/ssrf.md')
```

Class files are plain markdown with H3 technique subheadings (or `•` bullet lists),
each technique followed by concrete bypass mechanics and, where relevant, real CVE/practice
cases (Portainer, MLflow, SonicWall, Next.js, Axios, Craft CMS, PHP2Shell, Spring4Shell, …).

## Companion note — web3 integrity

Because appsec.fyi is web2-only, do **not** treat it as a web3 source. When a target is
on-chain, use `web3-audit` / the `hunt-*` web3 family and leave this shelf out of the loop
except for the tangential `supplychain.md` (Web3 C2) and `fuzzing.md` (contract fuzzing) notes.