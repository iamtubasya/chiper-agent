# Bugcrowd Brief Scraping (JS-rendered) — camofox recipe

## When to use
Bugcrowd engagement briefs (scope, rewards, announcements) do NOT render via plain curl on the
engagement page itself:
- `curl bugcrowd.com/engagements/<slug>/brief` → 301
- `/targets`, `/scope` probes → 301 / SPA shell
Use the local anti-detect browser stack instead — BUT try the JSON fast path below first: it needs
no browser and returns the full structured brief.

## FASTEST PATH — the changelog `.json` endpoint (no login, no browser) — verified 2026-10
The SPA fetches the whole brief from a changelog endpoint. Appending `.json` serves it **completely
unauthenticated** (worked on a "login-gated" program):
```bash
# 1) the changelog UUID is embedded in the engagement page HTML — grep it out:
curl -s -H 'User-Agent: Mozilla/5.0' https://bugcrowd.com/engagements/<slug> \
  | grep -oE 'changelog/[0-9a-f-]{36}' | head -1
# 2) fetch the full brief JSON:
curl -s -H 'Accept: application/json' \
  "https://bugcrowd.com/engagements/<slug>/changelog/<uuid>.json" -o brief.json
```
Structure of `brief.json`:
- top level: `data` → `brief`, `scope`, `resources`, `engagement`, `vrtScopeRules`, `vrtVersion`
- `data.brief`: `description` (HTML = the General Program Rules + test-property template),
  `targetsOverview` (the Out-of-Scope prose), `additionalInformation`
- `data.scope`: an ARRAY of groups; each = `{name, inScope, rewardRange{p1MinCents..p4MaxCents},
  targets:[{uri|name, category, tags[]}]}`
  - reward values are in **cents** → `/100` for USD; `inScope:false` marks the Out-of-Scope group
  - some rows carry the host in `name` when `uri` is null — fall back to `name`
- Also public with **no auth at all**: `/engagements/<slug>/statistics`
  (`rewardedVulnerabilities`, `averagePayout`, `validationWithin`) and `/engagements/<slug>/scope_ranks`.
- The page HTML also embeds the SPA's route map — grep for `"<name>Api":{` blocks to discover every
  engagement endpoint (brief, statistics, announcements, changelog-preview, scope_ranks, …).

Parse `data['scope']` with python rather than scraping the DOM — faster and structured.

### FALLBACK when the changelog `.json` 404s — the SPA mount node's own attributes
`/engagements/<slug>/changelog/<uuid>.json` is not always served (private/login-gated program,
or the UUID rotated). The SAME page HTML still carries the brief: a
`<div data-react-class="ResearcherEngagementBrief" data-props="…" data-api-endpoints="…">`
where both attribute values are **HTML-entity-encoded JSON**. No browser needed —
`html.unescape()` the attribute, `json.loads` it:

```python
import re, html, json, urllib.request
raw = urllib.request.urlopen(urllib.request.Request(
        "https://bugcrowd.com/engagements/<slug>",
        headers={"User-Agent": "Mozilla/5.0"})).read().decode("utf-8", "replace")
anchor = raw.find("engagementsUrl")                 # any unique string from the payload
el = raw[raw.rfind("<", 0, anchor): raw.find(">", anchor)+1]
attrs = dict(re.findall(r'([a-zA-Z0-9_\-]+)="([^"]*)"', el))
props = json.loads(html.unescape(attrs["data-props"]))
api   = json.loads(html.unescape(attrs["data-api-endpoints"]))
```

- `props.earlyFetchProps.headerProps` → name, `state` (in_progress), `rewardAllocation`,
  `startsAt`, `scopeRank`, logo, engagement type.
- `props.earlyFetchProps.description` → the **full program description HTML**: the focus-area
  bullets, the VRT note, and "shares the same codebase as the cloud version" style caveats.
  This is often where the *real* scope nuance lives (e.g. "octopus.com is NOT in scope").
- `api` → the live route map per feature: `engagementStatsApi`, `engagementBriefApi`
  (incl. the changelog UUID), `announcementsApi`, `engagementScopeRankApi`, `engagementsApi`.
- Still public JSON with no auth: `/engagements/<slug>/statistics`
  (`rewardedVulnerabilities`, `averagePayout`, `validationWithin`) and `/scope_ranks`.
- `/announcements` returns **406** for `Accept: application/json` — fetch it as HTML.
  Announcements are the freshest scope changes ("X is now out of scope") — always read them.
- The **targets table itself needs JS** on some engagements (the DOM/table fast path below).
  `data-props` gives you the description; render in a browser for the scope tables.
Notes: `web_extract` (ddgs backend) is search-only and cannot fetch these → use `curl`. MSYS mangles a
relative `-o` path → always pass an absolute output path (`-o "D:/.../brief.json"`).

## FAST PATH first — built-in browser tools + DOM queries (verified 2026-09, Rapyd)
Before starting the camofox server, try the built-in browser tools. `browser_navigate` renders the
engagement page and the scope targets are plain `<table>` elements — quickest, most structured read:

