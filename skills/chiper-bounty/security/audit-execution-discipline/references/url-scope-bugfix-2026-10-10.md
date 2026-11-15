# Bugfix: malformed URL → tools attack the WRONG HOST (2026-10-10)

Discovered on `plugins.jetbrains.com` (property #3 of the 11-property JetBrains sweep).
Symptom: `dalfox` / `nuclei` processes whose **argv pointed at a third-party host** and ran
20–53 min each while producing nothing.

```
"C:\...\dalfox.EXE"  url "https://plugins.jetbrains.com///www.googletagmanager.com/ns.html?id=GTM-5P98"
                          └──────────── wrong target smuggled into the path ────────────┘
```

## The true root cause — protocol-relative hrefs (NOT "raw regex", which was the first guess)

My first two diagnoses were wrong. The real cause is three lines of the crawl branch:

```python
# audit-pipeline-orchestrator.run_recon() — BEFORE
for _href in re.findall(r'(?:href|src|action)=["\']([^"\'\s]+)["\']', _html):
    if _href.startswith(("http://", "https://")):
        candidate_urls.append(_href)                      # ← no scope check at all
    elif _href.startswith("/") and not _href.startswith("//"):
        candidate_urls.append(f"{root}{_href}")
    elif _href and not _href.startswith(("javascript:","#","mailto:")):
        candidate_urls.append(f"{root}/{_href}")          # ← "//host/x" lands HERE
```

The GTM `<noscript>` iframe in the page source is **protocol-relative**:

```html
<noscript><iframe src="//www.googletagmanager.com/ns.html?id=GTM-5P98" ...></iframe></noscript>
```

`"//www.googletagmanager.com/..."` does **not** start with `http`, and the `"/"` branch
explicitly excluded `//` — so it fell through to the catch-all and was glued as
`root + "/" + "//host/path"` = **`root///host/path`**. That string is then
indistinguishable from a legitimate deep path by `urlparse` (see §"Why urlparse alone is
not enough"), so every downstream scope check passed it.

**Lesson: the dangerous input was not an absolute third-party URL — it was a
protocol-relative one that the branch structure silently mis-joined.** Check the *join*,
not just the *source*.

## Four fix layers (all needed — fixing one leaves the others open)

### L1 — `execute-variants.py`: wordlist paths have no leading slash

`sensitive-files-wordlist.txt` stores `.env`, `.git/config`; the inline `PATH_ENDPOINTS`
dict stores `/.env`. The concat made the host itself a filename:

```python
url = f"https://{domain}{payload}"              # → https://plugins.jetbrains.com.env  ✗
url = f"https://{domain}/{payload.lstrip('/')}" # ✓
```

Measured: **46/100** info-disclosure probes errored (`getaddrinfo failed`), **32/32** SSRF.
E2E proof: broken form → curl status `000`; fixed form → `404` (request actually lands).

### L2 — `force-full-execution._param_url()`: substring host test

```python
# BEFORE — any URL merely CONTAINING the host passed
if u.startswith("http") and "?" in u and host in u.split("/")[2].lower():
    return u
```

`"plugins.jetbrains.com" in "plugins.jetbrains.com///www.googletagmanager.com"` → True.

```python
# AFTER
if not (u.startswith("http") and "?" in u):
    continue
if "///" in u or "//" in u.split("://", 1)[-1]:          # smuggled second host
    _extra = u.split("://", 1)[-1].replace(_h, "", 1)
    if "//" in _extra:
        continue
_n = urlparse(u).netloc.lower().split(":")[0]
_n = _n[4:] if _n.startswith("www.") else _n
if _n == root_dom or _n.endswith("." + root_dom):
    return u
```

⚠️ Compare against the **root domain** (`jetbrains.com`), NOT the full host. My first
attempt used the full host and my own test caught it: `blog.jetbrains.com` — a legitimate
in-scope fuzz target — was being rejected.

### L3 — `audit-pipeline-orchestrator.run_recon()`: explicit `//` branch + backstop

```python
elif _href.startswith("//"):
    _abs = "https://" + _href.lstrip("/")
    if _in_scope(_abs):                    # scope-check it like any absolute URL
        candidate_urls.append(_abs)
```

plus a final backstop before `urls.txt` is written, so *no* producer path can leak one:

```python
def _clean(_u):
    if not _u.startswith("http"):
        return False
    _tail = _u.split("://", 1)[-1]
    _tail = _tail.split("/", 1)[-1] if "/" in _tail else ""
    return "//" not in _tail
candidate_urls = [u for u in candidate_urls if _clean(u)]
```

Also added `tel:` / `data:` to the skip list (same class as `javascript:` / `#` / `mailto:`).

### L4 — `deep-endpoints.py` + `_deep_recon()` merge

`deep-endpoints.add()` used `netloc in ("", base_netloc)` — an exact match that misses
subdomains and lets resolved protocol-relative third-party hosts through. Replaced with the
same root-domain + `"//"`-guard check. `_deep_recon()` filters both sides of the merge.

## Truth about the first two diagnosis attempts (read this before guessing)

I called the cause wrong twice and burned three restarts:

1. **"The crawl regex appends any absolute URL"** — plausible, and I patched it. The
   malformed URL was still there on the next run.
2. **"It comes from the dork-recon merge"** — checked `dork-urls.txt`: 0 hits. Wrong.
3. **Actual**: the protocol-relative `//host` path in the crawl's fall-through branch.

What made the difference was not more reasoning but **reproducing with the real input**:
I quoted the actual `<noscript><iframe src="//...">` HTML into the test harness and ran the
branch logic against it. Before that, every test I wrote used absolute URLs — i.e. I was
testing my assumption, not the input. **When a malformed value survives a fix, build the
test from the literal bytes found on the wire/page, not from a reconstructed idea of them.**

## Why `urlparse` alone is not enough

```
urlparse("https://plugins.jetbrains.com///www.googletagmanager.com/x").netloc
  → "plugins.jetbrains.com"          # second host lives in the PATH
```

A pure netloc check passes. The `"//" in rest` guard is the only thing that catches it.

## Verification that actually proved it (do these, in this order)

1. `py_compile` on all 4 files.
2. Logic test replicating each branch, fed with the **real** GTM iframe HTML → no
   third-party URL survives; in-scope absolute / relative / subdomain / protocol-relative
   **all still kept**. (Test both directions — a filter that drops everything is not a fix.)
3. Live curl: broken form `000`, fixed form `404`, malformed `///` form `400`.
4. `bundle-sync.py` → **0 drift** after copying the changed files to
   `bundle-src/audit-pipeline-bundle-v1/toolkit/scripts/`.
5. **Runtime confirmation on a fresh run** — the decisive evidence:
   ```
   dalfox.exe: url "https://plugins.jetbrains.com" --skip-bav        ← correct
   urls.txt:   123 real endpoints (was 27 + 104 lost), 0 third-party hosts
   deep-recon: urls.txt 27 -> 123 real endpoint(s)                   ← merge now works
   ```
   Unit tests passed while the pipeline was still broken. Only the live argv + the
   `urls.txt` host census proved it.

## Bonus bug introduced by fix L4 itself — a tuple, not a string

My first `_deep_recon` root-domain expression was a one-liner that produced a **tuple**:

```
deep-recon failed (non-fatal): 'list' object has no attribute 'split'
```

Non-fatal, so the run continued — **and silently lost all 104 enumerated endpoints**
(123 → 27 URLs, i.e. 22 % coverage). Two lessons:

- **A "non-fatal" catch can hide a coverage catastrophe.** Grep the log for
  `failed (non-fatal)` and treat every hit as a real defect, not as noise.
- Compute a derived string in explicit steps, not a nested one-liner:
  ```python
  _host = target.replace("https://","").replace("http://","").split("/")[0].lower()
  if _host.startswith("www."): _host = _host[4:]
  _parts = _host.split(".")
  _rd = ".".join(_parts[-2:]) if len(_parts) >= 2 else _host
  ```
- My own pre-restart check asserted `isinstance(g, str)` — that is why the tuple was
  caught *before* wasting another full run. **Add a type assertion to derived-value
  helpers.**

## Operator policy on killing tools (clarified over two corrections, 2026-10-10)

I got this wrong once in each direction; the settled rule is:

| tool state | action |
|---|---|
| running normally, **correct** target | **let it finish** — even well past the configured cap |
| **wrong target** (argv netloc ≠ scope) | kill |
| **timeout** (age ≫ cap, will not return) | kill; let `TIMEOUT` be recorded |
| **freeze / hang** (CPU-delta ≈ 0 across two samples) | kill |

First correction: *"dalfox jgn dkill kl dia berjalan normal"* → I stopped killing entirely.
Second correction: *"tp kl salah target, atau timeout, freeze, dan hang, itu silahkan kill"*
→ the correct rule is the table above, not "never kill".

So before killing, answer **two** questions, not one: (a) is it alive? (CPU-delta),
(b) is it aimed at the right host? (read the argv). A tool can be perfectly healthy and
still be worth killing because it is scanning a Google Tag Manager page.

## Recurrence note

The same "malformed probe URL" class was already logged on `account.jetbrains.com`
("56/56 probes errored"); that pass fixed **one call site**. Generalise:

> Normalise URL joining in **one** helper (`https://{host}/{path.lstrip('/')}`) and
> scope-check at **every** handoff — page → crawl → `urls.txt` → tool arg — never at just one.

Sibling: `coverage-lies-and-report-quality.md` ("hollow coverage"), and
`pipeline-tool-timeout-budget.md` §7 (the overrun that led here).
