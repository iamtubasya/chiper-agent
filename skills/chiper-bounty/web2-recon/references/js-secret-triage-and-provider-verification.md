# JS-bundle secret triage — from grep hit to "is this key actually live and unrestricted"

A grep hit is a string. A finding is a credential that **authenticates against the provider** and
lacks the control that is supposed to constrain it. Almost every hit is neither. The skill is
separating them in a few minutes without either overclaiming or — the more expensive error —
dismissing a live key because the *display* looked like a placeholder.

## The failure this file exists to prevent

2026-10-29, Deutsche Telekom estate. A JS/secret sweep produced 113 hits. Reviewing them, the
Google API keys printed as:

```
AIzaSy...pVXo
AIzaSy...rZxU
AIzaSy...xnAg
```

They look fake — middle elided, the classic `...` of a redacted example. I classified them as
placeholders and moved on. **The `...` was my own output truncation.** The stored values were 39
characters, the exact length of a real Google API key. One of them (`AIzaSyDo7W8bpq…`, from
`b2b-europe.telekom.com/fileadmin/template/Public/js/myscript.js`) was **live, unrestricted, with
the Geocoding API enabled on project 291523791773** — a reportable Low that sat undetected for
several rounds because of a display artifact.

**Rule: never triage a secret from a truncated string.** Print `len(secret)` and the full value
before judging. If your tooling elides, that is a display decision, not evidence.

## Step 1 — classify before you test

| shape | usually | action |
|---|---|---|
| `AIza…` 39 chars | Google API key | test (see §2) |
| `AKIA…`/`ASIA…` 20 chars | AWS access key ID | test with `sts get-caller-identity` |
| `SG.…` 69 chars | SendGrid | test `/v3/scopes` |
| `sk_live_…` | Stripe secret | **stop** — do not test, report on sight |
| `eyJ…`.`eyJ…`.`…` | JWT | decode, check `exp`, check if it's a *service* token |
| `-----BEGIN … PRIVATE KEY-----` | key material | check for surrounding context first (§3) |
| `token:"constant.language"`, `secret:"settings.encrypted.x"` | **minified JS identifiers** | drop — not secrets |

That last row is the highest-volume false positive. Minifiers rename variables, and a property
named `token`/`secret`/`password` in a bundle is orders of magnitude more often a JSON-schema token
type or an i18n key than a credential. Sample: of 21 "generic_secret" hits in the Telekom sweep,
**13 were minified identifiers** (`token:"constant.language.boolean"`, `password:"eOTT_OneTimePassword"`).

## Step 2 — verify against the provider, and always run a negative control

The naive test is "does the key work". The *trustworthy* test is "does the key work **while a
sibling key from the same estate fails**". Without the control you cannot distinguish a genuinely
live key from a provider that returns `200` to everything.

Measured, three Telekom keys, identical request (`/maps/api/geocode/json`):

| key source | `status` | meaning |
|---|---|---|
| b2b-europe.telekom.com | `OK`, 1 result | **live + API enabled + unrestricted** |
| auth.api.telekom.com | `REQUEST_DENIED — This API is not activated on your API project` | key valid, API not enabled |
| backend.modelai-dev…halo.telekom.net | `REQUEST_DENIED — This API is not activated…` | same |

The two failures prove three things at once: your request is well-formed, the endpoint is not
permissive-by-default, and the one `OK` reflects *project-level enablement* rather than luck.

### Restriction checks that turn "key works" into "key is a finding"

For Google keys, the same call under different `Referer` values is the whole test:

```python
for label, hdrs in [("no referer", {}),
                    ("evil origin", {"Referer": "https://evil.example/"}),
                    ("other origin", {"Referer": "https://attacker.test/"})]:
    r = requests.get("https://maps.googleapis.com/maps/api/geocode/json",
                     params={"address": "Alexanderplatz Berlin", "key": KEY},
                     headers=hdrs, timeout=15)
    print(label, r.json().get("status"))
```

- All three `OK` → **no referrer restriction** → finding.
- All three `REQUEST_DENIED — Requests from referrer … are blocked` → restricted → correct, drop it.
- Mixed → the key is restricted to specific origins; note which, usually not a finding.

Repeat the *same key* three times to separate a real success from jitter, and record `elapsed_ms`
and `len(results)` — a `200` with `results: []` is not the same evidence as `results: 1`.

## Step 3 — the private-key false positive that costs an hour

`-----BEGIN OPENSSH PRIVATE KEY-----` inside a JS bundle is almost always a **UI string**, not key
material. Yopass/Coder/IAP consoles ship the literal as an input placeholder or a validation
message. Check the surrounding bytes before you treat it as a leak:

```python
i = text.find("BEGIN OPENSSH PRIVATE KEY")
print(text[max(0, i-300):i+400])
```

Telekom sample — the hit resolved to
`"sshPrivateKeyPlaceholder":"-----BEGIN OPENSSH PRIVATE KEY-----"`. A placeholder for an empty
textarea. Nine "privkey" hits across two hosts, zero real keys. A real key has base64 lines of
~70 chars and a matching `END` marker within a few hundred bytes.

## Step 4 — scoring honest impact

A live unrestricted third-party API key is **quota/billing exposure** (CVSS `A:L`), not a data
breach: `AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L` ≈ **5.3 → Low**. Do **not** escalate it by asserting
"an attacker could run up an unbounded bill":

- do not exhaust the quota to prove it — that degrades a live service and violates most programmes'
  Rules of Engagement;
- state the request count you actually made (here: 7);
- note the provider's default daily cap as the thing that bounds the ceiling;
- mark financial-loss impact as **reasoned, not proven**.

The same discipline as every other class: prove the control is missing, cap the severity at what
you can demonstrate, and say plainly which part is inference.

## Checklist

- [ ] Full secret value printed (no `...`), and `len()` confirmed
- [ ] Minified identifiers / i18n keys / schema tokens filtered out
- [ ] Each real-looking key tested against its provider's cheapest read endpoint
- [ ] ≥2 **sibling keys from the same estate** tested as negative controls
- [ ] 3 repeated rounds on the working key; `status` + result-count recorded
- [ ] Restriction probes run (Referer for browser keys; IP for server keys)
- [ ] Private-key hits inspected for placeholder context before being reported
- [ ] Severity capped at quota/billing (`A:L`), impact split into proven vs reasoned
- [ ] No quota exhaustion, no brute force; request count written into the report
