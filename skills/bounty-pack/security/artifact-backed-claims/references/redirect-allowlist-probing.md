# Redirect-allowlist probing — and the output-mask trap that fakes a bypass

Class: **open-redirect / SSRF-to-redirect hunting on a validator that gates the `link`/`url`/
`next`/`callback` parameter by host.** Measured 2026-10-30 on `sentz.page.link` (Firebase Dynamic
Links fronting `moby.app`), but the matrix and the trap generalise to any allowlisted-redirect
sink (OAuth `redirect_uri`, SSO `RelayState`, password-reset `?next=`, image/webhook proxies).

---

## 1. The trap that nearly produced a false Critical: the OUTPUT LAYER masks bytes

A probe of `link=https://moby.app#@evil.com/` returned `302`, and the console printed:

```
Location: https://***@evil.com/
```

The tool-output layer had **redacted the substring `moby.app#@` into `***`**. Read naively that is
an open redirect to `evil.com` — a Critical-shaped finding on a payments app.

The raw bytes said otherwise:

```bash
curl -s -m 20 -o /dev/null -D hdr.txt 'https://sentz.page.link/?link=<encoded>&apn=...&efr=0'
grep -ai '^location' hdr.txt | xxd
# 00000010: 2f2f 6d6f 6279 2e61 7070 2340 6576 696c  //moby.app#@evil
# 00000020: 2e63 6f6d 2f0a                           .com/.
```

`Location: https://moby.app#@evil.com/` — the `#` begins the **fragment**, so the browser navigates
to host `moby.app` with fragment `@evil.com/`. The allowlist held. **Not a redirect.**

**Rule:** any time a captured value looks altered, redacted, shortened, or suspiciously convenient
(`***`, `…`, `[truncated]`, `<redacted>`), re-read it from a **file at byte level** before building a
claim on it. Console output is a rendering, not data. This is the false-POSITIVE mirror of the
truncation trap in the parent SKILL.md — same fix, opposite failure direction.

---

## 2. The allowlist matrix (run all of it; record every row)

Baseline first: a known-good in-allowlist URL must return the real redirect (positive control).
Then vary exactly one axis per row. Verdict per row: `302 → Location` (honoured) vs `400` (rejected).

| # | Shape | Example | What it tests |
|---|---|---|---|
| 0 | **CONTROL** in-allowlist | `https://moby.app/?action=pay&handle=test` | must 302 to moby.app — proves the probe works |
| 1 | off-domain host | `https://evil.example.com/` | strict host check |
| 2 | allowlisted-domain **suffix** | `https://moby.app.evil.com/` | suffix vs exact match |
| 3 | **subdomain** of allowlisted | `https://evil.moby.app/`, `https://api.moby.app/` | is the whole zone trusted? |
| 4 | **userinfo** `@` | `https://moby.app@evil.com/` | parser reads host after `@` |
| 5 | **fragment** `#@` | `https://moby.app#@evil.com/` | validator sees pre-`#`, browser too → **stays on allowlisted host** |
| 6 | **query** `?@` | `https://moby.app?x=@evil.com/` | same as #5 — inert |
| 7 | explicit **port** | `https://moby.app:8080/` | port in the authority |
| 8 | **case** | `https://Moby.App/` | host lowercasing before compare |
| 9 | **trailing dot** | `https://moby.app./` | FQDN root-dot normalisation |
| 10 | **scheme downgrade** | `http://moby.app/` | is http allowed |
| 11 | `javascript:` | `javascript:alert(1)` | scheme allowlist |
| 12 | `data:` | `data:text/html,<script>…` | scheme allowlist |
| 13 | **protocol-relative** | `//evil.com` | scheme-less authority |
| 14 | leading whitespace / tab | ` https://moby.app/` | trim before parse |
| 15 | backslash authority | `https://moby.app\@evil.com/` | WHATWG vs RFC3986 parser split |

**Reading the result.** A validator that returns `400` for rows 1–4, 7–14 is a **strict host+scheme
allowlist** — a verified negative. Rows 5–6 returning `302` is **not** a bypass (see §1): hexdump
them, confirm the Location host is still the allowlisted domain, and record them as
`tested — not a redirect (fragment/query is inert)`.

**Parameter injection within the allowlist is usually by design.** If row 0-style links let you
append params (`handle=test%26admin%3Dtrue` → `Location: …?handle=test&admin=true`), that is the
deep-link resolver passing its payload through. It is only a finding if the **landing host acts on
the injected param** — test that separately (does the pay page reflect/act on `?admin=`?). If the
landing page ignores unknown params, it is Low-at-most and usually informational.

---

## 3. Adjacent surfaces worth one probe each

- **Custom FDL domain vs the generic one.** `links.sentz.com?link=…` returned **403** while
  `sentz.page.link?link=…` returned 302 — the branded domain rejected direct link construction.
  Probe both; they are different code paths.
- **FDL debug mode (`?d=1`).** Returns Google's generic DurableDeepLinkUi page. Confirms deep-link
  mechanics (`app.moby://google/link?deep_link_id=…`, Play Store fallback
  `…pcampaignid=fdl_long…`) but leaks **no project id or API key**. Useful for mapping the chain,
  not a finding.
- **`.well-known/assetlinks.json` + `apple-app-site-association`.** App identifiers only
  (`com.mobilecoin.moby`, Android signing-cert SHA256, iOS team `8JT9JJD9Y5` / bundle `app.moby`).
  No secrets — do not inflate.
- **Long-value handling.** A 4000-char `link` param was honoured verbatim (302 to the full value,
  no truncation/crash). Note it; it is not a vuln by itself.

---

## 4. Honesty gate for this class

- A `302` whose Location host (post-hexdump) is the allowlisted domain = **NEGATIVE**, even if the
  printed string looked alarming.
- A `400` across the whole matrix = **verified negative**; report it as such with the row list.
- Only a Location that **actually resolves to an attacker-controlled host in a real browser** is a
  finding — and you must show the bytes that prove the host, not the console rendering.
- `could redirect` / `appears to bypass` = not a bug. Prove it or drop it.
