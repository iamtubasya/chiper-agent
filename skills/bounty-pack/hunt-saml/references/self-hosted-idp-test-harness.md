# Self-hosted IdP test harness for SAML/SSO bounties

Built and validated end-to-end in a real engagement (Bugcrowd, fintech SP with a SAML 2.0
feature). Everything below is what actually worked on Windows 10 + git-bash, no Docker.

---

## 0. FIRST: check whether the SP will even accept your IdP domain

**This is the step that wastes hours if skipped.** Modern SPs validate the IdP's Entry Point /
Issuer against an allow-list of known providers. Observed on a live portal's SSO screen:

```
The Entry Point and Issuer URLs must belong to a trusted identity provider (Google, Microsoft, or Okta).
—— and separately ——
Invalid parameters or file structure
```

Symptoms seen in order:
1. `https://localhost:8443/...` IdP → **Save button stays disabled**; a submit attempt returns
   `Invalid parameters or file structure`.
2. Same Keycloak exposed publicly over real HTTPS (cloudflared tunnel) → **Save becomes enabled**,
   then the trusted-IdP message appears.

So: a self-hosted Keycloak (even with a public HTTPS hostname and a valid cert) is **rejected by
design** on such SPs. Before building the lab, read the program brief — if it says "you'll need a
SAML 2.0 IdP: Okta, Microsoft Entra ID, or Google Workspace", believe it and go straight to a
captcha-solvable provider (Okta Integrator Free Plan). Keep the Keycloak lab anyway: it is still
the fastest way to **train the payloads** (XSW/replay/comment-injection) against your own
SP harness before you point a real tenant at the target.

Signals to record in the report even when the IdP route is blocked:
- the exact validation string the SP returned (it names the allow-list),
- whether Save enable/disable depends on the URL (client-side gate) vs the message (server-side).

---

## 1. ACS baseline before anything else (cheap, sometimes reportable alone)

```bash
ACS="https://target/…/login/sso/callback"
curl -s -o /dev/null -w "%{http_code}\n" -H "X-Bugcrowd: Bugcrowd-<handle>" "$ACS"
curl -s -X POST -H "X-Bugcrowd: Bugcrowd-<handle>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "SAMLResponse=&RelayState=" "$ACS"
# then a bogus base64 assertion + evil RelayState:
curl -s -X POST -H "X-Bugcrowd: Bugcrowd-<handle>" \
  -H "Content-Type: application/x-www-form-urlencoded" --max-redirs 0 \
  --data "SAMLResponse=PHNhbWxwOlJlc3BvbnNlPjwvc2FtbHA6UmVzcG9uc2U%2B&RelayState=https%3A%2F%2Fevil.example.com%2Fpwn" \
  "$ACS"
```

Good SP behaviour = typed JSON error (`…_INVALID_SAML_REQUEST`) and **RelayState not followed** on
an invalid response. Record it as a working control, not as a finding.

---

## 2. Keycloak lab (Java, no Docker)

```bash
# 1. get the distribution (check the latest tag first)
curl -s https://api.github.com/repos/keycloak/keycloak/releases/latest | grep -o 'keycloak-[0-9.]*\.zip' | head -1
curl -sL -o keycloak.zip https://github.com/keycloak/keycloak/releases/download/<ver>/keycloak-<ver>.zip
unzip -q keycloak.zip && cd keycloak-<ver>

# 2. first boot (dev mode) — bootstraps the admin user into the embedded H2 DB
export KEYCLOAK_ADMIN=admin KEYCLOAK_ADMIN_PASSWORD='***'   # used ONLY on first boot
nohup ./bin/kc.bat start-dev --http-port=8090 --hostname-strict=false > kc.log 2>&1 &
```

Pitfalls (all hit for real):

| Symptom | Cause | Fix |
|---|---|---|
| `Port already bound: 8080` | something else owns 8080 (on Windows it may be a service you cannot `taskkill` — "Access is denied") | use a free port, e.g. `--http-port=8090`; check with `netstat -ano \| grep ':8080 '` |
| `'D:\data' is not recognized as an internal or external command` | `kc.bat` mangles quoted CLI args containing **spaces** | put cert/key/config files in a space-free dir (`C:/idp/`) and pass those paths |
| Admin password "wrong" after a restart | `KEYCLOAK_ADMIN_PASSWORD` only applies at first boot | keep the first password you set, or reset via `kcadm` |
| Killing the wrapper leaves the JVM listening | `.bat` spawns a child JVM | `taskkill /F /T /PID <pid>` (tree), then re-verify the port is free |
| Config edits vanish / args chopped | `-s` with JSON containing spaces/quotes gets mangled by cmd | create/patch via a **JSON file**: `kcadm create clients -r <realm> -f client.json` |

### Realm, SAML client, user (kcadm)

