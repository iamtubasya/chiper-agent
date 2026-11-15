# make_evidence.py — transcript prefix contract (live catch 2026-10, bluewin.ch DW2 report)

`scripts/make_evidence.py` renders every `raw/*.txt` to `img/*.png`, but its `extract()` keeps
ONLY lines that start with:

| prefix | rendered as |
|---|---|
| `PoC ` | title/context line (yellow) |
| `[` | step/label line (yellow; green if it also contains `RESULT`) |
| `RESULT` | response line (green) |
| `-----` | block separator (dim) |
| `test test::` | test line (green) |

Everything else — headers, `$ curl …` command lines, `HTTP/1.1 200` status lines, JSON response
bodies — is **silently dropped**. The batch printout `DW2-poc: <path> lines=N` reports how many
lines actually survived; compare it with the meaningful line count of your transcript BEFORE
embedding the PNG.

Observed failure: a 50-line curl PoC transcript rendered `lines=6` (title bar + five `[n]`
labels) — an evidence image with almost no content, and the report would have shipped with it.

## Working transcript shape (curl-based PoC)

```
PoC transcript - <target> <finding> - <UTC timestamp>
All requests: plain GET, no cookies, no authorization header, fresh TLS session.
-----
[1] STAGING host.example/path - plain GET, no credentials
RESULT 200 application/json
RESULT body: {"build":{"artifact":"...","version":"..."}}
-----
[2] PRODUCTION host.example/path - plain GET, no credentials
RESULT 401 | Basic realm="Realm"
RESULT body: (empty body)
-----
```

Rules:
1. The command becomes part of the `[n]` label; each response line becomes a `RESULT` line.
2. Long bodies: trim to ~300 chars on a single line (the renderer wraps at 118 chars).
3. After rendering, assert `lines=` ≈ count of `[n]` + `RESULT` + `-----` lines; re-render if not.
4. Strip ANSI escapes first when the transcript came from a colorized tool (see the SKILL.md
   Strip-ANSI note) — ANSI bytes break `startswith()` even on well-formed prefixes.
5. Embed with `![caption](path/to/img.png)` in the report markdown.
