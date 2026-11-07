---
name: bug-report-delivery
author: RESEARCHER_NAME
description: "PDF bug report: use skill format, deliver to chat."
metadata:
  hermes:
    tags: [bug-bounty, reporting, delivery]
    budget_kb: 30
---

## ⛔ KONTRAK INTEGRASI (WAJIB DIBACA SEBELUM PAKAI SKILL INI)

Isi skill ini **dipecah**: core ada di file ini (auto-load), sisanya di `references/_split/`.
File di `references/` **TIDAK ikut ter-load otomatis** — hanya ter-LIST saat skill dibuka.
**Karena itu: buka file di tabel bawah ini lewat `skill_view(name=..., file_path=...)`
sebelum mengerjakan bagian yang relevan. Jangan menebak dari judulnya.**

Aturan pakai:
- Bagian CORE di bawah = aturan wajib, selalu berlaku, jangan dilewati.
- Bagian yang dipisah = kedalaman per-topik. **Panggil saat pemicunya muncul, jangan dibiarkan tak terpakai.**
- Kalau ragu bagian mana yang relevan, baca `references/_split/_INDEX.md` dulu (satu file, murah).

### Tabel pemicu → file (WAJIB dipanggil saat kondisi terpenuhi)

| kapan dipanggil | file |
|---|---|
| saat mengerjakan: **Email-draft delivery (vendor correspondence by email) — NEVER SE** | `references/_split/01-email-draft-delivery-vendor-correspondence-by-email-never-.md` |
| saat mengerjakan: **Unauthenticated API testing** (CAPTCHA-blocked signup, type juggling, version-changelog CVE hunting) | `references/unauthenticated-api-testing.md` |
| **Web-form submission** (ASP.NET / hidFormData) | `references/aspnet-webforms-cvd-form-submission.md` |
| saat mengerjakan: **Workflow** | `references/_split/02-workflow.md` |
| saat mengerjakan: **PDF Generation — reportlab Patterns** | `references/_split/03-pdf-generation-reportlab-patterns.md` |
| saat mengerjakan: **Evidence Authenticity — CRITICAL LESSON (Chime 2026-09)** | `references/_split/04-evidence-authenticity-critical-lesson-chime-2026-09.md` |
| saat mengerjakan: **File Locking Pitfall (Windows)** | `references/_split/05-file-locking-pitfall-windows.md` |
| saat mengerjakan: **Complete Report Structure (Standard Sections)** | `references/_split/06-complete-report-structure-standard-sections.md` |
| saat mengerjakan: **⚠️ `execute_code` Pitfall — DO NOT Generate PDFs Inline** | `references/_split/07-execute_code-pitfall-do-not-generate-pdfs-inline.md` |
| saat mengerjakan: **📂 Related Files** | `references/_split/08-related-files.md` |
| saat mengerjakan: **🏆 GOLD STANDARD REPORT — Zinc/Zootbox Case Study (PATUHI, DITIRU** | `references/_split/09-gold-standard-report-zinczootbox-case-study-patuhi-ditiru.md` |
| butuh daftar lengkap split / arsip | `references/_split/_INDEX.md`, `references/_split/_full-archive.md` |


# ⛔ PRE-LOAD CHECK (MANDATORY — DO NOT SKIP)

Before loading this skill, ALL of these MUST be verified:

```
[ ] $BB_DATA/_progress/<target>/PHASE_LOG.md exists
[ ] PHASE_LOG.md shows Phase 0C COMPLETE (all vectors tested)
[ ] $BB_DATA/_progress/<target>/findings.json exists
[ ] findings.json has ≥1 candidate entry OR explicit "vectors tested, no bounty-worthy findings"
[ ] Phase 0F is the ONLY remaining phase
```

**VERIFICATION METHOD (not optional):**
```bash
# MUST run this — do not assume
cat $BB_DATA/_progress/<target>/PHASE_LOG.md
# Verify: Phase 0A=COMPLETE, Phase 0B=COMPLETE, Phase 0C=COMPLETE
# Verify: Phase 0F=PENDING
```

**If ANY item unchecked or Phase 0C ≠ COMPLETE:**
- REFUSE to load report generation
- Print: "⛔ PRE-LOAD CHECK FAILED: Phase 0C incomplete. Return to testing."
- Return user to Phase 0C with: "Testing must complete before report. See PHASE_LOG.md for gaps."
- DO NOT generate ANY report content until this passes.

**Exception — ad-hoc target with NO pipeline workspace.** If there is no `$BB_DATA/_progress/<target>/`
directory at all (the target was worked directly, outside the 0A-0F pipeline), the PHASE_LOG gate has
nothing to check and must NOT be used to refuse — the operator can legitimately ask for a report on a
target that was never run through the pipeline. In that case: (a) do the VRT/viability/program-exclusion
reasoning by hand (Phase 1 + 2), (b) label every finding with its honest severity (an info-disclosure =
Low/Informational, likely excluded — say so), and (c) when the operator explicitly asks for low/info
reports, produce them as clearly-labelled *documentation*, never inflated — **one PDF + one staged draft
email per finding** (see "Self-hosted VDPs" below for the mechanics). Re-confirm no workspace with
`ls $BB_DATA/_progress/` before treating a target as ad-hoc. A clean negative ("no exploitable finding
on this surface") remains a valid deliverable and needs no PDF at all.

**After PRE-LOAD PASS:**
- EVICT Phase 0C skills from context (summarize to digest)
- Load this skill (30KB)
- Proceed with report generation

> This hard gate prevents report-before-done. A report generated before all vectors
> are tested is worse than no report — it wastes the bounty opportunity.

> **⚠️ COMPACTION RECOVERY:** If context was compressed and you're unsure where you are,
> read PHASE_LOG.md FIRST. It is the single source of truth for audit progress.
> Resume from the last COMPLETE phase. Do NOT restart from scratch.

---

# Bug Report Delivery — MANDATORY HARD RULE



## Evidence screenshots + attachment completeness (operator hard rule, 2026-10-16, finanzen.net VDP)

Operator rejected drafts whose PDFs only *referenced* evidence: a finding draft must CARRY its proof.

- Screenshot = a live capture of the real request/response, EMBEDDED in the PDF body. The stager's
  `build_pdf` renders markdown image lines `![caption](abs/path.png)` (additive patch, 2026-10-16);
  a `## Evidence screenshots` section with that line is what the operator expects to see in the PDF.
- Attach to the draft: the PDF + raw-evidence `.txt` + the PNG itself. Verify sha256 on read-back and
  assert one-subject-per-draft in ONE `messages.list(labelIds=['DRAFT'])` pass.
- Fixing an already-staged finding = `drafts.update(id, raw)` IN PLACE with the SAME draft id. Never
  re-create: the operator asked for "perbaiki semua draftnya", and re-creating leaves duplicates.
- Real-capture recipe when the target WAFs headless tooling (Akamai/Core): run a small local HTTP
  server that performs the ACTUAL request at page-render time (same session construction as the PoC:
  full browser header set, www = `Accept` + `Sec-Fetch-*`, login host = plain) and prints raw
  request + raw response; screenshot `http://127.0.0.1:PORT/<route>` with headless Chrome
  (`--headless=new --screenshot`, a FRESH `--user-data-dir` per shot because a locked profile fails
  SILENTLY with no output). Add `--virtual-time-budget=12000` only for pages whose evidence is
  produced by page JS; server-rendered pages need it not.
- Run the local server under the SAME interpreter family that the target's WAF tolerates (on this
  host: WSL python3, not Windows python - the Windows client's TLS/behaviour profile gets 403 where
  WSL gets 200). Bind 0.0.0.0 so the Windows-side Chrome can reach it.
- **Slow evidence routes (multiple upstream API/RPC calls per render) time out the screenshot.**
  A route making 5 sequential RPC calls needs ~40 s; Chrome's `--timeout` plus the tool's 60 s
  foreground cap kills the shot. Fix: add a module-level cache to the route (`_CACHE = {}`; return
  the cached HTML after the first computation), restart the server, warm the route with
  `curl` (foreground, generous timeout), THEN screenshot — the cached render is instant. Skip
  `--virtual-time-budget` entirely for server-rendered pages.
- **Verify WHAT a screenshot captured without a vision model: re-capture and compare hashes.**
  When a shot is suspect (e.g. the upstream endpoint started erroring mid-session), re-run the
  same Chrome command against the current state to a second file and sha256 both. Identical
  hashes prove the original captured the current state (e.g. an HTTP 500 page), not the earlier
  success — re-capture after the upstream recovers. Different hashes mean the original is
  probably the good capture.
- Kill orphaned `chrome.exe` processes between screenshot runs (`taskkill //F //IM chrome.exe`
  on Windows) — locked profiles make later shots fail silently, and orphan accumulation is
  invisible until every shot comes back blank.
- Check the program policy CLAUSE BY CLAUSE before staging: request-identifying header, mandated
  tool/AI-assistance + manual-verification disclosure (must appear in the PDF too, not just the body),
  language, submission channel, and the non-qualifying list.

## Staging drafts via the Gmail REST API — raw-MIME is the reliable path (coderpad 2026-10-17)

> **No OAuth token / token dead?** Use the IMAP App-Password path instead (`imap_tools`): `references/imap-append-draft-via-app-password.md` — covers the `append(message, folder)` arg-order trap (message FIRST), `BytesGenerator` for guaranteed bytes, the redactor workaround for reading the App-Password from `check_basabasi_email.py`, and the **localized drafts-folder trap**: resolve the folder by the `\Drafts` FLAG (Indonesian Gmail = `[Gmail]/Draf`), never by name-matching — a name match lands in a look-alike top-level `Drafts` folder and the draft is invisible in the UI ("gakada draft nya", hit live 2026-10-25 mail.com).

Two dead ends, then the pattern that works, when adding attachments to a draft:

- **Do not** build `drafts.update` as JSON with attachment bytes — `bytes` is not JSON-serializable.
- **Do not** use the `multipart/related` metadata+attachments form for `drafts.update` — it returns
  `400 Bad Request` even with the documented part layout.
- **Do** build the complete RFC822 message yourself — `To/Subject/MIME-Version` +
  `Content-Type: multipart/mixed; boundary=...`, one `text/plain; charset="UTF-8"` body part, then
  one part per attachment (`Content-Type: <mime>; name="<fn>"`, `Content-Transfer-Encoding:
  base64`, `Content-Disposition: attachment; filename="<fn>"`, body wrapped at 76 chars) — then
  `drafts.create`/`drafts.update` with `{"message": {"raw": <base64url of the whole MIME>}}`.
  Read-back verification (subject, attachment filenames, `sizeEstimate`) is unchanged. Deleting a
  staged draft = `DELETE .../drafts/<id>` (trash-recoverable); assert the total draft count returns
  to baseline afterwards.

**⛔ The local `gmail_ops.py` helper cannot attach files — do not reach for it first.** Its `draft`
subcommand accepts only `--to / --subject / --body` (see `--help`); there is no `--attach`, so a
report draft staged through it silently ships text-only, which is a rule-0a-2 rejection. Skip it for
deliverables and go straight to the raw-MIME path above. Minimal working shape (verified 2026-10-29):

```python
d = json.load(open(os.path.expanduser("~/.chiper/skills/bounty-pack/google_token.json")))  # NOT ~/.hermes/
tok = requests.post(d["token_uri"], data={"client_id": d["client_id"],
        "client_secret": d["client_secret"], "refresh_token": d["refresh_token"],
        "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
msg = EmailMessage()
msg["To"], msg["From"], msg["Subject"] = TO, FROM, SUBJ
msg["Message-ID"] = make_msgid(domain="report.local")     # unique per draft — REQUIRED on REST too
msg.set_content(BODY)
msg.add_attachment(open(pdf, "rb").read(), maintype="application", subtype="pdf",
                   filename=os.path.basename(pdf))
raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
requests.post("https://gmail.googleapis.com/gmail/v1/users/me/drafts",
              headers={"Authorization": f"Bearer {tok}"},
              json={"message": {"raw": raw}}, timeout=60)
```

**Multi-account mailbox: pick the account by LABEL, never `accts[0]`.** When the operator keeps
several Gmail tokens in `~/.chiper/skills/bounty-pack/gmail_accounts/`, `bounty_mail.account_files()`
returns them in filesystem order and index 0 is NOT the bounty mailbox (convention: bounty drafts
go from **RESEARCHER_USERNAME**). Select explicitly, then build the draft through that account's service
(verified 2026-10-30, DedSec CCTV):

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "~/.chiper/skills/bounty-pack"))
from bounty_mail import account_files, gmail_service

