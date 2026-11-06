# Cloud-trial → admin console (no local install needed)

Alternative acquisition route to Phase 4-6 when the vendor runs a **cloud-managed
edition** of the product you must attack. Instead of installing the package
locally, provision *your own* trial instance on the vendor's infrastructure and
take admin on it. The instance is yours (policy usually says so explicitly),
fully licensed, and it exposes the same API/console the on-prem product does.

Verified on Genians (Genian NAC 5.0 Cloud) 2026-10-27. Vendor policy even
instructs researchers to create tests this way and delete the servers afterwards
("If you have created one or more servers in CSM for bug bounty testing, please
delete the servers after the bug bounty test is complete").

## 0. Prefer this route when

- The program has its own account portal + trial/demo provisioning.
- On-prem install needs licensing you cannot obtain (IP-bound, phone-verified).
- The console you need is the **product's own** UI/API, not a marketing site.

Cost: ~15 minutes versus hours of repo archaeology. Do this first; fall back to
`vendor-product-lab` Phase 2-4 (package repo) only if no cloud edition exists.

## 1. Provision through the account portal, not the marketing form

Two planes exist and they differ:

| Plane | Purpose | Gotcha |
|---|---|---|
| account portal (`my.<vendor>.com`) | the customer account that owns licenses | registration may require a **bug-bounty-specific** register URL — read the policy, it is usually a `?registertype=bugbounty` style param, and registering through the normal form can disqualify the reward |
| **demo/staging portal** (`my.demo.<vendor>.co.kr`) | test tenant with working provisioning | far more permissive; opens the same product APIs |

Register with an address whose inbox you actually control (operator plus-alias).
Then find the provisioning page - it is usually linked from the account
dashboard ("Create trial", "체험 환경 생성하기", "Start free trial") and posts to
the portal's own AJAX endpoint, not to an API you can guess.

## 2. Read the provisioning contract out of the page, then replay it

The trial form is a single AJAX call with a server-issued CSRF token. Capture it
from the page source instead of driving the browser:

```bash
curl -sL "https://<portal>/try-cloud-gsp" -H "Cookie: <session>" -o try.html
grep -oE "action'\s*:\s*'[a-z_]+'" try.html            # gn_async_create_csrf_token, gn_cloud_start_subscribe
grep -oE "data.append\('[a-zA-Z_]+'" try.html           # every posted field name
```

Replay order (the token is **single-use**, mint one per request):

```
GET  /wp-admin/admin-ajax.php?action=<create_csrf_token>       -> {"csrf_token":"..."}
POST /wp-admin/admin-ajax.php                                  -> action=<start_subscribe>&...&csrf_token=<tok>
     Content-Type: multipart/form-data   (SSL cert/key uploads ride in the same body)
```

**Field-value trap.** `<option value="nac" value2="5">Genian NAC 5.0</option>`
means *submit* `nac`; the numeric `5` is only a lookup key for a **different**
action (`get_plans?product=5`). Sending the numeric id to the provisioning action
returns a generic "invalid access" that looks like an authorization rejection but
is really a bad enum. Read the `value` attribute, not the label or `value2`.

Useful read-only side calls on the same endpoint (no state change, good recon,
cheap to test for auth gaps): `get_plans?product=<n>` leaks the whole product/plan
catalogue incl. `trial_period`, `plan_code`, addons, prices; `get_branches`,
`get_regions` leak build channels and cluster names.

## 3. What provisioning actually gives you - and what it does not

After `{"result":true,"message":"success"}`:

- A **site hostname** `<sitename>.demo.<vendor>.co.kr` + a real license row on the
  account page: product, edition, node count, status `Trial`, start/end dates.
- **Admin credentials for the product console** = the email + password you typed
  into the provisioning form. Not a separate invite mail.
- The product's own console under that host, e.g.
  `/` -> 302 -> `/mc2/` -> `/mc2/faces/adminlogin.xhtml`.

**Client-supplied license fields are ignored.** Requesting `nodes=10` produced a
**300**-node license (the plan default); requesting `validityperiod=3650` produced
**30 days**. That is the *correct* behaviour - record it as a verified negative,
not as a finding. To claim a limit bypass you must show the requested value
persisting, not merely that the field is accepted.

**Trial quota is per ACCOUNT and global across products** - first trial succeeds,
every later one (including a different product) returns "maximum number of trial
versions exceeded (1)". Plan the whole engagement around a single instance; do
not burn it on a smoke test.

## 4. Getting into a JSF / PrimeFaces appliance console

The console is typically JSF + PrimeFaces, which breaks ordinary Playwright flows.

**Login chain (Genian NAC shape):**

1. `/<ctx>/faces/adminlogin.xhtml` - `form1:userId`, `form1:passwd`, `form1:dologin`.
2. Password accepted -> the page **re-renders in place** and shows
   "Please enter your Authentication Code." The OTP field is **not in the DOM**:
   it lives in a dialog iframe `/<ctx>/faces/otpAuthDlg.xhtml?init=1&popupmode=iframe`.
   Walk `page.frames` for `otpAuthDlg` and fill `form1:fldCheckAuthNumber`, click
   `form1:actionBtn`. The same TOTP secret the account portal uses can be
   re-enrolled here.
3. First login lands on `faces/regist/userAgreement.xhtml` (EULA) -> pick the
   agree radio -> `form1:btnConfirm` -> `faces/regist/initialSetup.xhtml` ->
   `form1:btnConfirm` -> `faces/mainFrame.xhtml`.

Success marker: page title `<sitename> - Management Console`, not a redirect away.

**Do not report the OTP stage as "MFA required, blocked"** - check whether the
console accepts the *same* TOTP seed and whether the password-only response
already differs (a changed error string = credentials valid, factor pending).

**PrimeFaces mechanics that cost time:**

- Selector escaping: an element `id="form1:userId"` needs `#form1\\:userId` in a
  Python string (`page.fill("#form1\\:userId", ...)`).
- `wait_until="networkidle"` **never settles** (the console polls). Use
  `domcontentloaded` + a fixed settle wait.
- Clicking a button behind a dialog throws
  `subtree intercepts pointer events` - the OTP iframe and the license-warning
  modal both do this. Work inside the frame, or `page.evaluate` a direct click.
- Tab panels (`ui-tabs-panel ui-helper-hidden`) and wizards keep later steps
  `disabled` until an earlier step posts; a tab whose panel is empty in the static
  HTML is loaded asynchronously - drive it with real clicks, not `page.content()`.
- Resource endpoints `/faces/javax.faces.resource/<name>?ln=<lib>` serve the
  product's own JS - grepping them (`adminlogin.js`, `app.js`, `pages/*.js`)
  yields the endpoint names and dialog paths the UI never shows in the DOM.

Then map the REST plane: `bash<br>/<ctx>/rest/` returns an HTML error shell when a
path does not exist (so a `200` is not evidence of a live endpoint - check
`content-type`/body), `/rest/information/version/<product>` gives the build id,
`/rest/sessions/current` leaks the full permission map.

## 5. Edition/licence gates: UI-disabled is not server-enforced - prove it

A page gated "requires Enterprise edition or later" still rendered fully on a
Professional licence: ~77 form inputs, 17 of them `disabled`.

Test in this order, and stop at the first one that shows persistence:

1. `page.fill()` on the gated field -> if it times out with *element is not
   enabled*, the gate is client-side only so far.
2. Force-enable via JS, then click Update -> may still be blocked by an overlay.
3. Force-enable **and** `page.evaluate(() => el.click())`, wait, then
   **reload and re-read the value**.

Verdict on Genian NAC: value did **not** persist across reload -> the server
rejects writes to edition-gated settings, so the gate is real and there is no
finding. Only a persisted change is a licence-bypass finding. Two failed attempts
were not enough to conclude anything; the reload check is what decided it.

Corollary negative worth recording: values of disabled fields are still readable
from the DOM (`input.disabled` + `value`). That is information exposure of
minimal attack value and is excluded by most policies' "extremely minimal" clause.

## 6. One-time credentials need a control BEFORE the variants

Provisioning/SSO tokens are single-use, so a variant matrix is worthless unless
the control is measured on an equal footing:

- A baseline assertion replay failed on the *second* submit while the first
  succeeded -> the credential was consumed, not rejected. Nothing to conclude.
- Re-capture a **fresh** credential per variant (intercept the request and
  `route.fulfill` so the browser never consumes it), fire the control, then fire
  one variant, discard, repeat.

Same discipline as `vendor-product-lab` Phase 7: a "gate passed" is a lead, and a
control that itself fails means the matrix is uninterpretable.

## 7. Clean up

The policy usually requires deleting test servers after the engagement. Note the
sitename/licence ids you created, delete the servers, and record the deletion in
the engagement log next to the credentials.
