# Attack-Surface Change Monitoring (continuous recon)

> Use AFTER an engagement ends at verified-negative/verified-complete. New attack
> surface appears over time — new subdomains, new API routes, a new chain, a new
> contract. A cheap watcher turns that into an actionable signal instead of a
> full re-audit. Answer to the operator question *"can you watch the target and
> jump in the moment something new opens up?"*

## The pattern: snapshot → baseline → diff → report ONLY on change

1. **Snapshot** every surface feed into one JSON-serialisable dict.
2. **Store** it as the baseline (`state.json`).
3. Next run: **diff** baseline vs live. Identical response + process `.json`.
4. **Stay silent when nothing changed.** The watcher's stdout IS its signal —
   empty stdout means nothing to report. Any noise here trains the operator to
   ignore it.

Run the script once by hand to establish the baseline, then schedule it.

## What to snapshot per target class

| Target shape | Feed | Why it is new surface |
|---|---|---|
| any | CT logs `crt.sh/?q=%25.<domain>&output=json` | new subdomains appear before anything else notices |
| any web/API | each service's OpenAPI (`/documentation/json`, `/openapi.json`) → sorted `paths` keys | a new route is a new endpoint to authorize-test |
| any web/API | a service root that self-lists `/endpoints[]` | undocumented routes often hide there |
| protocol / bridge | `/chains` (or equivalent) → per-chain `vmType` + depository | a **new VM type = a brand-new attestor surface** |
| protocol / bridge | protocol `/addresses` page → contract set | a new deployment is unaudited by default |
| docs-driven target | `llms.txt` / sitemap → page list | new doc pages describe new features |

Canonical implementation: `scripts/surface_monitor.py` (edit its CONFIG block,
run once, then hand the script to the cron tool).

## Cron wiring pitfalls (Hermes) — each of these bit for real

1. **Script path must be a BARE FILENAME.** The cron `script` argument resolves
   relative to `~/.chiper/skills/bounty-pack/`; an absolute path
   (`D:/.../monitor.py`) is **rejected outright**. Copy the script there first.
2. **`deliver` defaults to `local` = save-only, no notification.** Set
   `deliver='origin'` or the alert never reaches the operator and the watcher is
   pointless.
3. **Set `enabled_toolsets`** (e.g. `["terminal","file","web","skills"]`) — the
   job otherwise loads the full toolset every tick for no reason.
4. **The prompt MUST branch on the change marker.** Agent-mode cron always runs,
   so instruct it: *"if the injected output has no `<MARKER>` line, reply with
   exactly `X: no change` and nothing else; if it does, load the phase skills and
   hunt the new asset."* Without that branch the agent runs a full investigation
   every single tick.
5. **6h is a sane default** for a protocol/bridge target. Go tighter only if the
   surface is genuinely volatile.

## Pitfalls that cost real time

- **EMPTY BASELINE = BLIND WATCHER.** A feed that fails transiently (rate-limit,
  slow TLS, DNS) silently bakes an *empty* list into the baseline — after which
  every run either reports everything as new or nothing at all. **Always print
  the counts after the first run and verify they are non-empty.** Hit for real:
  the first `crt.sh` call returned `0 names`; an immediate re-run returned `66`.
  An unverified baseline is worse than no watcher.
- **MSYS vs native paths.** A bash heredoc writes MSYS paths (`/c/Users/...`)
  into the `.py`; Python's `open()`/`os.path` cannot resolve those →
  `FileNotFoundError`. Patch the state path to the **native** form
  (`/home/agentuser`) after writing the file. Budget one `sed` pass for every
  heredoc-written script.
- **State path must be absolute, not relative to `__file__`** — the script gets
  copied between `~/.hermes/scripts/` and the engagement dir and a relative path
  silently forks the baseline.
- **Sort sets before diffing** or reordering churn produces false "changes".

## Triage the alert — don't just relay the diff

When the marker fires, the watcher's job is to *hunt*, not to forward a diff:

1. New subdomain → `httpx -status-code -title -tech-detect`, then probe
   `/.well-known/security.txt`, `/documentation/json`, `/openapi.json`.
2. New route → empty JSON body, then a minimal *well-formed* body; classify
   `401` (gated) vs `400` (validation-first) vs `200` (open). **See the
   validation-before-auth trap** — a `400` on an empty body is NOT an open route.
3. New chain / new `vmType` → fetch the chains feed, note the depository; a new
   VM type is a new attestor adapter to run the class-11 amount-source diff on.
4. New contract → pull verified source from the explorer before reasoning.
5. Report the honest negative when a probe is clean — negatives are deliverables.

## Companion references

- `/hunt`-class entry + phase gate: `bug-bounty` (stop-rule 23 ledger; rule 24 "no
  menus — pick highest-EV and execute").
- Cross-chain value-path diffing: `web3-audit` →
  `references/cross-chain-settlement-and-attestor-audit.md`.
