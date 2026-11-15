# SAML & Signed Token Forgery — Research Articles Compendium

> Source: 3 PortSwigger Research articles on SAML/signed web tokens, 2025-2026 (d0ge, Heyes). Extracts: `_portswigger-extracts/articles/`. Complements: `saml-exploitation-patterns.md`, `jwt-playbook.md`.

## Article Map

| Year | Title | Contribution |
|---|---|---|
| 2025 | SAML roulette: the hacker always wins | DTD/!ATTLIST dup xmlns → XSW on Ruby-SAML; WS-Fed metadata as free signed XML |
| 2025 | The fragile lock | Attribute pollution + REXML/Nokogiri dual-parser + Void Canonicalization → auth bypass post-patch |
| 2026 | Introducing SignSaboteur | Burp ext: brute-force Flask/Express/Rails/etc signed session tokens, re-sign, auth bypass |

## Key Techniques

- **XSW root cause** — SP runs 2 parsers (REXML verifies sig, Nokogiri parses assertion). XPath `//ds:Signature` grabs FIRST signature anywhere; digest extracted via REXML, hashed element via Nokogiri → inconsistent handling = wrapper injection.
- **SAML roulette (DTD)** — inject `<!ATTLIST>` duplicating `xmlns` to desync parsers → forged Assertion accepted. Patched 1.12.4 (DTD ban) but root cause (dual parser) survived.
- **Attribute pollution** — duplicate simple-name attrs w/ different namespaces: `<samlp:Response ID="1" samlp:ID="2">` — libxml2 `xmlGetProp` returns FIRST attr (order-dependent); REXML returns opposite when prefix present. Signature XPath `//*[@ID='id']` vs `node['ID']` resolve different elements → which attr is "signed" attacker-chosen.
- **REXML namespace confusion w/o DTD** — `xml` prefix is reserved & un-redefinable, but REXML treats it as regular attr: `<Signature xml:xmlns='http://www.w3.org/2000/09/xmldsg#'/>`. Hide real Signature from REXML `//ds:Signature` while Nokogiri still sees it: `<Parent xmlns='...xmldsig#'><Child xml:xmlns='#anything'><Signature/></Child></Parent>`.
- **Void Canonicalization** — `xmlns:ns="1"` (relative URI) is well-formed but errors in libxml2 c14n → Nokogiri returns EMPTY STRING instead of failing → DigestValue = SHA-256 of "" = `47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=`. Same for SignatureValue of empty SignedInfo → fully arbitrary Response passes validation ("Golden SAML Response"). Affects ruby-saml <1.18.0, php-saml, xmlseclibs <3.1.4. NOT: xmlsec, Shibboleth.
- **Free valid signatures** — no assertion theft needed: (1) SAML metadata `?sign=true`; (2) signed error responses — send malformed AuthnRequest `<samlp:AuthnRequest ID="&#x80;" IssueInstant="INVALID" Version="INVALID">` → IdP MUST respond signed; (3) WS-Fed metadata (Okta/Entra, always public). Reflected error content triggering c14n error = void signature too.
- **Extensions/StatusDetail injection points** — schema-legal elements BEFORE Signature; nest hidden real signature in Extensions, fake in Assertion.
- **Impossible XSW caveat** — fake Signature left inside Assertion breaks digest (self-referential hash). Solve via void canonicalization (empty-string digest), not collision.
- **SignSaboteur methodology** — spot tokens (fixed-length b64/hex in cookie/param/body); timestamp change → sig change = derived; identify framework → default secrets/salts (docker env, config); brute-force derivation (Known/Fast/Balanced/Deep modes); then: id→1/admin claims, unknown param names (`id`,`user_id`), re-sign w/ default key. Claims attacks: OpenID standard claims w/ collaborator (SSRF via picture), Flask `_id`/`_user_id`, Express `passport`, Rails key derivation.

## Payload / Bypass Table

| Technique | Weakness | Exploit |
|---|---|---|
| Attribute pollution | ns-agnostic attr lookup | `<Response ID="signed-id" samlp:ID="attack">` order swap |
| Namespace hide | `xml:xmlns` REXML bug | wrap real Sig in `<Child xml:xmlns='#x'>` |
| Void c14n | relative xmlns → empty digest | `xmlns:ns="1"` on root; DigestValue = SHA256("") |
| Golden Response | sig over empty string | reuse/predict empty-string SignatureValue |
| Signed error | spec MUST respond | malformed AuthnRequest → signed Response |
| Metadata sig | `?sign=true` variant | extract enveloped Sig → transplant |
| Token brute force | weak/default secret | SignSaboteur Fast→Balanced→Deep |
| Claims forgery | known secret | id=1, `passport`, `_user_id` admin placeholder |

## By-Design / SKIP Filters

- xmlsec / Shibboleth xmlsectool: NOT vulnerable to void c14n — don't report.
- ruby-saml ≥1.18.0, xmlseclibs ≥3.1.4: patched — version-gate first.
- Okta signed-error reuse: vendor replied "SP must patch" — IdP-side only, target SP unpatched required.
- Metadata unsigned (default): `?sign=true` needed; no signed XML obtainable = chain blocked → INFORMATIONAL.
- Assertion reuse/one-time-cache: SP caching kills replay — test freshness first.
- Unknown-token brute force without confirmed framework: pure guessing = LOW/INFO unless key found.

## Severity Guide

- **CRITICAL/HIGH** — auth bypass: forged Assertion/void-c14n Response accepted as any user (PROVEN login as victim).
- **HIGH** — signed token secret recovered → admin session forged; collaborator ping via claims = solid evidence.
- **MED** — parser differential confirmed (2 parsers disagree) but full bypass unproven.
- **INFO** — token present, no derivation weakness, brute force failed.
- Signature accepted but authz unchanged ⇒ INFO. Blocked chain (no signed source XML) ⇒ INFORMATIONAL.

## Reporting Checklist

- [ ] Capture full SAML Response (b64+decoded XML) + SP framework/version.
- [ ] Attribute pollution: show order-dependence (two documents, swapped result).
- [ ] Void c14n: show DigestValue = `47DEQpj8...` (SHA256 of empty) in accepted response.
- [ ] Golden Response: modify claims arbitrarily + screenshot authenticated admin state.
- [ ] Signed-error source: show malformed request + IdP's signed response.
- [ ] Token brute force: show secret key found + original vs forged token + admin access.
- [ ] Tools: d0ge/XSW Burp ext, SAML Raider, SignSaboteur (BApp), SAMLRaider CVE-2025-25292 helper.
- [ ] State library versions tested (ruby-saml, php-saml, xmlseclibs) + patch status.
- [ ] Chain blocked (no valid sig source) ⇒ INFORMATIONAL per master KB.

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
