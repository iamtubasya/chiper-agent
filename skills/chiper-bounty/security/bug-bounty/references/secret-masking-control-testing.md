# Testing a Secret-Masking / Redaction Control

> Use when a product claims to redact values marked `sensitive` / `secret` / `masked` from
> logs, build output, task logs, artifacts, or an API field. Repeatable, reportable bug class
> (CWE-532 insertion of sensitive info into a log; CWE-312 cleartext storage). Pays on CI/CD
> and deployment products (Octopus, GitHub Actions, GitLab CI, Jenkins, Terraform Cloud, …).
> Worked end-to-end on Octopus Deploy (2026-10, bugcrowd) → 2 accepted-shape findings.

## Why this class pays

Masking is a **security control**, not a formatter. The program usually *says* it cares — a
focus-area line like *"we are concerned when variables explicitly marked sensitive are not
correctly masked in the task logs for a deployment"* is a standing invitation. Findings are
also cheap to prove: one deploy, one `curl`, one quoted log line.

## The mistake to avoid

Do not treat "the script printed the secret" as automatically out of scope. Every masking
test involves a script printing something — that is the only way a secret *can* appear in a
log. The discriminator is whether the **control itself** has a hole (a length cut-off, an
encoding assumption, a partial-match gap) versus the operator deliberately defeating it
(`base64 secret`, `rev`, `md5sum`). Test the first kind; mention that you did not report the
second kind.

## Test matrix

Create one sensitive variable per row, deploy a Bash step that emits it, and read the task log.

| # | Vector | What it proves |
|---|--------|----------------|
| 1 | `echo "#{Secret}"` | baseline — masking works at all |
| 2 | **value lengths 1,2,3,4,5,8,16** | finds a **minimum-length cut-off** (Octopus: values < 4 chars are never masked) |
| 3 | value with **internal newline** (2, 3, then 40 lines) | multi-line handling |
| 4 | `echo "#{S}" \| head -n 1` / `tail -n 1` / `head -n 2` of a multi-line value | **partial reproduction** of a multi-line secret |
| 5 | `echo "#{S}" \| cut -c1-20` / `cut -c1-100` | partial reproduction of a single-line secret |
| 6 | `echo "x#{S}y"` | value embedded inside a longer line |
| 7 | value that contains a tab / quote / CRLF | normalisation gaps |
| 8 | full value vs partial, back-to-back in the SAME step | the clean side-by-side the report needs |
| 9 | 150+ lines of filler then the secret | streaming chunk-boundary handling |
| 10 | platform-rendered surfaces: Manual Intervention instructions, step Notes, approval text containing `#{S}` | does masking cover non-script surfaces, or only the log stream? |
| 11 | `GET` the variable-set / config API for the same name | does the read API return the value for a sensitive entry? |
| 12 | the *other* log endpoints (`/raw`, `/details`, `/details?verbose`) | one surface may be masked while another is not |

Keep vectors that *transform* the value (2-encoding, hashing, reversing) as sanity checks to
show you understand the boundary — they are not findings.

## Root-cause patterns to look for in the implementation

When the product is installed locally you can read, or at least name, the failing code:

- **Minimum-length cut-off.** A "don't mask short strings, it would mask everything" guard
  applied to the *sensitive value* rather than to candidate matches. Octopus:
  `if (string.IsNullOrWhiteSpace(instance) || instance.Length < 4) continue;` in
  `SensitiveValueMasker.CreateTrie()` → every 1–3 char secret is skipped entirely. Note the
  secondary bite: normalising the value (stripping `\r\n`) *before* the length check demotes a
  4-char value containing a newline to 3 chars — also skipped.
- **Exact/completion-only matching.** A multi-pattern matcher (Aho-Corasick, trie, hash set)
  that only reports *complete* pattern hits, plus a "deferred partial" buffer that is flushed
  **unmodified** when the match never completes. Octopus: `AhoCorasick.Find()` only records
  complete matches, and `SensitiveDataMask.ProcessDeferred()` passes the buffered text to the
  output callback unchanged ("Scenario 1") → any prefix/subset of a value reaches the log in
  cleartext. Industry peers (GitHub Actions, GitLab) mask substrings, so this is a genuine gap.
- **Exception fallback to raw.** A `try { mask } catch { emit(raw) }` around the masking call
  is a bypass primitive: anything that makes the masker throw emits the unmasked line.
- **Masking only on one code path.** Rendering paths (UI, API, export, artifact) usually each
  need their own call — check all of them, they are frequently out of sync.

## Also check the control AT REST — storage is a second claim

For a self-hosted/installable product you usually get the database too, and "sensitive values are
encrypted at rest" is the **same control class** (CWE-312) declared one layer down. A DBA, a
backup, or anyone who reaches the DB is a legitimate audience for it, so it is worth one pass.

**Technique — unique marker, then look where it landed:**
1. Via the product's own API, set a sensitive variable to a **unique literal** you control
   (`DBPROBESECRET-5f3a9c21`) *and* a non-sensitive one as the control (`DBPROBEPLAIN-7e11b4`).
2. Enumerate the storage for candidate tables/columns instead of guessing:
   `SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%Sensitive%' OR TABLE_NAME LIKE '%Secret%' OR TABLE_NAME LIKE '%Variable%' OR TABLE_NAME LIKE '%Key%'`
   then `INFORMATION_SCHEMA.COLUMNS` for `nvarchar(max)` columns on those tables.
3. Search for the literal; read the stored form of both markers.

