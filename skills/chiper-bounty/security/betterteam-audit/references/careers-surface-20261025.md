# careers.betterteam.com — in-scope job pages + application form (tested 2026-10-25 round 4)

The ONE in-scope career surface. Every other `*.betterteam.com` career site belongs to a customer and
is out of scope. This file records how to reach real job pages without publishing anything, and the
full negative matrix, so round 5 does not re-derive it.

## Getting a live `/:slug` without publishing a job

`careers.betterteam.com/robots.txt` exposes:

```
Sitemap: https://app.betterteam.com/feed-static/sitemap.<uuid>.xml
```

That single file is a public ~30,844-URL list of every live job across the platform. Grep it for
`careers.betterteam.com/` and you get Betterteam's **own** postings (in-scope), e.g.
`/senior-full-stack-engineer-1` and `/senior-full-stack-engineer-2`. No approval, no publishing, no
policy problem.

```bash
curl -s https://app.betterteam.com/feed-static/sitemap.<uuid>.xml -o sitemap.xml   # ~4.5 MB
grep -o 'https://careers\.betterteam\.com/[^<]*' sitemap.xml
```

Cross-check that customer jobs do NOT leak into the careers.* namespace: customer URLs in that sitemap
are `<company>.betterteam.com/<job-slug>`, a different host, so the split is clean.

> Note on the root: `https://careers.betterteam.com/` can return a branded 429 ("Too many requests —
> Betterteam") or Cloudflare `error code: 1015` after automated passes. `/robots.txt`, `/favicon.ico`,
> `/nonexistent` and every `/:slug` keep serving during that window — it is a route-level throttle, not
> a host block. Sequence this host FIRST in a run, before scanners burn the rate budget.

## Measured results (all negative)

| probe | result |
|---|---|
| `GET /senior-full-stack-engineer-1` | 200, 32,200 B, `<title>` = "Senior Full Stack Engineer, Makati, Metro Manila" |
| `GET /senior-full-stack-engineer-2` | 200, 31,080 B, Melbourne |
| `GET /{slug}/apply` | 200, 20,691 B |
| `GET /{slug}/apply/standard` | 200, 17,398 B |
| query-param reflection (`utm_source`, `utm_campaign`, `ref`, `q`, `callback`, `lang`, `from`, `src` × 2 payloads) | **NEGATIVE** — canary `zxq9probe` never appears; response md5 byte-identical to baseline `d2157ce7ff` |
| HTML payload in any param | Cloudflare "Access blocked — Betterteam" 403 (WAF, not reflection) |
| cross-tenant slug (`msk-teleradiology`, `cdl-a-owner-operator-tanker`, `painter`, `server`) | 404 |
| neighbour slugs (`-0`, `-3`, `-1-1`) | 404 |
| `%2e%2e` / `%00` in slug | 400 from Cloudflare, 155-B stock page, no body leak |
| uppercase slug / `.json` suffix | 404 |
| `/senior-...-1/../senior-...-2` | 200 for `-2` — normal path resolution, not traversal |

## `/apply/standard` form internals

```html
<form class="" encType="multipart/form-data" method="POST">
```

- **No `action` attribute** (posts to the current URL), **no CSRF token**, **no hidden job id**, and
  **no captcha** (recaptcha / turnstile / hcaptcha all absent from the DOM).
- Fields: `email`, `name`, `phone`, `resume` (file, `accept=".pdf,.doc,.docx,.txt,.rtf"`), `body` (textarea).
- `data-testid`-less; the loader context is `window.__reactRouterContext` (React Router v7 / Remix
  style manifest at `s.betterteam.com/sites/assets/manifest-*.js`,
  routes `CareersPage` → `careers-job-layout` → `CareersJobPage` path `:slug`,
  plus `CareersJobApplyPage` / `CareersJobApplyStandardPage` / `CareersJobApplySuccessPage`).

**NOT TESTED, BY DESIGN:** the multipart POST handler, resume upload handling, and the success page.
Submitting an application is explicitly out of scope. Any finding here would need a submitted
application, which the program forbids — including on Betterteam's own posting.

## Remaining untested angles (the only real gaps)

1. The multipart POST handler itself — unreachable without submitting (OOS).
2. `JobDetailsWidget` rendering of employer-controlled fields, if a customer ever gained a
   `careers.betterteam.com` path. Currently only Betterteam's own postings exist there.
3. Whether the 429/1015 throttle can be avoided by a cold client (fresh IP/TLS fingerprint) to test
   `/` itself rather than `/:slug`. Low value: the routes that matter serve fine.

## Artifacts (2026-10-25 run)

`D:/data/hermes/betterteam-fresh-20261025/03-hunt/`:
`careers-live.txt`, `careers-reflect.txt`, `careers-reflect2.txt`, `careers-form-detail.txt`,
`careers-context.txt`, `careers-map.txt`, `careers-shell.txt`, `careers_senior-full-stack-engineer-1*.html`,
`careers-js/` (19 JS chunks), `feed-sitemap-full.xml`.
