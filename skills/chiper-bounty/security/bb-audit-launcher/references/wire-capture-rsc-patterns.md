# Wire capture + tampering of Next.js RSC flight data

Next.js **App Router** ships a page's serialized application state inside the HTML as inline
`self.__next_f.push(...)` blocks (the "flight" format). On the wire that is the *first* response a
scanner sees, so it is both a **disclosure surface** and a **tampering surface**.

Provenance: reconstructed for this deployment. The skill's reference table described this file as
"Next.js RSC wire-capture + tampering patterns (quarterwise 2026-09-24)"; the run log itself is not
in this deployment, so the patterns below are the ones the sibling skill
**`modern-web-framework-attacks`** documents (§1 and §9f), written up as a capture-and-tamper
playbook. Extraction basics live there — read §1 for the field list; this file is the *wire* view.

## 1. Capture — you already have it, you just have to look

RSC data does **not** need a special request. It is inline in the document:

```bash
curl -s "https://TARGET/page" | grep -oP 'self\.__next_f\.push\(\[1,"[^"]*"\]\)' | head -5
```

Because it is inline, it also lands in **every proxy/HAR capture you already make**. Prefer reading it
from the captured exchange rather than re-fetching: the payload is identical, and a re-fetch can
return a different variant (A/B, geo, cache).

## 2. What to pull out of the flight JSON

```bash
# config objects — feature flags, SDK keys, settings
curl -s "https://TARGET/page" | grep -oP '"(socureSdkKey|stripeKey|apiKey|secret|token|auth)[^"]*":"[^"]*"'

# API endpoint patterns
curl -s "https://TARGET/page" | grep -oP '/api/v[0-9]+/[^"\\]*' | sort -u

# a whole nested config object
curl -s "https://TARGET/page" | grep -oP '"initialConfig":\{[^}]+\}'
```

Classes worth extracting: feature flags (unreleased features, internal toggles), payment/KYC provider
config, API endpoint schemas (types leak through error strings), token/network catalogues,
`initialConfig`-style bootstrap objects.

## 3. Severity discipline (this is where reports die)

- **Client-side SDK keys are public keys, not secrets.** `socureSdkKey`, `pk_test_…`-shaped Stripe
  keys and friends are designed to ship to the browser. Reporting one as "exposed secret" is an
  instant credibility loss.
- Escalate only when the key or config **enables an action** the user should not reach (e.g. an SDK
  key that lets you drive a KYC flow, or a demo endpoint that actually executes).
- Baseline severity for pure disclosure is therefore **low-to-medium**; say so plainly instead of
  inflating the class.
- **Read the sink before claiming XSS.** A `bgcolor`-style parameter reaching
  `dangerouslySetInnerHTML` is NOT a finding when it also passes a strict pattern
  (`^#[0-9a-fA-F]{3,8}$`). Check the validation, then claim.

## 4. Tampering — the RSC-reflection trap (escaped ≠ XSS)

Seed a marker into a parameter and search the raw HTML for it. You will almost always find it —
**inside the flight JSON, as an escaped string**:

```
"c":["","reset?why=cpmark987abc\u0026..."]
```

`\u003c`-escaped payloads are **not executable**. A naive "the marker is in the raw HTML → XSS"
claim is a false positive, because the marker is *always* present in the flight data.

Decide it with three questions instead of one grep:

| question | why |
|---|---|
| is the marker in **visible text**? | reflected-but-escaped text is not execution |
| is the marker in a **sink attribute** (`href`, `src`, `action`)? | that is the dangerous position |
| for raw HTML context: is it inside a **quoted JSON string** (escaped) or an unquoted attribute/node? | only the unquoted sink can execute |

**Only an unescaped sink is a finding.** Record the three answers as the evidence, not the grep hit.

## 5. Tampering — trust the commit, not the wizard

When a multi-step flow (upload → mapping → preview → import) is involved, the **preview is safe by
design** and the commit is the real boundary. Preview will render payload-shaped text as plain text;
that proves nothing about what gets stored.

- Complete the flow (confirm → choose target → commit) and **capture the final commit POST**.
- Verify by reading the **export**, not the wizard's visible state:
  - entries page — escaped text, or an executed `<img onerror>`?
  - XLSX export — literal in `xl/sharedStrings.xml`, or an `<f>` formula? (formula = injection)
  - CSV export — was a `'=` prefix added (mitigated) or not?
- Free-plan gating and multi-step wizards mean the visible UI can disagree with the server's final
  state; the captured request/response is the truth.

## 6. Checklist

1. Capture the document (or reuse an existing proxy/HAR capture).
2. Extract flight JSON → flags, provider config, endpoint map.
3. Classify each key: **public by design** vs **action-enabling**. Label it.
4. For any marker reflected into RSC: run the three-question sink test before writing "XSS".
5. For any multi-step flow: capture the commit, verify by export.
6. Escalate only on demonstrated action; otherwise report as disclosure with an honest severity.

See also: `modern-web-framework-attacks` §1 (RSC extraction) and §9f (flight reflection),
`nextjs-version-cve-gate.md`, `nextjs-nextdata-disclosure.md`.
