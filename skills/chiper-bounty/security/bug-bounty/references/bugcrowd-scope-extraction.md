# Bugcrowd program scope extraction (unauthenticated)

## When to use
Any Bugcrowd engagement where the brief/scope looks login-gated: the engagement page is a React SPA
(`curl` returns a shell whose only text is `<title>… - Bugcrowd`), `/engagements/<slug>/scope`
301-redirects, and the obvious brief endpoints 404. **You do not need a Bugcrowd researcher session.**

## The trick — changelog `.json` suffix
1. Fetch the public engagement HTML and read its inlined API route map. The SPA embeds every
   endpoint, including `engagementBriefApi.getBriefVersionDocument`. Grep the changelog id:
   ```bash
   curl -s -H "User-Agent: Mozilla/5.0" \
     "https://bugcrowd.com/engagements/<slug>" -o /tmp/eng.html
   grep -oE 'changelog/[0-9a-f-]{36}' /tmp/eng.html | head -1
   ```
2. GET that path **with a `.json` suffix**. The plain path 404s
   (`{"errors":[{"detail":"Not found"…}]}`); the `.json` variant serves the entire brief without auth:
   ```bash
   curl -s -H "User-Agent: Mozilla/5.0" -H "Accept: application/json" \
     "https://bugcrowd.com/engagements/<slug>/changelog/<id>.json" -o /tmp/brief.json
   ```

## Response shape (`data`)
`data` = `{ brief, scope, resources, engagement, vrtScopeRules, engagementConfiguration }`

- `data.brief.description`        → program rules (e.g. UA must contain "bugcrowd"; test-property naming)
- `data.brief.targetsOverview`    → out-of-scope *classes* in prose (DoS, SE, missing-headers, AI, …)
- `data.brief.additionalInformation`, `data.brief.safeHarborStatus`
- `data.scope[]`                  → the real target groups:
  `{ name, inScope, rewardRange{p1MinCents..p4MinCents}, targets[]{ uri, name, category, tags[] } }`
  This is the authoritative in/out-of-scope host list **and** the per-tier reward table.
- `data.vrtVersion`               → the VRT version the program scores against

Blank `uri` entries: fall back to the target's `name` field (localized-site notes, path excludes
like `*.tripadvisor.*/Trips`).

Other endpoints that answer to a plain GET (JSON):
- `/engagements/<slug>/statistics` → `rewardedVulnerabilities`, `averagePayout`, `validationWithin`
- `/engagements/<slug>/scope_ranks` → `scopeRank`

## Pitfalls
- Plain `/…/changelog/<id>` → **404**; the `.json` suffix is mandatory.
- `/h/…`-prefixed paths return the SPA HTML shell, not JSON — use the non-`/h/` host.
- **Do not** `curl … | python3 - <<'PY'`: the heredoc becomes python's stdin and the piped body is
  discarded (you parse an empty string). Write the parser to a file, then `python3 parser.py < brief.json`.
- **Do not** write curl output to a *relative* filename in MSYS bash (`-o b.json` after `cd /tmp`):
  the Windows `curl.exe` resolves it against the Windows cwd, so the file won't be where the shell
  `ls`es for it. Always pass an absolute path (`-o /tmp/b.json`).

## Ready-made
`scripts/bugcrowd_scope_extract.py <slug>` — fetches the HTML, finds the changelog id, and prints the
scope tiers, reward table, and rules. No login.
