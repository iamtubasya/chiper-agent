# Liferay DXP Testing Quick Reference

## Fingerprint
```bash
curl -sI https://target.com | grep -iE "Liferay-Portal|Set-Cookie|Server"
curl -s https://target.com | grep -oE 'liferay-[0-9]+-theme-[a-z0-9-]+'
```

## API Discovery
```python
import urllib.request, re
req = urllib.request.Request("https://target.com")
html = urllib.request.urlopen(req, timeout=10).read().decode()
o_paths = set(re.findall(r'/o/([a-zA-Z0-9_/-]+)', html))
portlets = set(re.findall(r'([a-z_]+_portlet_[a-zA-Z0-9_]+)', html))
```

## Key Endpoints — UNPATCHED 7.4 baseline (verified live 2026-10, moneta.cz)
Byte-accurate behaviour of a hardened Liferay DXP 7.4 + F5 ASM estate. Use this as the
"what a healthy target looks like" column: exactly these shapes = control working, NOT a finding.

| Endpoint | Observed | Meaning |
|----------|----------|---------|
| `/api/jsonws` | `404` + body `{}` | JSONWS servlet not mapped (good) |
| `/api/jsonws/invoke` | `403` + body `{}` (2 bytes, `application/json`) | mapped but auth-gated by WAF/Liferay |
| `/api/jsonws/user/get-current-user` | `404` + `{}` | method dispatcher not exposed |
| `/o/api` | `403` + `{ }` (3 bytes) | headless root gated |
| `/o/headless-admin-user/v1.0/user-accounts` | `403` + `{ }` | gated |
| `/o/headless-delivery/v1.0/sites` | `404` + 62-byte body | version/route absent, not gated |
| `/o/openapi.json`, `/o/swagger-ui*`, `/o/v3/api-docs` | `404` **Liferay-branded HTML** (≈208 KB) | portal 404 page, not the API |
| `/c/portal/render_portlet` | `200` with **0 bytes** | reachable but no portlet named → try `p_p_id` |
| `/c/portal/login` | `302 → /` | normalised, no `redirect=` passthrough |
| `/c/portal/update_language?redirect=<abs>` | `404` / `403` / normalised→`/` | **open-redirect negative**; only relative works |
| `/documents/<groupId>/0/<name>` | `404` Liferay HTML | private tree not enumerable |
| `/o/<bundle>/__liferay__/index.js` | `200` | JS bundle — the real recon surface (below) |

**Fingerprint beat the header.** No `Liferay-Portal` response header was present; the version was
established only from asset paths and theme id:
`/o/mmb-2024-theme/js/main.js` (theme = the product), `/o/frontend-js-web/liferay/*.js`,
`/o/frontend-taglib-clay/__liferay__/exports/@clayui$*.js`, `/o/dynamic-data-mapping-form-field-type/__liferay__/index.js`.
Also check `<combo?…themeId=<x>theme_WAR_<x>theme…>` in the HTML — it leaks the theme WAR name.

## The real recon surface: React portlet bundles (7.4 pattern)
Modern Liferay installs ship custom React widgets as OSGi bundles under `/o/`. They are NOT in the
portal HTML — you get their URLs only by capturing **runtime** requests. Playwright + request listener
on the page that hosts the widget recovers the whole chunk list:

```python
pg.on("request", lambda r: reqs.append({"m": r.method, "u": r.url, "rt": r.resource_type}))
await pg.goto(URL, wait_until="domcontentloaded"); await pg.wait_for_timeout(20000)
[u["u"] for u in reqs if u["rt"] == "script" and "moneta.cz" in u["u"]]
# -> /o/react-widgets/unified-onboarding.js, runtime.js, 2644.<hash>.js, 6930.<hash>.js ...
```
Then `grep -oE '"/[a-zA-Z0-9_./{}$:-]{4,90}"' *.js` over the chunks gives the private API map that
appears NOWHERE in the public HTML. Each portlet also injects a config block worth reading verbatim:
`<script type="application/json" id="react-widget-global-configuration">` → `openApiUrl`,
`reCaptcha.siteKey`, `isEnterprise`, plus a per-widget `configuration = { qrEndpoint: … }`.
The inline widget config is where endpoints, site keys and product ids actually live.

## CVEs — and the 2026 reality on a patched target
- CVE-2020-7961 (JSONWS deserialization) — dead if `/api/jsonws/invoke` is 403.
- CVE-2022-29082 (RSS SSRF) — needs a valid `p_l_id`; unobtainable unauthenticated → do not chase.
- CVE-2022-42118, CVE-2024-25608, CVE-2025-4388, CVE-2025-4576 — all ran clean on 7.4 (see below).
- CVE-2023-36196 (deserialization via portlet) — still needs an authenticated render.

Verified invocation (curated, 24 requests total — appropriate for a bank):
```bash
nuclei -u https://www.moneta.cz -u https://ib.moneta.cz \
  -t <T>/http/misconfiguration/liferay -t <T>/http/exposed-panels/liferay-portal.yaml \
  -t <T>/http/cves/2020/CVE-2020-7961.yaml -t <T>/http/cves/2022/CVE-2022-42118.yaml \
  -t <T>/http/cves/2024/CVE-2024-25608.yaml -t <T>/http/cves/2025/CVE-2025-4388.yaml \
  -t <T>/http/cves/2025/CVE-2025-4576.yaml -rl 4 -c 2 -timeout 10 -o out.txt
# Templates: 9, Requests: 24/24, Matched: 0
```
The six generic templates are `liferay-api`, `liferay-axis`, `liferay-jsonws`,
`liferay-resource-leak`, `liferay-workflow`, `liferay-portal`.

## Pitfalls
- Headless APIs answered `403` with a **3-byte** `{ }` body — that is a gate, not a JSON parse error.
  Do not "retry with different Accept headers" for hours; 3-byte 403 = enforced.
- JSONWS `500` with a 2-byte `{}` body is NOT a crash to escalate — it is the servlet refusing.
- 404s that return ~208 KB of Liferay-branded HTML mean **the portal handled it** (route absent).
  A 404 with a tiny body means an edge/WAF answered instead. The byte size tells you which layer spoke.
- `p_l_id` guessing is a dead end; skip it and go after `/o/<bundle>/` JS instead.
- A `/documents/` URL that works for marketing images proves nothing about private documents —
  different `groupId`, and the private tree needs auth. Do not report "document library exposed"
  off a public asset URL.
- Do not bother with `/combo?…` — it is a CSS/JS concatenator, returns `404` when hand-built.
