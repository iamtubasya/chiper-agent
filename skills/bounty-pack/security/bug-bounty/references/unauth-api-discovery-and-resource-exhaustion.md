# Unauthenticated API discovery & resource-exhaustion technique bank

Condensed from the MONETA (moneta.cz) engagement, 2026-10-26. Every recipe below was executed and
produced a result. Ordered by value.

---

## 1. Discover endpoints from PRODUCT pages, not from the paths you already know

The single highest-yield move of the whole engagement. I had already mapped the loan calculators and
declared the widget surface "exactly 4 endpoints". Re-fetching a spread of product pages
(`/pujcky-a-uvery/...`, `/hypoteky/...`, `/kalkulacky/...`, `/ucty-a-karty/...`, `/zivnostnici-a-firmy/api`)
and grepping for endpoint literals surfaced three **mortgage** endpoints nobody had probed:

```
/unsecured/portal/mortgage/calculator/flexi/calculation
/unsecured/portal/mortgage/calculator/flexi/creditworthiness
/unsecured/portal/mortgage/calculator/refinanso/calculation
```

One of them carried the only confirmed finding of the engagement.

Recipe:
```bash
for u in <spread of product/calculator/onboarding pages>; do
  curl -sS -A "$UA" -m 25 "https://target/$u" -o "pages/$(echo $u|tr / _).html"
done
grep -ohE '"/[a-zA-Z0-9/_-]*(unsecured|portal|calculator|lead|alacarte)[a-zA-Z0-9/_-]*"' pages/*.html | sort -u
```
Also grep for the widget config keys that carry endpoints:
`endpointUrl|historyEndpoint|qrEndpoint|searchEndpoint|apiUrl|openApiUrl|cblOpenApiUrl|serverUrl`.

**Lesson:** "I already enumerated the API" is almost always false. Enumerate per *page that hosts a widget*,
not per endpoint family you happened to look at.

---

## 2. Iterative NotNull error oracle — recover a full request schema with zero docs

The API returns field-level validation errors in the body with HTTP 200:

```json
{"status":"ERROR","responseObject":{"code":"NotNull","message":"maturity","localizedMessage":"must not be null"}}
```

Loop: POST `{}` → read `"message":"<field>"` → add that field with a plausible value → repeat until the
error stops naming a field. Recovered four required fields per endpoint in 4-5 requests each.

```python
pl = {}
for _ in range(14):
    r = S.post(BASE + ep, json=pl, timeout=25)
    m = re.search(r'"message":"([^"]+)"', r.text)
    if not m:
        print("FULL RESPONSE:", r.text[:700]); break
    f = m.group(1)
    pl[f] = 30 if re.search(r'matur|year|month', f, re.I) else \
            (5_000_000 if re.search(r'amount|realty', f, re.I) else 5)
```
Pick values that are *realistic*, not just non-null — several endpoints only leave the validation layer
and return real data once the values are in a sane range (see §6).

---

## 3. Playwright network capture when parameter guessing fails

I guessed seven payload shapes for `/o/es/search` and every one returned the same generic error. One
Playwright run that typed into the real search box captured the actual contract in a single request:

```json
{"exchangeRatesDate":"2026-10-26T01:00:00"}
```

Rule: after ~3 failed guesses, stop guessing and capture. Guessing burns requests and teaches nothing;
one capture gives the exact parameter name, type and format.

```python
pg.on("request", lambda r: cap.append({"m": r.method, "u": r.url, "body": r.post_data})
             if r.resource_type in ("xhr", "fetch") else None)
```
Filter on `resource_type in ("xhr","fetch")` — a first attempt filtered on a URL substring and captured 0.

---

## 4. Parameter-name discovery via the validation-error oracle

Same oracle as §2 but for *query* parameters. An endpoint that returns `200, 0 bytes` with no params and
`400 {"error":"inputValue is required"}` once `groupId`+`languageTag` are present has just told you its
parameter name. Then `inputValue must be at least 3 characters long` confirms the type and the minimum.

---

## 5. Escaping map — decide reflected-XSS exploitability without a scanner

When a parameter reflects into an inline `<script>` string, measure the escaping character by character
instead of running dalfox and hoping:

```python
for name, ch in [("lt","<"),("gt",">"),("quot",'"'),("apos","'"),("amp","&"),
                 ("bslash","\\"),("slash","/"),("eq","="),("semi",";"),("lbrace","{"),
                 ("newline","\n"),("cr","\r"),("tab","\t"),("pct","%"),...]:
    payload = "Z" + ch + "Z"
    ... grep the reflection, compare to payload ...
```

Observed on a hardened target: `< > " ' &` all entity-encoded, everything else raw, newline/CR WAF-blocked.
Because HTML entities are **not** decoded inside `<script>`, entity-encoding the five breakout characters is
sufficient — no XSS. That is a *verified control*, and it is a far stronger statement than "dalfox found
nothing".

