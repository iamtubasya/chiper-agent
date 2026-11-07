---
name: target-pool
version: 1.0.0
author: RESEARCHER_NAME
description: "Query the deduped bug-bounty target pool."
metadata:
  hermes:
    tags: [bug-bounty, targets, pool, recon, self-hosted]
---

# Target Pool — unified, deduped, queryable

## When to Use
- the operator says "gas a target" / "ambil target" / starts a bounty session without naming a target
- Before auditing any domain — dup-check against past audits
- After finishing an audit — mark status in the pool
- When building a recon batch — pull N targets from `pending`

The operator's standing bug-bounty target pool. **Query it first when starting work** instead of
asking him for a target.

## Where it lives

```
D:/data hermes/target-pool/
  pool.json     4.6 MB  full records (8126 domains)
  targets.csv   1.5 MB  flat view for Excel/Sheets
  dupes.json    109 KB  794 merge events (audit trail of dedupe)
```

CLI: `~/.chiper/skills/bounty-pack/pool.py` — **verify it exists first; on 2026-10-17 the
scripts dir was gone and only the data files remained.** Fallback = parse `pool.json`
directly (see "Programmatic access" below — that path needs no CLI).

## Usage

```bash
PY314="/usr/bin/python3"
cd ~/.chiper/skills/bounty-pack

# discover
"$PY314" pool.py stats                        # counts by category + audit state
"$PY314" pool.py body eu                      # which TLDs count as a region
"$PY314" pool.py pick --region eu --limit 10  # ready-to-work candidates + score + reason
"$PY314" pool.py pick --country de --reward monetary
"$PY314" pool.py pending --limit 80           # monetary + live + untouched

### "yang terbaru" (newest) — pool.py has NO date sort
`pick` sorts by score, not by `first_seen`. For "ambil 1 terbaru" requests filter the
raw JSON yourself (fields `first_seen`, `last_seen` are ISO `YYYY-MM-DD`, sort descending):

```bash
"$PY314" - <<'PY'
import json, random
p = json.load(open("D:/data hermes/target-pool/pool.json", encoding="utf-8"))
recs = list(p["domains"].values())          # top level = {count, by_category, by_source, merge_events, domains}
EU = set("al ad am at az by be ba bg hr cy cz dk ee fi fr gr hu is ie it kz xi lv li lt lu mt md mc me nl mk no pl pt ro ru sm rs sk si se ch ua gb uk gi je gg im fo gl".split())
f = [r for r in recs if (r.get("country") or "").strip().lower() in EU
     and r.get("reward") == "monetary"
     and r.get("audit_status", "untouched") == "untouched"]
f.sort(key=lambda r: (r.get("first_seen") or "", r.get("last_seen") or ""), reverse=True)
top = f[:20]                                  # newest batch
print("\n".join(f'{r["first_seen"]} {r["domain"]:35} {r["country"]} live={r.get("live")}' for r in top))
print("PICK:", random.choice(top)["domain"])  # random dari 20 terbaru
PY
```

Then `pool.py why <dom>` for the full record before proposing.
"$PY314" pool.py list --reward monetary       # ALL paying (incl. already worked)
"$PY314" pool.py list --state finding-pending # what's awaiting report
"$PY314" pool.py search venice
"$PY314" pool.py get spectrocoin.com          # raw record
"$PY314" pool.py why spectrocoin.com          # record + state + notes

# mark results (PERSISTS + timestamped note)
"$PY314" pool.py set  <dom> audited       --note "0 temuan"
"$PY314" pool.py set  <dom> policy-dead   --note "policy 404"
"$PY314" pool.py set  <dom> no-reward     --note "credit-only"
"$PY314" pool.py skip <dom>               --note "terlalu susah"
```

### Programmatic access (execute_code / python)
`pool.json` top level is a dict: `{count, by_category, by_source, merge_events, domains}`.
`domains` is a **dict keyed by domain** (not a list!) and `live` is the **string** `"True"`,
not a bool. Direct access pattern:

```python
pool = json.load(open(r"D:/data hermes/target-pool/pool.json", encoding="utf-8"))
recs = list(pool["domains"].values())          # values, not the dict itself
cand = [r for r in recs
        if str(r.get("reward","")).lower()=="monetary"
        and str(r.get("country","")).lower() in EU_TLDS
        and str(r.get("live")).lower()=="true"   # string compare
        and r.get("audit_status","untouched")=="untouched"]
```

Gotchas that cost retries: iterating `pool["domains"]` directly yields domain
strings; `r.get(...)` on them raises AttributeError. `live == True` never matches
(string). EU region TLD list: `pool.py body eu` (38 codes incl. ch, uk, no, is).

### Audit states (`audit_status`)
`untouched` (default) · `recon-done` · `audited` · `finding-pending` · `submitted` ·
`paid` · `rejected` · `policy-dead` · `no-reward` · `skipped`

The `--untouched` filter (and `pick`/`pending`) excludes **every** non-`untouched` state —
so a target flagged `policy-dead` / `no-reward` / `skipped` never resurfaces for work.
`--note` is stored permanently and shows in `list`, `why`.

### Prompt cheat-sheet (natural language → action)
Full mapping in `references/prompt-cheatsheet.md`. Quick version:
"kasih target dari pool" → `pick` · "eropa monetary belum dikerjakan" → `pick --region eu`
· "yang country de" → `--country de` (aliases: jerman→de, inggris→uk)
· "<dom> udah digarap?" → `why <dom>`

## Pool contents (built 2026-10-12)

| category | count | what |
|---|---|---|
| `selfhosted-any` | 8046 | all self-hosted programs from the 2026-10-06 sheet |
| `master-list` | 49 | curated web3/web2 self-hosted (MASTER_SELFHOSTED_PROGRAMS.txt) |
| `swiss-programs` | 20 | Swiss programs (2 xlsx via MyGroupBot, merged 2026-10-15; 7 platform-intake entries — intigriti/immunefi/gobugfree hosts — flagged `skipped` as "bukan target, cuma platform") |
| `quarterwise-competitor` | 11 | Quarterwise peer companies + their policy status |

Sources merged: `self-hosted-bug-bounty-programs-2026-10-06.xlsx` (3 sheets),
`MASTER_SELFHOSTED_PROGRAMS.txt`, `kompetitor_quarterwise_bugbounty.xlsx` (x2 revisions).

**794 duplicate domains were merged** (e.g. a domain present in both the big sheet and the
master list keeps both `sources[]` and the richer field set). `dupes.json` is the audit trail —
check it before claiming "no duplicates".

## Field schema (per domain)

`domain, program_name, category, reward (monetary|swag|...), policy_url, contact,
security_txt, safe_harbour (stated|not_stated), country, hosting, status, live,
first_seen, last_seen, expires, langs, sources[], already_audited`

## Verified candidate intel (2026-10-21 session)

Asia monetary+selfhosted+untouched slice is THIN (8 candidates, most problematic):
- **Pepabo family (lolipop.jp, shop-pro.jp, suzuri.jp) = NO-REWARD.** Policy pepabo.com/contact/vulnerability-reporting states "現在、報奨金制度は設けておりません" (no bounty system). VDP-only. Marked no-reward in pool. One Pepabo policy covers all their services (Lolipop, Heteml, shop-pro, suzuri, minne...).
- **huffingtonpost.jp = BuzzFeed HackerOne program** (platform, not self-hosted) → skip per "hindari platform".
- **dopetech.au** = no cash programme; **levoit.au** = VeSync global program mirror (storefront mostly out of scope).
- britemed.com.tw / loans.cashconverters.co.nz = safe_harbour not_stated (weak).

**Widening to EU/global works.** Web2 filter that produced 252 candidates: reward=monetary AND live=true AND audit_status=untouched AND hosting!=platform AND country not in (id,in) AND safe_harbour==stated AND domain NOT matching crypto regex (crypto|chain|defi|token|swap|finance|wallet|web3|nft|dao|bitcoin|eth|solana|blockchain|staking|yield|perpetual|dex|exchange|trading|protocol|\.xyz|\.fi|\.finance). Top countries: global 166, nl 17, ch 13, ai 12, io 8.