accts = dict(account_files())
label = next(l for l in accts if "RESEARCHER_USERNAME" in l.lower() or "RESEARCHER_USERNAME" in str(accts[l]).lower())
svc = gmail_service(accts[label])

msg = MIMEMultipart("mixed")
msg["To"], msg["Subject"] = TO, SUBJECT
msg.attach(MIMEText(BODY, "plain", "utf-8"))
part = MIMEBase("application", "pdf")
part.set_payload(PDF.read_bytes())
encoders.encode_base64(part)
part.add_header("Content-Disposition", "attachment", filename=PDF.name)
msg.attach(part)
svc.users().drafts().create(userId="me",
    body={"message": {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}}).execute()
```

Then verify with `python gmail_ops.py drafts --account RESEARCHER_USERNAME --limit 3` — the newest subject must
be yours. If the program has no email channel (GitHub-only PVR), mark the `To:` as a placeholder and
say so in the body; the operator fixes the recipient before sending.

**Prove the attachment landed — never report "draft staged" from the POST response alone.** Fetch
the draft back and walk the MIME tree; the three things that matter are filename, mimetype and size,
plus the label:

```python
j = requests.get(f"https://gmail.googleapis.com/gmail/v1/users/me/drafts/{draft_id}?format=full",
                 headers={"Authorization": f"Bearer {tok}"}).json()
for p in j["message"]["payload"].get("parts", []):        # recurse: nested parts exist
    if p.get("filename"):
        print(p["filename"], p["mimeType"], p["body"]["size"])
assert j["message"]["labelIds"] == ["DRAFT"]              # staged, not sent
```

A `200` from `drafts.create` with an id is necessary but not sufficient — the read-back is what makes
"PDF attached, not sent" an artifact-backed claim rather than a self-report.

> **Pitfalls that shipped broken deliverables (read before staging):** `references/staging-pitfalls-and-fixes.md`
> — typo'd image path = silent no-embed PDF (assert `/Subtype /Image` + size >30KB post-build);
> re-running the stager creates a duplicate draft (delete stale or drafts.update in place); the body
> validator requires the literal phrase "responsible disclosure"; Gmail token expiry-as-int fix;
> redactor masks display not files; MSYS/heredoc traps.

## VDP submission-format clauses that override the PDF-first default (coderpad 2026-10-17)

Some programs forbid the report living in an attachment: CoderPad's policy says *"Do not link main
description of the report as attached text, PDF file, linked document… we receive many reports and
share content via a ticketing tool"* — **the full description must be in the email body**, with
screenshots/videos/PDFs as supplements only. Before staging, grep the policy for the
submission-format clause and set body-vs-attachment accordingly: body = complete narrative
(finding, observed behavior, PoC request/response, impact); PDF = evidence pack (embedded
screenshots + raw HTTP + hashes). Also honor per-program counting rules (CoderPad: *"1 Finding =
1 message = 1 ticket"* — one draft per finding, never combined) and no-severity-claims clauses
(*"don't assess the criticality level, we do"* — drop CVSS/severity labels from body and PDF).

## A finding can die AFTER staging — fix the draft in place, then recommend hold (coderpad 2026-10-17)

Impact tests run after drafts were staged killed both findings (alias overloading: measured
amplification negligible; urlencoded POST: cookie-auth differential proved no CSRF surface). The
drafts' bodies contained the earlier, stronger claims — leaving them would ship overstated impact.
Correct shape: `drafts.update` **in place** (same draft id) with the verified facts, explicitly
stating *"impact not demonstrated"* plus the tests run, attach the deepening evidence, and tell the
operator plainly: do not send, both map to the program's explicit None-list (rate limiting /
missing throttling; CSRF with no or low impact), and sending out-of-scope reports risks a program
ban. Drafts staged ≠ cleared to send; the operator decides, with the scope risk quoted verbatim.

## Host pitfalls that silently break these builds (Windows + git-bash, 2026-10-16)

- Terminal heredocs above roughly 10 KB get TRUNCATED in transit -> `unexpected EOF while looking for
  matching '`; write big files in several `cat >>` chunks and `ast.parse` after each.
- The output redactor rewrites auth-header-shaped literals INSIDE files you write
  (`Authorization: Bearer <token>` -> `***`, or eats a quote), which produces broken shells/headers.
  Fragment them (`"Bea" + "rer "`, `HDR = "Author" + "ization"`) exactly as `stage_finding_draft.py`
  already does. A tell-tale symptom: the server answers `accessToken ... must not be null`.
  **It also eats shell command substitutions mid-line** — `TOKEN=$(curl ... | grep -oP 'name="_token"...')`
  comes back as `TOKEN=*** -oP ...` and bash dies with `syntax error near unexpected token`.
  Symptom tells: a stray `***` inside a `$(...)` or a `[Command timed out]` right after a
  token-extraction line. Fix: put the whole probe in a Python script file and run that, never a
  token-shaped shell one-liner.
- Prefer forward slashes in file paths written through the shell (`/home/agentuser`) so a stripped
  backslash cannot silently corrupt the path.
- WSL `/tmp` is VOLATILE across tool calls (the distro stops between calls) - keep evidence under
  `/mnt/c/...`. Also kill orphaned `chrome-headless` processes between screenshot runs and use a fresh
  profile dir; 18+ orphans will hold profile locks and every later screenshot fails silently.

## Evidence-server routes that make live calls: cache before screenshotting (2026-10-19)

An evidence route that performs several upstream calls at page-render time (e.g. 5 Solana RPC reads,
~40 s) will blow the 60 s foreground tool limit when Chrome screenshots it, and the screenshot command
itself times out even though the file lands. Pattern that works:

1. Add a module-level cache to the slow route: compute once, store the rendered HTML, return the cache
   on every later request.
2. Warm the cache with a plain `curl` (background it if needed), then screenshot - the Chrome load is
   instant.
3. If Chrome still hangs, `taskkill //F //IM chrome.exe` first: orphaned headless instances from
   earlier shots hold profile locks and every subsequent `--screenshot` fails silently.
4. **Resolve the target IP up front and keep an IP fallback in the server** (hit 2026-10-31, Zenya).
   A background evidence server using `urllib` died with `getaddrinfo failed` for the target host
   while the *same* host resolved fine from `execute_code` in the same session — the resolver
   behaves differently per process context. Two fixes, both cheap: (a) build the server on
   `requests` rather than `urllib`, and (b) resolve the hostname once with `socket.gethostbyname`
   in a context that works, write the IPs to a small JSON next to the server, and on any
   `RequestException` retry against `https://<ip>/<path>` with an explicit `Host: <hostname>`
   header. Symptom to recognise: the warmed page renders instantly and small, with
   `grep -c result_code` returning 0 and the body showing `URLError: <urlopen error [Errno 11001]
   getaddrinfo failed>` — that is a resolver failure inside the server, NOT the target being down.

## Gmail token file corruption after refresh (2026-10-19)

- **A Gmail API call returning `401 Unauthorized` mid-session = access token expired (1-hour
  lifetime), NOT a revoked token.** Refresh first, then retry — do not conclude "token revoked"
  and send the user to re-authorize. The refresh flow:
  ```python
  data = {"client_id": info["client_id"], "client_secret": info["client_secret"],
          "refresh_token": info["refresh_token"], "grant_type": "refresh_token"}
  # POST https://oauth2.googleapis.com/token -> save new access_token (and refresh_token if rotated)
  ```
  **DNS-failure fallback (hit 2026-10-26, DuoCircle):** Python's `google-auth` / `requests`
  raised `getaddrinfo failed` for `oauth2.googleapis.com` while `curl` on the same host
  resolved fine (Cloudflare WARP DNS at 127.0.2.2). When the Python refresh path dies with
  `TransportError` / `NewConnectionError`, fall back to a `subprocess.run(['curl', ...])`
  POST to the token endpoint, parse the JSON, and write the new `access_token` + `expiry`
  back to the same token file. The Gmail API calls themselves (via `googleapiclient`) then
  work normally with the refreshed in-memory credentials — only the token-refresh HTTP call
  needs the curl detour.
  Only `invalid_grant` on THIS call means genuinely revoked (needs user re-auth). Hit 3x in one
  session (2026-10-21) — each time a 401 on `messages.list`/`drafts.create` was just expiry.
  Save the refreshed token back to the same file immediately so subsequent calls reuse it.

Symptom: `Credentials.from_authorized_user_file` raises
`AttributeError: 'int' object has no attribute 'rstrip'` on the `expiry` field. A token refresh
round-trip can serialize `expiry` as a unix int instead of the RFC3339 string google-auth expects.
Fix before staging (read the file, coerce, write back):

```python
d = json.load(open(tok))
if isinstance(d.get("expiry"), (int, float)):
    d["expiry"] = datetime.datetime.fromtimestamp(d["expiry"], datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S")
    json.dump(d, open(tok, "w"))
```
- **Gmail token `expiry` can come back as an int** after a refresh cycle and
  `Credentials.from_authorized_user_file` dies with `AttributeError: 'int' object has no
  attribute 'rstrip'`. Fix in place: load the token JSON, convert
  `datetime.utcfromtimestamp(expiry).strftime("%Y-%m-%dT%H:%M:%S")`, write back, then refresh.
- **A "killed" evidence server can survive as an OS process.** Restarting on the same port then
  has TWO processes LISTENING (`netstat -ano | grep <port>` shows two PIDs) and requests are
  served by the OLD code - stale routes, old typos, hashes that "mysteriously" match the wrong
  build. `taskkill //F //PID <pid>` every listener, confirm the port is free, then start one.
- **Chrome `--screenshot` runs that exceed the tool timeout may still have written the PNG** -
  check the output file before re-running. Orphaned `chrome.exe` from earlier shots are the
  usual cause of the hang: `taskkill //F //IM chrome.exe`, fresh `--user-data-dir` per shot.
- **MSYS `/tmp` is invisible to the Windows Python interpreter** - a file bash wrote to
  `/tmp/x.txt` raises `FileNotFoundError` in python. Write evidence into the workspace and use
  native forward-slash paths (`D:/...`) inside Python.

### Staging mechanics hit live (2026-10, LoopScale VDP)

- **The stager joins a relative PDF path with the markdown's directory** (`ws = dirname(md)`;
  `pdf = join(ws, a.pdf)`) - pass a BARE FILENAME (`LS-01.pdf`), never `reports/LS-01.pdf`, or
  `doc.build` dies with a `reports/reports/LS-01.pdf` FileNotFoundError.
- **Three-attachment drafts** (rule 0a-2): extend `stage_finding_draft.py` with `--attach`
  (`action="append"`), append to the `files` list, and add a read-back loop that pulls EVERY
  attachment via `messages().attachments().get()` and asserts `sha256(remote) == sha256(local)` -
  not just the PDF.
- **Evidence-server routes that make live API/RPC calls at render time take 30-60s** and the
  headless screenshot times out. Cache the rendered HTML in a module-level dict after the first
  computation, warm the route with `curl` (~5s), THEN screenshot (instant load). A timed-out
  `--screenshot` call may still have written the PNG - check the file before re-running.
- **Windows Python cannot resolve MSYS paths** (`/c/Users/...`) when a script opens skill files -
  use native `/home/agentuser` inside Python; MSYS form only in bare shell commands.
