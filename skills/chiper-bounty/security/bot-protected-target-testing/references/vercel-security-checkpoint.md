# Vercel Security Checkpoint — identify, discard, recover

Observed on a Vercel-hosted product estate (5 hostnames: app / api / ai / explorer / docs) during a
bug-bounty session, 2026-10.

## Signature

| Field | Value |
|---|---|
| Status | `403` |
| Body size | **~34,150-34,200 bytes** (drifts a few bytes per request) |
| `Content-Type` | `text/html; charset=utf-8` |
| Title | `Vercel Security Checkpoint` |
| Marker | `data-astro-cid-…` attributes (Astro-built interstitial) |
| `Server` / `X-Vercel-*` | present as usual for the host |

**Discard rule (same as SKILL.md §3a):** when a wordlist run produces one status code and one
near-identical byte length across thousands of paths, the run measured the block page, not the app.
A 4719-result `ffuf` run was 4718 × `403` + `~34.1-34.2 KB` — one real artefact (`308` redirect)
and zero usable path findings. Report it as a coverage gap, never as "paths are protected".

## Triggers (both are self-inflicted)

1. **Sensitive-path wordlist.** `.env`, `config.php`, `web.config`, `server.key` → 403 while the
   index still returns 200, so the estate is not globally blocked — only the "interesting" request
   shapes are.
2. **Any request carrying an attack payload in the URL.** A single
   `?q="><img src=x onerror=alert(1)>` was enough to flip the **entire estate** to 403 — every host,
   every path, including the app's own XHR endpoints. Subsequent benign requests kept returning the
   checkpoint; the site was not down.

`Origin` does not matter — this is a network-edge check, not CORS.

## Timeline and recovery

| Time | State |
|---|---|
| t+0 | payload request sent |
| t+0..40 min | estate-wide 403 (~34 KB), including `/` |
| + scanners stopped, ~15 min idle | recovered |
| canary | single `GET https://app.<t>/api/announcements` with a desktop Chrome UA → real JSON |

Recovery procedure:

1. Kill every scanner by PID (`ps -W | grep -E "nuclei|ffuf|dalfox"`, then kill the MSYS PID — the
   wrapper PID alone leaves the child alive).
2. Wait 10-20 minutes. Do **not** rotate egress, do not retry hot.
3. One canary request, browser UA. Astro page back → wait again. Real body → resume at low rate
   (`-rl 3`, `-t 3`) and keep payload-shaped strings out of URLs on Vercel targets.

## Related Next.js / Vercel artefacts that look like findings

- **`308 Location: <same path minus trailing slash>`** on `/.git/logs/`, `/.git/` — this is Next.js
  trailing-slash normalisation. Following it returned `404`. Not source disclosure, not a path oracle.
  Follow every redirect before counting a hit (`curl -D- -o /dev/null`).
- **`X-Matched-Path: /api/points/[wallet]`** — the handler's own route template. Genuinely useful
  recon (see `hunt-spa-api`), not a vulnerability.
- **`403 {"message":"Origin not allowed"}`, `403 {"error":"Forbidden"}`** — an application-layer
  allowlist on POST handlers. Bypassed by any non-browser client (curl has no `Origin`), and the
  responses carry **no** `Access-Control-Allow-Origin`, so it is anti-abuse hardening, not access
  control. Check `ACAO` presence before writing CORS anything.
- **`Server: railway-hikari`** on a sibling host = Railway, not Vercel — different edge, same
  discipline about discarded scan runs.

## Honest reporting language

    "The estate returned a Vercel bot-checkpage (403, ~34 KB, consistent across every path) for the
     duration of the automated run, including to requests the site itself makes. That run is not
     evidence of path protection in either direction, so I make no claim about those endpoints; the
     application-layer behaviour I report below was re-tested after the challenge cleared."
