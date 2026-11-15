---
name: advisory-intel
description: "Use when ingesting vendor advisories into attack playbooks."
version: 1.0.1
author: curator
license: MIT
metadata:
  hermes:
    tags: [security, advisories, cve, intel, bug-bounty, skill-wiring, automation]
    budget_kb: 12
---

# Advisory Intel — Vendor Advisories → Attack Variants

Turns a vendor's **published, already-patched** advisories (GitHub Security Advisories, CVE feeds) into
fresh, high-yield test vectors for any product of the same class (PHP/LAMP, EHR, CMS, SaaS, dApp,
appliance). Real paths, real parameter names, real payloads, real root causes — no guessing.

## When to Use

- User says "cek advisories/&lt;repo&gt;", "filter high+critical", "ambil teknik attacknya",
  "integrasikan ke skill/phase" — or names a vendor repo plus a CVE/advisory feed.
- You want proof-backed test vectors for the current target class (same stack/product family).
- A new high/critical advisory landed and an existing technique playbook needs re-ingesting.

**Hard constraint that usually rides along:** integration must be **additive** — no change to phase
order, context budget, eviction rules, or any existing command in the pipeline.

---

## Step 1 — Fetch (GitHub Security Advisories API, tokenless)

```
GET https://api.github.com/repos/<owner>/<repo>/security-advisories?per_page=100&state=published
Accept: application/vnd.github+json
```

- **`per_page=100` caps the page; `page=2` can return the SAME 100 rows.** You MUST follow the cursor in
  the `Link: <...>; rel="next"` response header (`?after=<cursor>`). A naive fetch that "looked complete"
  reported 100 of 153 for one repo this way.
- **Verify before trusting the count:** `comm -12 <(jq -r '.[].ghsa_id' p1|sort -u) <(jq -r '.[].ghsa_id' p2|sort -u)`
  — 100% overlap means you re-fetched page 1, not page 2.
- Dedupe by `ghsa_id`; keep a `manifest.json` of seen ids so re-runs report **only NEW** ids.
- `GET /advisories?affects=owner/repo` returns nothing for some repos — the repo-scoped endpoint is the
  reliable one. Tokenless core limit is 60 req/hr; a full two-repo sync costs ~5. An optional
  `GITHUB_TOKEN` raises it.
- Ready-made tool: `D:/data hermes/advisory-intel/fetch_advisories.py` (cursor pagination, dedupe,
  `last_sync_result.json` → `new_high_critical`). Add a vendor by **appending to `REPOS`** — keep the
  existing entries first so their manifest keys and slugs never change.

### Which vendors actually publish GHSA (verified 2026-10-01)

| vendor | GHSA repo | advisories |
|---|---|---|
| WordPress core | `WordPress/wordpress-develop` | 43 (8 high/crit) |
| Laravel | `laravel/framework` | 9 (5 h/c) |
| Symfony (Laravel/Drupal dep) | `symfony/symfony` | 55 (12 h/c) |
| TYPO3 CMS | `TYPO3/typo3` | 97 (28 h/c) |
| Drupal / Joomla / Magento | **none** — `drupal/drupal`, `joomla/joomla-cms`, `magento/magento2` return 0 | use NVD |

### NVD-only vendors → `fetch_nvd.py` (same schema, classifier untouched)

Drupal/Joomla/Magento/Moodle/PrestaShop CVEs only live in NVD. `fetch_nvd.py` normalises NVD 2.0 into
the **exact advisory shape** the pipeline already consumes (`ghsa_id` = `NVD-<CVE-ID>`, `cve_id`,
`severity`, `summary`, `description`, `cwes[{cwe_id}]`, `published_at`, `updated_at`) so
`brief.py` / `digest.py` / `cluster.py` work with **zero changes**. It writes `adv_nvd_<kw>.json` and
its own `nvd_manifest.json` / `nvd_last_sync.json` — never touching `manifest.json` used by
`fetch_advisories.py`.

```bash
python fetch_nvd.py                 # default keywords, last 2 years
python fetch_nvd.py drupal joomla   # explicit
NVD_API_KEY=*** python fetch_nvd.py # 50 req/30s instead of 5 req/30s
```
Verified: `nvd/drupal` → 176 CVEs in a 1-year window, 34 high/critical, with CWE + CISA-KEV refs.

## Step 2 — Filter + cluster (let the distribution pick your sections)