- **Two servers can hold the same port on Windows** (SO_REUSEADDR): after killing a background
  evidence server, `netstat -ano | grep <port>` and taskkill EVERY listener PID, or the stale
  instance keeps serving old code and your patch appears to have had no effect.
- **Re-read the program's OOS list per finding immediately before staging.** A clause like
  "reports of secrets, API keys, or credentials publicly available without proof of active
  exploitation" kills an otherwise-tempting finding (dropped an NX_API_KEY bundle leak this
  session because key liveness could not be demonstrated). Scope check is per-finding, not
  per-target.
- **After the operator sends drafts they leave the DRAFT label.** Assert the new batch against
   `labelIds=['DRAFT']` AND confirm the earlier subjects in `labelIds=['SENT']` before concluding
   anything is missing - "1 draft found" is correct when 3 were already sent.
- **Operator already SENT the report → never `drafts.update` it; stage a NEW `Re:` supplement (hit 2026-10-21, mail.com).** The operator sends the staged draft from Gmail themselves. A later scope expansion (e.g. the same bug confirmed on 3 more hosts) must NOT try `drafts.update` on the old id — Gmail answers `400 Message not a draft` because a sent message is no longer a draft. Correct shape: (1) check `messages().list(labelIds=['SENT'], q='to:<vendor>')` FIRST and say plainly that the original shipped; (2) build a **new** draft with `Subject: Re: <original subject> - supplement (<what changed>)` and `In-Reply-To`/`References` set to the original `Message-ID` so it threads, body opening "This is a short supplement to my report of earlier today …"; (3) attach the UPDATED PDF (rebuilt with the new facts) + the same evidence txt + PNG, verify sha256 per attachment; (4) report both ids and state the supplement is staged, not sent.
- **`final-deliverable.py build` output is a STUB — always rebuild the real deliverable (hit 2026-10-21, mail.com).** It passes the reportability gate and emits `<slug>.pdf` + `<slug>.eml`, but the eml body is the generic stub ("One finding, one report… impact not stated") and the PDF is ~4 KB with NO screenshot embedded — a rejected deliverable under rules 0a-2/0c. Fix after it runs: (1) write the real `report.md` (title → summary → endpoints → repro → PoC verbatim → `![caption](C:/abs/path.png)` → impact-as-attacker → honest boundary → remediation → sha256 table); (2) write the rule-0c body; (3) rebuild the PDF by importing the stager's builder — `spec.loader.exec_module(stage_finding_draft)` then `sfd.build_pdf("report.md", out, title)` (needs no Gmail token); a correct build is ~30 KB and contains `/Image`; (4) assemble the `.eml` yourself (EmailMessage, unique `Message-ID`, 3 attachments) and stage via `drafts.create` with the base64url raw, then assert `/Subtype /Image` in the PDF bytes and per-attachment sha256 read-back.
- **Slow evidence routes need a cache + warm-up** - a route that makes 5 sequential RPC calls takes
  30-60s per page load and Chrome's `--screenshot` times out at the tool's 60s ceiling. Add a
  module-level `_CACHE` dict to the route (compute once, serve the HTML string after), warm it with
  one `curl` call, THEN screenshot - the page load is instant.
- **A timed-out screenshot may already be on disk** - Chrome can finish the `--screenshot` write
  after the tool call returns its timeout. `ls -la` the target PNG (and ink-check it) before
  re-running; re-running wastes a minute and adds another orphan Chrome.
- **`&` anywhere in a heredoc body trips the terminal tool's backgrounding guard** - a docs quote
  containing "App & Services" made bash reject the whole command ("unexpected EOF"). Write such
  files via `python3 - << 'EOF'` with the content in a Python string, or drop the ampersand.
- **Vision backend connection errors are transient** - `vision_analyze` failed twice with
  "Connection error" mid-session. Fall back to the PIL ink-check (unique-grey count) plus a
  `--dump-dom` grep of the evidence route, or simply re-capture; do not block the deliverable on it.

### Pitfalls hit live (LoopScale engagement, 2026-10-18) — read before the next staging run

- **Stager PDF argument is a BARE FILENAME, not a path.** `stage_finding_draft.py` joins the pdf arg
  with the markdown's directory, so `reports/x.pdf` silently becomes `reports/reports/x.pdf` and the
  build dies with FileNotFoundError. Pass `x.pdf` and let it land next to the md.
- **A restarted evidence server can be a ghost.** Killing the background process (and bash `kill %1`,
  and the missing `pkill` on Windows) does NOT guarantee the python server died: two listeners ended
  up sharing port 8571 and the OLD code kept answering while the patched file sat on disk. Symptom:
  patched constants not taking effect. Fix before restart: `netstat -ano | grep <port>` then
  `taskkill //F //PID <pid>` for EVERY listener pid.
- **A 500 from a live probe is not automatically rate-limiting.** Several cycles were burned assuming
  a write endpoint was throttled when the real cause was a typo'd constant in the evidence server
  (one character short in a base58 address). Rule: when a probe that worked minutes ago starts
  erroring, re-test the same call with a known-good parameter (a different valid id) before
  concluding outage/rate-limit — and keep the invalid-input 500 as an honest footnote, not as the
  finding.
- **Windows python3 does not resolve MSYS paths.** `open('/c/Users/...')` raises FileNotFoundError
  inside python even though bash accepts it; use native `/home/agentuser` in all Python code (shell
  commands may use either).
- **Scope-clause gate immediately before staging.** Re-read the program's out-of-scope list and map
  each finding clause-by-clause; drop whatever maps instead of staging and hoping. Live example: a
  build-secret report (NX_API_KEY in the app bundle) was dropped because the program excludes
  "reports of secrets, API keys, or credentials publicly available without proof of active
  exploitation" and key liveness could not be demonstrated. Worked engagement:
  `references/loopscale-2026-10-engagement.md`.

## Web form is a channel too
Some programmes take reports only via a web form — read the channel from the policy before staging any email (Zenya: form-only; the staged Gmail draft was wasted work). Never hand-build the hidden payload: ASP.NET WebForms gives visible inputs no `name` attribute, so the real submission is a JS-built hidden field. Fill in a real browser, call the page's own `collectFormData()`, read it back, assert 3× behind a hard gate. Verify dropdowns by resolved value, never by index (index 8 for `7976` returned `7977`). HTTP 200 is not confirmation. Details: `references/web-form-submission.md`.

## Trigger
User requests: PDF bug report, exploit results PDF, security finding report, laporan temuan, laporan PDF.
**Applies globally** — dari mana aja (Telegram DM, Telegram topic, WhatsApp), kapan aja. Hard rule ini berlaku untuk SEMUA permintaan user, bukan hanya topik tertentu.



## Scope re-validation BEFORE staging (operator hard rule, 2026-10-26)

Before staging ANY draft, re-read the program's out-of-scope list clause-by-clause and map
each finding against every exclusion. Two findings were rejected as OOS in one session:

1. **Username enumeration** on an unauthenticated form — the bounty explicitly excludes
   "username enumeration on public sign-up or password-reset flows". The endpoint was a
   license-redemption flow, not sign-up/reset, but the vendor applied the same exclusion.
2. **Type juggling → 500** — not in the "what we pay for" list, arguably "denial of service".

**Rule:** if a finding is borderline, tell the operator BEFORE staging. When the operator asks
"km yakin ini gk oos?" — they are signalling the finding is weak. Be honest, re-read the scope,
and either find a stronger angle or say plainly it won't qualify. A rejected OOS report damages
reputation and risks a program ban.

## Source-code findings when live trigger is blocked

When a vulnerability is confirmed in source code but cannot be triggered live (auth wall,
CAPTCHA, valid-token requirement), the report still has value IF it carries:

1. **Source code citation** — exact file, function, and vulnerable lines from the public repo.
2. **Live endpoint behavior confirmation** — e.g. GET returns 405 (route exists, public),
   POST with invalid param returns 404 (entity lookup ran). This proves the route is reachable.
3. **Version match** — compare live build asset hashes against repo files. Identical hashes
   prove the deployed code matches the reviewed source.
4. **Ready-to-run PoC script** — the vendor can execute it with their own token/account in
   minutes. Include the exact curl command and expected response.

Be explicit in the report about what was and was not demonstrated live. "Source code confirms
the vulnerability; live trigger requires a valid project token which I was unable to obtain" is
honest and actionable. Do not claim a live exploit you did not perform.

## Hard Rules (WAJIB — no exceptions)

**0a. ONE FINDING = ONE DRAFT = ONE PDF (operator hard rule, restated 2026-10).** Every finding gets
its **own separate draft email** with its **own complete PDF PoC attached**. Never bundle two or more
findings into a single email, and never send a finding as bare text with no PDF. If a target yields
N findings, you produce N drafts and N PDFs. Filename the PDF after the finding so it is unambiguous which draft carries which PoC. (This is separate from, and additional to, the validate-≥3× rule:
validate first, then one self-contained draft+PDF per finding.)

**How to decide GROUPING when the policy does not forbid it (agent correction, 2026-10-28, binobi).**
Programmes rarely say "one bug per email", so the tempting read is "grouping is allowed". Read the policy
for the **unit of scoring** before deciding, because that is what grouping actually risks:

- Grep the programme text for `case` / `report` / `finding`. Binobi's page scores and closes by *case*
  — *"If the bug is not confirmed and reproduced or is already known, the Binobi team closes **the case**
  with no reward"* and *"the size of the reward in any of the foregoing **cases** depends on the
  severity"*. Under that wording, nine findings in one email is one case with one severity, and one weak
  item can sink the batch. Split.
- A programme that says *"1 Finding = 1 message = 1 ticket"* mandates splitting. A programme that asks
  for a single consolidated report mandates the opposite. Neither wording is the default — look.
- **Never let an "unproven" or "observation only" item ride along in the same email as solid findings.**
  It is the strongest argument for splitting even when grouping is permitted: a body headed
  "9 findings" that contains one finding the author themself calls unproven invites the triager to
  discount the whole batch. Hold the unproven one until it is provable; drop the observation.

**⛔ Do not emit a separate "Addendum" / "correction" document while NOTHING has been sent
(2026-10-28).** This is a distinct failure from the version-hygiene trap above: not wording a
correction, but *shipping it as its own email*. Sequence that happened: main report built → more work
done → an `Addendum_1` PDF built and staged as a second draft with subject "…Addendum 1: corrected
fuzzing coverage…" → the main report had never been sent, so the vendor would have received ONLY an
addendum referring to a report they never got. Operator: *"tidak perlu addendum, kamu kan bisa revisi
aja toh ini juga belum pernah dikirim"*.

Rules:
1. If nothing has shipped, **fold the new work into the finding set** — add the new findings as
   additional per-finding reports, and put any methodology correction in the body of the affected
   report. No second document, no "Addendum" filename, no `Addendum 1` subject.
