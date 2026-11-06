---
name: evidence-hygiene
description: "Evidence-capture and PoC-redaction discipline for bug-bounty submissions: cookie redaction protocol (which fields to mask, Preview annotation / Burp panel hiding / DevTools workflow), PII black-bar discipline (what to mask in other-user data — names, emails, phones, faces — vs what is safe to leave — usernames, trace IDs, request bodies), HAR file sanitization (jq filters for Cookie/Set-Cookie/Authorization headers), Burp Repeater/Intruder screenshot hygiene (hide request body, show only Results table for rate-limit attacks), Chrome DevTools Console PoC patterns (credentials include so cookies are not echoed, labeled console.log), screenshot capture order, filename conventions, post-submission rotation hygiene. Use BEFORE any PoC screenshot, BEFORE attaching a HAR, or whenever preparing evidence with session cookies or other-user PII. Pairs with bugcrowd-reporting and report-writing."
sources: community, operator_experience
---

# EVIDENCE HYGIENE — PoC Capture & Redaction Discipline

> Use this skill BEFORE capturing any screenshot, exporting any HAR, or attaching any evidence to a bug-bounty submission. It catches the most common evidence-hygiene mistakes that cause cookies to leak, PII to be shared without consent, or screenshots to be unsuitable for triage.

The core principle: **Bug-bounty evidence is meant to convince a triager. Anything beyond that — live cookies, real-user PII, internal trace IDs that aren't useful — should not be in the evidence.**

---

## 1. Three Categories of Sensitive Data

Every PoC artifact (screenshot, HAR, raw HTTP request, terminal transcript) potentially contains data that needs different treatment.

| Category | Examples | Treatment |
|---|---|---|
| **Your-account secrets** | Session cookies, OAuth tokens, refresh tokens, API keys | Always redact. Even in private bug-bounty platform attachments. Your account, your session — protect it. |
| **Other users' PII** | Real names, emails, phone numbers, addresses, profile photos, account IDs | Redact unless explicitly demonstrating cross-account impact. Even then, mask faces and minimize the data you display. |
| **Target-leaked secrets** | Keys/tokens/app IDs the *vendor or their customer* exposed to you (pre-auth config endpoints, JS bundles, public repos, misconfigured buckets) | Redact harder than your own — see §1.1. Policies often impose an explicit duty to delete all copies. |
| **Triager-useful metadata** | Trace IDs (`x-datadog-trace-id`), request IDs, server timestamps, your test account UID/email, GraphQL operation names, response shapes | **Leave visible** — these help the triager correlate to logs and reproduce. |
| **Test-account passwords (limited use)** | Throwaway passwords on a test account (e.g., `Testing@5678`) | Acceptable in screenshots if you rotate immediately after submission so the value shown is dead. Don't leave real-use passwords in evidence. |

### 1.1 Target-leaked secrets — the category people forget

Your own cookie has an exit: rotate it. Other users' PII has an exit: mask it. **A secret
the target leaked to you has no exit — you are now a custodian of it**, and most programs
say so in writing. Typical clause: *"if you inadvertently access sensitive information
(credentials, message content, personal information), you must immediately stop, report
the exposure, and permanently delete all copies"* — with the data forbidden from being
saved, stored, transferred, shared, or placed in public locations, sometimes with
**third-party / AI tools named explicitly**.

Practical protocol:

1. **In the report, prove possession without republishing.** Show the key name plus a
   truncated prefix and a hash:
   ```
   googleDrivePickerConfig.devKey = "D9K5nAIr…"   sha256:1f9c3ab2…
   ```
   The hash is verifiable by the vendor against their own value; the secret never leaves
   the report. Do NOT paste the raw value into the report body, a screenshot, or a chat.
2. **Never attach the raw dump.** If the finding is "this endpoint returns tenant
   configuration", the repro is one request and a redacted excerpt — not
   `settings_full/*.json` for every host you found.
