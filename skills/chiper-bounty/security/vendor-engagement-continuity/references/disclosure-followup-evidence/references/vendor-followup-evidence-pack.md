# Worked example — vendor follow-up evidence pack

Real engagement, 2026-10. Pattern: **source-review finding → filed by email → triager asked for
the tested commit + a standalone repro.** Reproduced here as the canonical shape.

---

## The finding (for context)

Target's settlement indexer, Express API. API-key middleware authenticated a route only when:

```ts
if (!req.path.startsWith(pathPrefix)) {   // pathPrefix defaults to "/api/" — CASE-SENSITIVE
  return next()                           // -> skips auth entirely
}
```

Express's router default is `caseSensitive: false`, so `/API/tokens` (a) failed the prefix test,
so the middleware called `next()` without ever checking the key, and (b) still matched the
`/api/tokens` route. One capital letter in `/api/` removed authentication from the whole API
surface, including `POST /api/admin/replay/transfers`, which the code guarded with a *second*
middleware defeated by the same line. CWE-178 + CWE-287.

Two guard call-sites, both defeated: the blanket one on `/api/`, and the admin one on `/api/admin/`.

---

## What the vendor asked

> "Thank you for the detailed report and for keeping the testing local. We've received the PDF.
> Could you share the exact source commit you tested and the standalone reproduction script so our
> security team can compare your results? Please keep any further reproduction local; there's no
> need to test administrative endpoints on a live service."

Two items + one boundary instruction. Note they explicitly acknowledged that testing stayed local —
which is why restating the boundary in the reply (§5 of the skill) lands as confirmation rather than
as a defensive excuse.

---

## The commit pin

```
repo     github.com/<org>/<project>        (public)
branch   main
commit   b2f3e0e5fba9381293f030ef340ffb4872687fcf
subject  chore: publish v0.0.7
date     2026-09-11 16:31:26 +0000

audited  packages/indexer/src/auth.ts
         packages/indexer/src/server.ts

line refs
  auth.ts:41     const pathPrefix = options.pathPrefix ?? "/api/"
  auth.ts:44     if (!req.path.startsWith(pathPrefix)) { return next() }   <- case-SENSITIVE
  auth.ts:48     if (isApiKeyAuthorized(req.headers[headerName], expectedApiKey))
  server.ts:169  const adminAuth = createApiKeyMiddleware(expectedApiKey, { pathPrefix: "/api/admin/" })
  server.ts:174  app.post("/api/admin/replay/transfers", adminAuth, ...)
  server.ts:210  app.use(createApiKeyMiddleware(expectedApiKey))           <- blanket guard

per-file SHA-256 at that commit (working tree clean, `git status --porcelain` empty)
  REDACTED_********  packages/indexer/src/auth.ts
  REDACTED_********  packages/indexer/src/server.ts

runtime
  express 4.19.2   (exactly what packages/indexer/package.json pins)
  node v24.13.1    (reproduction host)
```

The `working tree clean` line is doing real work: it is the difference between "I reviewed *a*
version of this file" and "the commit hash and the file hashes both pin the exact bytes I read."

---

## The repro output (captured, not retyped)

```
runtime      express 4.19.2
resolved     <...>/node_modules/express/index.js
target       <project> @ b2f3e0e5fba9381293f030ef340ffb4872687fcf
bind         http://127.0.0.1:59762  (loopback only)

401  GET   /api/tokens                      | lowercase /api, NO key
200  GET   /api/tokens                      | lowercase /api, WITH key
200  GET   /API/tokens                      | UPPERCASE /API, NO key
200  GET   /Api/Tokens                      | mixed case /Api/Tokens, NO key
200  GET   /API/BALANCES/0xdead             | UPPERCASE /API/balances, NO key
202  POST  /API/admin/replay/transfers      | UPPERCASE ADMIN, NO key
202  POST  /Api/Admin/Replay/Transfers      | mixed-case ADMIN, NO key

admin handler executed 2 time(s) WITHOUT an API key
protected data served 3 time(s) WITHOUT an API key

VERDICT: AUTH BYPASS CONFIRMED via path case-folding
         controls held (lowercase blocked without a key, allowed with one);
         case-varied paths reached data and admin handlers with no key.
```

