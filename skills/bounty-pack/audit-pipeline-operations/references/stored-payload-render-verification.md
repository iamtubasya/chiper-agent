# Proving a stored-payload class is SAFE (the negative that is hard to earn)

Applies when input is stored verbatim and echoed back — so "it's stored, therefore XSS" looks true —
but you must decide whether it is a finding (High) or a negative you are about to write down.

Measured 2026-10-25, betterteam dashboard: two job records already held titles
`zq"><img src=x onerror=window.__xss2=1` and `XssT<img src=x onerror=window.__xss=1`.
`GET /career-page` and `GET /companies/me` echoed them back byte-for-byte. Both were **not** XSS.

## Why "stored + echoed" is not enough

Three different layers answer three different questions, and only the last one matters:

| layer | question | how it lies |
|---|---|---|
| storage | did the server persist my bytes? | persists happily, proves nothing about execution |
| server echo | does a JSON/XML API return the raw string? | echo ≠ render; APIs are supposed to return raw data |
| render | does the browser create a DOM node from it? | **this is the only finding question** |

An API echo plus a copied bundle's `dangerouslySetInnerHTML` grep is a guess. Render it.

## The probe (browser, not curl)

Log in with a real browser, navigate the exact page a victim/employer would see, then assert on the
DOM — never on page source (source always contains your payload):

```python
PROBE = """() => {
  const imgs = Array.from(document.querySelectorAll('img')).filter(i => i.getAttribute('src') === 'x');
  const oe   = Array.from(document.querySelectorAll('*')).filter(e => e.hasAttribute('onerror'));
  const txt  = document.body.innerText || '';
  return {
    imgSrcX: imgs.length,          // >0  => HTML parsed into an element  => XSS
    onerrorEls: oe.length,         // >0  => inline handler survived    => XSS
    flagX:  (typeof window.__xss  !== 'undefined') ? String(window.__xss)  : null,
    flagX2: (typeof window.__xss2 !== 'undefined') ? String(window.__xss2) : null,
    payloadAsText: txt.indexOf('onerror=window.__xss2=1') >= 0   // true => ESCAPED TEXT => safe
  };
}"""
```

Also capture dialogs as a second, independent oracle:

```python
dialogs = []
pg.on("dialog", lambda d: (dialogs.append(d.message), asyncio.ensure_future(d.dismiss())))
```

Verdict rules:
- `imgSrcX>0` or `onerrorEls>0` or `flagX*` non-null or `dialogs` non-empty → **XSS, report it**.
- `imgSrcX==0 and onerrorEls==0 and flags null and dialogs==[] and payloadAsText==true` →
  **NEGATIVE, and you now have proof**: `payloadAsText=true` is the positive evidence that the payload
  reached the page and was neutralised, not that your test failed to deliver it.

That last point is the whole trick. A bare "flag absent" is weak — it cannot distinguish
"escaped" from "payload never rendered / wrong page / cached shell". `payloadAsText=true` closes it.

## Two false trails that cost a cycle each

1. **Shell served to non-browser clients.** `GET /jobs/<slug>` via Python returned a 15 KB SSR
   shell for *every* slug including foreign ones — that looks like a missing job and it is not an
   authz result. Browser + `wait_until="networkidle"` is what actually renders data.
2. **Regex-in-evaluate.** A JS regex inside `page.evaluate` is a string-through-JSON twice; one
   unescaped `/` yields `SyntaxError: Invalid regular expression: missing /` and the whole probe
   dies. Use `indexOf` / `includes` / `querySelectorAll` and return plain numbers and booleans.

## Enumerate the render surfaces before closing the class

The same stored value is rendered in more than one place, and only some are in scope. For each
stored-payload candidate list every consumer: dashboard list view, dashboard detail view, public
profile/career page, transactional email, PDF export, admin panel, third-party widget.
In-scope-only rule bites here: on betterteam the raw HTML rendered **only** on the customer career
site (`<company>.betterteam.com`), which the program puts out of scope — so a genuinely-unescaped
sink there is not reportable. Write that down as "sink exists, scope excludes it", which is different
from "no sink".

## What to record

- the exact payload, the exact page/selector, the browser build, and the four probe numbers;
- the sanitizer actually in use (betterteam: `sanitize-html` with an allowedTags whitelist, no
  `on*`/`style`, schemes `http|https|ftp|mailto|tel`) — from the bundle, as corroboration only,
  never as the proof;
- the out-of-scope render surface, named explicitly, so the next auditor does not re-run this.