3. **Least-data framing.** "This endpoint leaks the tenant config, including a
   third-party API key (redacted above)" beats "63 hosts leaked full configuration".
   Enumeration depth is what turns a valid finding into a policy problem, and it adds
   nothing to reproducibility.
4. **Watch for the two clauses in the policy**: (a) "all evidence must be contained within
   the report — do not host on external services"; (b) the third-party/AI-tool destination
   prohibition. If your workflow pipelines raw dumps through any external service or
   model, extract the minimum (field name + prefix + hash) BEFORE handing anything off.
5. **Delete the local copies** once the report is submitted/accepted — keep only the
   redacted artifact. The duty survives the payout.
6. **Do not "prove" a leaked third-party key by using it** against the third party's API
   beyond a bare validity call. Exercising it is unauthorised testing of a third party:
   outside scope, outside safe harbour, and a much bigger problem than the finding.
7. **Report the exposure even when the finding itself is Informative.** The duty to notify
   is separate from whether the program pays for it.

---

## 2. Cookie Redaction Protocol

### 2.1 What must be masked

The session cookie value is the highest-value secret in any PoC. Mask:

- The session cookie (`authn`, `session`, `sid`, `__Secure-id`, etc. — name varies per target)
- `csrf-token` if it's bound to your session
- `Authorization` headers (Bearer tokens, JWT)
- `Cookie` request header values for any session-bearing cookie
- `Set-Cookie` response header values for any session-bearing cookie

### 2.2 What's safe to leave visible

- Cloudflare cookies (`__cf_bm`, `_cfuvid`) — these are bot-management, not session-bearing
- Analytics cookies (`ajs_anonymous_id`, `_ga`)
- Trace correlation IDs (`x-datadog-trace-id`, `x-request-id`)
- Server / framework headers (`Server: cloudflare`, `X-Frame-Options`)
- Your test account email/UID (per BC_ALIAS alias section in `bugcrowd-reporting`)

### 2.3 Redaction methods (ranked by practicality)

**Method A — Don't capture the cookies in the first place** (preferred when possible)
- For DevTools Console PoCs: use `credentials: 'include'` so the browser sends cookies automatically. Console output won't echo the cookie. Screenshot the Console output, never the Network tab Headers panel.
- For Burp Repeater PoCs: drag the bottom request/response panel divider DOWN to hide the request body before screenshotting. Capture only the Results table for Intruder runs.

**Method B — Black-bar in image editor** (when capture inevitably includes cookies)
- macOS: Open screenshot in Preview → Tools → Annotate → Rectangle → set fill color to black → drag rectangle over the cookie value → save
- Windows: Use Snip & Sketch's annotation tools or any image editor (Paint.NET, etc.)
- Burp itself: in Burp's Proxy → Match and Replace, you can pre-emptively redact cookie values to placeholder strings before screenshotting

**Method C — Find/replace in raw text** (for HAR files, terminal transcripts)
- See §4 for the jq commands

### 2.4 Pre-screenshot checklist

Before clicking Capture:

```
[ ] Network tab Headers panel is collapsed or out of frame
[ ] Burp's Request panel is hidden behind the divider drag
[ ] No "Copy as cURL" output is visible on screen
[ ] DevTools Application → Storage → Cookies tab is closed
[ ] Browser URL bar doesn't show a session token in query string (rare but possible)
```

After capturing:

```
[ ] Open the screenshot at full resolution before saving
[ ] Search for the session cookie name substring in any visible text — if present, redact
[ ] Search for the literal first 6 chars of your cookie value — if present, redact
[ ] Compare to the previous PoC screenshot in the same engagement — same redaction discipline
```

---

## 3. PII Black-Bar Protocol

When a PoC necessarily exposes another user's data (e.g., demonstrating IDOR by showing the victim's email in an attacker-session response), redact the actual PII even in private attachments.

### 3.1 What to mask (other-user data)