```js
[...document.querySelectorAll('table')].map((t,i)=>({i, txt:t.innerText.slice(0,2500)}))   // scope tables
[...document.querySelectorAll('h3,h2,h4')].map(h=>h.innerText.trim()).filter(t=>/tier|scope|target/i.test(t))
document.body.innerText.slice(document.body.innerText.indexOf('Things to know'))           // rules/limits
```
Verified shape on a public Bugcrowd engagement:
- Table 0 = Tier 3 (Premium) — rows carry tags like `API Testing`
- Table 1 = Tier 2, Table 2 = Tier 1 wildcards
- Last table = **Out of Scope Targets** (rows typically have NO tag column — that missing tag is the tell)
- Headings read `Tier 3 In scope Premium` / `Tier 2 In scope` / `Tier 1 In scope` /
  `Out of Scope Targets`; use them to label tables instead of trusting order
- Per-tier reward bands, "Out-of-scope vulnerabilities", harder rate-limit wording and the
  required traffic header all live in body text, not tables
- Stable anchors: `#targets`, `#resources`, `#things_to_know`

If the extract step returns nothing for these pages (search-only extract backends), skip retries and
render in a browser — the briefs are SPAs.

## Stack: camofox server (~/camofox-browser)
- Start: `cd /home/agentuser/camofox-browser && npm start` (background, port 9377)
- Health: `curl -s http://localhost:9377/health`
- Underlying binary: Camoufox (anti-detect Firefox) at `~/.local/share/camoufox/`

## API (verified working)
1. Open tab:
   `curl -s -X POST http://localhost:9377/tabs/open -H "Content-Type: application/json" -d '{"userId":"hermes","url":"https://bugcrowd.com/<slug>"}'`
   → `{"ok":true,"targetId":"<id>",...,"title":"..."}`
2. Snapshot (a11y tree, YAML-ish, includes refs + full text):
   `curl -s "http://localhost:9377/tabs/<targetId>/snapshot?userId=hermes" -o snap.json`
   → `{"url", "snapshot", "refsCount", "truncated", "totalChars"}`
   **PITFALL: `userId` is REQUIRED as query param — omitting returns `{"error":"userId required"}`.**
3. Extract + parse:
   ```python
   import json
   d = json.load(open('snap.json', encoding='utf-8'))
   open('snapshot.txt','w',encoding='utf-8').write(d['snapshot'])
   ```
   Then read snapshot.txt with offset/limit and mine sections: rewards tables, targets, announcements, exclusions.

## Camoufox binary recovery (server fails to launch: cache empty/incomplete)
Symptom: `/tabs/open` hangs or errors; cache dir `~/.cache/camoufox/browsers/official/<ver>/` empty or missing exe.
`camoufox fetch` / `python -m camoufox fetch` can hang past 5min timeout (500MB download) — do it MANUALLY:
1. Check cache: `ls ~/.cache/camoufox/browsers/official/` → note version dir name (e.g. `152.0.4-beta.30-ea52a02f`).
2. Download matching release zip (~500MB, run in background):
   `https://github.com/daijro/camoufox/releases/download/v<release>/camoufox-<release>-<build>-win.x86_64.zip`
   e.g. `v152.0.4-beta.30/camoufox-152.0.4-beta.30-win.x86_64.zip`
3. Unzip INTO the version dir: `cd ~/.cache/camoufox/browsers/official/<ver> && unzip -o -q <zip>`
4. Create `version.json` in that dir: `{"release":"152.0.4","version":"beta.30"}` (match dir name parts).
5. **CRITICAL: server resolves the exe at Cache ROOT, not only the version dir:**
   `cd ~/.cache/camoufox && cp -rn browsers/official/<ver>/* .`
   Verify: `ls camoufox.exe version.json properties.json` all present at Cache root.
6. Restart server (`npm start`), then POST /tabs/open → must return targetId in seconds.

## Per-program capture workflow (consistent with _progress convention)
Dir: `D:\data hermes\bug-bounty\_progress\<program-slug>\`
Files: `snap.json` (raw) → `snapshot.txt` (extracted) → `scope.md` (facts: payout tables, targets, credentials, headers/bonus, exclusions, announcements w/ their special header IDs) → `progress.md` (gates + phased plan + log).
- Always capture: per-target-class reward tables (mobile vs web differ), excluded submission types, N-day policy, per-announcement `X-Luno-Announcement-ID`-style required headers, signup/credentials section.
- Announcements = freshest attack surface; owners explicitly state what they want tested.

## Pitfalls
- `camoufox fetch` via terminal foreground WILL timeout on 500MB — always background the manual zip download (notify_on_complete=true).
- Snapshot can include hundreds of trailing `- img` lines (avatars) — stop reading there, real content ends before.
- Never test/live-claim from the snapshot alone: snapshot = scope intel; actual probing needs the program's required traffic-identification headers from the brief.
