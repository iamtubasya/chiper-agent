# Unauthenticated enumeration, parameter discovery & reflection testing

Techniques proven on a hardened bank target (moneta.cz, 2026-10-26) where the unauth perimeter
turned out to be clean. The *methods* are the asset — they generalise to any Liferay/Spring/F5
stack and to any "find the unauth surface" mandate.

---

## 1. Error-oracle parameter discovery (better than guessing)

Guessing parameter names is low-yield: 7 guessed shapes for an Elasticsearch-backed search
endpoint all returned the same generic error. The oracle approach found the real name in 3 requests.

Pattern — add parameters one at a time and read the *validation* error, not the data error:

```
GET /endpoint                                  -> 200, 0 bytes        (no validation triggered)
GET /endpoint?groupId=20143&languageTag=cs-CZ  -> 400 {"error":"inputValue is required"}
GET /endpoint?inputValue=a&...                 -> 400 {"error":"inputValue must be at least 3 characters long."}
GET /endpoint?inputValue=hypoteka&...          -> 500 (real execution path reached)
```

Rules:
- A 400 with a *field name* is the server telling you the contract. Harvest it.
- A 200-with-empty-body usually means "no validation branch taken" → you have not reached the code.
- Once you have the name, sweep for length/type/enum constraints; each 400 is free schema.
- Then sweep *values* (valid / boundary / wrong-type) to find which reach execution (500 vs 200).

Applied here: `/o/es/search` on a Liferay host. The param was `inputValue`, min length 3, GET-only
(POST → 405). A groupId sweep showed only the *real* site group produced 500 while 0/1/999999/empty
returned 200-empty — proving the backend query really executed for the live group.

## 2. Reflection escaping map (decide XSS with data, not vibes)

When a parameter is reflected, do NOT stop at "it reflects". Measure which characters come back
raw vs escaped, character by character, and reason about the *sink context*.

```python
# one request per character, then regex the reflection out of the response
chars = [("lt","<"),("gt",">"),("quot",'"'),("apos","'"),("amp","&"),("bslash","\\"),
         ("slash","/"),("eq","="),("semi",";"),("lparen","("),("lbrace","{"),("rbrack","]"),
         ("newline","\n"),("cr","\r"),("tab","\t"),("pct","%"),("hash","#"),("at","@"),
         ("caret","^"),("pipe","|"),("tilde","~"),("bracket","[")]
```

Key insight that decides most JS-string reflections:
**HTML entities are NOT decoded inside `<script>`.** So `"` → `&#034;` inside an inline script is
safe even though it looks like a failed escape — the JS parser sees the literal six characters
`&#034;`, not a quote. Only an *unescaped* `"` (or a raw newline in some parsers) breaks the string.

Worked result (bank search page, `var searchUrlParam = "<value>";`):
```
<  -> &lt;     >  -> &gt;     "  -> &#034;     '  -> &#039;     &  -> &amp;     => no breakout
\  / = ; ( { ] [ tab % # @ ^ | ~                                        -> RAW
newline, CR                                                             -> WAF 403
```
`\` being raw is a red herring: without an unescaped `"` you cannot close the string, and you
cannot inject `"` because it is entity-encoded. Conclusion: verified control, not a finding.

Always also check the *second-order* sink: is the reflected value later fed to `innerHTML`
(entity decode → re-parse) or `eval()`? Here `searchUrlParam` only went into a config object and
out to an API; `eval(` count in the bundle was 0.

## 3. WAF fingerprinting by differential

Map what the edge blocks before concluding anything about the app:

| payload | result | meaning |
|---|---|---|
| `test123` | 200, 16 reflections | benign input reaches the app |
| `<script>alert(1)</script>` | 403 | WAF signature |
| `</script>`, `</SCRIPT>`, `<img`, `javascript:`, `${...}`, backtick, `';alert(1);//`, newline+alert | 403 | aggressive rule set |
| `<a href="x">` | 200, fully escaped | app escaping works |

Two distinct failure modes to keep separate:
- **WAF block** (403, uniform) — you learned nothing about the app. Do not report it as a finding
  and do not report it as a negative either; it is "unreachable behind WAF".
- **App escape** (200, escaped) — the control works. Report as a verified control.

If the WAF blocks every interesting payload, say so explicitly in the ledger. XXE is the classic
case: XML bodies to JSON endpoints returned the ASM block page on every request, so the parser was
never reached — "not exploitable *through this edge*", not "not vulnerable".

## 4. Response-size fingerprinting (stop misreading ffuf)

On a stack with an F5 ASM / CDN in front, several distinct byte sizes appear constantly. Learn them
before trusting any ffuf/nuclei output, or you will report a block page as an endpoint:

- `46650` bytes = F5 ASM block page (uniform, appears for *every* path when the tool's header set
  trips a rule). This is what made an early "ffuf found /backup, /temp, /tmp" result worthless —
  those were rule matches on the *path name*, not existing directories.
- `48397` bytes = application 403 page (directory exists, listing denied).
- `490053` bytes = application 404 page.

Practical rules:
- Always send a browser `User-Agent` to ffuf/nuclei; default tool UA is itself a signature.
- `-fs`/`-fr` on the *known* block size, and manually verify every "hit" with curl before believing it.
- A run where every path returns the identical size is a **suspect run**, not a negative
  (see also `references/recon-triage-and-vendor-claim-verification.md`).

## 5. Get the real contract with a browser capture, not guesswork

When an endpoint's parameter shape is unknown, one Playwright network capture beats a dozen guesses.
Drive the real UI (accept the cookie banner, type into the field) and read `request.post_data`
/ the query string off the wire. This is also the only reliable way to learn:
- the exact JSON envelope a SPA wraps around raw bodies,
- which headers the app actually sends (auth tokens, custom version headers),
- whether a "secured" call is genuinely secured or just flagged client-side.

Pitfall hit this session: Playwright's async API raised `TypeError: function takes exactly 5
arguments` on `query_selector` after a library upgrade — the sync API and the MCP browser tools are
the fallbacks, and a plain `curl` with the captured headers reproduces the call afterwards.

## 6. A 500 is a lead, not a finding — and usually an operational bug

`500 {"error":"Internal server error"}` with no stack trace, no version, no host is:
- not an information disclosure (nothing leaked),
- not an injection surface (you never reached a sink),
- usually a broken feature for that access level.

For a bank/fintech this is a *product* defect and belongs on the programme's separate product
address, not the bounty channel. Record it in the ledger as an observation with the exact
reproduction, and move on. Do not inflate it.