- First name, last name (full or partial)
- Email address (mask the local part; can leave domain if non-identifying)
- Phone number (mask the last 7 digits, optionally leave country code)
- Physical address (mask everything below city)
- Date of birth (mask the year, optionally the month)
- Government IDs (SSN, passport — mask everything)
- Profile photos / face images (black-bar the face entirely)
- Account IDs that the user could correlate to public profiles

### 3.2 What to leave visible (proves the bug, not the user)

- The fact that the field was returned (the JSON key name)
- The shape / type of the field (`"first_name": "<REDACTED>"`)
- Your own (attacker session's) UID / email — this proves cross-account
- The endpoint URL and request method
- The trace ID

### 3.3 Worked example — IDOR PoC body

**Bad (leaks victim's full PII):**
```json
{"data":{"contact":{"first_name":"Nadene","last_name":"Afton","email":"nadene.afton@example.com","phone":"+1-555-867-5309"}}}
```

**Good (proves the bug, masks the PII):**
```json
{"data":{"contact":{"first_name":"<REDACTED — real first name>","last_name":"<REDACTED — real last name>","email":"<REDACTED>@example.com","phone":"<REDACTED>"}}}
```

In screenshot form, black-bar each value with a rectangle annotation labeled "REAL PII REDACTED" if there's space.

### 3.4 In the report body

Reference the redaction explicitly:

```markdown
## Proof of Concept

The screenshot below demonstrates the IDOR. The attacker session (uid 12345678) successfully retrieves the victim's profile data (uid 99887766). **Real PII fields in the response are masked with black rectangles to limit unauthorized exposure of victim data, per responsible-disclosure hygiene.** The unredacted response is available privately on request.
```

This signals the triager that you're disciplined and gives them a clear path to the unredacted version if they need it for verification.

---

## 4. HAR File Sanitization

HAR (HTTP Archive) files are JSON dumps of network traffic with full request/response bodies and headers. They include cookies, auth tokens, and any PII that was in transit.

### 4.1 Generate the HAR

Chrome DevTools → Network tab → right-click anywhere in the request list → "Save all as HAR with content"

### 4.2 Sanitize before attaching

Use `jq` to strip sensitive headers. Save this as a shell function or one-liner you can re-use:

```bash
sanitize_har() {
  local input="$1"
  local output="${1%.har}.sanitized.har"

  jq '
    .log.entries |= map(
      (.request.headers |= map(
        if .name | ascii_downcase | IN("cookie", "authorization", "x-csrf-token") then .value = "<REDACTED>" else . end
      )) |
      (.response.headers |= map(
        if .name | ascii_downcase | IN("set-cookie") then .value = "<REDACTED>" else . end
      )) |
      (.request.cookies |= map(.value = "<REDACTED>")) |
      (.response.cookies |= map(.value = "<REDACTED>"))
    )
  ' "$input" > "$output"

  echo "Sanitized: $output"
}
```

Usage:

```bash
sanitize_har /path/to/exported.har
# Output: /path/to/exported.sanitized.har
```

### 4.3 Verify before attaching

> Self-test state hygiene — logging every mutation of YOUR OWN test identity, reverting it, cleaning
> up throwaway members, and not chasing "corrupted" values that are only masked in tool output:
> see `references/self-test-state-hygiene.md`.

```bash
# Check that no Cookie or Authorization values are leaking
grep -i 'authn\|"cookie"\|authorization' /path/to/exported.sanitized.har | head -20
```

If you see your real cookie value in the output, the sanitization missed something — fix the jq filter for that specific field name.

### 4.4 Remove other-user PII (if applicable)

If the HAR captured cross-account data (e.g., during an IDOR demo), additionally strip the response body fields that contain victim PII. Add to the jq filter:

```jq
(.response.content.text |= (
  if . then 
    (fromjson? // .) | tostring | gsub("real.first.name.example"; "<REDACTED>")
  else . end
))
```

Customize the gsub patterns to your specific captured data.

---

## 5. Burp Suite Screenshot Hygiene

### 5.1 Repeater (single request demo)

1. In the Repeater request panel, the Cookie header is on its own line — drag the panel divider DOWN to hide everything below the request line / target line
2. Or: temporarily delete the Cookie header text from the Repeater pane (it doesn't affect the original captured request) before screenshotting, then restore
3. Capture only the response panel (right side) showing the JSON / HTML response that demonstrates the bug

### 5.2 Intruder Results table (rate-limit / brute-force demos)

The Results window is the strongest evidence for rate-limit findings. To capture cleanly:

1. After the attack finishes, drag the horizontal divider between the Results table and the Request/Response panels DOWN, until only the Results table is visible
2. Screenshot only the columns: `Request#`, `Payload`, `Status code`, `Response received`, `Length`
3. Don't include the Request / Response sub-panels — they contain the cookie

### 5.3 Proxy HTTP history (capture demo)

Almost never the right screenshot — it shows entire request/response pairs with cookies. Use Repeater for demos instead.

### 5.4 Scanner findings (if applicable)

The Scanner tab's Issues panel is generally safe to screenshot — it shows finding summaries without the underlying request bodies. Click into a specific finding before screenshotting only if you've redacted its evidence first.

---

## 6. Chrome DevTools Console PoC Patterns

### 6.1 The clean-PoC pattern

```js
fetch('/api/endpoint', {
  method: 'POST',
  headers: {'content-type': 'application/json'},
  credentials: 'include',  // sends cookies automatically — they won't appear in your code
  body: JSON.stringify({ /* your payload */ })
}).then(r => r.json()).then(j => console.log("LABEL:", JSON.stringify(j)))
```

Why this is clean:
- `credentials: 'include'` means the browser sends cookies. Your code never references them. They never appear in screenshots.
- `console.log("LABEL:", ...)` produces a labeled output line you can search for in the screenshot
- `JSON.stringify(j)` formats the response on a single line — easier to crop tightly

### 6.2 Multi-step PoCs (clear console between calls)

For a 4-step PoC (verify before / change / verify after / revert), clear the console between calls so each screenshot only shows ONE call and ONE response:

- Mac: `Cmd+K`
- Windows / Linux: `Ctrl+L`

Take the screenshot immediately after the response prints — don't wait for unrelated framework warnings to appear.

### 6.3 Long responses (truncate for screenshot)

If the response body is too long for a clean screenshot, log a summary instead:

```js
fetch('/api/endpoint', { /* ... */ })
  .then(r => r.json())
  .then(j => {
    console.log("RESPONSE SHAPE:", Object.keys(j.data || {}));
    console.log("CRITICAL FIELD:", j.data?.victim_id, j.data?.email);
    // (Don't dump the full j — your screenshot becomes unreadable)
  })
```

### 6.4 Allow-pasting reminder

Chrome blocks paste into DevTools Console as anti-self-XSS protection. Type `allow pasting` (literal phrase) once at the start of each session. Do this BEFORE you take any "running PoC" screenshot — otherwise the warning text appears in the screenshot.

---

## 7. Screenshot Capture Order Discipline

### 7.1 The 5-step PoC pattern (for state-change findings)

For findings like "password change without step-up," the canonical 5-screenshot pattern is:

1. **Pre-state verification** — `verify_password("current") → true`. Proves you knew the starting state.
2. **The bug itself** — `update_password(...)` succeeds without step-up. THE most important screenshot.
3. **Post-state verification (negative)** — `verify_password("old") → false`. Proves the change took effect.
4. **Post-state verification (positive)** — `verify_password("new") → true`. Proves the new credential is active.
5. **Out-of-band side effects** — inbox screenshot showing whether a notification email arrived. Proves whether passive defense exists.

### 7.2 Filename conventions

Numbered, descriptive, hyphen-separated:

```
{finding-#}-step{step-#}-{description}.png

Examples:
04-step1-verify-true-before.png
04-step2-update-password-no-stepup.png
04-step3-verify-false-after.png
04-step4-verify-true-new-pw.png
04-step5-inbox-notification-check.png
```

In the report body, reference each by filename:

```markdown
- **Screenshot 1 (`04-step1-verify-true-before.png`)** — verify_password returns true with the current password.
- **Screenshot 2 (`04-step2-update-password-no-stepup.png`)** — update_password returns User with no StepUpRequiredError. THIS IS THE BUG.
- **Screenshot 3 (`04-step3-verify-false-after.png`)** — verify_password with old password returns false.
- **Screenshot 4 (`04-step4-verify-true-new-pw.png`)** — verify_password with new password returns true.
- **Screenshot 5 (`04-step5-inbox-notification-check.png`)** — inbox showing whether out-of-band notification was sent.
```

### 7.3 Capture timing

- Take all screenshots in one sitting, not across multiple sessions. Mid-session inconsistencies (different browser sizes, different cookie values) are confusing for the triager.
- Don't reload pages between screenshots if avoidable. Reloads regenerate cookies and may invalidate prior captures.

---

## 8. Post-Submission Hygiene

After clicking Submit on the bug-bounty platform:

### 8.1 Rotate the test account credentials

```
1. Log out of the target
2. Log back in (this rotates the session cookie — any cookie shown in your screenshots is now dead)
3. Change the password to a fresh value not used elsewhere (any password shown in your screenshots is now dead)
```

### 8.2 Save the unredacted artifacts privately

Keep your unredacted HARs / screenshots in a local folder accessible only to you. The triager may ask for the unredacted version during verification. **Never share unredacted artifacts via email — use the platform's private attachment system on the existing submission thread.**

### 8.3 Don't post about the finding publicly

Most platforms' confidentiality applies to BOTH unresolved and resolved issues. Don't tweet, blog, or discuss the finding in any forum until the program explicitly says you can.

### 8.4 Audit your local artifacts

Quarterly, sweep your `~/security-research/` and `~/Downloads/` for stale HARs / screenshots from old engagements. Either move them to a properly-encrypted archive or delete them. Bug-bounty engagement artifacts are sensitive — they accumulate fast and become a liability.

---

## 9. Pairing with Other Skills

| For this question / task | Use this skill |
|---|---|
| "Should I report this finding at all?" | `triage-validation` |
| "What does the program's policy require of my evidence?" | `triage-validation` Gate 4 + this skill §1.1 |
| "The target leaked third-party keys/config to me — what do I ship?" | This skill §1.1 (redact to prefix + SHA-256, delete copies) |
| "What's the report body template?" | `report-writing` |
| "What VRT / severity / OOS rebuttal for Bugcrowd?" | `bugcrowd-reporting` |
| "How do I redact / sanitize this evidence?" | This skill (`evidence-hygiene`) |
| "Will the programme bounce this on policy grounds?" | This skill §10 + `references/self-hosted-program-policy-check.md` |
| "Is any host I plan to name actually out of scope?" | `scripts/host_scope_check.py` (flags third-party CNAME aliases) |
| "What CVSS should I put in the report?" | This skill §10.3 (compute the version the policy names) |
| "How do I demonstrate the bug actually fires?" | `security-arsenal` |
| "Where are the recon probes for this asset class?" | `offensive-osint` |

---

## 10. Pre-submission policy compliance sweep

Run this BEFORE you polish formatting — the policy's clock may already be running, and
three of these checks change the *content* of the report, not its presentation.

1. **Deadline first.** Self-hosted programmes often clock the duty from *discovery*, e.g.
   *"vulnerabilities affecting live assets must be reported within 72 hours of discovery.
   Withholding a known vulnerability — to stockpile it, time its submission, or seek
   leverage — is a material violation."* Note the timestamp when you first *confirm* the
   finding and check that clock before spending a day on layout. A valid finding filed late
   is a policy problem.
2. **Required identifiers.** Policies mandate fields nobody volunteers: the researcher
   traffic header value (`X-Bug-Bounty: <email>` — must match your single programme
   identity) AND the **source IP(s)** used during testing. A technically perfect report can
   still be rejected for omitting these. Capture them at test time; you cannot reconstruct
   the egress IP later.
3. **The CVSS version the policy demands.** "Use the latest published CVSS version" is not
   CVSS 3.1. Compute 4.0 for anything you propose, base metrics only (policies forbid
   temporal/environmental modifiers):
   ```bash
   pip install cvss
   python -c "from cvss import CVSS4; c=CVSS4('CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N'); print(c.base_score, c.severities()[0])"
   # 6.9 Medium  — the identical finding scores 5.3 on CVSS 3.1; the version changes the tier
   ```
   A wrong-version score is a free credibility hit and a common stated basis for downgrade
   (which you then have to appeal).
4. **Verify every host you NAME resolves to the target.** Policies commonly exclude *"any
   domain that is a CNAME alias for a third-party system, or proxied through a CDN directly
   to a third-party platform"* — naming or testing one is a scope violation, not a bonus.
   Run `scripts/host_scope_check.py` over your host list and drop third-party aliases
   (CloudFront, Zendesk, vendor-specific SaaS like `api-us1.chd01.com`, external load
   balancers) before writing. First-party DNS (target → target, including a customer-looking
   name pointing at the vendor) is fine.
5. **Disclose incidental scope slips proactively, in one line.** If a broad subdomain sweep
   sent a handful of harmless GETs to hosts that turned out to be third-party aliases, say
   so: *"a small number of hosts which turned out to be third-party aliases received a
   handful of harmless GETs — 403/404, nothing retrieved — and I excluded them."* Safe
   harbour typically covers *accidental, good-faith* violations; concealment is what converts
   a slip into misconduct. Then never touch those hosts again.
6. **Consult the ineligible list BEFORE submitting**, not after the $0 verdict. These
   programmes enumerate borderline classes ("most rate-limiting issues", "software version
   disclosure / enumeration without demonstrated PII", "CSV injection", "missing security
   headers", "logout CSRF", "open redirects without impact") that close as Informative.
   If your finding sits on one of those lines, check whether the programme's
   **accepted-classes / CWE table** also contains it — an enumerated accepted class is your
   argument, and quoting their own table beats asserting severity. Watch for the internal
   contradiction (accepted `CWE-307 missing login rate limiting` vs "most rate-limiting
   issues are Informative"): the fix for that is not louder claims but framing the issue as
   *the control being disabled product-wide* with the config value as proof.
7. **Know the appeal envelope.** Typically once per report, inside a fixed window (e.g. 30
   days), on new technical evidence only — never "I believe it deserves more". Park your
   strongest unused evidence (a negative control, a second bypass path) for that window
   rather than re-filing the same report as a new submission, which is a violation.

Worked example with real numbers (payout table, ineligible list, the CWE-table
contradiction, appeal windows): `references/self-hosted-program-policy-check.md`.

---

## 11. Verify the RESULT, not the shell exit code

A finding that comes out of a one-liner must be confirmed from the actual OUTPUT, never from the
command's exit status — the two diverge constantly and the divergence manufactures false positives.

Classic trap seen live this session:
```bash
grep -o '<b>BOLD</b>' page.html | head -3 && echo "RAW TAG PRESENT"   # ALWAYS prints
```
A pipeline's exit status is the LAST command's (`head` → 0 even when `grep` matched nothing), so
the `&&` branch fires on an empty result. That nearly produced a fabricated "stored XSS / HTML
injection" report — the page in fact stripped the tags (`<div>Bugcrowd QA marker BOLD END</div>`).

Rules:
- Never chain a finding-claiming `&& echo` off a pipeline. Capture and test explicitly:
  `n=$(grep -c PATTERN file); [ "$n" -gt 0 ] && echo present`.
- Prefer `grep -c` / `grep -q` / explicit count compare over exit-status chaining.
- **Presence in source ≠ rendered ≠ executes.** Finding the payload string in the HTML does not
  prove the sink is unescaped, let alone that it runs. Confirm the sink (read the rendered DOM /
  the actual response field) before claiming any injection.
- Empty file / "0 findings" / blank screenshot is more often a SILENT tool failure than a clean
  target. Re-run with a positive control before concluding "not vulnerable".
- Same discipline for screenshots: a "successful" capture can be blank or a WAF page. Check it
  (non-uniform pixels; dump the DOM) before attaching it as PoC evidence — a blank screenshot in a
  report is worse than no screenshot.

## 12. On-chain PoC redaction (web3)

A contract PoC leaks secrets in a different shape than a web PoC: not cookies, but
**keys, RPC credentials, and other people's funds**. The same three rules apply —
mask what authenticates, never touch what isn't yours, verify the artifact.

### 12.1 What must be masked in an on-chain PoC

| Secret | Where it hides | Mask how |
|---|---|---|
| **Private key / mnemonic** | `PRIVATE_KEY=0xabc…` in `.env`, `foundry.toml`, the test file, a `vm.sign` helper | `PRIVATE_KEY=[REDACTED — test key, throwaway]`. If the key controls *any* funded account, rotate it before publishing, then redact. |
| **RPC endpoint with an API key** | `--fork-url https://eth-mainnet.g.alchemy.com/v2/<KEY>`, `https://mainnet.infura.io/v3/<KEY>` | `--fork-url https://eth-mainnet.g.alchemy.com/v2/[REDACTED]`. Say which provider, not which key. |
| **Explorer / submission API key** | `ETHERSCAN_API_KEY`, `--verify` flags, `cast` calls | redact; the reader does not need it to replay a fork test |
| **Victim addresses with PII linkage** | a real user's address + their ENS/email from an off-chain join | keep the address if it is **necessary to the proof**; drop the off-chain identity. On-chain addresses are public, but the *linkage* is not yours to publish. |
| **Other users' balances, positions, or tx history** | a fork trace printing 50 accounts | print **only** the attacker and the one victim the proof needs. Never dump a holder list. |
| **Signed payloads you captured from prod** | a real signature in a replay PoC | regenerate the signature in-test with `vm.sign` and a throwaway key. A production signature in a report is a live credential. |
| **Node/infra hostnames** | `--fork-url http://internal-rpc.corp:8545` | keep the scheme, redact the host; say "internal RPC" |

### 12.2 What's safe to leave visible

- The target contract address (it is the subject of the report)
- The block number / fork block used — **required** for reproducibility, and it is
  public data
- Chain ID, gas numbers, revert reasons
- Your own throwaway attacker address
- Function selectors and calldata
- The test output (`forge test -vvvv` traces) after the above is masked

### 12.3 Redaction methods, ranked

**Method A — use a deterministic test key, never a real one** (preferred)
```solidity
// in the test, not in .env
uint256 constant ATTACKER_PK = 0xA11CE;          // anvil key #0, publicly known
address constant ATTACKER   = vm.addr(ATTACKER_PK);
```
Anvil's default keys are **published** — using them means there is nothing to redact,
and the PoC stays byte-for-byte replayable. This is the web3 equivalent of "don't
capture the cookie in the first place".

**Method B — environment variable, redacted in the paste**
```bash
forge test --fork-url "$FORK_RPC" --match-test test_exploit -vvvv
# report shows: forge test --fork-url "$FORK_RPC" --match-test test_exploit -vvvv
# + a line: "FORK_RPC = any mainnet archive RPC; block 21_000_000"
```

**Method C — black-bar the trace**
Keep the `-vvvv` trace (it is the proof) but delete the lines that print your key or
RPC. Deleting lines from a trace is acceptable **only** if you say so —
*"trace trimmed: 3 lines containing the RPC credential removed"*. Silently editing a
trace is fabrication.

### 12.4 Verify the artifact, not the intent

- **Grep the final PDF/body** for `0x[0-9a-f]{64}` (a 32-byte private key) and for
  `alchemy|infura|quicknode|/v2/|/v3/` before sending. One hit = do not send.
- **Replay the published command** in a fresh clone. If it only runs with a secret
  you redacted, the PoC is not reproducible — say what the reader must supply
  ("any archive RPC at block N") instead of leaving a hole.
- **A redacted key that still controls a funded account is a leak with extra
  steps.** Rotate first; redaction is not a substitute for rotation.
- **Do not publish a fork URL that costs you money per request.** A public RPC or
  the reader's own endpoint is the right instruction.

### 12.5 Pairing

- The per-class **proof bar** for the web3 classes lives in
  `report-gotchas/references/class-gotchas.md` (reentrancy, on-chain access control,
  oracle, signature replay, vault accounting, AMM, restaking, intent).
- The **economic gate** (attacker P&L after gas, cost-vs-extraction) belongs in the
  report body, not the appendix — a masked PoC that omits it reads as a
  theoretical finding.

## Notes on usage

This skill is meant to be loaded together with `report-writing` and (for Bugcrowd) `bugcrowd-reporting` when preparing a submission. It does NOT cover:

- **What** to capture (that's `triage-validation` and `report-writing`'s job — they tell you what evidence is required for the report to be accepted)
- **How** to demonstrate exploitation (that's `security-arsenal`'s job — payloads to send)
- **Where** to find the assets (that's `offensive-osint`'s job — recon)

This skill covers ONLY the redaction / sanitization / hygiene layer that sits between "I have evidence" and "I'm attaching it to the platform."

---

## Related Skills & Chains

- **`report-writing`** — When evidence is redacted and ready for the report body. Workflow primitive: after redaction passes the pre-screenshot checklist, hand off to `report-writing` for the platform-specific report template (H1 / Bugcrowd / Intigriti / Immunefi).
- **`bugcrowd-reporting`** — When the redacted evidence is destined for Bugcrowd specifically. Workflow primitive: redacted screenshots + sanitized HARs become attachments referenced in `bugcrowd-reporting`'s VRT-mapped submission body.
- **`triage-validation`** — When deciding which evidence is required at all. Workflow primitive: `triage-validation` says "you need a 5-screenshot PoC for password-change-without-step-up"; this skill says "here's how to capture and redact those 5 screenshots cleanly."
- **`security-arsenal`** — When the payload that produced the evidence is being documented. Workflow primitive: the payload (from `security-arsenal`) goes in the report verbatim; its output / response (handled by this skill) gets cookie / PII redacted before screenshotting.
- **`bb-methodology`** — When Phase 5 (Validate & Report) needs evidence captured. Workflow primitive: Phase 5's evidence-capture step routes through this skill before the report is drafted.

---

## ➕ Additive companion — `autonomous-exploration` (optional sidecar)

> Purely additive. Nothing above changes. These tools only CREATE files under
> `<target_dir>/_graph`, `/_plan`, `/_traces`, `/_traffic`; they never modify pipeline scripts,
> and the 0A–0F pipeline runs identically with or without them.

- `dualgraph.py` — asset graph + exploration graph + anchors (SQLite); coverage/lineage queries
- `chainplan.py` — dependency-gated step ledger; `next` = the ONLY step you may dispatch now
- `tracestore.py` — cross-step trace exchange (reuse raw observations from other steps/subagents)
- `trafficrec.py` — on-demand mitmproxy recorder (automatic PoC transcript, port 8081)

Load skill **`autonomous-exploration`** when you need queryable coverage, a dependent multi-step
chain, or automatic PoC capture. Optional — a normal run does not require it.

> Evidence hook: `trafficrec.py` writes a faithful request/response transcript to
> `<target>/_traffic/traffic.db`, so a PoC's raw exchange is captured automatically instead of
> hand-copied. Redaction rules above still apply before anything reaches a report.
