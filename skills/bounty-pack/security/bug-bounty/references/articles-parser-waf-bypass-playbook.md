# Parser Discrepancy & WAF Bypass — Research Articles Compendium

> Source: 8 PortSwigger Research articles on parser differences / evasion, 2018-2025 (Heyes, Kettle et al). Extracts: `_portswigger-extracts/articles/`.

## Article Map

| Year | Title | Contribution |
|---|---|---|
| 2018 | Bypassing WAFs and cracking XOR with Hackvertor | Multi-level tag encoding in Repeater beats Cloudflare |
| 2022 | Hunting evasive vulnerabilities | Taxonomy of why vulns evade auditors; lazy techniques |
| 2023 | The curl quirk that exposed Burp Suite & Chrome | `--data-binary @file` local-file disclosure in copy-as-curl |
| 2023 | Backslash-powered scanning (extracts) | `\`-differential hunts unknown vuln classes |
| 2025 | Bypassing character blocklists with unicode overflows | Codepoint truncation `%256` → forbidden ASCII |
| 2025 | Bypassing WAFs with the phantom version cookie | RFC2109 `$Version`/quoted-string vs modern parsers |
| 2025 | Splitting the Email Atom (companion) | Email parser desync → access control bypass |
| 2026 | (see saml-auth-tokens playbook) | XML dual-parser desync — companion reference |

## Key Techniques

- **Unicode truncation** — server stores codepoint in 1 byte: `0x4e41 % 256 = 0x41 ('A')`. Craft `0x4e41 0x4f41 0x5041 0x5141` → `AAAA`. JS variant: `String.fromCharCode(0x10000 + 0x31)` wraps above 0xFFFF → `1337`. Real-world: MS firewall bypass + CRLF→XSS ($6k). Automate via ActiveScan++ + Hackvertor tag; Shazzer unicode table lists truncation chars.
- **Phantom $Version cookie (RFC2109)** — Tomcat/Spring: legacy parser on `$Version=1` → unescapes `\` in quoted values, honors `$Path/$Domain` (reflected cookie attrs). `Cookie: $Version=1; foo="\b\a\r"` → `foo=bar`. AWS WAF: `eval('test')` blocked, `"\e\v\a\l\(\'\t\e\s\t\'\)"` passes; octal `"\145\166\141\154..."` also passes (Python octal escapes: `\012`=LF, `\015`=CR, `\073`=`;`).
- **Cookie-name blocklist bypass** — RFC2109 comma separator: `$Version=1; foo=bar, abc = qux` → server sees cookie `abc=qux`, WAF sees value of `foo`. Spaces/tabs around `=` legal per spec.
- **Cookie splitting (multiline)** — send `Cookie:` header twice: Python/Ruby/PHP join with `,`; quoted value spans the comma → WAF sees half-payloads in separate headers: `Cookie: name=eval('test//` + `Cookie: comment')` → server: `name=eval('test//, comment')`. Param Miner automates.
- **Backslash-powered scanning** — inject `\` + payload / payload + `\`; differential in reflection/backslash handling flags XSS/SQLi/space-escapes in obscure parsers. Unknown vuln classes without known signatures.
- **curl `@` file read** — `--data-binary @/path` reads local file into body. If app generates curl commands with attacker-controlled body/header → LFI in operator context. Patched Burp 2020.5.1 (→ `--data-raw`); Chrome DevTools also patched. Works on any app invoking curl w/ user data; useful during SSRF testing.
- **Hackvertor multi-encode** — nested tags `<@base64_1><@hex_0(" ")>...` in Repeater/Intruder/Proxy; throw_eval XSS tag converted pre-send → Cloudflare bypass (`window.onerror=eval;throw'...'`).

## Payload / Bypass Table

| Technique | Weakness | Exploit |
|---|---|---|
| Unicode overflow | byte/codepoint truncation on storage | `0x4e41` → `A`; fromCharCode(0x10000+0x31) → `1` |
| Phantom $Version | Tomcat RFC2109 legacy mode | `Cookie: $Version=1; q="\\e\\v\\a\\l(...)"` |
| Octal escapes | Python SimpleCookie quoted strings | `"\073"` → `;`, `"\012"` → newline |
| Comma separator | WAF ignores RFC2109 commas | `foo=bar, sqli = payload` |
| Cookie splitting | header join w/ comma | 2 Cookie headers, quoted value split |
| Reflected cookie attrs | `$Path/$Domain` echoed | `Set-Cookie` attribute injection |
| Backslash differential | parser `\` semantics | `\`+payload vs payload+`\` response diff |
| curl @read | `--data-binary @file` | body starts `@` → local file exfil |

## By-Design / SKIP Filters

- Modern Tomcat ≥9.0.x default config may still honor `$Version` — test; absence of legacy handling = dead chain.
- Cookie quoted-string tricks fail server-side if app re-serializes/validates cookie values strictly.
- Unicode truncation requires actual byte-storage (DB varchar/char with 1-byte charset, downcast code) — echo-only reflection without truncation = no bypass.
- WAF blocks without confirmed downstream parser desync = blocked chain → INFORMATIONAL per master KB.
- curl quirk needs attacker influence over generated curl args — user-copy only, heavy interaction: label realistically.

## Severity Guide

- **HIGH** — auth bypass via parser desync (cookie injection → session confusion), confirmed CRLF→XSS from truncation.
- **MED** — WAF bypass reaching exploitable sink (SQLi/cmd injection delivered through evasion), reflected Set-Cookie attribute injection.
- **LOW** — evasion works but sink is benign (reflected text, no exec).
- **INFO** — differential response only, no confirmed parser desync downstream.
- Chain blocked (WAF passes but target parser rejects) = INFORMATIONAL, never claim HIGH.

## Reporting Checklist

- [ ] Identify target parser stack (framework + version) before/after WAF — show both interpretations.
- [ ] Unicode: show raw bytes sent + truncated char produced server-side (hex dump or echo).
- [ ] Cookie: show server-parsed cookie dict (error/reflection proving `$Version` mode active).
- [ ] Splitting: show reassembled value reaching the vulnerable sink.
- [ ] curl: show file contents in outgoing request (redact secrets) + app's copy-as-curl origin.
- [ ] WAF bypass alone ≠ finding — prove payload executed downstream.
- [ ] Automate: Param Miner (cookie tricks), ActiveScan++ (unicode), Hackvertor (encode chains).
- [ ] Blocked chain ⇒ INFORMATIONAL per master KB, no severity inflation.

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
