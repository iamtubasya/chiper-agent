# 06 — Skill ports (Item 6) — LICENSE-GATED

ARTEX's `skills/` folder: `api-recon`, `playwright-cli`, `scopesentry`. Same AGPL gate as 05:
**study the technique, write our own skill** — never copy their text verbatim.

## Mapping to what we already have

| ARTEX skill | what it does | our counterpart | action |
|---|---|---|---|
| `api-recon` | harvests an SPA/MPA's route map, builds a permission tree, runs a preload runtime harvest | `hunt-api-misconfig`, `hunt-spa-api` | extract the *route-map harvesting* + *runtime preload* techniques into those skills |
| `playwright-cli` | scripted browser automation: request mocking, storage-state reuse, tracing, video recording, test generation | our browser/CDP tooling (`browser-cdp-auth-audit`, `browser-session-daemon`) | port any missing technique (request mocking, storage-state, tracing/video for PoC capture) |
| `scopesentry` | scope/authorization discipline | `recon-scope-triage` | compare checklists, fold in anything we lack |

## Do this

1. Read the ARTEX skill for *technique only* (what it does, in what order, with what output).
2. Write the technique in OUR wording into the matching skill (or a new `references/` file under it).
3. Never paste their prose/code. If a technique is genuinely novel, credit "inspired by ARTEX
   (AGPL-3.0), clean-room re-implementation" in a note — that is honest and keeps us clean.


---

## OUTCOME LOG (executed 2026-10-09, clean-room)

| ARTEX skill | outcome | where it landed |
|---|---|---|
| `api-recon` | **PORTED** — full methodology re-expressed in our words | `hunt-api-misconfig/references/api-runtime-recon.md` (+ pointer) |
| `playwright-cli` | **PORTED (partial)** — state reuse, mocking, tracing/capture techniques | `security/browser-cdp-auth-audit/references/playwright-state-and-mocking.md` (+ pointer) |
| `scopesentry` | **NOT PORTED — deliberately** | see below |

### Why `scopesentry` was not ported

It is not a technique; it is an **integration guide for a third-party scanning platform** (its own
hosted instance + an MCP client). Nothing in it improves our own scope discipline, and adopting it
would mean depending on *their* platform. Our `recon-scope-triage` already covers the authorisation
and ownership triage that matters. Recorded here so nobody re-evaluates it.

### What was explicitly NOT copied from any of them

- No ARTEX rule text, rule UUID, IOC value, framing string, or sentence.
- No ARTEX script was copied; the reference files describe the *method*, and where a concrete command
  appears it is written for our toolchain (`curl`/`grep`/`ffuf`/`nuclei`/CDP), not transliterated.
- Credit line used: "inspired by ARTEX (AGPL-3.0); clean-room re-implementation".
