# ASP.NET WebForms recon — abhieo.in worked case (2026-10-17)

Target: ABHIEO Fintech (India, NPCI-approved recharge/bill-pay/wallet). Stack: IIS 10 /
Windows Server / ASP.NET 4.0.30319, WebForms + AngularJS SPA shell + SmarterMail webmail
on the subdomains. Everything below is unauthenticated, single-request, human-paced.

## 1. ViewState MAC tamper test (do this before believing any deserialization lead)

A WebForms page with `__VIEWSTATE` is only a deserialization-RCE candidate when the MAC is
disabled. One request decides it:

1. GET the page, lift `__VIEWSTATE`, `__EVENTVALIDATION`, `__VIEWSTATEGENERATOR`.
2. base64-decode the ViewState, flip one byte in the middle, re-encode.
3. POST the form back with the tampered value (any submit button).
4. **HTTP 500 "The state information is invalid for this page and might be corrupted"**
   = MAC ENABLED → deserialization RCE not viable, record the negative and move on.
   A normal validation error (or a 200) = MAC may be off → escalate carefully.

abhieo.in: tamper → 500 MAC-failure page. Negative, one request, no retries needed.
Note `__VIEWSTATE` starting `ff 01 …` after decode is the LOSFormatter marker — it appears
whether or not the MAC is on, so it proves nothing by itself; only the tamper test does.

## 2. Hidden-field PII surface on bill-fetch flows

`Root/TariffPlan/BillFetchAPI.aspx?OperatorID&Number&Optional1&Optional2&Type` renders a
"Loading..." page whose JS (`closeIframe()`) copies server-populated hidden fields
(`hddAmount`, `hddCustomerName`, `hddDueDate`) into the parent form. Shape to recognise:
a consumer-number lookup that returns **customer name / due date / amount** — if it answers
unauthenticated for arbitrary numbers it is a PII-exposure finding (High on most fintech
programs). Verification requires a valid OperatorID plus a consumer number you own; never
probe with a real customer's number (program rule: own data only). The same family:
`PlanAPI.aspx?OperatorID&CircleID&MobileNumber&Type`,
`ROfferFetchAPI.aspx?OperatorID&Number&OperatorName&Type`.

## 3. WebMethods (Page/Method) auth behaviour

ASP.NET AJAX page methods (`MakeRecharge.aspx/OperatorFetch`, `/GetSurcharge`,
`RC_Transactions.aspx/fillOperatorbyService`) answer POST `{}` with
`401 {"Message":"Authentication failed.","StackTrace":null}` when unauthenticated.
`StackTrace: null` = no stack leak (good for them). A stack trace here, or a 500 with
`System.Web.Services` detail, is the reportable shape.

## 4. Error-message leaks on dynamic-data endpoints

`DynamicData.aspx?id=<base64>` — valid id → 200 page; malformed id (`AAAA`, `0`) →
**500 "Input string was not in a correct format"**. Generic .NET format exceptions are
usually triaged informational; the reportable version leaks SQL/stack/internal paths.
Record the exact error text either way.

## 5. Multi-subdomain single-SPA pattern

12+ subdomains (pay / partner / cpanel / mail / webmail / webdisk / cpcalendars /
cpcontacts / hostmaster / blog / more / nearby) all served the **same 5,166-byte AngularJS
shell** with identical bundle hashes — the subdomain only selects the app context. Do not
count these as 12 services; count distinct bundles/titles (same lesson as wildcard DNS).
The bundle turned out to be **SmarterMail** (build in the filename; `/api/v1/mail/*`,
`/interface/*` paths) — third-party software on their subdomains; check the program's
third-party clause before reporting product CVEs, and compare the build against public
advisory fix-builds.

## 6. Other notes

- Registration is captcha-gated (`txtCapchaCode` + `/Root/Capcha.aspx`) — browser-driven
  provisioning needed; the money-path WebMethods sit behind login.
- HTTPS: the app subdomains were HTTP-only (TLS handshake reset) while the apex had HSTS —
  a payment portal over plaintext HTTP is worth a misconfiguration note, severity per program.
- Marketing WordPress (`/wp-content/plugins/user-registration/` 1.8.3/1.8.4) lived beside
  the WebForms app — check plugin versions against public CVEs, but confirm which host
  actually serves WP before reporting.