```bash
jq -r '[.[].cwes[]?.cwe_id]|group_by(.)|map({k:.[0],n:length})|sort_by(-.n)[]|"\(.n)\t\(.k)"' adv.json
```

Keep `severity in (critical, high)`. The dominant CWE cluster IS the product's dominant bug class.
Observed shape (OpenEMR, 153 advisories): CWE-862 ×22, CWE-639 ×18, CWE-79 ×16, CWE-89 ×9, CWE-284 ×7,
CWE-22 ×5 → **authorization, not injection**, so the playbook leads with IDOR/ACL variants.

## Step 3 — Extract TECHNIQUES, not summaries

`advisory.description` is markdown containing the fix diff, the sink, the parameter name and often a
copy-paste PoC.

- keep lines matching: `php://|/path/|/api/|library/ajax|SELECT |UNION |\?\w+=|<param>=|file_path|eval\(|unserialize|\.\./|curl |POC`
- drop headings matching `patch|workaround|reference|credit|disclosure|timeline|cvss|affected|fix|mitigation`
- tools in `D:/data hermes/advisory-intel/`: `digest.py` (trimmed markdown), `brief.py` (marker-line
  extract), `cluster.py` (CWE clustering)
- **Write to a file, then page it** (`brief.py > brief_<repo>.txt`) — never print ~90 advisories inline.

## Step 4 — Write the variant playbook (class level, not a list)

Destination that fits the existing pipeline: `skills/security/exploit-cookbook/references/<vendor>-advisory-techniques.md`
(the "Public Disclosures" bundle the 0C phase already loads).

