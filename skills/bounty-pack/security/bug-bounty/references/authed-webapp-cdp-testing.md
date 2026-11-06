# Authenticated web-app testing via headful Chrome + CDP

For creating a test account and driving authed flows on WAF'd / bot-protected sites
(DataDome, GeeTest, reCAPTCHA Enterprise) where curl/headless scanners get blocked.

## Getting a CDP browser when the Hermes browser_* tools point elsewhere
`config.yaml` carries `browser.cdp_url` (e.g. `ws://localhost:9222`). The Hermes
`browser_navigate` tool may still try a different backend (Camofox) and fail — drive
CDP directly instead:
```
chrome.exe --remote-debugging-port=9222 --remote-allow-origins=* \
  --user-data-dir="<dedicated profile dir>" --no-first-run --no-default-browser-check \
  --disable-blink-features=AutomationControlled about:blank
```
Then use the `browser_cdp` tool: `Target.getTargets` (get the page targetId) →
`Page.navigate` → `Runtime.evaluate` → `Input.*`. Launch Chrome on the **same port**
as `browser.cdp_url`. Headful + a real profile passes DataDome far more often than headless.

## Filling legacy / MooTools / React forms (duplicate IDs!)
Real pitfall hit on TripAdvisor: the visible field **container AND the inner `<input>`
share the same id** (e.g. both a `<div id="regSignUp.password">` and
`<input id="regSignUp.password">`). Consequences:
- `document.getElementById('regSignUp.password')` returns the **DIV**, not the input.
- Setting `.value` on it silently creates a JS expando (looks like it worked on read-back!)
  while the real input stays empty.
- Dispatching synthetic `input`/`change` events throws errors from the site's own
  MooTools observers and can reset other fields.

Fixes that work:
- Target the real input explicitly: `document.querySelector('input[id="regSignUp.password"]')`.
- Fill with **real input**, not JS setters: focus the element, then CDP
  `Input.insertText {text}`. Blur/advance to trigger validation.
- For clicks on the real element when JS `.click()` misfires, use CDP
  `Input.dispatchMouseEvent` at the element's `getBoundingClientRect()` centre —
  and re-read the rect right before clicking (layout shifts; a stale rect lands off-target).
- Always **read back** each field's value via `querySelector('input[id="..."]').value`
  before submitting.

## reCAPTCHA Enterprise may not actually block submit
A visible checkbox anchor can be present yet the form still submits successfully
(score-based). Try the submit once before assuming you must solve it. Clicking the
checkbox with CDP mouse events frequently does NOT register — don't burn many calls on it.

## Email verification
Test aliases (e.g. `*@BC_ALIAS.com`) forward to the real inbox. Read via IMAP with
the account app-password and search recent headers for the sender/subject; fetch the
newest matching message and extract links. (A fresh signup may not require verification
before the session is usable.)

## Evidence hygiene
Log every target state change and revert it before closing the session (fields you set,
accounts created). Re-read the rendered DOM to confirm the revert (e.g. marker text gone).

## Verification pitfall that caused a FALSE POSITIVE this session
`grep -o PATTERN file | head -3 && echo "FOUND"` **always prints FOUND**: the pipeline's
exit status is `head`'s (0), and `head` succeeds even when grep matched nothing. Never
branch on a piped exit code. Instead capture the count explicitly and test it:
```
n=$(grep -c 'PATTERN' file); [ "$n" -gt 0 ] && echo "FOUND $n" || echo "none"
```
This exact bug produced a bogus "HTML injection" hit — always re-verify a hit with an
independent read (context grep / DOM read-back) before believing it.
