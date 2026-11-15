---
name: poc-technique-atlas
author: RESEARCHER_NAME
description: >-
  Method-level technique atlas extracted from the local PoC corpus (2,223 GitHub PoC repos,
  filtered + deduped) plus PortSwigger Web Security Academy topic structure. Use during a
  web2 / pentest / bug-bounty audit when you need the METHOD for a vulnerability class —
  RCE & command injection, SQLi, XSS, SSRF, LFI, XXE, SSTI, deserialization, auth bypass,
  IDOR/BOLA, CSRF, race conditions, file upload, CRLF/smuggling, prototype pollution,
  GraphQL, NoSQL, memory corruption, crypto flaws, cloud/metadata, supply chain — or want to
  see how a CVE class is actually exploited without pulling raw exploit code. Reference shelf,
  NOT an orchestrator: owner skills' rules win on conflict. Read ONE class file per phase.
metadata:
  hermes:
    tags: [security, techniques, poc, web2, portswigger, reference-shelf]
---

# PoC Technique Atlas

A **method shelf**: what each bug class *is* and how it is actually exploited, distilled from
a 2,223-repo local PoC corpus and the PortSwigger Web Security Academy. **No exploit bodies,
no malware, no payload dumps** — technique lines + one exemplar repo to read if you need
detail.

> Provenance: `D:/data hermes/poc-compact/` (2,223 GitHub PoC repos; 61,135 files after
> compaction) → classified → malware/scam-filtered → deduped → 1,901 techniques in 27 class
> files. PortSwigger: 29 topic files scraped from portswigger.net/web-security (topic +
> subtopic technique headings). Rebuild with `D:/data hermes/_poc_techniques/` scripts.
>
> **Pass 2 (2026-10-17):** gap-fill dari repo yang belum terekstrak — 54 CVE yang ada di
> corpus tapi belum masuk atlas + 870 repo tanpa-CVE. Hasil: **+65 teknik** di 6 kelas
> (rce +50, xss +6, auth-bypass +4, lfi +4, sqli +1). Filter 4 tahap: klasifikasi →
> buang kode/CLI/non-latin → wajib kata mekanisme → wajib konteks vuln.
> 1.295 → 301 → 147 → 65 (noise dipotong bertahap; kualitas > jumlah).
>
> **Deep pass (2026-10-17):** gali 393 repo tanpa README dari **source code**
> (komentar/docstring + pola API berbahaya). Temuan jujur: **369 repo KOSONG total**
> (0 file — sisa clone gagal), 10 repo source tapi bukan vuln (tooling: codechecker,
> fastecdsa, regreSSHive), hanya **2 repo** yang punya teknik nyata
> (`G33l0_Cve-2026-64638` WordPress 4.7.0–7.0.2 open-redirect→XSS chain via missing-plugin
> 301; `12121211aaaaa_CVE_2024_30085` clfs.sys struct-size parsing). Hasil: **+12 teknik**.
> 33 → 17 → 13 → 12 (repo tooling & "code signal" polos dibuang).
>
> **Koreksi (2026-10-17, operator challenge):** 3 repo yang sempat dikira "tooling"
> ternyata **PoC system-level nyata** dan sudah dimasukkan ke kelas benar:
> `regreSSHive` = **CVE-2024-6387 regreSSHion** (OpenSSH SIGALRM race → RCE root, pre-auth);
> `xz-cve-2024-3094` = **xz/liblzma supply-chain backdoor** (nilai audit = deteksi, bukan
> eksploit); `Geal_trailer` = heap-layout primitive. Yang **benar** dibuang hanya
> `Ericsson_codechecker` (analyzer statis, 993 file) dan `AntonKueltz_fastecdsa`
> (library ECDSA). **Aturan: jangan buang repo hanya karena isinya C/shell — cek dulu
> apakah ada CVE-ID atau mekanisme RCE/privesc di komentar header.**

---

## When to use

