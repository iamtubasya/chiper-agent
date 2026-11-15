---
name: program-shortlist-verification
version: "1.0"
created: "2026-10-25"
author: "Qwen (curator)"
license: "MIT"
description: "Use when ranking bounty targets from a pool."
metadata:
  hermes:
    tags: [bug-bounty, target-selection, policy-verification, target-pool]
    related_skills: [target-pool, recon-scope-triage, bug-bounty]
---

# Program Shortlist Verification — pick targets, then prove they're real

## When to Use

- *"cari target dalam pool yg mirip seperti <X>"* — find peers of a known target
- *"kasih target dari pool"* / picking the next engagement
- Before proposing a ranked list of programs to work
- Whenever a store (pool row, sheet, cached note) says a program is `active` / `retired` /
  `monetary` and you are about to act on that label

**Not** for: working a target you have already committed to (that is `bug-bounty` phases 0A-0F),
and not for authorization triage of a *specific* asset (`recon-scope-triage`).

## The two halves — and why both are required

1. **Peer-match**: turn "similar to X" into a *product-shape* query, not a keyword query.
2. **Verify**: fetch each candidate's live policy and confirm it exists, is current, is funded,
   and actually scopes the surface you would attack.

Skipping (1) gives you programs that merely share vocabulary with X. Skipping (2) gives you a
confident ranking built on stale metadata — measured 2026-10-25, **two of the top five candidates
had a wrong status flag**: one retired-flagged program was live and paying, one "active" program
was unreachable.

## Step 1 — Profile the reference target by PRODUCT SHAPE

Do not start from the name or the words in its policy. Write down four lines:

```
WHAT IT SELLS        e.g. decentralized GPU/CPU compute + node marketplace + app hosting
HOW IT EARNS         e.g. node-operator fees, token, marketplace take
WHERE THE BUG LIVED  e.g. the web app (console / passkey / marketplace API), NOT the chain
SCOPE SHAPE          e.g. web app + public APIs + contracts; reward monetary
```

The third line is the one that matters and the one a naive match gets wrong. **Match on the surface
where the previous finding lived**, not the industry label. RunOnFlux's paid finding was a
`postMessage` WebAuthn leak in a web app — so "crypto project with on-chain-only scope" is a *worse*
match than "compute platform whose scope explicitly includes its console/API", even though the first
sounds more similar.

### Vocabulary that actually discriminates

| strong | weak (saturates the pool, produces noise) |
|---|---|
| compute, gpu, cpu rental, bare metal, vps, kubernetes, container, serverless, node operator, cluster, relay, inference, object storage, indexer, rpc | crypto, blockchain, token, web3, protocol, network, dao |

Measured on a 35,633-row pool: `web3=True + monetary` = **141 rows, almost all irrelevant**
(wallets, DEXes, exchanges). Switching to `monetary + ≥2 infra words` collapsed it to **3 rows** that
were readable. The narrow query is the useful one — a shortlist you cannot read is not a shortlist.

### Scoring shape that worked

```python
score = 2*len(depin_hits) + 1*len(infra_hits)   # infra words are the discriminators
if not (depin_hits or infra_hits): skip
```
Then read the top ~30 by hand and drop the vocabulary coincidences.

## Step 2 — Verify each candidate before proposing an order

Fetch the policy URL (for GitHub-hosted policies, `raw.githubusercontent.com` of the `SECURITY.md`
beats the blob page — no JS, no truncation). Then answer, in order:

| # | Question | Kill / keep signal |
|---|---|---|
| 1 | Does it respond? | DNS resolving is NOT reachability — **probe HTTP and HTTPS**; DNS-ok + both timeout = unreachable, park it |
| 2 | Freshness | a `Last update:` / `Effective:` date inside the body beats any cached status column |
| 3 | Funded? | published per-severity **amount table** = funded; *"appropriate reward or other form of recognition"* = discretionary |
| 4 | Paid in what? | cash / USDC ≫ project token with a lockup ≫ credits / recognition |
| 5 | Does scope name the WEB surface? | look for `web app`, `console`, `dashboard`, `frontend`, `API`, `backend services`, or an explicit in-scope **asset table** |
| 6 | Any pause/retire/sunset banner? | see the keyword trap below |
| 7 | Registrable? | signup page responds and does not geo-wall on first load |