2. Only create a supplement when something **has** shipped (then rule "a finding can die AFTER
   staging" applies: `Re:` + `In-Reply-To`, delta only).
3. **Delete the superseded artefacts.** Remove the combined PDF and its draft, and move the old
   files into `superseded/` — a stale addendum next to the real set is exactly what gets sent by
   accident. Then verify the mailbox holds ONE draft per finding and nothing else for that vendor.
4. Sanity-check the staging against the operator's own habit: **N findings ⇒ N drafts, each with its
   own PDF, each subject naming its own finding** (`#1 … #6`). A draft whose subject describes a
   document type ("Addendum", "Summary", "Report bundle") instead of a finding is a red flag.

**0a-2. THE EVIDENCE SET IS COMPLETE — three attachments per draft (operator correction, 2026-10-16; asked twice, verbatim: "kamu tidak menyertakan SS evidence... dlm pdfnya menyatakan ada evidence tp jg tidak kamu masukkan k struktur pdf ataupun ke dalam attachement").** Every staged draft carries, minimum:

1. the report PDF with the **live screenshot EMBEDDED in the report structure** (not merely referenced),
2. the raw request/response evidence as a **plain-text attachment** (evidence_<F>.txt built from the dated re-verification JSON),
3. the **screenshot PNG as its own attachment**.

Mechanics: put `![<caption>](<absolute path.png>)` lines in the report md — `stage_finding_draft.build_pdf` renders image lines as embedded figures since the 2026-10-16 patch (PIL mode-converted to RGB first, KeepTogether + caption). To replace an already-staged draft in place **keeping its draft id**, build the raw message yourself (unique `Message-ID` per rule above) and PUT it: `users().drafts().update(id, body={"message": {"raw": raw}})` — then verify **every** attachment's `sha256(attachment) == sha256(local file)` via `messages().attachments().get()`, not just the PDF. A draft whose PDF says "evidence attached" while only the PDF is attached is a rejected deliverable — grep the report's Supporting material section and make sure each listed file is really in the draft. For the screenshot itself use the runnable template `scripts/evidence_screenshot_server.py` (renders the REAL request/response at page load, headless Chrome screenshots it; includes the cross-origin browser-proof page, the ink-check rules, and the fresh-`--user-data-dir`-per-shot pitfall).

**0a-3. IMPACT IS ITS OWN PDF SECTION WITH THE ATTACKER PLAYBOOK (operator question, 2026-10-16: "sudah dijelasin impact dan apa yg bisa dilakukan dgn temuan ini didalam pdf atau draft email nya?").** The reader must be able to answer "what does an attacker DO with this" from the PDF alone. Do not fold impact into the "What this proves" paragraph of the PoC. Structure it as: numbered concrete attacker actions (crafted link / request + what the victim or system does), then the honest boundary (what it does NOT give: no token theft, no RCE, ...), then CIA-triad phrasing where the submission form asks for it (templates/submission-form-fields.md carries the field-by-field mapping). Each email body still gets one compact impact sentence.

**0a-5. IF THE POLICY ASKS FOR "ACCOUNTS USED", THE INVENTORY GOES IN THE PDF *AND* THE EMAIL BODY — from the first draft (operator correction, 2026-10-30, Bankr).** The operator had to ask mid-delivery: *"bisa kamu lengkapi email yg dipakai dalam ujicoba beserta walletnya didalam draft gmail? atau tulis dsni jg boleh biar sy copi"*. Two lessons, both structural:

1. **Grep the policy for the disclosure inventory clause BEFORE writing the report, not after.** Crypto/agent programs routinely require it (Bankr §7 item 5: *"Accounts used — every Bankr account (email or handle) and wallet address you used while testing, and the dates you tested. We use this to tell your testing apart from unauthorized activity."*). Failing to include it is not a formatting nit — the clause exists so the vendor can distinguish your probes from an attacker, and omitting it can get activity treated as unauthorized use. Read §7-style "Required: Clear Reproduction" lists as a **field checklist** and tick every item.
2. **The inventory must be in the email body too, not only the PDF.** Triagers read the body first; a body that says "full details in the attached PDF" with no account list is what triggered the correction. Put a compact `ACCOUNTS AND WALLETS USED` block in the body and the full table in the PDF.

**Write it as a field-per-line list, not a table** — the operator copies it into the submission form, and a markdown table with long addresses renders as shredded columns in the PDF (see the `colWidths`-are-points trap in `reportlab-security-pdf`). Shape that worked:

```
Account 1 (the account under test)
  login         : <email>
  EVM wallet    : 0x…
  Solana wallet : <base58>
  note          : every request, webhook and file in this report belongs to it.
                  The wallet held a zero balance for the whole test.
Account 2
  login         : <email>
  wallets       : none of its own - resolves to Account 1
  note          : plus-alias; Privy issued a separate identity (did:privy:…) but the
                  vendor normalised the address, so no second wallet exists.
```

**Be precise about the degenerate cases — this is where a sloppy inventory becomes a false statement:**

| case | how to write it |
|---|---|
| alias that collapsed to the same account | `wallets: none of its own — resolves to Account 1`, and name the distinct IdP identity so the vendor can match it |
| signup that failed before provisioning | `wallets: none`, plus the exact failure (`POST /user/bootstrap` → `500 "Failed to set up your Bankr wallet"`) and the IdP identity that WAS created |
| a key pair you generated but never linked | list it **and** state it was never linked, never signed anything, has no on-chain history — "listed only so the record is complete" |
| an account used only for a negative test | still list it; the vendor matches activity, not intent |

Also carry **testing dates** (first and last timestamp, UTC) and the **egress IP** in the same block — Bankr-style clauses ask for dates explicitly, and both are already required by the report metadata rules above.

3. **Offer the block as plain text in chat on request.** "tulis dsni jg boleh biar sy copi" is the operator asking for a copy-pasteable version outside the artefact. Deliver it as plain fenced text in the reply — not a summary, not "see the PDF" — because it is going into a web form.

**0a-4. Check SENT before touching drafts.** The operator works on the mailbox while you build: a draft set can disappear because they **sent** it (staged → sent is the normal path, not data loss). When asked about draft status, or before re-staging anything, query `messages?labelIds=SENT` for the subjects first. If the sent version's attachment set is already complete, do nothing; if it went out incomplete, tell the operator plainly which version shipped and offer a supplemental note — never silently recreate a shipped draft.

### ⛔ Never assert "staged, not sent" from a stale read — re-verify `labelIds` at the moment you claim it

Hit live 2026-10-29 (Telekom): the draft was staged and verified `labelIds: ['DRAFT']` mid-session,
the operator was told **"verified unsent"**, and a later read — same draft id — returned
`labelIds: ['SENT']`. Between those two reads, the message shipped. The claim had been true when
made and was false when repeated.

**Rule: a "not sent" claim has a shelf life. Re-read the label immediately before stating it, and
never carry an earlier verification forward as if it were current.** The verification is cheap
(one `drafts.get(id)`); the credibility cost of a wrong "unsent" is not.

```python
j = requests.get(f"https://gmail.googleapis.com/gmail/v1/users/me/drafts/{draft_id}",
                 headers={"Authorization": f"Bearer {tok}"}, timeout=30).json()
print(j["message"]["labelIds"])        # ['DRAFT'] = staged · ['SENT'] = it shipped
```

**When a tracked draft id reads `SENT`, do not assume a bug or a duplicate — establish provenance.**
`drafts.create` returns both a draft id and `message.threadId`. A SENT message in that **same
threadId** is provably the message you staged, not a different one:

```python
sent = requests.get("https://gmail.googleapis.com/gmail/v1/users/me/messages",
                    params={"q": f"to:{vendor}"}, headers=H, timeout=30).json()
# for each hit: compare internalDate ordering against the draft's creation time
# and match threadId — a threadId match settles "did MY draft go out?"
```

That check is what turns "the draft vanished, did something break?" into a factual statement
(*"message `1a188…` in thread `1a1881…` — the same thread as my draft — was sent at 22:03"*).
Report it that way, and **ask the operator whether they sent it** rather than speculating about a
compromise. In this engagement every cron job was a script-mode watcher with no `drafts.send` call,
which ruled out automation in one pass — worth doing before raising an alarm.

Corollary: record `draft_id`, `message_id` and `threadId` together when staging. The threadId is the
only handle that survives the draft→sent transition, and without it provenance afterwards is guesswork.

**0b. IMPACT MUST BE DEMONSTRATED — the four-part reportability test (operator, 2026-10-10).**
*"draft gmail yg lengkap poc pdf nya, dgn hasil yg benar2 ada impactnya, ada demonstrated impact
dalam poc nya ... bukan berhenti di teoritis, krn wajib dibuktikan."* A finding is reportable only
when **all four** hold; fail any one and it is EXCLUDED with its reason written down:

| # | requirement | why |
|---|---|---|
| 1 | present in `passed-findings.json` | it cleared the impact gate **and** the 7-question triage gate |
| 2 | carries a **demonstrated-impact record** — `probe` (the exact action) **and** `observed` (raw, unedited output, ≥40 chars) | a claim without its raw result is theory |
| 3 | that record **re-verified CONFIRMED 3x** (`reverify.py`) | a finding that does not reproduce is not a finding |
| 4 | an impact statement saying what the observed output **proves** | `"impact: potential"` is not an impact |

Enforced by `scripts/final-deliverable.py` (lives in `~/.chiper/skills/bounty-pack/`):

```bash
python .../final-deliverable.py check <target_dir>          # reportability only, writes nothing
python .../final-deliverable.py build <target_dir> --to <vendor> --from <me>
```

It emits, per reportable finding: `poc-pdfs/<slug>.pdf` (reportlab, the structure in rule 1 below,
with a **PROOF OF CONCEPT — DEMONSTRATED IMPACT** section carrying probe + raw observed output +
"what this proves", a **Verification** block with the 3x verdict and its artefact, and a supporting-
material table) and `email-drafts/<slug>.eml` — RFC5322 with that PDF attached. `.eml` on purpose: no
OAuth token needed, inspectable byte-for-byte, importable into Gmail. **Staging is never sending.**

**findings.json shape for `final-deliverable.py` (hit live 2026-10-21, mail.com):** `reverification`
must be a DICT `{"verdict": "CONFIRMED", "runs": [...]}`, NOT a bare list — the checker does
`rv.get("verdict")` and a list raises `AttributeError: 'list' object has no attribute 'get'`. Each
finding needs `demonstrated_impact` as `{probe, observed, proves}` (or `request`+`response` keys).

**⛔ `final-deliverable.py build` output is NOT shippable as-is (2026-10-21, mail.com):** it emits
(a) the STUB body ("One finding, one report... impact not stated") which rule 0c rejects, and (b) a
~4 KB PDF whose "/Image" byte-check false-positives — the screenshot is NOT actually embedded. Correct
pipeline that shipped: (1) `final-deliverable.py check` for the reportability gate only, (2) import
`build_pdf` from `skills/bug-report-delivery/scripts/stage_finding_draft.py` via importlib and build
the PDF from a markdown report carrying the `![caption](abs/path.png)` line (29 KB with the image
really in), (3) assemble the `.eml` yourself with `email.message.EmailMessage` — unique `Message-ID`
via `make_msgid(domain="report.local")`, `set_content(body)`, then `add_attachment` per file
(PDF + raw-evidence .txt + PNG per rule 0a-2), (4) read back and assert per-attachment
`sha256(remote) == sha256(local)`. Sanity gates before shipping: PDF size > 20 KB when it carries a
screenshot; body passes the banned-word/`responsible disclosure`/signature checks; attachment count
== 3. Delete the stub-body `.eml` and the undersized PDF from the earlier run so only the good
deliverable remains.

**When nothing qualifies it produces NOTHING — that refusal is the feature.** Manufacturing a draft
for a finding with no demonstrated impact is the phantom-evidence failure that gets reports closed
without investigation, and it is the same failure class as writing up a gate-dropped finding. Report
the negative result instead (see the negative-report guidance in `audit-execution-discipline`).

**⚠️ `final-deliverable.py` output is a SKELETON, not a shippable draft (verified 2026-10-21,
mail.com host-header finding).** The gate logic is correct (use it: `check` then `build`), but its
generated artefacts fail three operator rules and must be rebuilt before staging:

| What it emits | What's wrong | The fix |
|---|---|---|
| `.eml` with body `"One finding, one report… (impact not stated…)"` | Rule 0c stub — no intro, no channel, no signature, no probe verbatim | Write the 0c body yourself (intro/channel → finding with exact command+value → nothing-changed → close + real name), validate against the banned-word list, then rebuild the message |
| `poc-pdfs/<slug>.pdf` at ~4 KB | Too small to carry an embedded screenshot — references evidence it does not contain (rule 0d violation) | Rebuild via `stage_finding_draft.py`'s `build_pdf(src_md, out_pdf, title)` imported with `importlib.util.spec_from_file_location` — it renders `![caption](abs/path.png)` lines as embedded figures |
| One attachment (the PDF) | Rule 0a-2 requires THREE: PDF + raw evidence `.txt` + the PNG | Assemble the final `.eml` with `email.message.EmailMessage`: `add_attachment` for each of the three files, unique `Message-ID` via `make_msgid`, then read back and assert `sha256(local) == sha256(attachment)` per part |

Worked sequence that shipped: `final-deliverable.py check .` → `build .` (gate proof only) → write
`report.md` with the `![...](abs.png)` line → write `body_<ID>.txt` → import `build_pdf` → assemble
`.eml` with 3 attachments → Gmail `drafts.create` with the raw base64url → API read-back of every
attachment hash. Delete the skeleton `.eml`/`.pdf` the builder produced so only the real one remains.

Wired into the pipeline's 0F on **both** branches (positive after `report-agent.py`, negative after
the no-findings path), so it fires automatically the moment a real finding clears the gates.

