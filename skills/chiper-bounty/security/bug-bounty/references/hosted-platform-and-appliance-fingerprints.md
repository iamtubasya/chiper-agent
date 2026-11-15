# Hosted-platform + appliance fingerprints (for OOS scope triage and infra mapping)

A subdomain on the target's domain is not automatically theirs. These fingerprints tell you in one
request whether you're looking at the client's app or a third-party vendor's hosted platform, and
which appliance you're facing (fingerprint only — do not attack VPN/remote-access infra).

## Third-party hosted platforms — likely OUT of scope

**Teamtailor** (recruitment/ATS career sites, e.g. `career.<brand>.com`):
- HTML is Stimulus-driven: `data-action="click->blocks--cover--scroll#handleScrollDown"`,
  `data-blocks--jobs-language-code-value="en-GB"`.
- `robots.txt` carries `User-Agent: aihitdata` / `Disallow: /jobs/internal/` / `Content-Signal:`.
- => the app belongs to Teamtailor; a bug there is Teamtailor's, not the brand's. **OOS** even
  though it's `*.brand.com`. Confirm ownership before spending time.

Other hosted-ATS/CDN tells: `*.ghost.io` CNAME, Kinsta (`X-Kinsta-*`), `myshopify`, `webflow`,
`squarespace`, `hubspot`, `atlassian.net`.

## Appliances / identity front-ends — fingerprint, don't attack

| What you see | What it is | Note |
|---|---|---|
| 302 -> `/global-protect/login.esp` | **Palo Alto GlobalProtect** VPN portal | `GET /global-protect/prelogin.esp` -> `<prelogin-response>` XML. `<msg>Valid client certificate is required</msg>` => mTLS-enforced (hardened). Do not attack. |
| 302 -> `login.microsoftonline.com/<tenant-guid>/oauth2/authorize?...&state=AppProxyState:...` | **Entra ID Application Proxy** (on-prem app published via Entra) | leaks the **tenant GUID** — recon only |
| 302 -> `/.auth/login/aad` | **Azure Static Web Apps / App Service EasyAuth** | |
| `/` 302/403 with a Java server banner + `jamf` name | **Jamf MDM** console | |
| 403 with `Server: UploadServer` + `X-GUploader-UploadID` + `Access-Control-Allow-Origin: *` | **Google Cloud Storage** custom-domain bucket | listing denied (403 XML `AccessDenied`); `storage.googleapis.com/<hostname>` returns `NoSuchBucket` — bucket name != hostname, so you cannot enumerate by key |
| 400 `<html>...<title>429</title>` | GCP Cloud Armor rate limit (see `web2-recon` -> `references/live-target-scan-budget-and-429-backoff.md`) | |

## Infrastructure signal mapped from CSP alone

The CSP `connect-src` / `img-src` on a marketing page names the real backend estate
(`api.prod.<vendor>.io`, `cdn.prod.<vendor>.io`, `relay.prod.<vendor>.io`,
`experimentation.public.prod.<vendor>.io`, `analytics.<brand>.se`, `files.<brand>.se`) — cheaper
than subdomain brute force. Probe each: a **403 `AccessDenied`** with an `X-GUploader-UploadID`
header means a GCS bucket; a **503 "no healthy upstream"** with `server: istio-envoy` means the
route exists but isn't reachable without the right path/host.

## WordPress custom-plugin AJAX triage

`/wp-json/` returns the full route table (count them — 202 on one corporate site) and namespaces
that reveal the plugin stack (`gravityforms/v2`, `nps-survey/v1`, custom `nordnet-*`). Custom
(brand-named) plugins usually register **no REST route** — their surface is `admin-ajax.php`.
Harvest the `action:` values from inline page JS and probe each via POST
(`curl -X POST -d "action=<name>" .../wp-admin/admin-ajax.php`). `nopriv` handlers that return 500
on an empty body exist but may be harmless — for a handler taking a base64-JSON `atts` blob,
decode it, then re-POST tampered fields and check the response encodes them (nordnet_stock escaped
`isin`/`info` => no HTML injection, no SSRF trigger: verified negative).
