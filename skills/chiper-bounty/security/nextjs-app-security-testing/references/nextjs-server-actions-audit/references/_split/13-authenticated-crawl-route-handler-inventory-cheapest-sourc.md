## Authenticated crawl → route-handler inventory (cheapest source of new surface)

An anonymous crawl sees the landing pages. A crawl with the session cookie sees the app AND
its handlers:

```bash
katana.exe -u https://target -H "Cookie: qw_session=<value>" -jc -kf all -d 3 -c 5 -rl 6 \
           -timeout 15 -silent -o authed.txt -fs rdn
```

Then download every `_next/static/chunks/app/app/**/page-*.js` the crawl revealed and grep
for route handlers — they are plain strings, not action ids:

```bash
grep -ohE '"/api/[A-Za-z0-9_./{}$?=&-]+"' chunks/* | sort -u
grep -ohE '.{160}type:"file".{200}' chunks/*        # upload forms + their accept-list
grep -ohE '\{\s*id:"(\w+)",label:"([^"]+)"\}' chunks/*   # tab definitions (find gated tabs)
```

**Same inventory with `requests` + the session cookie (no katana needed).** Fetch each authed page
(`/app`, `/app/imports`, `/app/review`, `/app/account/*`, `/app/billing`, `/app/file`, `/app/hmrc`,
`/app/year-end`, `/app/other-income`, **and one `/app/sources/<own-uuid>`**), regex
`/_next/static/chunks/[^"'\\ ]+\.js` out of the HTML, download those chunks, then grep. The source
page matters — its per-route chunk is what carries the per-entry handlers. ~26 chunks / ~800 KB
total, a few seconds.

**Grep the bare path segment, not a quoted string.** Handlers here are built by concatenation —
`href:"/api/properties/".concat(t,"/export?format=xlsx&taxYear=all")` — so a `"/api/…"`-quoted grep
misses them entirely. Use the unquoted prefix:

```bash
grep -ohE '/api/[A-Za-z0-9_./{}$?=&-]{2,70}' chunks/* | sort -u
```

That is how `/api/properties/{id}/export?format=pdf|xlsx&taxYear=<year>` surfaced this pass — a full
ledger export (dates, categories, descriptions, amounts, account email) that neither the anonymous
crawl nor the OpenAPI document had ever listed. Test each new handler as its own BOLA case.

On Quarterwise this surfaced two handlers the HTML never referenced — `/api/attachments/{id}`
(receipt files on ledger entries) and `/api/invoices/{id}/pdf` — plus `type:"file"` inputs
and a tab (`InvoicesTab`) whose props (`invoicing`) showed it is feature-flagged per account.
Test each new handler as its own BOLA case: owner session / second account / no session /
random uuid. Result that time: 200 / 404 / 307 / 404 → control holds (worth reporting as a
positive). When a feature flag hides the object (no invoicing on your account) say
"coverage gap", not "clean".

**Receipt attachments hang off the LEDGER ENTRY, not the note.** The upload input only
appears in the entry's EDIT form (`id="files-<txnId>"`, `name="files"`, accept images+PDF),
and the link to the file only renders after clicking `button[aria-label="N attached file"]`
— grep the DOM for `/api/attachments/<uuid>` *after* that click, not before.