**0c. THE DRAFT BODY HAS A FIXED SHAPE — the default body baked into `scripts/stage_finding_draft.py` is
a PLACEHOLDER and MUST be replaced (operator correction, 2026-10-12).** Verbatim: *"kamu perkenalan, terus
jelaskan temuannya, tutup dgn sopan, tanpa tanya reward, kasih nama saya … jgn lupa pdf pocnya yg lengkap
dan rapi, pakai skill humanizer"*. Shipping the stub ("Hi, / Findings attached. Full technical detail…")
is a rejected deliverable even when the PDF is perfect and every verification passed. Pass `--body <file>`
with, in this order:

1. greeting, who you are, and the channel — "My name is <operator's real name>. I am an independent
   security researcher, and I am sending this report through your responsible disclosure programme at
   <policy URL>.";
2. what you found, with the exact command and the exact value it returned;
3. one sentence stating that nothing was changed and the report is not shared with anyone else;
4. a polite close offering the raw evidence / a walkthrough / to retest a fix, then the operator's
   **real name and contact address** as the signature.

Banned in the body: any reward / bounty / credit / Hall-of-Fame request, "I hope this helps", emoji, and
a handle or bare "researcher" where the operator's real name belongs (this operator: **RESEARCHER_NAME**,
RESEARCHER_EMAIL). Run every body through the `humanizer` skill and assert it mechanically before
staging — `[t for t in ["\u2014","\u2013","delve","pivotal","leverage","seamless"] if t in body] == []`.

**Program URLs can trip the reward-word validator (2026-10-21, mail.com):** the submission address
`report@bugbounty.mail.com` and the policy URL contain the substring "bounty", so pasting the channel
into the body fails the mechanical banned-word check even though no reward is being requested. Fix:
keep the channel out of the body entirely (the `To:` header and the PDF already carry it) and write
"your responsible disclosure programme" with no URL. Same discipline for any vendor whose domain,
programme slug, or contact address embeds a banned word.
The PDF that rides with it must be complete and tidy: markdown → PDF → `qa_pdf_layout.py --margin-mm <m>`
must report `clean` for *every* finding (wrap long curl lines in the markdown first — an overflowing code
line is the usual offender), then re-stage the affected drafts.

**0d. EVERY DRAFT CARRIES THE EVIDENCE ITSELF — embedded screenshot + raw evidence + PNG (operator rule, 2026-10-16, from the finanzen.net VDP).** The operator checked the staged drafts and rejected them: *"kamu tidak menyertakan SS evidence, dan dlm pdfnya menyatakan ada evidence tp jg tidak kamu masukkan k struktur pdf ataupun ke dalam attachement, perbaiki dl semua sesuai aturan mereka dan attachmentny jg harus lengkap"*. Concretely, for every finding draft:

1. The PDF must EMBED the screenshot inside the report structure (a figure section), not merely *name* an evidence file. A PDF that references `final_evidence/F1_cors.json` without containing it is a rejected deliverable.
2. Each draft carries three attachments: the PDF (screenshot embedded), the raw request/response evidence as a plain-text file, and the screenshot PNG as its own file.
3. Screenshot provenance: prefer a REAL browser capture of the live flow. When the flow needs auth + custom headers or the WAF blocks browsers, use the **live evidence renderer** pattern — a local HTTP server that performs the actual request when the page renders and displays request + raw response, then screenshot that page with headless Chrome (`--headless=new --virtual-time-budget=12000` when JS must settle). Full recipe: `references/live-evidence-renderer.md`. Never fabricate values into a screenshot.
4. After staging, read back and assert ALL of: (a) draft-per-subject count via `messages.list(labelIds=['DRAFT'])`, (b) the attachment filename list, (c) `sha256(local file) == sha256(attachment)` via `attachments().get`, (d) `/Subtype /Image` present in the PDF bytes (proves the image really embedded), (e) `qa_pdf_layout.py` reports `clean` on every rebuilt PDF.
5. `stage_finding_draft.py`'s `build_pdf` understands markdown image lines since 2026-10-16: a line `![caption](C:/abs/path.png)` (forward slashes, `.png/.jpg` suffix, absolute path) embeds the image scaled to fit with a caption, RGB-guarded against the RGBA crash. To replace an already-staged draft in place, use `drafts().update(id=..., {"message": {"raw": ...}})` with the same draft id — never `create()` a second copy, and never recreate a draft that shows up in SENT (it shipped).

