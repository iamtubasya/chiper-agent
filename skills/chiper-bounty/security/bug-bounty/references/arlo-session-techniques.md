# Reference: Arlo Bounty Session Techniques (2026-08-28)

> Real-world application of web-infra-recon techniques against Arlo bug bounty.
> Cloudflare WAF blocked ALL standard web-app attacks across 217 live hosts.

## Session Summary

**Target:** Arlo (arlo.com) — HackerOne bug bounty
**Blocker:** Cloudflare WAF returns 403 for all injection payloads (XSS, SQLi, SSTI, CRLF, etc.)
**Pivot:** Infrastructure analysis → S3, pre-prod, JS bundles, supply chain configs

## Technique 1 Applied: S3 Deep Enumeration

```bash
# downloads.arlo.com — S3 bucket listing ENABLED
curl -sk "https://downloads.arlo.com/?list-type=2&max-keys=1000"
# Result: 1000+ public files including:
#   - au/wrangler.toml (Cloudflare config leak)
#   - css/arlo/images/Thumbs.db (Windows thumbnail cache)
#   - backup/ directory with QSG PDFs
#   - docs/ with Netgear router manuals (legacy)
```

**wrangler.toml content:**
```toml
name = "devtestarlocom-arlosecure-vanity-url-redirects"
type = "webpack"
account_id = "141b07bb246caf7b97343ddc61de6947"
route = "devtest.arlo.com/arlosecure"
zone_id = "625ab506448a48710a58cad9050fb4e3"
```

**Finding:** Cloudflare Account ID + Zone ID leaked via public S3. Info disclosure (LOW ~3.1).

## Technique 2 Applied: Pre-Production Discovery

```bash
# preprod.arlo.com — 401 with Basic Auth
# Reveals: www-authenticate: BASIC realm="preprod.arlo.com/on/demandware.servlet"
# This is Salesforce Commerce Cloud (Demandware)!

# OCAPI accessible WITHOUT Basic Auth:
curl -sk "https://preprod.arlo.com/dw/shop/v21_3/product_search?q=test"
# Returns: {"_v":"21.3","fault":{"type":"MissingClientIdException"}}
# This means: API is OPEN, just needs valid client_id!

# Error type analysis:
# MissingClientIdException → API processes requests, needs client_id
# UnknownClientIdException → client_id validated (not just ignored)
# DemoClientIdException → "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" recognized (sandbox only)
# MethodNotAllowedException → /baskets GET not allowed (POST requires Authorization)

# Site ID discovered from storefront error:
# /on/demandware.store/Sites-Arlo-Site/default/ → 500 (site exists!)
```

**Key insight:** The OCAPI is a Salesforce Commerce Cloud API that doesn't require Basic Auth — only a client_id. The site ID is `Sites-Arlo-Site`. If client_id is discovered, product/store data accessible without auth.

## Technique 3 Applied: JS Bundle DOM XSS Analysis

```bash
# Downloaded OMS core JS (28KB)
curl -sk "https://oms.arlo.com/bundles/core/js?v=uY1NSDSLAJZK4NDc6VP1b1m2htoub7Sytv2G3s9IhYM1" > core.js

# Found DOM XSS sinks:
# Sink 1: .html() with unsanitized user data
kt=function(n){$.post("/Account/GetProfile",{username:n},function(n){dt($.parseJSON(n))})}
dt=function(n){
  $(".accountAvatar img").attr("src",n.GravatarUrl+"?s=70")
  $(".accountFullName").html(n.FirstName+" "+n.LastName)  // DOM XSS SINK
}

# Sink 2: Template literal injection in hidden input creation
vi = (n, t, i, r=false) => {
  for (const u in n) {
    r || f === "true" ? i.append(`<input type="hidden" name="${u}" value="${n[u][0]}" />`) : ...
  }
}

# Trigger: mouseover on #UserIdentityLink
$("#UserIdentityLink").on("mouseover",function(){kt(userIdentity)})

# Attack chain: Attacker registers with malicious FirstName → Admin hovers → XSS
# Status: Chain incomplete (GetProfile returns empty without auth)
```

## Technique 4 Applied: Supply Chain Config Leaks

Two wrangler.toml files found in S3 (same content):
- `downloads.arlo.com/au/wrangler.toml`
- (original from prior session)

Cloudflare Worker: `devtestarlocom-arlosecure-vanity-url-redirects`
Route: `devtest.arlo.com/arlosecure`

**Also discovered:**
- `css/arlo/images/Thumbs.db` — Windows thumbnail cache (info disclosure)
- `backup/` directory with Quick Start Guide PDFs

## Technique 5 Applied: ASP.NET Enumeration

```bash
# trace.axd — EXISTS (302, not 404)
curl -sk "https://oms.arlo.com/trace.axd" -D-
# HTTP/1.1 302 Found
# Location: /WebError?aspxerrorpath=/trace.axd
# → Handler is registered but auth-protected

# web.config — EXISTS (403, not 404)
curl -sk "https://oms.arlo.com/web.config" -o /dev/null -w "%{http_code}"
# 403 → file exists, blocked by IIS/Cloudflare

# Error page path disclosure:
# SamlConsume → 302 → Error500 (crash, reveals endpoint name)
# ForgotPassword → 200 with Error500 (server crash on invalid input)

# X-AspNet-Version: 4.0.30319 (on communityone.arlo.com, care.arlo.com)
# Access-Control-Allow-Origin: * (on communityone.arlo.com, care.arlo.com)
```

## Additional Findings from Session

### CommunityOne Open CORS
- `communityone.arlo.com` — ASP.NET 4.0, `Access-Control-Allow-Origin: *`
- `care.arlo.com` — ASP.NET 4.0, `Access-Control-Allow-Origin: *`
- Both serve public content → CORS misconfiguration but no sensitive data to exfiltrate

### OMS No Rate Limiting
- 100+ login attempts, 0 blocked
- CSRF token present (`__RequestVerificationToken`) but insufficient protection
- Third-party: Deck Commerce platform
- Severity: MEDIUM ~5.3 (CVSS: AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:L)

### SamlConsume Crash (DoS)
- `POST /SamlConsume` → 302 → Error500 (server crash)
- Unauthenticated trigger possible
- Severity: LOW-MEDIUM

## What Didn't Work (and Why)

| Technique | Result | Reason |
|-----------|--------|--------|
| XSS (12+ payloads) | BLOCKED | Cloudflare WAF |
| SQLi | BLOCKED | Cloudflare WAF |
| SSTI (6 payloads) | BLOCKED | Request validation |
| CRLF injection | 400 Bad Request | IIS/Cloudflare |
| HTTP request smuggling | 400 Bad Request | Cloudflare |
| Host header injection | 403 Forbidden | Cloudflare |
| Open redirect | No redirect | ReturnUrl not reflected |
| IDOR on OMS | 404 | Routes don't exist |
| CSRF on ChangePassword | 200 but needs reset token | Not exploitable |
| Cookie manipulation | 403 | Cloudflare WAF |

## Lesson Learned
When Cloudflare WAF is the primary defense, **infrastructure-level analysis** yields more results than web-app injection attempts. The OCAPI exposure on preprod and the wrangler.toml leak were both found through infrastructure pivoting, not web-app testing.