Corollary: if `\` reflects raw but `"` does not, there is no string breakout. Do not report it.

---

## 6. Timing-based resource exhaustion + parameter isolation matrix

The technique that produced MON-01. Measure server response time as a function of one numeric parameter,
then isolate which parameter is responsible.

```python
base = {"fixation":5,"maturity":30,"realtyAmount":5000000,"loanAmount":3000000}
for mat in [30, 40, 50, 100, 500, 1000, 5000, 20000]:
    t0 = time.time(); r = S.post(URL, json={**base,"maturity":mat}, timeout=180)
    print(mat, round(time.time()-t0, 2), "OK" if '"status":"OK"' in r.text else "ERROR")
```

Then isolate — this is what makes the report credible:

| variation | time | verdict |
|---|---|---|
| maturity=20000 | 66.70 s | **trigger** |
| fixation=20000 | 2.51 s | not the trigger |
| realtyAmount=1e12 | 0.30 s ERROR | properly validated |
| loanAmount=1e12 | 0.38 s ERROR | properly validated |

Then prove the *absence* of throttling (6 consecutive requests all served, 7 slow ones with no 429), and
find the plateau (50000→65s, 200000→61s, 2000000→44s, 20000000→62s) so you can say "server-side cap exists,
input validation does not".

**Validate 3x** on the triggering value and record all three numbers.

Realistic-value note: several endpoints only return real data once values are in range. `{}` and
`{"maturity":5}` both error; `{"fixation":5,"maturity":30,"realtyAmount":5000000,"loanAmount":3000000}`
returns a full calculation. Always retry with sane values before concluding "broken".

---

## 7. Fingerprint WAF block pages vs application responses BEFORE reading any scan result

This cost me a whole wrong conclusion. On a Cloudflare→F5→Liferay stack, four distinct byte sizes:

| size | meaning |
|---|---|
| 46650 | F5 ASM block page (looks like a 200 to ffuf) |
| 48397 | application 403 page |
| 490053 | application 404 page (Liferay themed) |
| 65802 | Liferay "not authorized" rendering the full homepage |

An ffuf run reported 17 "hits" on `ib.moneta.cz` that were all ASM blocks. Rule: **filter by size**
(`-fs <blocksize>`) and spot-check one "hit" with curl before believing it. A uniform byte size across
many paths is a WAF signature, not an application map.

Also: a 403 that returns the *homepage HTML* is not an endpoint — grep the body for the endpoint's own
error text before treating it as a lead.

---

## 8. jadx economics on large APKs

- `jadx -d out <dex>` on a 14.6 MB dex reported `finished with errors, count: 4658` of 6697 classes and I
  briefly treated that as "70% of the code is invisible". It is **per-method** failure on obfuscated code:
  10350 `.java` files were still produced and every security-relevant class was present.
- `jadx --single-class <fqn> --single-class-output X.java <dex>` is dramatically cheaper and succeeded every
  time. Use it as the default; reach for full `-d` only when you need to grep a whole package.
- Locate the owning dex first (`androguard` DEX class scan) so you decompile 300 KB instead of 14 MB.

---

## 9. String-pool hits are not call sites

`getExternalStorageDirectory` appeared in three dex files and looked like external-storage usage. It was
only in the **method-name string table**, alphabetically adjacent to `getExternalCacheDirs` /
`getExternalFilesDir`. No method referenced it.

Verify with per-method source (`m.get_source()`) or a targeted decompile before treating a string hit as
behaviour. Same trap produced a false "debug menu in production" lead — the view existed in the layout but
was `android:visibility="gone"` and nothing ever set it VISIBLE.

---

## 10. Cross-verify against the whole binary, not one decompile

I concluded "the JS bridge cannot be reached" from the `classes6` decompile alone. Re-checking with a regex
over all 37 concatenated dex (94 MB) gave the independent confirmation (`arg_script_file` = 1 occurrence
total). When a conclusion rests on one partially-failed decompile, re-derive it from the raw blob.

---

## 11. Ledger discipline — check telemetry before writing a coverage claim

I twice wrote a comfortable number into the coverage ledger that the telemetry contradicted:

- "nuclei killed at 1%" → it had actually issued **26 648 / 34 410 requests (77%)** over 43 minutes.
- "curated 9-template run" → a *different* run had loaded **1396 templates** and issued 4221 connections.

Both were corrected in writing. Rule: read `nuclei_both.err` / the tool's own stats line before claiming
volume, and disclose the real total. Overclaiming coverage and underclaiming volume are the same failure.

---

## 12. Honest framing when a finding sits near a programme's exclusion list

MON-01 (unbounded computation) sits close to two exclusions: "errors thrown when using an invalid request"
and "missing rate limit". The report stated both up front, argued why the finding is neither (it is the ~60 s
of computation, not the error; it is unbounded algorithmic complexity, not just throttling), and accepted
the vendor's right to reclassify. That framing survived review; hiding the ambiguity would not have.