**Cheapest liveness proof:** the sibling service hosts named in the scope (`scan.`, `swap.`,
`launchpad.`, `console.`, `app.`) returning `200` proves a live multi-service product in four
requests — do it before writing the candidate up.

### Pause/retire keyword trap

Grep the fetched body for
`sunset|shut ?down|acquired by|no longer|discontinu|paused|retired|not currently|suspended`.

**Read the surrounding sentence before acting.** `"no longer"` matched a *threat-model* sentence
("the cluster is no longer controlled by its legitimate operators") on a perfectly live program — a
keyword-only read would have discarded a $50k-max candidate. Same class of error as a soft-404 false
positive: the string is a hypothesis, the sentence is the evidence.

### Status flags are hypotheses in BOTH directions

`retired` does not mean dead; `active` does not mean alive. Decide from the page, then write the
correction back to the store so the next session does not re-litigate it:

```bash
pool.py set <dom> untouched --note "2026-10-25 verified <what you saw>: <date>, <table>,
  <in-scope hosts>; pool '<flag>' STALE because <reason>"
```
Keep the state as `untouched` (do not invent a new state) so the picker can still surface the target
while the note carries the evidence.

**When the policy contradicts the reward flag, change the state — not just the note.** A
`reward_type: monetary` row whose policy says verbatim *"does not operate a bug bounty program…
no monetary rewards, credit, or any other compensation"* is a **wrong flag**, and a note alone
leaves it rankable. Set it to `no-reward` with the quote as evidence:

```bash
pool.py set <dom> no-reward --note "2026-10-26 verified: policy states verbatim '<quote>' — VDP
  only. Pool 'monetary' flag WRONG"
```

Measured 2026-10-26: one of four policy-verified candidates had exactly this shape. The
note-only path would have left a VDP ranked above two funded programs.

## Step 3 — Propose an order, with the blocker named

Rank by **(reward ceiling × scope fit) / friction**, not by ceiling alone. Friction includes: paid in
a locked token, policy paragraphs aimed at AI-written reports, an unreachable host, a login wall on
the scope surface, and reward tables that are "indicative, not a funded commitment".

Per candidate state: what it is · why it matches the reference shape · whether the web surface is in
scope · reward band · the one blocker. **Name the blocker rather than dropping the candidate
silently** — the operator picks differently depending on whether the wall is "unreachable" or "low
ceiling".

## Pitfalls (all hit for real)

- **A name scan is not a peer scan.** Searching the pool for `flux` returned `bitflux.ch` (Swiss ISP)
  and `fluxcd.io` (GitOps tool) — three shared letters, nothing else. And `runonflux` itself was
  **not in the pool at all** (0 matches): the reference target may be absent, so match by shape, not
  by finding the reference first.
- **A tag/category column can be absent from most of the pool.** 27,424 of 35,633 rows had no
  `category`; only 431 carried `web3: true`. The signal lives in free-text `scope` / `company` /
  `reward_text` — build the filter over those, not over a sparse tag.
- **`live` may be the string `"True"`, `None`, or `"unverified"` — never a bool.** `live == True`
  silently matches zero rows.
- **`status` (program state) and `audit_status` (your progress) are different columns.** Filtering
  progress with the program column returns 0 rows and looks like "no candidates".
- **"monetary" ≠ funded.** Discretionary wording, "may recognize or reward", and "indicative
  schedule, not a funded commitment" appeared in the same shortlist as real amount tables. Read it.
- **Do not rank an unreachable host high because the reward is good.** DNS resolves → both schemes
  time out → GitHub org 404 = not testable today regardless of the table.
- **Ceiling ≠ value.** A $500-max program whose scope is exactly the product shape you know how to
  break can outrank a $50k program whose scope is on-chain-only. State both numbers.
- **Notes you write must carry the date and the quote**, or the next session re-verifies the same
  five programs from scratch.

### Step 2b — The registrability gate is a separate question from liveness

