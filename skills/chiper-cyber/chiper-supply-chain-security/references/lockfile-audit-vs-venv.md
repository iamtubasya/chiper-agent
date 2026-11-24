# Lockfile-vs-Venv Dependency Audit

Practical notes for auditing a Python/npm repo's dependency posture without
mistaking a clean dev venv for a clean project.

---

## The core trap: audit the LOCKFILE, not the venv

A dev venv drifts from the pinned manifest. Real case from a 2026 audit of a
~470K-LOC Python agent repo:

| Package | Pinned in `pyproject.toml` | Installed in `.venv` | Verdict |
|---|---|---|---|
| `python-multipart` | `0.0.20` (14 advisories, 3 HIGH) | `0.0.33` (fixed) | **pin is vulnerable, venv looks fine** |
| `aiohttp` | `3.13.4` (52 advisories) | `3.14.5` (fixed) | same |
| `starlette` | `1.0.1` | `1.10.0` | same |
| `cryptography` | 46.0.7 (transitive) | 50.0.2 | same |

Had the audit run `pip-audit` against the installed environment it would have
reported **zero** findings on four packages that every fresh install pulls in
vulnerable form. New users get the bad version; the person auditing gets the
good one.

**Rule:** the manifest + lockfile is the artifact you ship. Scan it.

---

## Exact pinning does not protect the transitive layer

A repo can have a long, well-reasoned comment block explaining that every
direct dep is pinned `==X.Y.Z` for supply-chain reasons (citing a real PyPI
compromise incident), and still carry 318 open advisories across 31 packages.
Why:

- Direct pins constrain only the direct layer. `uv.lock` / `package-lock.json`
  resolve ~200-1100 transitive packages independently.
- Pinning is a **freeze**, not a **monitor**. Nothing tells you when a frozen
  version becomes known-vulnerable.
- Bonus failure mode: when Dependabot for pip/npm is deliberately disabled
  (common in "we pin exactly" repos) *and* the tradeoff is "the GitHub
  Dependabot security-updates setting covers it," that setting is often not
  actually enabled. Verify it; assume nothing.

The audit that found 318 advisories found **zero CI gates** that could have
surfaced them.

---

## OSV API is the fastest path (no auth, no install)

`pip-audit` needs to resolve the environment. OSV answers straight from a
lockfile you parse yourself. Batch endpoint caps at 1000 queries; 100 keeps
request bodies small.

```bash
python scripts/osv-lockfile-audit.py uv.lock
python scripts/osv-lockfile-audit.py package-lock.json --ecosystem npm --json out.json
```

Raw shape if you want to inline it:

```python
import json, urllib.request
payload = {"queries": [
    {"package": {"name": "pyjwt", "ecosystem": "PyPI"}, "version": "2.13.0"},
]}
req = urllib.request.Request(
    "https://api.osv.dev/v1/querybatch",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
print(json.load(urllib.request.urlopen(req, timeout=60))["results"])
```

`querybatch` returns **only vulnerability ids** — no severity, no affected
range, no fixed version. You need one extra call per advisory:

`GET https://api.osv.dev/v1/vulns/<ID>` → `database_specific.severity`
plus `affected[].ranges[].events[].fixed`.

Budget for that: ~90 advisories/pipeline-run is the point where the extra
per-id fetches dominate wall time. Use `--no-severity` for a fast first pass.

---

## Severity triage that survives scrutiny

Don't rank by raw advisory count. Rank by **reachability from the exposed
surface**:

1. **Trust anchors** — anything that decides whether a certificate or a token
   is valid. `certifi` (root CA store), `cryptography`, `pyjwt`. A CRITICAL
   here means every outbound TLS call or every token check is suspect.
2. **Parsers fed by untrusted input** — image decoders (`Pillow`), archive
   readers (`tarfile`, `zipfile`), XML (`lxml`), multipart form parsers
   (`python-multipart`). These run on data from users, targets, or the network.
3. **HTTP stacks** — `aiohttp`, `starlette`, `uvicorn`, `h11`. Request
   smuggling / WS bypass / host-header issues land here.
4. **Everything else** — dev deps, build tooling, transitive leaves.

A package with 88 advisories in tier 2 outranks one with 5 advisories in tier 4.
Say this out loud in the report — "88 advisories" without the reachability
argument reads as noise.

### Stale-comment trap

Repos that pin with inline CVE comments (`"requests==2.33.0",  # CVE-2026-25645`)
create a false sense of patched status. The comment records that *a* CVE was
addressed, not that *no* CVE applies now. In the 2026 audit, `PyJWT==2.13.0`
carried a comment listing four `PYSEC-2026-*` ids — and OSV returned 29 open
advisories for that exact version, including one CRITICAL. Always re-query;
never trust the comment.

---

## CI gates that would have prevented this

Minimum viable set for a repo with a lockfile. Each is one file, each catches a
distinct class the others miss:

| Workflow | Catches |
|---|---|
| `ci.yml` — pytest matrix | nothing runs tests today |
| `audit-osv.yml` — scheduled `osv-scanner`/`pip-audit` + `npm audit` | the 318 advisories |
| `dependency-review.yml` — `actions/dependency-review-action` on PR | blocks new vulnerable deps *before* merge |
| `lock-check.yml` — `uv lock --check` / `npm ci --dry-run` | manifest-vs-lock drift |
| `lint.yml` — ruff + type check | tooling pinned in `dev` extra but never executed |
| `release.yml` — tag → wheel → publish | confirms the package actually ships |

The audit finding was not "they picked bad packages" — it was "nothing in the
repo could ever tell them." Report it that way.

---

## npm side

`package-lock.json` (v2/v3) carries `packages{}` with `name` + `version` per
node, including transitives. Feed those to OSV with `ecosystem: "npm"`.
For Electron desktop apps check the Electron major specifically — sandbox
`allow-popups` bypass, `<webview>` Node integration in workers, and
cross-origin file reads cluster there and are not scored as loud as they are.
