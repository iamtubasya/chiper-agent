# RBAC escalation matrix on an appliance console — worked case

Source: Genian NAC 5.0.92 (`NAC-CLOUD-R-154085-5.0.92.1022`), own provisioned instance, 2026-10.
Outcome: **clean negative** — RBAC enforced server-side. The value of this file is the *method* and the
evidence shape that made the negative defensible, plus the JSF/PrimeFaces control quirks that cost time.

---

## 0. Preconditions

You need superadmin on an instance you provisioned yourself. Then build the low-priv identity **through
the product**, so the account is a real one the server itself created (not a hand-edited row).

Two facts worth capturing at this stage because they are cheap and reusable:
- The product version, from the product's own API (`GET /rest/information/version/nac` →
  `{"value":"NAC-CLOUD-R-154085-5.0.92.1022"}`). Check it against the vendor's advisory page **before**
  chasing known CVEs: rev 154085 was above every published fix threshold (150340 / 148665 / 148817), so
  those CVEs were already closed on this build. That single request saved the whole CVE branch.
- The permission vocabulary, from the same class of endpoint (see step 2).

---

## 1. Create the read-only admin

Entry point is not the obvious one. The Tasks menu rendered "Add User" but clicking it did nothing
visible — it opens an iframe:

```
#userWizardPop  ->  /faces/user/userWizard.xhtml?cmd=create&selectedTab=userSelectTab
```

Drive that URL directly. Tab structure is PrimeFaces `ui-tabs`:

```
form1:tabView1 — Select(0) | General(1) | Administrator(2)
  tabLevel0 radios : form1:tabView1:rdoNewUser (value 0, "Add New User")
                     form1:tabView1:rdoExistUser (value 1, "Create with existing user base")
  btnPre / btnNext / btnConfirm(Save) / Cancel
```

Tab 0 loads **empty on a cold GET** — the radio panel only materialises when the wizard is opened with
`?cmd=create&selectedTab=userSelectTab`. That is why "the wizard has no fields" is a false reading.

Field contract on tab General (fill these, nothing else needed):

| field | note |
|---|---|
| `form1:tabView1:fldId` | username |
| `form1:tabView1:fldName` | full name |
| `form1:tabView1:lbxAdminRole` | **the role** — options: `<Not Selected>`, `auditor`, `ipAppManager`, `superAdmin` |
| `form1:tabView1:lbxPurpose` / `lbxStatus` | default `USER` / `1` |
| `form1:tabView1:fldPasswd` / `fldConfirmPasswd` | password + confirm |
| `form1:tabView1:USER_EMAIL` | email |
| `form1:btnConfirm` | Save |

Ignore the `_VALIDCHECKSTRHIDDEN_*` / `_VALIDCHECKHIDDEN_*` pairs — server-side validation blobs, they
populate themselves.

Success signal is a redirect plus a toast string: `User has been registered successfully.`

---

## 2. Log in as the low-priv account — three gates, all solvable

| gate | exact behaviour | resolution |
|---|---|---|
| concurrent session | `An account is already in use by the device with IP <your-ip>` | check the hidden `form1:forceLogin` ("Disconnect all previous connections") — it exists but Playwright `check()` times out because it is styled away; `await el.click()` then verify `is_checked()` (a raw `el.click()` in `evaluate` toggles it twice and lands back on false) |
| IP dialog | iframe `/faces/allowIpDlg.xhtml`, "Allowable IP Settings" — Web Console IP1/IP2 | submit **empty** and it proceeds. Check the account's "Number of Auth IPs/MACs/Devices": if `0` there is no allow-list, so this is default-permissive, **not** a bypass — do not report it |
| 2FA | `/faces/signin/mfa.html` — "Enable two-step verification" vs **"Continue without two-step verification"** | the skip link exists for a fresh enrolment while the primary admin gets a mandatory OTP dialog. Record it as an anomaly; see §5 |

After these you land on `/faces/mainFrame.xhtml` with a visibly reduced sidebar (System + Preferences
absent) — that is the UI half of the control.

---

## 3. Permission-map diff (the test plan)

`GET /rest/sessions/current` returns the model:

```json
{"permLevelMap":{"fullControl":20,"edit":10,"addEdit":15,"readOnly":5,"noPerm":0},
 "adminPermMap":{"mgmt_user":20,"setup_config":20, ... 30 keys ...},
 "defaultPermMap":{...}}
```

Extract both maps and diff. Measured:

- superadmin → `20` on all 30 keys
- `auditor` → `5` on 26 keys, **`0`** on `setup_config`, `genian_mgmt`, `mgmt_ipmapp`