**Never assert a policy term the vendor does not actually have.** The email-shape template closes by
declining compensation on the grounds that the policy offers none (*"I understand from your policy that
none is offered"*). That is only true for a no-reward VDP. When the policy **does** offer a reward —
Gasunie's says *"we will, in most cases, give the reporter an appropriate reward"* — that sentence
states a falsehood about their own programme in the first email a triager reads. Either drop the
compensation paragraph entirely or keep it neutral (*"I am not asking for anything in return for this
report"*) without making a claim about their policy. Same discipline as the identity block: read the
policy text **before** the template's fixed sentences go out.

Keep the body free of AI-flavoured filler as well. Beyond the mechanical banned list
(`delve`/`pivotal`/`leverage`/`seamless`, em/en dash), avoid grand narrative sentences and any phrasing
that reads as generated prose — the operator asked for this explicitly (*"hindari kata2 terkait ai atau
reward"*). Plain, first-person, specific beats polished.

**The stub is now STRUCTURALLY unreachable, not just discouraged.** `scripts/stage_finding_draft.py` takes
`--body` as a **required** argument and its loader refuses to stage a body that (a) lacks the intro /
channel / signature markers, or (b) contains a reward word (`bounty`, `reward`, `credit`, `hall of fame`,
`swag`) or an AI-ism (`delve`, `pivotal`, `leverage`, `seamless`, em/en dash). The old generic fallback
body was deleted. Skeleton to copy per finding: **`templates/disclosure-email-body.md`** — it carries the
rules, the fill-in slots, and a shipped worked example.

Lesson worth keeping: when the operator corrects an *output shape*, fix the **generator's default**, not
just the prose rule. A rule the agent can forget will be forgotten; a required argument it cannot omit
will not be. Rule 0c existed before this session and the stub still shipped — that is what "patch the
root cause" means in practice.

0. **GATE BEFORE FORMAT (pre-step — do not skip):** Before a single word of the report is written,
   run the findings through the toolkit gate and chain builder:
   ```bash
   python $TOOLKIT/shared/finding_gate.py findings.json --report REPORT-survivors.md
   python $TOOLKIT/shared/chain_builder.py findings.json --goal <impact>
   ```
   - Only findings that **survived the gate** may enter the PDF. A dropped finding is informational — 
     writing it up anyway is severity inflation and it will be rejected.
   - **SCOPE MAP CHECK (operator hard rule, 2026-10-26, DuoCircle):** Before staging ANY draft, re-read the 
     program's "what we pay for" AND "what we do not pay for" lists clause-by-clause. Every finding MUST map 
     to a payable category. The user caught an OOS submission (username enumeration → vendor explicitly 
     excludes "username enumeration on public sign-up or password-reset flows"). Submitting OOS findings 
     damages reputation and risks program ban. If a finding only maps to an exclusion (DoS, enumeration, 
     missing headers, info disclosure, theoretical), DO NOT stage — tell the operator it is OOS and why.
   - **The gate is a keyword heuristic, not an oracle — review its verdict, never obey it blindly.**
     `finding_gate.py` scores a finding with regexes over its text, so it is wrong in BOTH directions
     (verified by reading the source, 2026-10):
     - **False POSITIVE**: `IMPACT_PATTERNS` includes `\b(pii|email|phone|address|kyc|...)\b` weighted 6.
       Two crypto findings whose text merely quoted a **contract address** scored "pii-exposure 6" and
       sailed through as REPORT, with no privacy impact at all.
     - **False NEGATIVE**: `fund-loss` (weight 10) only fires on
       `\b(funds?|balance|withdraw|transfer|mint|steal|drain)\b.{0,30}\b(unauthor\w*|arbitrar\w*|without)\b`.
       A proven on-chain reward-accounting bug — half of a funded emission window never credited to
       stakers, the matching TIMBS locked in the contract, PoC 3/3 PASS — scored 0 and was DOWNGRADED
       with "no concrete impact signal (data/funds/authz) found", because the prose said "loss of
       rewards to LPs" instead of "funds ... without authorisation".
     So: when the gate and your evidence disagree, the **evidence wins** — but state the gate's verdict
     and your disagreement explicitly in the write-up and to the operator. Never reword a finding to
     farm a keyword (that is gaming the filter), and never let a 0 score delete a PoC that passes.
   - If the gate drops everything, the correct deliverable is the one-line statement
     *"no reportable finding on this surface"* + the gate output as evidence — **not** a padded PDF.
   - Every finding in the PDF needs its PoC evidence to match the gate's recorded proof
     (screenshots / raw HTTP / tx hash). No evidence → no section.

> **⛔ OPERATOR FORMAT PREFERENCE (2026-10-31, Zenya): the standing default is `.docx`
> (python-docx), NOT PDF, unless the operator explicitly asks for PDF.** Memory carries this as
> *"Dokumen laporan: .docx (python-docx), BUKAN PDF kecuali diminta"*. The PDF/reportlab machinery
> below stays as the fallback for when PDF is requested or when the vendor mandates it. For the
> `.docx` path: build with `python-docx`, embed the evidence PNG with
> `doc.add_picture(path, width=Inches(6.3))` plus an italic centred caption, and keep every other
> rule unchanged — same section structure, same three attachments (report + raw evidence `.txt` +
> PNG), same sha256 read-back, same rule-0c body. A `.docx` carrying an embedded screenshot lands
> around 80 KB, which is the size sanity-check to use in place of the PDF's ">20 KB" rule.

1. **FORMAT:** Always use skill reporting format (references/reporting.md from bug-bounty skill). Structure: Title → Summary → Severity/CVSS → Steps to Reproduce → Proof of Concept → Impact → Remediation → Supporting Material.

2. **SAVE LOCALLY:** Save PDF to working directory (e.g., `/home/agentuser/arlo-bounty/` or project dir). Always use clear, descriptive filenames.

3. **DELIVER TO CHAT:** After generating the PDF, MUST deliver it to the SAME chat/topic where the request was made using `MEDIA:<absolute_path>` format. This means:
   - If user asks in Telegram topic X → send MEDIA: to topic X
   - If user asks in WhatsApp → send MEDIA: to WhatsApp
   - The file must be sendable/clickable, not just text output

4. **SCREENSHOTS/POC:** Reports must include evidence — screenshots (browser capture) or terminal output as POC. If browser blocked by WAF, use curl terminal output as evidence.

5. **EVIDENCE FILES:** Also create and send evidence text files (curl logs) alongside the PDF.



## Two transport traps that read as failures but are not (2026-10-25)

- **IMAP read-back false negative:** `EmailMessage` folds a long `Subject:` header, so `imap_tools`
  returns `"... onboarding\r\r\n (djangoeurope.com)"` and an exact `m.subject == subject` check prints
  `READ-BACK FAILED: draft not visible in folder` for a draft that staged perfectly. Compare normalised
  (`re.sub(r"\s+"," ",s).strip()`), keep subjects short, and list the draft folders before concluding
  anything (this account has four: `Drafts`, `INBOX.Drafts`, `[Gmail]/Draf`, `[Gmail]/Drafts`).
- **Build order:** write the report as **markdown**, then run `md_to_report_pdf.py` — do not hand-splice a
  reportlab generator through `cat >> x.py <<'EOF'` chunks. Shell-hostile squote/pipes and the
  auth-header redactor break the splice, while markdown heredocs chunk safely. `md_to_report_pdf` has NO
  markdown-table branch (a `|` line renders as a run-on paragraph), so write comparison tables as bullets.

Full recipe: `references/pdf-build-order-and-imap-readback.md`.

## Deliverable integrity — identity, version hygiene, cross-artifact agreement

### Identity / contact block: never leak another platform's alias

Operator correction, 2026-10: *"kok ad tulisan BC_ALIAS? ini an self host"*.

- A **platform-specific alias** (e.g. `RESEARCHER_BC_EMAIL`, which exists for Bugcrowd) must NOT
  appear in a report for a **self-hosted / vendor-direct** program. It signals the wrong taxonomy and
  makes the triager question where the report is coming from.
- Default to the operator's **own established convention for that program**. Their prior reports are
  the reference: if those carry name + role and no address, match that. Do not add an email just
  because a template has a contact field.
- **Check every artifact, not just the body.** That one string is also pushed into the PDF canvas
  header/footer on *every* page, so a single constant fixes — or breaks — all of them. Grep the built
  PDF for `@` and for the platform name before delivering.
- If a reply address is genuinely needed, ask which address to use **for that program**. Bugcrowd
  alias, personal mail, and program-specific mail are not interchangeable.

### Version hygiene: if the operator has NOT submitted yet, ship ONE clean version

Operator correction, 2026-10: *"jgn ad koreksi segla macam, samakan dgn video, sy blm submit,
jd msh aman"*. Two situations, two different artefacts:

| Situation | What to produce |
|---|---|
| Already submitted / the vendor holds the old one | Explicit **correction framing is correct** — state what changed and why so the triager can re-verify |
| **Nothing submitted yet** | A single clean document stating the corrected facts as plain truth. **No** "correction", "corrected", "previous version", "previous submission", "erratum", "originally", "was changed", "no longer" — not in the subtitle, not as a section, not in metadata |

Mechanics for the clean case:

1. **Rewrite, don't annotate.** Delete the wrong value entirely instead of adding prose that explains it.
2. **Grep the built PDF for the forbidden words** plus the superseded value itself. Any hit means the
   rewrite is incomplete.
3. **Drop version suffixes** from the filename once it is the only version — `-v2` in a filename is a
   tell that a v1 is still sitting somewhere.
4. **Move superseded PDF/MP4 into `superseded/`** the moment a replacement exists. Side by side, the
   operator ships the wrong file.
5. **PDF and video share one basename** — they are a single deliverable.

### Cross-artifact agreement: every claim must appear in both

Any statement in the written report must be something the video also shows, and vice versa. A video
demonstrating a different URL / chain / parameter than the PDF describes is **worse than no video** —
it invites the triager to distrust both. Before delivering, walk the report's numbered steps and tick
off the segment that proves each one. If a step cannot be shown live, cut the claim or list it
explicitly under "Not claimed" (the Proven/Not-claimed table pattern in the gold-standard structure).

When the video reveals the report's steps are wrong, the operator usually needs **three** things, not
one — ask which they want, and default to all three:

1. the **regenerated clean PDF** (see version hygiene above),
2. the **video**, and
3. a **corrected-steps summary** — a plain-text, copy-pasteable block containing the corrected
   reproduction steps, the control tests, the artifacts to revoke, and a one-line note of what
   changed. The operator pastes it into the submission form / a triager reply; it is not a PDF.

Deliver (3) as a `.txt` in the same folder so it can be pasted without reformatting. Say plainly in
the reply which URLs/values changed and why — the operator may have **not** submitted yet, in which
case the summary silently fixes their draft before it goes out.

For the video side of this — routes, assembly, ffmpeg/Playwright pitfalls, vision-free verification,
and the live-target safety rails — see `references/video-poc-production.md`.

### ⛔ Every staged draft needs an explicit unique `Message-ID` — the REST path replaces drafts too

Hit live 2026-10-13 (Arrakis engagement, 2 findings). Finding F1 was staged through the Gmail **REST**
API (`users().drafts().create()`), read back, verified — attachment hash matched, `To:` correct.
Finding F2 was staged minutes later by the same code. F1 was **gone**: `drafts().list()` returned
exactly one draft. No error on either `create()`.

The `Message-ID` warning elsewhere in the library is written up as an IMAP `append` problem. **It is
not IMAP-specific.** `EmailMessage()` does not add a `Message-ID`, and Gmail treats an appended message
without one as a *revision of the previously appended draft*. `scripts/stage_finding_draft.py` had the
same hole and now sets it itself:

```python
from email.utils import make_msgid, formatdate
msg["Message-ID"] = make_msgid(domain="report.local")   # unique per draft — REQUIRED on REST too
msg["Date"] = formatdate(localtime=True)
```

Two corollaries, both of which cost time in that session:

- **Stage N drafts, THEN assert N live subjects in one pass.** The natural "stage one → verify one"
  loop passes for every draft and still misses the loss, because the victim is only destroyed when the
  *next* draft lands. Count by subject across the whole batch after staging, never per-draft alone.
- **`Message-ID: NONE` in the `format="metadata"` read-back is NOT a missing header.** After the fix
  the metadata view still showed `MSGID: NONE` — Gmail normalises an API-created draft. The
  authoritative proof is one draft per subject plus `sha256(attachment) == sha256(local pdf)` read back
  through `messages().attachments().get()`. Do not re-stage a draft that is already correct.
- **`drafts.list()` can return ZERO drafts while the draft demonstrably exists — never trust it as the
  existence check** (hit live 2026-10-13, Oh Dear). Stager reported `DRAFT r1856229749558253171
  VERIFIED`, but both `drafts.list()` and `drafts.list(q='subject:"…"')` returned `0`, which reads like
  the staging was lost. `drafts.get(id=…)` returned the full raw message and the attachment sha matched,
  so the draft was fine — only the listing index was empty. The reliable batch assertion is
  `messages().list(labelIds=['DRAFT'])`, then decode each `raw` and count by subject. In that run it
  showed 23 total drafts, exactly 1 for the finding. Rule unchanged: stage N, then assert N in ONE pass
  over `labelIds=['DRAFT']` — but run the assertion on messages, not on drafts.list.

Full transcript and the second trap in the same helper (the rule-0c body validator rejecting the word
`bounty`): `reportlab-security-pdf` → `references/gmail-message-id-rest-path.md`.

### Re-running the stager must not resurrect a draft the operator already sent

The staging script is re-run once per new finding, so it must be safe to run repeatedly against
a mailbox where earlier findings have already shipped. Operator caught this 2026-10-08: after they
said *"f3 sudah sy kirim"*, a re-run **created a second draft** for that same finding.

- **A tracked draft id returning 404 does NOT mean "lose the draft and remake it".** In Gmail a
  draft disappears from `drafts/` precisely because it was **sent**. Recreating it silently leaves
  a duplicate of content the vendor already has — and the operator may ship it twice.
- So: on 404, **recreate but mark it loudly** (`recreated_after_missing: true`, printed as a
  distinct `RECREATED: tracked draft was missing (already sent?)` line in the run output), rather
  than treating it as a routine create.
- **Add a duplicate sweep after staging** — list every matching draft and count by attachment
  filename; any filename appearing more than once is flagged. This is the safety net that catches
  the case the per-finding known-id check cannot see.

```python
by = defaultdict(list)
for c in api(".../drafts?q=" + quote('"<subject-stem>"')):
    m = message_from_bytes(b64urlsafe_b64decode(raw(draft_id)["message"]["raw"]))
    for p in m.walk():
        if p.get_filename():
            by[p.get_filename()].append(c["id"])
for fn, ids in sorted(by.items()):
    print(f"{fn:<46} {len(ids)}x {ids}" + ("  <-- DUPLICATE" if len(ids) > 1 else ""))
```

- **Do not delete the redundant draft to clean up.** The operator owns the mailbox and may have
  already acted on it. Flag it and let them decide — deleting without asking is the kind of
  irreversible action that needs a confirmation, and a stale duplicate is cheap next to a
  wrongly-deleted draft.

Note the distinction from the version-hygiene rule above: that one is about the *artefact* being
superseded and moving files to `superseded/`. This one is about the *transport* — a draft that is
gone from `drafts/` is gone because it shipped, not because it needs rebuilding.



## A draft you staged can be SENT by the operator before you update it (2026-10-21, mail.com)

Hit live: staged finding → operator reviewed it in Gmail and **sent it** → a later
`drafts().update(id, ...)` on the tracked id failed with `400 "Message not a draft"`.
The draft was gone from `drafts/` precisely *because* it shipped.

- **Check SENT before touching any tracked draft id.** One query settles it:
  `messages().list(q="to:<vendor>")` and look at `labelIds` for `SENT`. If the sent
  copy's attachment set is already complete, do nothing.
- If you later produce a strictly better version of an **already-sent** report (e.g. the
  affected-host list grew after a full sweep), do **not** try to replace the sent mail.
  Stage a **supplement draft**: `Subject: "Re: <original subject>"`, `In-Reply-To` /
  `References` = the original `Message-ID`, body framed as "supplement to my report of
  earlier today" + only the delta (new hosts, new negative tests), same PDF + evidence
  attachments. Operator decides whether to send.
- `final-deliverable.py` expects `reverification` as a **dict**
  (`{"verdict": "CONFIRMED", "runs": [...]}`), not a list — a list crashes
  `reportability()` with `AttributeError: 'list' object has no attribute 'get'`.
- `final-deliverable.py build` emits a **stub body** ("One finding, one report...") and
  attaches only the PDF — that output is a rejected deliverable under rules 0a-2/0c.
  Treat its `check` as the gate, then rebuild the real deliverable: import
  `build_pdf` from `scripts/stage_finding_draft.py` against a markdown report with an
  embedded `![caption](abs/path.png)` line, write the 0c-shape body by hand, and assemble
  the `.eml` (or Gmail draft) with **three attachments** (PDF + raw evidence txt + PNG),
  a unique `Message-ID`, and sha256 read-back of every attachment.



When the user says *"continue the X audit"* / *"lanjutkan audit yang tertunda"* on a target that
already has a workspace, do not start from the workspace alone. The workspace shows what was
**tested**; the mailbox shows what was **committed to and answered**. Recover both, in this order:

1. **Inventory the workspace.** `<BB_DATA>/_progress/<target>*/` — reports, session logs, logs/,
   scripts, creds. Read the session log and the newest report first; they carry the honest
   "outcome" and any cleanup/state residue.
2. **Rebuild the correspondence state from the mailbox** (read-only, `[Gmail]/Semua Email`,
   `TEXT "<vendor-domain>"`). Dump the bodies of the ~5 newest in the thread and answer, explicitly:
   was the report actually SENT (is there a sent copy)? did the vendor reply, and to what? which
   items did they already accept/fix? is a finder's fee or reward pending/paid? is there an open
   promise you made ("I'll do another pass")? That last one is usually THE pending task, and it is
   invisible in the workspace.
3. **Re-verify the findings LIVE before writing.** Note the build fingerprint in the old report and
   check whether it still holds — vendors redeploy between sessions (chunk hashes, server-action ids,
   and the arithmetic of public tools can all change). Re-running the read-only probe is cheap and it
   is what makes "confirmed still live on <date>" honest. Public/unauthenticated surface is the
   cheapest to re-verify and the most likely to have been missed by the account-based sweep.
4. **Then** generate the deliverable and exactly one in-thread draft (see above), threading on the
   captured Message-ID chain so it lands inside the existing conversation rather than as a new one.

Capture the Message-IDs you will thread on in step 2 and reuse them in step 4 — do not re-search for
them at send time.



## Headless-Chrome screenshot of a live endpoint (use BEFORE Pillow when a real capture is possible)

For a genuine visual of an HTTP response (metrics page, JSON body, error page) you do not need a
browser tab or a base64 round-trip through the conversation — write the PNG straight to disk:

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --no-sandbox \
  --hide-scrollbars --user-data-dir="D:/.../hl-shot" --user-agent="$UA" \
  --window-size=1280,1000 --screenshot="D:/.../evidence/metrics_screenshot.png" "https://host/metrics"
```

Then **verify it before embedding** — a blank or error-page screenshot inside a PDF is the fastest
way to lose triager trust. Two checks, neither of which needs a vision model:

```bash
# ink check: unique==1 or min==max ⇒ blank ⇒ throw it away
python3 -c "from PIL import Image;px=list(Image.open('metrics_screenshot.png').convert('L').getdata());print('unique',len(set(px)),'min',min(px),'max',max(px))"
# content check: prints the rendered DOM (for text/plain Chrome wraps it in <pre>)
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --dump-dom --user-data-dir="D:/.../hl2" "$URL" | head -c 400
```

Embed with `--dump-dom` output quoted in the PDF caption as the machine-readable counterpart, so the
artifact proves both what the endpoint emitted and how it rendered. Note `--headless=new` still
returns the real page for a WAF-free endpoint; if the shot comes back as a challenge/error page, say
so rather than shipping it.



## Pillow POC Screenshot Generation (Fallback when browser fails)

Browser Swagger UI/console tools sometimes fail (console returns null, clicks don't work, WAF blocks). Use Python Pillow to generate professional terminal-style POC screenshots.

### ⚠️ TARGET-SPECIFIC CONSTANTS (CRITICAL — not optional)
**`scripts/gen_poc_screenshots.py` contains hardcoded constants from a PREVIOUS target (Aurory).** Before generating screenshots for ANY new target, you MUST:
1. Open the script and find the constants section at the top
2. Replace ALL values: OWNERSHIP_ID, ACCOUNT_ID, PLAYER_ID, BASE_AUTH, BASE_URL, endpoints, etc.
3. New constants must match the values used in the PDF text exactly (single-source-of-truth)
4. If you skip this step, screenshots will show WRONG evidence (wrong IDs, wrong endpoints) while PDF text shows correct values — triagers WILL notice

**Pitfall (Chime session 2026-09-03):** Generated 4 PDFs with Chime-specific data but used Aurory screenshots. User caught it: "sudah dipastikan bahwa pdfnya dbuat brdasarkan skill report bugcrowd y? yg semuanya sinkron antara pdf, ss, dan poc nya?" — had to regenerate everything.

**Style:** Dark background (#1e1e1e), green (#00ff41) for success/request text, red (#ff4444) for vulnerability highlights, monospace font, step headers, watermark footer with "Reporter @ Bugcrowd | Timestamp".

**Reusable script pattern:**
```python
from PIL import Image, ImageDraw, ImageFont
import textwrap, os

W, BG, FG, RED, TITLE = 1200, '#1e1e1e', '#00ff41', '#ff4444', '#00bcd4'

def make_screenshot(lines, output_path, title="POC Evidence"):
    """Generate a terminal-style POC screenshot."""
    font = ImageFont.truetype("consola.ttf", 16)
    h = 40 + len(lines) * 24 + 60
    img = Image.new('RGB', (W, h), BG)
    draw = ImageDraw.Draw(img)
    y = 20
    # Title
    draw.text((20, y), title, fill=TITLE, font=font); y += 36
    for line, color in lines:
        draw.text((20, y), line[:110], fill=color, font=font); y += 24
    # Watermark
    draw.text((20, h-35), f"POC Evidence | BC_USERNAME @ Bugcrowd | {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", fill='#666666', font=font)
    img.save(output_path)
```

**Files to generate per finding:**
- `01-swagger-ui-overview.png` — API docs showing endpoint
- `02-endpoint-no-auth.png` — Swagger showing no lock icon
- `03-step1-[action].png` — First request + response
- `04-step2-[vuln].png` — Vulnerability trigger + response
- `05-step3-[verify].png` — Verification of exploit
- `06-step4-[impact].png` — Impact demonstration
- `07-impact-summary.png` — Attack chain + impact overview

The gen_screenshots.py from `~/aurory-report/` is a working reference implementation.



## Embedding Screenshots in PDFs (reportlab Image)

When building bug bounty PDFs with embedded POC screenshots, use reportlab's `Image` flowable:

```python
from reportlab.platypus import Image, KeepTogether
from reportlab.lib.units import inch

def screenshot_flowable(filepath, caption_text, max_width=460, max_height=340):
    """Embed a screenshot image with caption, auto-scaled to fit."""
    if not os.path.exists(filepath):
        return Paragraph(f"[Screenshot not found: {os.path.basename(filepath)}]", caption_style)
    img = Image(filepath)
    aspect = img.imageWidth / img.imageHeight
    w = max_width
    h = w / aspect
    if h > max_height:
        h = max_height
        w = h * aspect
    img.drawWidth = w
    img.drawHeight = h
    img.hAlign = 'CENTER'
    caption = Paragraph(f"<i>{caption_text}</i>", caption_style)
    return KeepTogether([img, caption])

# Usage in story:
story.append(screenshot_flowable("evidence/01-swagger-overview.png",
    "Figure 1: API Swagger UI — no auth required"))
story.append(screenshot_flowable("evidence/02-mint-jwt-vuln.png",
    "Figure 2: JWT minted WITHOUT authentication"))
```

**Key rules:**
- Always use `KeepTogether` to prevent page breaks between image and caption
- Scale to fit A4 margins (max_width ≈ page_width - margins)
- Use `img.hAlign = 'CENTER'` for consistent placement
- Save screenshots as PNG (reportlab supports PNG and JPEG natively)
- File size matters: 8 screenshots ≈ 600-700KB total PDF. Keep individual PNGs under 200KB

### ⚠️ Pillow RGBA Color Mode Pitfall (CRITICAL — hit 3x in UpScrolled 2026-09-01)

Pillow's `Image.new('RGB', ...)` creates RGB images, but certain operations (transparency, compositing, alpha channels) silently convert to RGBA mode. When reportlab tries to embed an RGBA PNG in PDF, it crashes with:
```
OSError: cannot save mode RGBA as PDF
```

**The fix — convert to RGB BEFORE saving to PNG:**
```python
# WRONG — may produce RGBA PNG that crashes reportlab
img = Image.new('RGB', (W, h), BG)
# ... draw stuff ...
img.save(output_path, 'PNG')  # Could be RGBA if any alpha operation occurred

# CORRECT — force RGB before save
img = Image.new('RGB', (W, h), BG)
# ... draw stuff ...
if img.mode == 'RGBA':
    img = img.convert('RGB')
img.save(output_path, 'PNG')
```

**Even better — guard in the screenshot function itself:**
```python
def make_screenshot(lines, output_path, title="POC Evidence"):
    img = Image.new('RGB', (W, h), BG)
    # ... draw ...
    # SAFETY: always convert before save
    img = img.convert('RGB')
    img.save(output_path, 'PNG')
```

**When embedding in reportlab PDF, also guard:**
```python
from reportlab.platypus import Image as RLImage

def safe_screenshot_flowable(filepath, caption_text, max_width=460, max_height=340):
    if not os.path.exists(filepath):
        return Paragraph(f"[Screenshot not found]", styles['CaptionStyle'])
    # Force RGB for reportlab compatibility
    pil_img = Image.open(filepath)
    if pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')
        pil_img.save(filepath, 'PNG')  # Overwrite with RGB version
    img = RLImage(filepath)
    # ... rest of flowable ...
```

**Root cause:** Pillow `Image.new('RGB', ...)` is RGB, but `.paste()` with transparency, `Image.alpha_composite()`, or font rendering with antialiasing can silently promote to RGBA. Always verify `.mode` before save.

### Pillow Screenshot Generation → reportlab Embedding Pipeline
Full pipeline for when browser fails:
1. Generate screenshots with Pillow (see gen_poc_screenshots.py)
2. Embed them in reportlab PDF via `Image()` flowable (above)
3. Final PDF is self-contained — no external file dependencies



## ⚠️ Re-verify every candidate LIVE before writing — drop what does not survive (edge-vs-origin trap)

A finding "found" during recon can evaporate on a second pass. Re-run the probe, capture verbatim
**dated** output, and only then write it up. The single most common way a phantom finding survives
into a PDF is attributing an **edge/CDN** response to the **origin**.

Concrete trap (2026-10, synology.com self-hosted VDP):

- `405 Not Allowed` on `TRACE /api/profile` looked like framework/route+method disclosure. On re-test
  the response carried `X-Cache: Error from cloudfront` and `X-Amz-Cf-Pop: SIN2-P9` — the **edge**
  answered, not the origin. That is standard CDN behaviour, not origin disclosure, and not a finding.
- The `404` for `DELETE /c2/api/v1/...` returned body `404 page not found` (Go-style), no framework
  signature either — so the whole "framework disclosure" candidate collapsed.
- **Rule:** before calling a 404/405 "framework / route / method disclosure", attribute the response
  to a layer. Inspect `Server`, `X-Cache`, `X-Amz-Cf-Pop`, `CF-Ray`, `Via`, `X-Powered-By`. If an
  edge produced it, it is not origin behaviour — drop it.

Apply the same discipline to every candidate: a header / CSP / hostname / storage-state observation
that cannot be reproduced on a fresh run is NOT a finding. Drop it, and name it in the report's
**"Negative Tests / What I Explicitly Excluded"** section with the reason — an honest exclusion list
is stronger than a padded report, and it pre-empts the triager's "did you check X?".

### ⛔ Never conclude from a TRUNCATED value — parse the whole thing (hit live 2026-10-31, Zenya)

The most expensive mistake of the Zenya round was a finding that was **wrong in the dangerous
direction**: reported to the operator as a vulnerability, then retracted on re-validation.

`GET /chat/auth/login` returned a 307 whose `Location` header was printed truncated at 220
characters. The visible portion ended at `&scope=openid+email` and showed no `state`, so the session
concluded *"OAuth authorization request omits the state parameter (CWE-352)"*. On re-validation the
**full** header was 354 characters and did contain `&state=eyJuIj...1nYs&prompt=select_account` — a
base64 JSON nonce `{"n":"<22 random chars>"}`, different on every request. The callback also rejected
every arbitrary state value thrown at it. There was never a vulnerability.

Rules that follow:

- **A truncated display is not evidence.** Any time a header, token, URL, body or hash is cut off by
  a print limit, re-read it in full before drawing a conclusion. Print `len(value)` next to it so
  truncation is visible rather than silent.
- **Parse, don't eyeball.** `urllib.parse.parse_qs(urlparse(loc).query)` turned a wrong conclusion
  into a correct one in a single call. Same for a JWT (`split('.')` + base64 decode each part), for
  header dicts, for anything structured. Never reason about a substring of a structured value.
- **A conclusion drawn from a prefix is a hypothesis, not a finding.** The 3x re-verification rule
  only helps if each of the 3 runs reads the *whole* value — three truncated reads confirm nothing.
- **Re-validate before the operator acts on it.** The F2 retraction above was caught only because
  the operator said "gas" and the draft step forced a fresh verification pass. Build that pass in
  deliberately: re-read the full raw value immediately before it enters a report or a draft.
- When a retraction happens, say so plainly and lead with it. A retracted finding costs one email;
  an unretracted wrong one costs credibility with the vendor and with the operator.

**A public repo / OSS snapshot is a hypothesis generator, not the deployed code. One live probe per claim, before the draft.** The clone you review is usually months-to-years behind the build in production, and the deployed build is where the validations live. Verified on pay.blink.sv (2026-10-12): the public Galoy snapshot's `POST /api/lnurl-proxy` had **no session check** and interpolated an attacker-supplied `callback` URL with **no origin validation**, relaying the upstream body back to the caller — a textbook unauthenticated read-SSRF on paper. Live, the same route produced three *different* error messages that expose a hardening the repo does not contain: a public JSON `lnurl` really was fetched (`Not a properly configured lnurl withdraw tag`), `http://169.254.169.254/…`, `http://127.0.0.1:3000/…` and `http://10.0.0.1/` were rejected in <1.1 s (`Invalid lnurl` — blocked at validation, not at fetch), and any callback whose host differed from the lnurl host got `Invalid callback URL`, including the userinfo bypass `https://paste.rs@httpbin.org/json`. Shipping the repo-derived chain would have been a phantom finding.

The mechanic to reuse: when source says "no validation", **read the server's own error strings as the deployed policy** — send the valid case, a private-IP case, and an off-origin case, and keep the matrix (status + body + latency per case) as the evidence. A fast uniform rejection = validator; a slow/partial one = real fetch. The candidate then goes into the exclusion list with its matrix, and the report gets stronger for it.

When only **one** low/informational candidate survives, ship exactly that one. Do not inflate the
count to satisfy "one draft per finding" — say which candidates you dropped and why. If the survivor
is informational-grade, flag it once to the operator (the skill's own gate says informational →
SKIP, and submitting noise damages reputation) and let them choose; then stage the single draft and
PDF regardless.



## POC Consistency Rule (HARD RULE)

When generating **multiple deliverables** (e.g., PDF report + screenshots + BUGCROWD_SUBMISSION.md + submission form text), the PoC content **MUST be identical** across ALL of them.

**User explicitly caught this twice:**
1. "POC yg ad di submission.md dgn yg ad d pdf kok beda?" — PDF POC differed from submission guide
2. Screenshots showed DIFFERENT account_id, player_id, endpoint hosts, and request bodies than the text narrative — making the report look fabricated/reconstructed

**How to enforce — SINGLE-SOURCE-OF-TRUTH pattern:**
1. Define ALL PoC data as Python constants at the TOP of the generation script:
   ```python
   OWNERSHIP_ID = "fad6fac2-..."
   ACCOUNT_ID = "s-00001337"
   PLAYER_ID = "p-maJF0Dg9QRijpfb"
   SECRET = "poc_test_secret_12345"
   BASE_AUTH = "https://auth-public-api.live.aurory.io"
   ```
2. The SAME constants drive: PDF text, PDF code blocks, screenshot text, AND submission.md
3. After generation, MANUALLY VERIFY these values match across ALL outputs:
   - account_id in PDF text == account_id in screenshots
   - endpoint host in PDF text == endpoint host in screenshots
   - request body in PDF text == request body in screenshots
   - account_id/player_id in submission.md == PDF == screenshots
4. Never hardcode different values in different generators

**CVSS Pitfalls (user caught these):**
- **UI:R vs UI:N**: If IDOR enumeration works WITHOUT victim interaction (attacker just guesses/brute-forces ownership_id), score it UI:N, not UI:R. UI:R is only when victim must click a link or perform an action.
- **Scope:Changed**: Don't use generic justifications ("impacts client account security boundary"). Scope Changed requires that exploitation in one component affects security authority of a DIFFERENT component outside its control. If you can't prove this, use Scope:Unchanged.
- **expires_at edge case**: If your PoC ownership record has expires_at BEFORE the report submission date, it looks sloppy. Always set expiry well into the future.



## Evidence-server and stager pitfalls hit live (2026-10-18/19, LoopScale + djangoeurope)

- **Stale servers share the port.** A killed background server can survive (the process tool
  reports killed but the OS process lives); starting a second instance then leaves TWO listeners
  on the port and requests keep hitting the OLD code. Symptom: a patched route still renders old
  values. Fix: `netstat -ano | grep <port>` and `taskkill //F //PID <pid>` every listener before
  restarting, then verify with a content probe (grep the expected NEW value), never just a 200.
- **Cache slow routes before screenshotting.** A route performing 5 RPC calls takes 30-40s; both
  headless Chrome's --timeout and the 60s foreground limit expire. Fix: memoize the route HTML in
  a module-level dict, warm it once with curl, then screenshot the cached render.
- **Kill orphan chrome between shots.** 10+ orphaned chrome.exe hold --user-data-dir locks and
  every later screenshot fails silently (no file written). `taskkill //F //IM chrome.exe` first,
  fresh profile dir per shot.
- **A typo'd address in the evidence server fakes a vulnerability.** An invalid base58 pubkey in
  a probe made the target answer HTTP 500, which read as "endpoint broken / rate-limited" but was
  really input validation. Always re-test the probe with a known-valid value before writing
  "endpoint returns 500" into evidence or a report.
- **Stager 3-attachment rule needs --attach.** stage_finding_draft.py attaches PDF + optional
  .asc only, but rule 0a-2 requires PDF + raw evidence txt + PNG per draft. Patch: add
  `ap.add_argument("--attach", action="append", default=[])` and
  `files = [pdf] + [f for f in a.attach if os.path.exists(f)] + (...)`; then read back
  sha256 per attachment via messages().attachments().get().
## Re-read the program OOS list before staging each finding — "enumeration" is interpreted BROADLY

A finding staged and then rejected as OOS costs reputation. Re-read the program's out-of-scope list and map
each finding clause-by-clause; drop whatever maps instead of staging and hoping.

**Live example (DuoCircle, 2026-10-26):** an unauthenticated AppSumo license-redemption endpoint returned
distinguishable responses for existing vs non-existing emails ("An account already exists with this email
address..."). The flow is NOT a sign-up or password-reset flow, so it seemed to dodge the OOS clause
"Username enumeration on public sign-up or password-reset flows." The vendor rejected it anyway — they
interpret "enumeration" broadly across ANY unauthenticated endpoint that reveals account existence. Lesson:
when a finding's core impact is "attacker learns whether X exists," assume the vendor's enumeration exclusion
applies regardless of which flow it lives in. Only stage it if you can chain the enumeration to a stronger
impact (data exposure, ATO, privilege escalation) with a demonstrated PoC.

## Gmail token refresh via curl subprocess (when Python google-auth fails on DNS)

The Python `Credentials.refresh(Request())` path can fail with `getaddrinfo failed` for
`oauth2.googleapis.com` even when curl reaches the same host fine (observed on a Cloudflare WARP host where
the Python resolver and the system resolver disagree). Fix: refresh via `subprocess.run(['curl', ...])`
POSTing to the token endpoint, parse the JSON response, write the new `access_token` and `expiry` back to
the token file, THEN build the Gmail service. This avoids the Python DNS path entirely.

```python
import json, subprocess, datetime
d = json.load(open(TOKEN_PATH))
cmd = ['curl','-s','--max-time','15','-X','POST','https://oauth2.googleapis.com/token',
       '-d',f'client_id={d["client_id"]}',
       '-d',f'client_secret={d["client_secret"]}',
       '-d',f'refresh_token={d["refresh_token"]}',
       '-d','grant_type=refresh_token']
resp = json.loads(subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout)
d['access_token'] = resp['access_token']
d['expiry'] = (datetime.datetime.utcnow()+datetime.timedelta(seconds=resp.get('expires_in',3600))).strftime('%Y-%m-%dT%H:%M:%S')
json.dump(d, open(TOKEN_PATH,'w'))
```

### OAuth triage in one call — `invalid_grant` means STOP and switch to IMAP (2026-10-28, binobi)

Do not spend iterations coaxing OAuth back to life. One POST settles it:

```python
r = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": t["client_id"], "client_secret": t["client_secret"],
    "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}, timeout=30)
r.json()  # -> {"error":"invalid_grant","error_description":"Token has been expired or revoked."}
```

- `invalid_grant` on **this** call = genuinely revoked → go straight to the IMAP App-Password path
  (`references/imap-append-draft-via-app-password.md`). Re-authorizing is the operator's job, not a
  reason to stall the deliverable.
- A stale `token` in the file (expiry hours in the past) is the *normal* state, not proof of
  revocation — that is what the refresh is for.
- **Resolve the drafts mailbox by the `\\Drafts` FLAG, never by name.** `imaplib.list()` on the
  Indonesian account returns `Drafts`, `INBOX.Drafts`, `[Gmail]/Draf` **and** `[Gmail]/Drafts`; only
  `[Gmail]/Draf` carries `(\\Drafts)`. Appending to the name-matched `Drafts` "succeeds" (`APPENDUID`)
  and the message is invisible in the Gmail UI — this reproduced again on 2026-10-28 despite being
  documented, because the name `Drafts` reads correct.
- **Clean up the stray folder properly.** `select` it, `store(i,"+FLAGS","\\Deleted")` for every id,
  then `expunge` — a plain delete leaves the folder behind. Then append to the flagged mailbox and
  assert the count from *that* mailbox only (`[Gmail]/Draf` read 39 while the stray read 1).
- Append signature is `append(mailbox, flags, date_time, message)` — message LAST; a wrong order
  fails or misfiles silently. `imaplib.Time2Internaldate(time.time())` for the date, and normalise
  the body with `.replace(b"\n", b"\r\n")` before appending bytes built by `EmailMessage.as_bytes()`.
- Verify from the mailbox, not from the drafts index: `FETCH n (RFC822.SIZE BODYSTRUCTURE)` shows the
  attachment as `("APPLICATION" "PDF" ... ("ATTACHMENT" ("FILENAME" "x.pdf")))` — that one line proves
  the PDF really rode along, which is what rule 0a-2 cares about.

## Staging pitfalls hit live (2026-10-21, mail.com engagement — first real finding of the run)

- **`final-deliverable.py` is a gate checker, not the final stager.** It passed the finding
  (1 REPORTABLE) but its built output was a rejected deliverable: the email body was the stub
  ("One finding, one report... impact not stated - refusal to write one is itself a reason to
  exclude"), the PDF was ~4KB (the 30KB screenshot could not actually be inside it), and the
  .eml carried only the PDF. Fix that shipped: `import` the module and call its `build_pdf`
  directly (`importlib.util.spec_from_file_location` on stage_finding_draft.py,
  `spec.loader.exec_module`), then assemble the .eml by hand with `EmailMessage` +
  `add_attachment` per file. Verify: PDF >20KB with `/Image` in the bytes, body has no banned
  words, 3 attachments, and `sha256(remote attachment) == sha256(local)` via
  `messages().attachments().get()`.
- **The banned-word check fires on vendor URLs.** mail.com's channel is
  `report@bugbounty.mail.com` — the substring `bounty` fails the rule-0c validator. Keep the
  channel out of the body (it is already in `To:` and in the PDF); the body just says "your
  responsible disclosure programme".
- **`drafts.update` on a draft the operator already SENT fails** with `Message not a draft`.
  When a finding ships and you later produce an expanded version, do NOT update in place —
  check `labelIds=['SENT']` first, then stage a NEW draft with `Re:`/`In-Reply-To`/`References`
  threading on the original Message-ID so it lands in the same thread as a supplement.
- **The output redactor eats `TOKEN=*** ... | grep -oP ...)` one-liners** mid-command
  (leaves a stray `***` and a bash syntax error). For anything with a token/header literal,
  write the script to a file with `cat > x.py` + a quoted heredoc, or build it in Python.
- **A Gmail token that memory records as revoked may refresh fine.** The 2026-10-20 entry said
  invalid_grant; on 2026-10-21 the same file refreshed successfully. Test the refresh before
  declaring the mailbox unreachable, and correct the memory entry when it works again.

## Why This Rule Exists
User was frustrated that:
- Reports were text-only, not clickable files
- Reports were sent as text output, not actual file attachments
- Reports lacked screenshots/POC evidence
- Files were saved but user didn't know where to find them
- Reports used wrong format (not skill-based)

---
