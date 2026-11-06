# Origin hunting & takeover verification on CF-fronted estates

Companion to `references/target-defense-patterns-and-wall-triage.md` (which covers the UA-block
bluff, Turnstile ladder, SvelteKit data endpoints, APK/Hermes, DNS-leak triage). This file adds
only what that file does NOT have: finding the origin behind the CDN, and verifying takeover
flags. Worked case: Byte Federal, 2026-10-20.

## 1. DNS categorization first (5 minutes, shapes everything)

Resolve ALL enumerated subdomains and bucket by IP class:

```
CLOUDFLARE proxy : 104.16-28.*, 172.64-67.*, 188.114.*, 173.245.*
TAILSCALE/CGNAT  : 100.*            -> internal hostname leak (see wall-triage §DNS leak)
BARE cloud IP    : everything else  -> DO/AWS/Vultr/etc, direct-origin candidates
```

Byte Federal: 35 CF / 8 Tailscale / 22 bare / 25 NXDOMAIN out of 90. The bare IPs clustered by
owner: the whole KYC/identity cluster (api.verify, coaster44xx, hitworks, furlberry, brightpoint,
alchemy, test.mobileapi) shared ONE origin `104.248.125.225`; the auth API was direct
(`147.182.183.15`); portal+MCP shared `159.65.39.81`; the Lightning cluster `165.22.44.115`.
That clustering itself is reconnaissance (it tells you which services share infrastructure).

## 2. Host-header origin test

```bash
curl -k https://<bare-IP>/ -H "Host: <cf-fronted-host>" -w "%{http_code} %{size_download}\n"
```

For each bare IP × each CF-fronted host. Byte Federal results:
- KYC origin answered ANY Host with a **default Apache+PHP vhost** (Set-Cookie: PHPSESSID) — not
  a bypass; CF is the only ingress. The origin later went dark (000) after heavy probing.
- `159.65.39.81` → 502 Bad Gateway for foreign Hosts (vhosts serve only their own apps).
- A Vercel-range IP → `DEPLOYMENT_NOT_FOUND` for foreign Hosts.

Verdict shape to write in the ledger: "no origin bypass — origins serve default vhost / 502 for
foreign Host headers". Negative with evidence, not a finding.

## 3. subzy takeover flags on CF-proxied hosts = verify before believing

subzy flagged `influx/ldbapi/ldbapiglobal` as "Cargo Collective" takeovers. All three resolve to
**CF proxy IPs** (104.18.1.29/104.18.0.29) and return the generic CF 404 — the fingerprint engine
matched the CF error page, not a Cargo service. FALSE POSITIVE.

Verification order (always):
1. A/CNAME record first. Resolves into a CF proxy range → zone is owned by the target, takeover
   impossible, done.
2. Real takeover needs a CNAME to a claimable service (s3/github-pages/heroku/cargo.site/…)
   AND that service's signature not-found page.
3. Bare-IP hosts with no HTTP: check port 22. **SSH open = live server**, not a dangling record
   (onyx/tagcase/skynyxvanta were all SSH-open). Only a deallocated cloud IP is recyclable.
4. dnsReaper/subzy output is a candidate list, never a finding — same rule as nuclei labels.

## 4. Soft per-IP rate limiting

After sustained probing, individual paths may start returning **CF error 1006** (observed on
`/web/dashboard` after heavy fuzzing). That's self-inflicted, not a finding — note it, rotate to
other hosts/classes, and if the target starts mass-429ing see
`references/passive-recon-during-target-lockout.md`.