Shape that works:
- **§A–§M sections of variants**, each row = `Variant | concrete vector | detect-by | writes/impact`
- per-section **classifier command** (cheap response-shape test first, escalate only what's reachable)
- payload/context cheat-sheets and a **guard-bypass mini-table**
- **chaining section** (these are scaffolding, not findings)
- **§M screen → variant probe matrix** — map each UI screen to the variants to try
- **HOW-TO-USE header** with a section index, so a future agent loads 1–4 sections, not the whole file
- **Maintenance footer**: refresh command, raw-JSON path, scope rule

## Step 5 — Wire in ADDITIVELY (file-level, never structural)

| Attach point | Kind of edit (one line/block each) |
|---|---|
| `exploit-cookbook/SKILL.md` | `References` list line |
| `reference-loader.md` (inside the 0C loader skill) | `##` block in the 0C loader |
| `security/bug-bounty/bug-bounty-testing.md` | block in the Phase 0C REFERENCE INDEX |
| `security/bug-bounty/SKILL.md` | line in the 0C load-step |
| `hunt-dispatch/SKILL.md` | fingerprint line → routes the stack (e.g. PHP/LAMP) to the new file |
| `hunt-*/SKILL.md` (class skills) | one `> **Extra attack variants** … §X` pointer per class |

Every inserted block restates: *additive, vectors only, still gated by `hunt-dispatch` Step 0 +
`triage-validation`*. A playbook of vectors is not a list of findings.

## Step 6 — Patch safely (idempotent, backed up, re-runnable)

1. **Backup first:** `tar -czf /d/data\ hermes/<area>/backup_$(date +%Y%m%d_%H%M%S).tar.gz -C <skills-root> <dirs...>`
   (Windows/MSYS: `D:` does not resolve in tar args — use `/d/...` or `-C`).
2. **Marker-gated idempotency:** every patch embeds the new filename; `if marker in text: NOOP`.
   Requirement: re-running the whole script yields **0 patches**.
3. **Anchor after a unique existing line**; never rewrite. Substring fallback if exact-line match fails.
   For files that may lack an H1, anchor on the **YAML frontmatter close** (`---`) — `next(...)` for
   `"# "` raises `StopIteration` and aborts the run mid-way.
4. **`--dry-run`** printing `PATCHED / NOOP / ANCHOR-MISSING` per file before applying.
5. **Verify after:** frontmatter parses (`yaml.safe_load` → 0 problems), marker count == 1 per file
   (no duplicate insert), line endings preserved.
6. Reference implementation: `D:/data hermes/advisory-intel/patch_pipeline.py` + `verify_patch.py`.

## Step 7 — Keep it fresh (optional, no-agent cron)

`scripts/advisory-watch.py` refreshes and prints **only when a new high/critical advisory appears**
(empty stdout = silence, watchdog pattern). Register with `cronjob(action='create', no_agent=true)`.
`script` must be a **bare filename relative to `~/.hermes/scripts/`** — an absolute path is rejected.

---

## Verification checklist

- [ ] advisory count matches the API (cursor pagination followed, not capped at 100; `comm` overlap check)
- [ ] playbook exists and appears in the umbrella's `linked_files` (`skill_view(name=...)`)
- [ ] re-running the patch script = all NOOP (idempotent)
- [ ] every touched SKILL.md has valid frontmatter; marker count == 1
- [ ] fingerprint skill routes the target class to the playbook
- [ ] phase order / budget / eviction unchanged (diff is additions only)

## Pitfalls

1. **`per_page=100` looks complete but isn't** — chase `Link rel="next"`, verify with `comm`.
2. **Page 2 can be byte-identical to page 1** — dedupe by `ghsa_id`, don't trust row counts alone.
3. **Never insert into a pipeline by rewriting a phase file** — additive + anchored + marker-gated only.
4. **Mixed line endings** — read `"rb"`, normalise `\r\n → \n`, write `newline="\n"`, or the diff becomes
   the whole file and hides the real change.
5. **Missing-H1 SKILL.md aborts the loop** — anchor on frontmatter close, not on `"# "`.
6. **Ownership guard** — if the umbrella/target skill is user-owned, curator writes are refused; put the
   new support file where it is writable and report the target for `hermes curator adopt <name>`.
7. **Never dress vectors as findings** — carry the Step 0 + triage-validation gate text into every block.
8. **NVD rejects any date range > 120 days with a bare `HTTP 404`** — not an error message, just 404, which
   reads like "no data". `pubStartDate..pubEndDate` must span **≤ 120 days**; chunk the window
   (`fetch_nvd.py` does this automatically, `NVD_DAYS` capped at 120). Symptom to recognise:
   `[NVD] <kw>: HTTP 404` on page 0 with every keyword.
9. **Not every vendor publishes GHSA.** Checking `drupal/drupal` returns 0 advisories and looks like a
   broken query; Drupal/Joomla/Magento only appear in NVD. Verify a candidate repo with
   `?per_page=1` before concluding the feed is empty.

## Ingested CVEs (provenance ledger)

| CVE | Class | Where it lives | Verified against |
|---|---|---|---|
| CVE-2026-98432 | Linux IPv4/TCP `ireq_opt` UAF → remote root via MPTCP (CVSS 9.8) | `exploit-cookbook/references/cve-2026-98432-ireq-opt-uaf.md` + `cve-2026-disclosures.md`; wired into `hunt-race-condition`, `hunt-rce` | NVD 2.0 API, kernel.org commit `e3f33b0a1d89`, oss-security 2026/10/30/1, Ubuntu + Red Hat + Debian trackers, `H1z3-br0/CVE-2026-98432` analysis |

Ingest discipline that produced it (reusable for the next CVE):

1. **NVD 2.0 API first**, not the blogosphere — `services.nvd.nist.gov/rest/json/cves/2.0?cveId=<ID>`.
   Check `vulnStatus`; `Received` means **no affected-version data** — do not infer a range from it.
2. **Pull the actual patch** from git.kernel.org (`/patch/?id=<sha>`) or the vendor's advisory. The
   diff tells you the true root cause and often the exact fix size (this one: 2 lines).
3. **Read the vendor severity disagreement** (kernel CNA 9.8 vs Red Hat 5.9–8.1). The gap is the
   real story about reachability, not noise.
4. **Separate "PoC available" from "working exploit".** Blog aggregators recycle the phrase. Read the
   toolkit author's own scope statement — here: trigger + oracle only, stage 3 deliberately absent.
5. **Check distro status per-version**, and note that a patched-but-not-booted kernel is still
   vulnerable.
6. **Verify the local/estate claim yourself** before writing anything: `uname -r`, `CONFIG_MPTCP`,
   `tcp_migrate_req`. A version below the fix line with MPTCP compiled out is *reduced exposure*,
   not *exploitable*.
7. **Extract the transferable technique**, not the CVE story. For this one the keeper is the
   **marker oracle**: a unique tag echoed back by a *different* request proves state confusion
   without a crash.

## Related skills

- `exploit-cookbook` — umbrella that hosts the generated technique playbook (0C "Public Disclosures" bundle)
- `bb-audit-launcher` — phase pipeline; its `reference-loader.md` is the 0C attach point
- `hunt-dispatch` — fingerprints the stack and routes to the right class skill
- `skill-management` — patch-vs-rewrite, merge, archive, pin