Verified-paying examples found this way: **CodeRabbit** (coderabbit.ai, Critical $5K-$20K/High $1K-$5K/Medium $500-$1K/Low $100-$500, full CFAA+DMCA safe harbor, submission via web form not email — security.txt Contact: coderabbit.ai/vulnerability-disclosure/submit-vulnerability). Swisscom pays CHF 100-10,000 BUT registration requires a copy of an international ID document (KYC barrier — deprioritize unless operator provides ID). Galaxus/Digitec (galaxus.ch/security) blocks curl via Akamai — browser-only.

- **Rootly (rootly.com) — self-hosted VDP, but the CASH is a Bugcrowd program (verified 2026-11-02).** Policy: "We also run a managed bug bounty program on Bugcrowd… For reports sent directly to us under this policy, we'll credit you publicly once a fix ships." → direct email to security@rootly.com = public credit ONLY; the paid bounty is the platform program. Pool had it `reward: monetary / Tiered` — over-count again. **Tell: "managed bug bounty program on <platform>" + "we'll credit you publicly" = platform-mediated cash, direct VDP = credit-only.** Registrability wall too: signup `status.rootly.com/users/sign_up` placeholder **"Work email"** + Cloudflare Turnstile, and `POST /users` answers a bare **404** even with a solved Turnstile token → B2B free-email (gmail) rejection, obfuscated 404. The IDOR/BOLA surface sits behind that auth, untestable unauth.

## Rules