The two rows with a key are the whole point. Without them, a reviewer cannot tell whether the
harness itself was misconfigured to skip auth — the first row alone would look identical.

---

## The bundle

```
relay-indexer-authbypass-repro_b2f3e0e.zip     78747 bytes
  sha256 REDACTED_********

  relay-indexer-authbypass-repro.js   6377 B  67fde7e8…  (the script that was run)
  repro-output.txt                    1536 B  c2487f86…  (captured run, exit 0)
  COMMIT.txt                          2362 B  c47f0046…  (commit + hashes + line refs)
  SHA256SUMS.txt                       356 B
  RELAY-indexer-auth-bypass.pdf      93799 B  b0529b1a…  (report as submitted)
```

Build + verify on Windows without `zip` (Python `zipfile`):

```python
import zipfile, pathlib, hashlib
src = pathlib.Path(".../F3-repro")
z   = pathlib.Path(".../relay-indexer-authbypass-repro_b2f3e0e.zip")
with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
    for p in sorted(src.iterdir()):
        if p.is_file():
            f.write(p, p.name)                      # flat archive, name only
print(hashlib.sha256(z.read_bytes()).hexdigest())
with zipfile.ZipFile(z) as f:
    assert f.testzip() is None                      # None == every CRC intact
```

Then the consistency check that keeps the bundle honest:

```python
# the script INSIDE the archive must be byte-identical to the script that was RUN
a = hashlib.sha256(zipfile.ZipFile(z).read("relay-indexer-authbypass-repro.js")).hexdigest()
b = hashlib.sha256(pathlib.Path(".../authtest/relay-indexer-authbypass-repro.js").read_bytes()).hexdigest()
assert a == b
```

---

## The reply (short, technical, boundary restated)

> Thanks for coming back so quickly. Here is both pieces.
>
> **1. Source commit tested** — `b2f3e0e5fba9381293f030ef340ffb4872687fcf` on
> `<repo>` (`main`, "chore: publish v0.0.7"). I confirmed my working tree was clean before and
> after the review, so that commit is exactly the code I tested. SHA-256 of the two files at that
> commit: `auth.ts` → `ce38da7c…abfa6`, `server.ts` → `d92e3ca0…965c`. The defect is `auth.ts:44`
> (`req.path.startsWith(pathPrefix)`, case-sensitive) against Express's `caseSensitive: false`
> default; guard call-sites are `server.ts:169`, `:174` and `:210`.
>
> **2. Standalone reproduction** — attached: `relay-indexer-authbypass-repro.js`. It transcribes the
> middleware and route table verbatim from that commit and runs against `express@4.19.2`, the
> version the package pins. `npm i express@4.19.2 && node relay-indexer-authbypass-repro.js`. It
> binds 127.0.0.1 on an ephemeral port, includes the two control requests, and exits non-zero if any
> case deviates — so it drops straight into CI. A captured run is in `repro-output.txt` inside the
> bundle (`…zip`, sha256 `1509e69e…a7108a`).
>
> **3. Boundary** — understood. Everything above is loopback-only; every probe I ever sent to a
> live host was a plain read-only GET, and I have not touched a live administrative endpoint.
> Nothing further will.

Three blocks: the two answers, then the boundary. No severity re-argument, no restating the whole
finding.

---

## Transferable rules

1. **Pin the commit + hash the files at review time.** Nothing else reconstructs it later.
2. **Controls are mandatory**, and the "must be allowed with the key" row is the one that makes the
   bypass unambiguous.
3. **Assert and exit non-zero** so the artifact is runnable by the vendor's CI against their fix.
4. **Verbatim transcription with `file:line`** in the script header — no paraphrasing.
5. **Hash the ZIP and the tested script; assert they match** before sending.
6. **Restate the testing boundary** when the vendor asks you to keep it local; confirm forward.
7. **Reply in-thread, short, as a draft** for the user to review.
