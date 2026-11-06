# Stored-XSS-via-upload: verify execution before claiming it

Condensed from the Scribble Maps engagement (2026-10-31), where an SVG containing
`<script>` was accepted by `POST /api/account/uploadOverlay` and served verbatim as
`image/svg+xml` — and was **not** exploitable. Full detail lives in
`security/scribblemaps-engagement/references/ssrf-and-upload-verification-playbook.md`.

## The rule

"Payload stored and served back" is not a finding. Execution is the finding, and execution is
decided by response headers you can read in one request.

## Checklist

1. Fetch the stored URL and read: `Content-Type`, `Content-Security-Policy`,
   `X-Content-Type-Options`, `Content-Disposition`, `Access-Control-Allow-Origin`.
2. **`CSP: default-src 'none'; ...; sandbox` without `allow-scripts`, together with
   `X-Content-Type-Options: nosniff`, defeats inline script in the stored document.** Measured
   exactly this on `cdn.scribblemaps.com/user/overlay/.../qWAmIi.svg`.
3. **Prove it in a real browser, not by reasoning.** Navigate to the URL, capture `console`
   and `pageerror`, and separately test `<img>` and `<object>` embedding from a neutral
   origin. Chrome's own message is the evidence:
   *"Blocked script execution in '...svg' because the document's frame is sandboxed and the
   'allow-scripts' permission is not set."*
4. Check whether the stored **filename is randomised** (measured: `probe.svg` →
   `.../qWAmIi.svg`). Randomisation kills path traversal via filename — worth one line in the
   coverage doc either way.
5. Delete the test artefacts through the product's own remove endpoint.

## Why this matters more than it looks

Reporting a CSP-sandboxed SVG as stored XSS is a false positive that costs credibility with
the program and burns a daily submission slot on programs that cap reports. The same
discipline applies to HTML uploads, avatar/OG-image endpoints, and any "we store your file and
serve it from our domain" feature: read the headers, then execute in a browser, then write.