Load this when an audit reaches a phase where you know the *class* but want the concrete
*methods* — e.g. "how do CVE-2024→2026 SSRF bypasses actually slip past hostname filters",
"which deserialization gadget families exist", "what race-condition patterns pay".

**Do not** load the whole shelf. Pick ONE class file for the phase you're in.

## Navigation

- `references/00-INDEX.md` — all 28 classes with technique counts and one-line scope.
- `references/<class>.md` — technique table: `# | Technique (method) | Exemplar repo`.
- `references/nuclei-detection.md` — 13,777 nuclei templates → per-class detection
  observables (matcher kinds) + severity mix. Use to build your own scanner rule.
- `references/distilled/00-INDEX.md` — distilled technique index of the pre-existing
  reference shelves (bug-bounty 730 files, exploit-cookbook 89, bb-audit-launcher 69,
  bugbounty-playbook 187, exhaustive-testing 20) → 827 KB, ~24x smaller. Check here
  before opening the original heavy shelf.
- `references/portswigger/00-INDEX.md` — 29 WSA topics → technique counts.
- `references/portswigger/<slug>.md` — WSA topic: technique headings + subtopic pages.
- `references/web-blogs/yeswehack.md` — 48 technique-relevant YesWeHack posts (URLs + gist).

Map from task → file:

| If the target shows… | Read |
|---|---|
| eval/exec/template/upload → code exec | `rce.md` |
| query params, auth forms, ORDER BY errors | `sqli.md` |
| reflected/stored/DOM input sinks | `xss.md` |
| URL fetchers, webhooks, image importers | `ssrf.md` |
| file/template includes, download paths | `lfi.md` |
| XML/SOAP/SAML parsers | `xxe.md` |
| template engines | `ssti.md` |
| serialized blobs (Java/PHP/Python/Node/.NET) | `deserialization.md` |
| login/MFA/JWT/OAuth/SAML/session | `auth-bypass.md` |
| object ids, /api/{id}, role gates | `idor-bola.md` |
| state-changing POST w/o token | `csrf.md` |
| limits, coupons, stock, check-then-act | `race-condition.md` |
| upload endpoints | `file-upload.md` |
| proxies/CDN, header handling | `crlf-injection.md` |
| redirect params | `open-redirect.md` |
| debug/VCS/backup/verbose errors | `info-disclosure.md` |
| JS merges, client state | `prototype-pollution.md` |
| /graphql | `graphql.md` |
| Mongo/operator queries | `nosql.md` |
| IMDS, buckets, containers | `cloud.md` |
| native parsers, binaries | `buffer-overflow.md` |
| crypto/tokens/hashes | `crypto.md` |
| CI/CD, packages | `supply-chain.md` |
| anything else | `other.md` (876) |

## How to read a class file

Rows are **methods**, not payloads. Take the method, adapt it to the target, and use the
exemplar repo name only as a pointer if you need the low-level detail. Never paste a payload
body from the corpus into a live target without adapting + validating impact first.

## Integration (additive, never overrides)

| Owner skill | Relationship |
|---|---|
| `web2-vuln-classes` | classes + root causes; this atlas = the *methods* per class |
| `security-arsenal` | payload tables; this atlas = the technique *shapes* |
| `exploit-cookbook` | worked playbooks; this atlas = the raw method inventory behind them |
| `bugbounty-playbook` | bugbounty.info mirror; complementary |
| `hunt-*` skills | per-class hunting steps; atlas supplies method breadth |
| `bb-audit-launcher` / `audit-execution-discipline` | on-demand shelf, read ONE file, does NOT count against phase context budget |

Where two skills disagree, the owner skill's rule wins.

## Hygiene

- Malware/scam repos (stealer, RAT, backdoor, miner, ransomware, dropper/loader, C2,
  credential-dumper, skimmer, phishing-hit) were **excluded** during extraction.
- `dos.md` is report-only: never run DoS/ReDoS against a live target (out of scope on most
  programs).
- One root cause per technique. If a row is a vendor CVE, the *method* is the transferable
  part — the CVE id is the exemplar.
