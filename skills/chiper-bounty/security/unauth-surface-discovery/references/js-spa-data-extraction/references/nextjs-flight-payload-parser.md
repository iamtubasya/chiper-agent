# Next.js flight payload — unwrap + brace-match

Session-verified recipe (2026-09-13) for lifting records out of a headlessly
rendered Next.js **App Router** directory.

## 1. Get a rendered dump

```bash
chrome --headless --disable-gpu --dump-dom --virtual-time-budget=8000 \
  "https://TARGET/directory" > page.html
```

A large dump (hundreds of KB) is normal and expected — that is the whole point.
Never pipe it into a summarising extractor; it is markup.

## 2. Locate the payload

App Router inlines data as repeated pushes:

```html
<script>self.__next_f.push([1,"a:{\"name\":\"...\"}\n"])</script>
```

Find them with a search (not a regex over the whole file):

```
self.__next_f.push(
```

## 3. Unwrap, then brace-match

Two steps, in this order — mixing them is what produces truncated output:

1. **Unwrap** each `push([1,"<escaped>"])` argument into its real string
   (unescape `\"`, `\n`, `\\`), and concatenate chunks **in document order**.
   The payload is a chunked stream split at arbitrary byte offsets — a record
   can begin in one chunk and end in the next, so joining is mandatory before
   any parsing.
2. **Brace-match** balanced `{...}` regions on the joined string rather than
   regexing. Nested objects and escaped quotes defeat greedy patterns
   (`\{.*\}` truncates at the wrong brace; `\{[^{}]*\}` misses nested fields).

Structured records usually appear as a JSON array inside one of the payload
prefixes, so it is often enough to brace-match the outermost `[` … `]` that
contains the record keys you expect (e.g. `"name"` together with `"url"`).

Ready to adapt: `scripts/unwrap_next_flight.py`.

## 4. Spot the list node in the dumped DOM (Route A fallback)

If the payload is unhelpful, read the DOM directly. Do it **inside the browser
context** (or with a small parser over the dumped file), not by eyeballing
markup:

- Anchor on a repeated element: the list node is whatever element repeats once
  per record (`document.querySelectorAll('a[href*="/program/"]')`).
- Extract attributes over text where possible (`href`, `data-*`) — they are
  uniform, whereas rendered text carries UI chrome (badges, separators, counts).

## 5. Verify before reporting

- Count the parsed records and compare with the total the page states it has.
- Spot-check one record against the rendered page — same name, same URL.
- Watch for a hard cap (e.g. "top 100") in the payload: it means the endpoint
  paginates and your batch is partial. Say so; don't present it as complete.

## Cross-check: the JSON endpoint usually wins

For the directory this recipe came from, an undocumented JSON endpoint on the
same host returned the same records with no rendering at all — cheaper, more
complete, and resilient to markup changes. Always spend two `curl` probes on
guessed endpoint shapes *before* committing to a payload parser.