A live, funded, in-scope program whose signup you cannot complete is a **partial** target, not a
good one. Two consecutive engagements have ended as documented negatives because the money paths
sat behind an authenticated area that signup never reached (geo-wall, mandatory SMS). Run this
after the policy check and before ranking:

```python
for u in ["/signup", "/register", "/login", "/pricing"]:
    # 200 on signup/register from the current egress = gate PASS
    # 200 but the body says "registration is no longer possible in your country" = FAIL
    # 422 naming a captcha field (cf_turnstile_response / recaptcha) = reachable, needs a browser
```

**A 422 naming a captcha field is a PASS, not a blocker.** It proves the route is live and tells
you the exact gate — drive it with a real browser (SeleniumBase CDP / persistent Chrome profile),
not with a bare POST. Measured 2026-10-26: `POST /api/auth/register` → `422 cf_turnstile_response
required` on a target whose signup then worked fine through a browser.

**A 200 on `/pricing` is worth one request.** It confirms the product is commercially live (a
sunsetting product often drops its pricing page first) and gives you the plan names you will need
for entitlement testing later.

### Step 2c — Verify the scope's asset list host-by-host, not just the apex

Modern VDPs enumerate scope as an explicit host table rather than a wildcard. Fetch the policy,
extract every host it names, and probe each one. Measured 2026-10-26 on a file-sharing SaaS: the
policy named nine hosts; probing them found two that were **out of scope but live**
(`docs.`, `status.` — both 200, both explicitly excluded), one that was a **third-party service
wearing the target's domain** (`link.<target>.com` served a Rebrandly page), and one that was a
**403-locked update feed**. Only that probe tells you which hosts are actually yours to test.

Also record the **`Expires` date from `/.well-known/security.txt`** — it is the one field that
tells you when the authorization you are relying on lapses. A policy expiring inside your
engagement window is a scheduling fact, not a footnote.

## Support files

- `references/peer-program-matching.md` — worked RunOnFlux → peer-shortlist session: the exact
  queries and their yields, the verified verdicts (in-scope asset tables, reward bands, blockers),
  and the false positives the vocabulary filter must reject.
- `scripts/policy_verify.py` — the seven verification questions as one runnable pass:
  `python policy_verify.py https://example.com/security` (or `--json`). Rewrites GitHub `/blob/`
  URLs to raw automatically, prints the freshness date, severity bands, whether the web surface is
  named, discretionary/token wording, the AI-report clause, and every dead-word hit **with 220 chars
  of context** so a threat-model sentence is not mistaken for a sunset notice. Only issues a
  `PAUSED_OR_RETIRED` verdict when the banner keyword sits next to "program/bounty/reward".

## Pool-query field traps (read before writing a filter)

The store's schema drifted: two generations of records coexist.

| field | old records | new records |
|---|---|---|
| `reward` (`monetary`/`swag`) | ✓ | ✗ |
| `reward_type` (`monetary`/`vdp`/`unknown`/`recognition`) | ✗ | ✓ |
| `category` | ✓ (~8.2k rows) | **absent** (~27.4k rows) |
| `company`, `reward_text`, `scope`, `policy`, `web3`, `tld_country`, `geo_no_pay` | ✗ | ✓ |
| `hosting`, `status`, `live`, `sources` | ✓ | ✗ |

Consequences, each of which produced a real 0-row or wrong-row result:

- Filter on **`reward_type` OR `reward`** — pick whichever is present:
  `(r.get("reward_type") or r.get("reward") or "").lower() == "monetary"`.
- A `category == "..."` filter silently covers only ~23% of the pool. The richest matching signal
  (`scope`) exists **only** in the newer generation — which is exactly why scope-based similarity
  matching works, and why category-based matching does not.
- `web3: true` is a usable boolean facet but only on the new generation (431 rows). It is the
  fastest first cut for a crypto/DePIN reference target.
- `live` is the string `"True"` / `None` / `"unverified"`. Compare `str(r.get("live")).lower()`.

## Related

- `target-pool` — the store itself (query CLI, field schema, how to mark results). This skill sits on
  top of it: match → verify → propose.
- `recon-scope-triage` — once a candidate is chosen, governs authorization + ownership triage of the
  specific assets.
- `bug-bounty` — the phased pipeline that starts once the target is committed.