**Trap 1 — non-`dbo` schemas.** `INFORMATION_SCHEMA.TABLES` lists tables from *every* schema, but a
bare `SELECT ... FROM <name>` only resolves `dbo` and answers `Invalid object name` for the rest.
Qualify with the schema (Octopus had `PlatformHub.ProcessTemplateSensitiveParameterValue`).
**Trap 2 — never conclude from a single `LIKE`.** A first `LIKE '%<marker>%'` pass reported the
*non-sensitive* control as "not literal" on every row; re-querying with
`SUBSTRING(CONVERT(nvarchar(max), col), CHARINDEX('<marker>', CONVERT(nvarchar(max), col)), 200)`
proved it *was* plaintext. Two independent query shapes before you conclude encrypted-vs-not.
**Trap 3 — empty sensitive tables prove nothing.** Tables named for sensitive values may simply hold
0 rows on a fresh lab; record them as "not assessable from data", not as secure.
**Trap 4 — do not brute-force "search every string column".** Faced with a few hundred tables the
tempting move is a generated query that concatenates a `LIKE` over *every* `nvarchar/varchar/ntext/xml`
column and `EXEC`s it. It is expensive, it can return no rows at all (so it reads like "the value is
stored nowhere"), and on a small lab the load takes the database — and then the whole container
engine — down mid-run, losing the result. Enumerate candidate tables from `INFORMATION_SCHEMA` first
(step 2 above), then run a handful of targeted `LIKE`s. A storage question is answered by 3–5 targeted
queries, not by a generated sweep.

**What good looks like (and is still worth reporting as a verified negative):** sensitive value as
`base64(IV/tag)|base64(ciphertext)`; API key as `PBKDF2-SHA256$<iters>$<salt>$<hash>` with the raw
key absent from every table; non-sensitive values in plaintext (expected). A confirmed
"encrypted at rest + hashed key store" is a strong honest-negative row for the coverage ledger —
it shows you checked the format rather than trusting the docs.

## Turn "should be visible to" into "is visible to"

Never write "any user with TaskView could read this". Create a second account holding only
plausible non-admin roles, log in, fetch the same artifact, and quote the response body with
the cleartext value in it. Concretely for Octopus: `Project viewer` grants `TaskView` (and
nothing that lets that user run a script) — one `GET /api/tasks/<id>/raw` as that user, plus
the returned `short=[abc]`, is the whole impact argument.

## Reporting shape that survives triage

- One section per **root cause**, with its own repro. Two holes in the same control (length
  cut-off, partial-match) are two root causes — say so and let the triager decide whether to
  file one or two; do not silently merge them.
- Show the **clean negative control in the same log**: the full value printed as `********`
  immediately next to the partial value printed in cleartext. That kills "the script just
  printed the secret" as an objection.
- Name the boundary precisely (`length 4+ masked, 1–3 not`) instead of "short values".
- Quote the shipped class/line when you can (`SensitiveValueMasker.CreateTrie`,
  `AhoCorasick.Find`, `SensitiveDataMask.ProcessDeferred`) — it converts a behavioural
  observation into an actionable fix and raises severity confidence.
- Propose the fix: drop the length guard, mask a deferred partial prefix instead of flushing
  it raw, normalise newlines on search as well as on trie build.
- Be honest about severity — but **look the platform's taxonomy up, do not assume P4/P5.** On
  Bugcrowd this class maps to `Sensitive Data Exposure > Disclosure of Secrets`, whose variants are
  `For Internal Asset` (**P3**) and `For Publicly Accessible Asset` (**P1**). A self-hosted instance
  *you* installed is the **internal** variant even though you reached it over localhost — quoting P1
  is a two-priority overclaim that gets corrected down at triage. Fetch the VRT JSON and read the
  variant's default priority rather than guessing (`references/vrt-lookup.md`). Still worth filing
  whenever the program lists masking as a focus area.
- A partial-disclosure control failure is not a critical, but on a program that names masking in its
  focus areas it is a clean, cheap, high-acceptance P3-shaped report — do not talk it down either.

## Do not over-claim the negatives

If the full value is masked on every surface you tried and only partials leak, report exactly
that. Writing "masking is broken" when the control works for complete values reads as
over-claiming and costs credibility on the parts that are real.

### Prove the test EXECUTED before you call it a negative

A surface that returns nothing has not been cleared — it has not been tested. Three ways this bites:

- **Artifacts.** `GET .../artifacts?regarding=<task>` returned `TotalResults: 0` because the step
  never produced a *collectable* artifact (writing a file is not enough; the product needs its own
  artifact API/declaration). Reading zero artifacts proves nothing about artifact masking.
- **Output variables.** `set_octopusvariable` ran (`HasWarningsOrErrors: false`, the following
  `echo` appeared), yet the variable name appeared in *no* API response — so its storage and
  rendering were never exercised.
- **Empty sensitive tables.** See Trap 3 above.

In all three cases the honest ledger entry is **"not assessable — the test produced no data"**, never
"clean". Same rule as the scanner ledger: a tool that silently did nothing and a target that is
genuinely clean look identical from the outside, so check for the artefact of execution first.

### Two things you must NOT dress up as findings

- **The fail-open `catch { emit(raw) }`.** It is a real bypass primitive *in theory*, but you may not
  be able to trigger it: the trie only ever grows (a union on rebuild), so a stale `lastSearchPath`
  still resolves and `Find()` does not throw. If you cannot construct a triggering input, record it
  as a defence-in-depth note and say plainly that you could not reach it — do not file it.
- **Cosmetic over-masking.** `GetMaskedSections` merges adjacent sections only on a strict `<`, so one
  value can render as two `********`. That is the opposite of a disclosure; padding the report with it
  dilutes the two real root causes.
