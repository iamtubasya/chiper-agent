# Bugcrowd engagement recon — full scope + rules without login

Applies to ANY Bugcrowd program (`bugcrowd.com/engagements/<slug>`), including
private/managed ones whose brief page looks login-gated. Confirmed on
`tripadvisor-bb-og`.

## The brief is NOT actually gated — hit the changelog endpoint with `.json`

The engagement page is a React SPA that fetches its brief from an API. Two gotchas:

1. The route map is embedded in the served HTML. Grep it for the engagement API paths:
   ```
   curl -s "https://bugcrowd.com/engagements/<slug>" | python3 -c "import sys,html;print(html.unescape(sys.stdin.read()))" \
     | grep -oE '"[a-zA-Z_]+":\s*"(/[^"]*<slug>[^"]*)"' | sort -u
   ```
   You will find e.g. `/<slug>/changelog/cfe0ee72-....` (the current brief document id).
2. Fetch that id **with a `.json` suffix** — no auth, no cookies:
   ```
   curl -s -H 'User-Agent: Mozilla/5.0' -H 'Accept: application/json' \
     "https://bugcrowd.com/engagements/<slug>/changelog/<uuid>.json"
   ```
   Without `.json` you get 404 (`{"errors":[{"detail":"Not found"}]}`) or the SPA shell HTML.
   With `.json` you get the WHOLE brief.

## Shape of the brief JSON

```
d = json["data"]
d["brief"]["description"]      # general program rules (HTML: <br>, <li>)  <- RULES LIVE HERE
d["brief"]["targetsOverview"]  # out-of-scope classes/brands (HTML)
d["scope"]                     # LIST of target groups
   group["name"], group["inScope"], group["rewardRange"] (p1..p4 cents)
   group["targets"][] -> {uri, name, category, tags[]}
```
Notes:
- `uri` can be empty for some rows; fall back to `name` (localized-site rows, tier-3
  "any public asset" rows).
- `rewardRange` cents ÷ 100 = USD. `rewardRangeData` may duplicate as dollars.
- Strip HTML entities before quoting rules: `re.sub(r'<[^>]+>','',html.unescape(s))`.

## Other public (unauth) endpoints worth pulling
- `/<slug>/statistics` → `{"rewardedVulnerabilities":..,"averagePayout":"$..","validationWithin":".."}`
- `/<slug>/scope_ranks` → `{"scopeRank":N}`

## Enforce the program's own rules (from `brief.description`)
Extract and honour verbatim; typical Bugcrowd clauses:
- **User-Agent MUST contain "bugcrowd"** for manual AND automated testing.
- **Accounts created for testing MUST contain "bugcrowd"** (display name + email/alias).
- Use existing **test properties**; only create your own if needed, with mandated values
  (e.g. first name "...Bugcrowd", last name "Test", a specific city, test bank details).
- Never touch live properties/customers. No DoS, no social engineering, no AI-system
  attacks, no physical. Honour the explicit OOS list (brands, paths like `/Trips`).

## Reporting mechanism
Bugcrowd submissions go through the **web form**, not email:
`/engagements/<slug>/submissions/new`. Do NOT produce an "email report" for Bugcrowd —
stage the report text (e.g. a Gmail draft) and paste it into the form.

## Tooling
`web_extract` (ddgs backend) is search-only and cannot fetch these — use `curl`.