```bash
K=./bin/kcadm.bat
$K config credentials --server http://localhost:8090 --realm master --user admin --password '<pw>'
$K create realms -s realm=<realm> -s enabled=true
# client.json (kept as a FILE — avoids cmd quoting hell):
#   clientId = the SP's Entity ID (e.g. rapyd_merchants_portal)
#   redirectUris = [ SP ACS URL, + your local harness ACS while testing ]
#   attributes: saml_name_id_format=email, saml_force_name_id_format=true,
#               saml.force.post.binding=true, saml.server.signature=true,
#               saml.assertion.signature=true, saml.signature.algorithm=RSA_SHA256,
#               saml_allow_direct_access=false
$K create clients -r <realm> -f client.json
$K create users -r <realm> -s username=researcher -s email=researcher@<alias> -s enabled=true -s emailVerified=true
$K set-password -r <realm> --username researcher --new-password '<pw>'
```

Use the **same email as the SP account** you are testing — otherwise you cannot exercise the
NameID→user mapping, and the ATO vector has no baseline.

### Export the signing certificate the SP wants

```bash
$K get keys -r <realm>     # take the "certificate" field where use == "SIG"
# wrap the base64 at 64 chars between BEGIN/END CERTIFICATE → save as <name>.crt
```
The SP file picker usually accepts `.pem,.crt,.cer` (read the `accept=` attribute). Some SPs hand
you a `.cert` from Okta and then reject `.cert` — renaming to `.crt` is expected, not a bug.

### Public HTTPS issuer via cloudflared (needed when the SP/backend must reach you)

```bash
cloudflared tunnel --url http://localhost:8090 --no-autoupdate > tunnel.log 2>&1 &
grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' tunnel.log | head -1
# then RESTART Keycloak with the public host, or the metadata comes out as http://:
./bin/kc.bat start-dev --http-port=8090 \
  --hostname <random>.trycloudflare.com --proxy-headers xforwarded
```

Verify before touching the SP UI:
```bash
curl -s "https://<host>/realms/<realm>/protocol/saml/descriptor" | grep -oE 'entityID="[^"]+"'
# must be https://<host>/realms/<realm>   (http:// here = --hostname/--proxy-headers wrong)
```

Local-only HTTPS alternative (browser side): self-signed cert with
```
openssl req -x509 -newkey rsa:2048 -keyout idp.key -out idp.crt -days 3650 -nodes \
  -subj "/CN=localhost/O=lab/C=ID" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```
plus `--https-port=8443 --https-certificate-file=… --https-certificate-key-file=…`.
Chrome shows `NET::ERR_CERT_AUTHORITY_INVALID` → bypass by focusing the interstitial and typing
**`thisisunsafe`** (via real key events when driving over CDP).

---

## 3. Pre-flight: validate your IdP against your own SP harness

Do this BEFORE wiring the target, so a later failure is provably the SP's behaviour, not your config.

1. Tiny ACS endpoint that logs the POST and decodes the assertion (base64-decode `SAMLResponse`,
   pull NameID / Issuer / InResponseTo / Destination, check for a `Signature`, write raw XML to disk).
2. Register `http://localhost:8091/acs` in the Keycloak client's `redirectUris`.
3. Generate a SP-initiated AuthnRequest yourself (no signature needed if the client does not require
   signed requests): raw DEFLATE (zlib, drop the 2-byte header + 4-byte adler) → base64 → urlencode,
   then open:

```
https://<idp-host>/realms/<realm>/protocol/saml?SAMLRequest=<urlencoded>
```

4. Log in as the test user; Keycloak POSTs the SAMLResponse to your ACS. Assert:

| Field | Expected |
|---|---|
| NameID | the email you configured (`…@<alias>`) |
| Issuer | `https://<idp-host>/realms/<realm>` (HTTPS, matches what you paste into the SP) |
| InResponseTo | equals the AuthnRequest `ID` you generated |
| Destination | your ACS URL |
| Signature | present (rsa-sha256 + exc-c14n typical) |

Regex gotcha: the response may use a `dsig:` prefix (not `ds:`), so `<Response…>\s*<Signature`
never matches — match `<(?:dsig|ds|…):Signature`, or just grep `<Signature` for presence.

---

## 4. What the SP's SSO screen needs (generic shape)

| Field | Value |
|---|---|
| Provider name | any label |
| Entry Point / SSO URL | `https://<idp-host>/realms/<realm>/protocol/saml` |
| Issuer / Entity ID | `https://<idp-host>/realms/<realm>` |
| Certificate | the realm **SIG** cert exported as `.crt` (PEM) |

The SSO login entry is usually on the SP's login page ("Sign in with SSO" / "Sign in with SAML") —
that is where replay / XSW / RelayState tests actually execute.

## 5. Reporting notes

- Capture the raw `SAMLRequest`/`SAMLResponse` base64-decoded alongside the browser screenshot.
- Out-of-scope traps common in SAML briefs: dummy/permissive IdPs (MockSAML, "signs anything"),
  the admin attacking their own SSO config, already-tracked IdP-IDORs. Read the brief's
  out-of-scope list before submitting.
- If the SP refuses non-allow-listed IdP domains, state that explicitly in your notes — it is why
  the SAML vectors were not testable, and a future session should not re-derive it.
