# Insecure Deserialization — Bug Bounty Playbook

> **Source:** PortSwigger Web Security Academy — portswigger.net/web-security/deserialization (raw extract, compressed). AKA **object injection**. Ruby = marshalling, Python = pickling. Core rule: user input should never be deserialized; validation *after* deserialization is too late. Binary/opaque formats are NOT safe — just harder to read. Typed languages (Java/C#) are equally vulnerable: attacks fire during deserialization, before app logic runs; an exception does not stop already-completed damage.

## 1. Quick Detection

Scan cookies, params, hidden fields, API bodies for structured blobs:

| Lang | Raw marker | Base64 marker | Probe |
|------|-----------|---------------|-------|
| PHP | `O:4:"User":1:` / `a:2:{` / `s:4:` | `Tzo0OiJVc2Vy` | `curl -s "$URL" -b "sess=<tampered PHP blob>"` |
| Java | hex `AC ED 00 05` | `rO0ABQ` | swap blob w/ `rO0AB...`; watch for `ClassNotFoundException` |
| Ruby | hex `04 08` + `o:` (Marshal) | `BAhv` / `BAhT` | tamper `BAh`-prefixed session cookie |
| Python | hex `80 04 95` (pickle proto) | `gASV` | decode b64 → pickle opcodes |

Signals: opaque cookies with internal structure; errors mentioning `unserialize` / `unmarshal` / `pickle` / `readObject` / `__PHP_Incomplete_Class`; stack traces naming libraries.

## 2. Vulnerability Types / Exploitation Vectors

| # | Vector | Technique |
|---|--------|-----------|
| 1 | Attribute manipulation | Edit field values in serialized object (e.g. `s:5:"admin";i:0` → `i:1`); feed app logic. No RCE needed. |
| 2 | Data type manipulation | Change typed fields (int→array, string→int) to trigger logic errors + verbose stack traces (recon). |
| 3 | App functionality abuse | Deserialized object feeds other features: user field in password-reset object → reset any account. |
| 4 | Magic methods | `__wakeup` / `__destruct` / `__toString` (PHP), `readObject` / `readResolve` (Java) — auto-invoked on deserialize; primary injection entry. |
| 5 | Arbitrary object injection | Swap object for ANY class available to the site — every reachable class gets instantiated regardless of expected type. |
| 6 | Gadget chains | Chain magic-method calls through app + library deps to a sink (exec, file write, SQLi). Pre-built first (ysoserial for Java), then documented chains, else build own by mapping source→sink. |
| 7 | PHAR deserialization (PHP) | Upload file with serialized PHAR metadata; `phar://` stream ops (e.g. `file_exists`) trigger deserialization. |
| 8 | Memory corruption | Deserialization engines can corrupt memory → crash/RCE; documented exploits work without gadget chains. |
| 9 | Python pickle | Pickle restores arbitrary objects with embedded reconstruction logic → user-supplied pickle = code-exec surface; treat `gASV` blobs as RCE candidates. |

Impact ladder: RCE (most common severe outcome) > privilege escalation > arbitrary file access > DoS.

## 3. Bypass / Payload Table

| Technique | Signature / Magic | Notes |
|-----------|-------------------|-------|
| Java magic bytes | `AC ED 00 05` / b64 `rO0ABQ` | Confirms engine → feed ysoserial chain matching target libs |
| Ruby Marshal magic | `04 08` / b64 `BAh` | Tamper attributes; keep structure/length counters valid |
| Python pickle magic | `80 04 95` / b64 `gASV` | Craft malicious pickle; no blind RCE testing in prod |
| PHP object injection | `O:<len>:"<Class>":<n>:{...}` | Fix internal length/count values when editing |
| Signature bypass | HMAC checked AFTER decode → tamper payload, keep original sig; if processed = broken design | Only robust if verified BEFORE deserialization |
| Post-deser validation bypass | WAF/app validates values after deserialize | Use classes/types never anticipated — validation cannot cover all cases |
| Gadget chain selection | Match target's library versions | ysoserial / phpggc / documented chains before hand-building |

## 4. By-Design Filters (SKIP — NOT findings)

- Integrity signature verified **before** deserialization; tamper attempts rejected → protected, no report.
- No user-controllable data is ever deserialized anywhere → nothing to report.
- Gadget chains / dangerous libs present in dependencies but no user-input deserialization → not a finding (vuln = deserializing user input, not chain existence).
- Deserialization exceptions on malformed input with no object instantiation or state change → noise.
- "It's Java/typed, so it's safe" → NOT a valid skip reason; strongly-typed apps are equally exploitable.

## 5. Severity Guide

| Scenario | Severity |
|----------|----------|
| RCE proven (gadget chain / pickle / PHAR / memory corruption) with callback | CRITICAL |
| Priv-esc, auth bypass, arbitrary file read/write via object tampering | HIGH |
| SQLi / SSRF / LFI reached as gadget sink | HIGH (per sink) |
| Attribute tamper with security impact (role, amount, account reset) | HIGH |
| Attribute tamper, limited / non-security impact | LOW–MEDIUM |
| Deserialization reached but chain blocked / no provable effect | INFORMATIONAL |
| Valid pre-deserialization signature, non-bypassable | NOT A FINDING |

## 6. Reporting Checklist

- [ ] Param/cookie location + raw serialized sample (marker identified)
- [ ] Engine/format confirmed (PHP/Java/Ruby/Python) with evidence
- [ ] Tampered payload + differential response proving acceptance
- [ ] Chain named: magic methods, injected classes, gadget libs/versions
- [ ] Impact demonstrated end-to-end — RCE needs out-of-band proof (DNS/HTTP pingback), not theory
- [ ] Signature/validation timing verified (pre- vs post-deserialization)
- [ ] Severity per §5; destructive tests (DoS, memory corruption) NOT executed live
- [ ] Remediation: avoid deserializing user input; verify signatures BEFORE deserialization; use class-specific serialization methods; never try to "fix" by removing gadget chains

> ⚠️ Blocked/unproven exploit chain = INFORMATIONAL per master KB rule. Never claim HIGH/CRIT from theory alone.