- **Region preferences are real filters (operator, 2026-10-17).** Asked for "asia" he walked the
  shortlist JP → KR → South Asia → Australia and rejected each step: Indonesia ("jgn indonesia"),
  India ("india gkpernah bayar" — his experience is that Indian programs don't pay). When he names
  a region, exclude `country in (id, in)` unless he names them himself; AU/NZ monetary self-hosted
  is thin (dopetech.au = no cash programme, levoit.au = VeSync global program) — expect to widen.
- **REGISTRABILITY GATE (operator, 2026-10-21 — the lesson that cost two full engagements).**
  Before committing to a target, verify that ACCOUNT CREATION works from the operator's current
  egress. Two consecutive engagements (Fastmail, mail.com) were geo-walled: signup from an
  Indonesian IP returned "registration is no longer possible in your country" / mandatory SMS
  phone verification. Both programs' money paths sat behind the authenticated area, so the entire
  high-value surface became untestable unauth and the engagements ended as documented negatives.
  The fix is a 5-minute pre-check BEFORE Phase 0B: load the signup page (or POST a throwaway
  registration) and confirm it does not (a) geo-reject, (b) demand an SMS-capable phone, or
  (c) demand KYC/business onboarding. A B2B fintech whose signup 404s or routes to sales is the
  same wall. Prefer consumer/SaaS platforms with open registration; treat geo-walled programs as
  "unauth-surface-only" engagements and say so up front rather than discovering it at Phase 0C.
  **Enterprise-SSO targets are the same wall (verified 2026-11-02, witivio.com).** A B2B target
  whose only auth is "Sign in with Microsoft work account" (Teams / M365 / Entra apps) can't be
  self-provisioned: the free path to a work identity is a Microsoft 365 Developer-Program tenant,
  which itself needs a Microsoft account, and Microsoft account signup requires CAPTCHA +
  phone/SMS (no legit bypass). Treat these as unauth-surface-only AND still hunt the unauth
  perimeter — Witivio's unauth `/teams-app/data` entitlement BOLA (Medium) was found exactly there.
  Say "SSO-gated, unauth-surface only" up front instead of discovering it at Phase 0C.
- **A pool domain can be a locale mirror of a bigger program — verify the REAL scope before
  committing (2026-10-17, levoit.au).** The AU entry is a Shopify storefront, but the actual bounty
  is VeSync's global IoT program (security.vesync.com, Critical $3K–10K) whose scope is
  "IoT appliances, mobile apps, cloud services, firmware, APIs" — the storefront itself is mostly
  out of that scope. Before starting, fetch the policy and answer: which domains/services does the
  program actually cover, and is the pool's domain inside them? Same class as the yandex.fr mirror
  note above.
- **`reward: monetary` from the source sheet is NOT trustworthy.** Verified 2026-10-14:
  medatixx.de was flagged monetary but its policy explicitly says "Ein Bug-Bounty-Programm
  bieten wir derzeit nicht an" (VDP + Hall of Fame only). Before committing a target, fetch
  the `policy_url` and look for the actual bounty statement. VDP-only → `pool.py set <dom>
  no-reward --note "<evidence>"`. Common pattern in the selfhosted sheet: self-hosted VDPs
  default to monetary even when recognition is non-monetary. Discretionary reward ("appropriate
  reward or other form of recognition", e.g. gasunie.nl) still counts as monetary but note it.
- **ALSO verify the service is still ALIVE (2026-10-21, skiff.com).** The pool entry said
  `status: active, reward: monetary`, but the fetched policy page opened with "Skiff has been
  acquired by Notion and services will be sunset" — the product is dead and no report can ever
  be paid. When you fetch the policy page, read the first meaningful paragraph for
  acquisition/sunset/shutdown language before anything else. Dead service → `no-reward` with
  the quote as evidence. The same fetch settles the reward question too, so it costs nothing.
- **ALSO verify the CORE scoped surface still has a WORKING auth path (2026-11-01, sqrx.com).**
  "Alive" (200 on the apex) can hide a decommissioned product when an acquisition already
  severed auth while leaving the website up. Signals, all seen on SquareX (post-Zscaler):
  (a) the SPA bundle ships a REDACTED Firebase/API key (literal `AIzaSy...LBQk` with `...`) →
  client auth cannot run; (b) the consumer extension is DELISTED from the store (CRX download
  `clients2.google.com/service/update2/crx?...uc` returns 204/empty); (c) the money path needs
  Firebase email-link login, which the redacted key blocks → no self-provisioned test account.
  For per-session-hostname products (cloud browser / VDI / container streaming): CT-log session
  hostnames (`url<NUMBER>.online.<t>`, `o1.ptr<NUMBER>.online.<t>`) that are ALL NXDOMAIN/404
  across a small range scan = no live sessions = the disposable/container surface is
  decommissioned. Verdict: `skipped --note "product decommissioned post-acquisition"`, not a full
  engagement. Same class as the REGISTRABILITY GATE but for "no functioning auth at all".
- **`reward_max == 9116` is a DATA BUG, not a $9,116 payout.** Entries whose `reward_text` is
  `VDP (Security.txt RFC 9116)` leak the RFC number `9116` into the numeric `reward_max` field —
  a thick band of `.at/.ch/.be/.br/.es` domains shows `$9116` for exactly this reason. Ignore the
  number and read `reward_text`/the live policy; those are VDP / unknown-payout, not verified cash.
- **Government CVD schemes = swag, not cash (verified 2026-10-15, politie.nl via NCSC NL).**
  National CERT/CVD pages (ncsc.nl, BSI, ANSSI, NCSC-UK style) route reports for the whole
  government estate; the reward is "beloning: van T-shirt tot cadeaubon" (T-shirt→gift-card,
  discretionary, no published amount). Tag as `no-reward` when the ask is "yang benar
  membayar/cash". Tell: policy wording "coordinated vulnerability disclosure" + wall-of-fame +
  no nominal. Government targets also carry the highest legal sensitivity — deprioritize.
- **Cash = policy with a PUBLISHED AMOUNT TABLE.** Verified pattern (jochen-schweizer.de):
  PDF/HTML reward table with per-severity euro amounts + explicit payment mechanics (bank
  transfer + invoice) = trustworthy. Worked example + extraction recipe:
  `references/policy-amount-check.md`.
- "no platform" / "self-hosted only" → filter `hosting != platform` (platform = Intigriti/
  HackerOne-hosted programs; the CLI `pick`/`list` don't expose a `--hosting` flag yet — use
  `pool.py get` + a JSON filter over `pool.json` domains dict, key is `domains` NOT a list).
- **Query before asking.** If the operator says "gas a target", run `pool.py pending` and propose from it.
- **Program-status gate before proposing (2026-10-20, Zora): fetch the LIVE policy page and look for a paused/retired banner.** Zora's brief read "Program status: paused as of August 10, 2026... reports submitted during this period are not eligible for rewards" — a paused program pays nothing, so switch targets instead of investing a full engagement. The pool's `status` field (active/retired/expired) comes from the source sheet and can be stale; the policy banner is authoritative. Paused programs often still accept funds-at-immediate-risk reports via the security contact — note that, don't treat it as a full engagement.
- **Dup-check before auditing.** `pool.py get <dom>` — if `already_audited` or
  `audit_status != untouched`, say so instead of re-auditing.
  **⚠️ Two fields, two meanings (cost a real 0-match bug 2026-10-15):** `status` is the
  *program's* state (`active` / `retired` / `expired` from the source sheet) — it NEVER
  holds audit progress. Audit progress lives only in `audit_status`. Filtering
  `status != untouched` returns 0 rows silently because `status` is never "untouched".
  Always pair: program filter → `status`; work filter → `audit_status`.
- **Mark progress.** After an audit completes: `pool.py set <dom> audited --note "..."`
  (other values: `recon-done`, `finding-pending`, `submitted`, `paid`, `rejected`).
- **Pool notes about delivery can be STALE — verify Gmail before staging or sending.** A note
  saying "STAGED as draft, NOT SENT" can be overtaken by an earlier session's send (verified
  2026-10-15: mydays.de notes said unsent, but `users.drafts.list` +
  `users.messages.list(q="to:<vendor>")` showed all 6 reports already sent with vendor tickets).
  Check drafts + sent first, then either send or skip — and write the vendor ticket IDs back into
  the note (`--note "... terkirim 2026-10-12, ticket ITSEC-xxxx"`) so the next session cannot
  double-send.
- **`reward: monetary` is NOT trusted — verify the policy first.** The source sheet
  tagged many EU self-hosted VDPs as `monetary` when they are actually VDP-only with
  Hall of Fame (verified example: medatixx.de — policy literally says "Ein Bug-Bounty
  Programm bieten wir derzeit nicht an"). Before proposing a target as "paying",
  fetch the policy page and look for an explicit reward/bounty statement. If no bounty
  → `pool.py set <dom> no-reward --note "policy: VDP-only/HallOfFame"`. Common tell:
  policy framed as EU Cyber Resilience Act (CRA) compliance — CRA mandates a disclosure
  channel, NOT a bounty, so CRA-worded VDPs are frequently non-paying.
- **"no platform" requests** = `hosting != "platform"` (i.e. `self_hosted`); platform =
  Intigriti/HackerOne/Bugcrowd-hosted programs. ~60/40 split in the EU monetary slice.
- **Respect each program's own policy** — the pool is a directory, not an authorization.
  Check `policy_url` / `safe_harbour` per target before active testing.
- **Deep-check the policy BEFORE proposing a target** (`policy_url` in the pool is often a
  shortlink or a JS-rendered page — the reward amounts and the real scope list are usually
  on a *different* page than the link itself). Verify: (a) ada nominal reward / memang bayar,
  (b) domain yang mau digarap ADA di scope list program. Pool entries are TLD/locale mirrors
  of one brand (e.g. `yandex.fr`) — the program scope may only list `*.yandex.com`.
  Recipe + worked example: `references/policy-amount-check.md`.
  **Reward-type triage + channel shapes** (voucher/credits ≠ cash, form-based programs with no
  mailbox, PDF out-of-scope lists, JS-rendered reward tables) + the web2 candidate filter that
  produced 248 verified-shape candidates: `references/web2-candidate-evaluation.md`
  (2026-10-21: Pepabo=VDP-only, Kontent=Amazon vouchers, Pokee=API credits, Kaartje2go=€50
  voucher, Cloudsmith=form submission).
- **Do NOT put credential dumps in the pool.** `BB 10K.txt` (10k `sk-` keys) stays out.
- `pending` filters strictly (monetary + live=true + not audited) — if it returns few rows,
  relax with `list --reward monetary`.

## Rebuild / refresh

Scripts: `~/telegram_scraper/pool_step1.py` (xlsx) → `pool_step2.py` (master txt + competitors)
→ `pool_step3.py` (dedupe audit + write). Re-run all three after adding new source files;
`add()` in step2 merges by normalized domain (lowercase, strip `www.`, strip scheme/path).