Those three `0`s are exactly the pages to test for a 302, and every `5` page is a read-should-work
control. Write the diff to a file — it is the coverage artifact.

---

## 4. Page matrix (status **and** size)

One request per page per role. Classify generic error pages by **size**, not status: this app answers
`200` with a fixed-size error document for unknown paths, so status alone lies.

**JSF generic-error fingerprints seen here:** `1109` (PrimeFaces system message), `1056`
(`/faces/error.xhtml`), `2655` (branded 404). Anything with one of those sizes is "no real page".

| page | permission | superadmin | auditor |
|---|---|---|---|
| `management/genianDevMgmt.xhtml` | `genian_mgmt`=0 | 200 / 61 052 | **302 → error.xhtml** |
| `setup/configMgmt.xhtml` | `setup_config`=0 | 200 / 71 773 | **302 → error.xhtml** |
| `management/softwareUpgrade.xhtml` | 0 | 200 / 26 746 | **302 → error.xhtml** |
| `policy/permMgmt.xhtml` | 5 | 200 / 28 316 | 200 / 28 083 |
| `policy/systemMgmt.xhtml` | 5 | 200 / 31 748 | 200 / 31 001 |
| `monitor/nodeMgmt.xhtml` | 5 | 200 / 142 783 | 200 / 142 785 |
| `user/userMgmt.xhtml` | 5 | 200 / 61 262 | 200 / 60 859 |
| `report/reportResult.xhtml` | 5 | 200 / 119 119 | 200 / **25 828** (trimmed = server-scoped) |

That table alone answers "is RBAC enforced?" — three `0`-pages redirected, `5`-pages served, one page
server-trimmed. Note it in the report verbatim; it is the evidence.

---

## 5. Write attempts as the low-priv role (all must fail)

- **Wizard re-entry**: `userWizard?cmd=create` → page **opens**, but `btnNext` is `disabled`. Force it:
  `b.disabled=false; b.removeAttribute('disabled'); b.click()` → server does **not** advance the tab.
  Create-as-readOnly refused.
- **Tasks menu**: `policy/permMgmt` Tasks menu still renders **Create** and **Delete** for the auditor,
  but every row checkbox is `disabled=True` and clicking Create opens no form. Menu strings are not
  permissions.
- **REST writes**: `POST/PUT/DELETE` on collection paths (`/rest/nac/nodes`, `/rest/nac/bpnotice`,
  `/rest/sessions/current`) return the generic error page for **both** roles — those paths simply do not
  accept the method. Do not read "admin also failed" as broken RBAC; it is the wrong test.

### Session-cookie confusion (cross the two cookies)

The app sets `JSESSIONID` + `mc.sessionId`. Authority test:

| cookie combination | `management/genianDevMgmt.xhtml` |
|---|---|
| admin pure | 200 |
| auditor pure | 302 |
| **auditor `JSESSIONID` + admin `mc.sessionId`** | **302 — no escalation** |
| admin `JSESSIONID` + auditor `mc.sessionId` | 200 (admin's own) |
| auditor without `mc.sessionId` | 302 |

Conclusion: authority is bound to `JSESSIONID`; `mc.sessionId` is inert. Clean negative — and this is
the check most sessions never run.

---

## 6. Two anomalies to record (not findings, but worth writing down)

1. **MFA optional at enrolment for new admin accounts.** A freshly created admin is offered
   "Continue without two-step verification", while the primary admin gets a mandatory OTP dialog
   (iframe `otpAuthDlg.xhtml`, field `form1:fldCheckAuthNumber`). If the instance has a
   "require MFA for all admins" policy this is a bypass. No such policy setting was found
   (no 2FA page under `setup/`), so per-user opt-in is the likely design → **unproven, do not report**.
   State the counter-evidence in the same paragraph so triage sees you checked.
2. **Allowable-IP dialog accepts an empty submit**, but with `Number of Auth IPs = 0` there is no
   control in place to defeat. Not a bypass.

---

## 7. Reporting shape for this class

```
Server-side RBAC is enforced on <build>:
  - 3 pages bound to perm=0 → 302 to error (superadmin 200)
  - 3 write attempts → no persistence / tab not advanced / row controls disabled
  - cookie-cross (low-priv JSESSIONID + admin secondary cookie) → no escalation
Sole observation: MFA is per-user opt-in at enrolment (no instance-wide requirement found),
so it is not a bypass. No finding raised.
```

That paragraph is the deliverable. It stops the next session re-running the same 30 requests and it is
what an honest "no finding" looks like after real work.
