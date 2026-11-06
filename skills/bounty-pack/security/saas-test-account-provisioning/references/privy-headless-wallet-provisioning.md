# Privy-backed web3 apps: headless provisioning over REST (no browser)

Verified 2026-10-30 on bankr.bot. Privy (`auth.privy.io`) is the embedded-wallet IdP behind a large
share of crypto / agent / trading apps, so this recipe transfers directly. The whole account —
including the app-side wallet — can be created with curl in about six calls.

## 1. Discover the tenant config from the front end

Privy identifies the tenant with two headers, both visible in the bundle and in any captured request:

```
privy-app-id:   cm4u45r3i030j14fhbxsnu8j5
privy-client:   client-WY5eXTPaG2NdNNZ1s7tgecB1sZSPbuzpDTENnUPcWi26S
```

Grep the main JS chunk for `client-[A-Za-z0-9]{20,}` (the public client id) and look at the
`GET https://auth.privy.io/api/v1/apps/<appId>` call the SDK makes on load — it returns the enabled
login methods, so you learn up front whether guest / SIWE / wallet login is even allowed. A headless
browser is not needed: one Playwright `page.on("request")` pass, or just reading the bundle, is enough.

**Check which methods are enabled before planning anything.** This app answered
`403 {"error":"Guest accounts are not enabled for this app","code":"disallowed_login_method"}` for
`/api/v1/guest/authenticate` and `{"error":"Login with wallet not allowed"}` for `/api/v1/siwe/init`.
Both are per-tenant switches — finding them out costs two requests and saves an hour.

## 2. The flow

```bash
H=(-H "content-type: application/json" \
   -H "privy-app-id: <appId>" \
   -H "privy-client: <clientId>" \
   -H "origin: https://<app-host>")

# 1. request a code
curl -sS -X POST https://auth.privy.io/api/v1/passwordless/init "${H[@]}" \
     -d '{"email":"user+tag@gmail.com"}'          # -> {"success":true}

# 2. exchange the 6-digit code
curl -sS -X POST https://auth.privy.io/api/v1/passwordless/authenticate "${H[@]}" \
     -d '{"email":"...","code":"123456"}' -o privy.json
# -> {user:{id:"did:privy:...", linked_accounts:[...], is_new_user:true}, token, identity_token}
```

`token` and `identity_token` are both JWTs and are **not interchangeable with an Authorization
header** — see the next step.

## 3. App-side auth is TWO custom headers, not Bearer

Read the app's own fetch wrapper out of the bundle rather than guessing. This app's wrapper was:

```js
s["x-access-token"] = <privy token>;
s["privy-id-token"]  = <identity token>;
fetch(url, { credentials: "include", headers: s })
```

So the authenticated calls are:

```bash
curl -sS https://api.<host>/user \
  -H "x-access-token: $TOKEN" -H "privy-id-token: $ID_TOKEN" -H "origin: https://<app-host>"
```

Sending `Authorization: Bearer <token>` answers a flat `401 {"error":"Authentication required"}` and
looks like a broken token. **If a Privy login "succeeds" but every app call 401s, you are sending the
wrong header.** Then:

```bash
POST /user/bootstrap     # app provisions the cross-chain wallet; 201 -> {evmAddress, solAddress}
POST /user/accept-terms
POST /api-keys {"name":"audit"}    # returns the secret ONCE
```

`POST /user/bootstrap` returning `500 {"error":"Internal server error","message":"Failed to set up
your Bankr wallet"}` on a *valid* Privy identity means the app-side provisioning refused — see §5.

## 4. Read the OTP from the mailbox, by context

- Gmail API refresh-token flow works and is the fastest (`messages?q=newer_than:10m`).
- **`user+tag@gmail.com` and dot variants collapse to the SAME app account.** Privy issues a new
  `did:privy:...` identity per address, but the app normalises the email and resolves it back to the
  first account — so the alias family gives you one wallet, not two. Confirm by calling `/user` on the
  second login and comparing the returned `address`.
- Guerrillamail has a usable REST flow with no auth:
  `GET https://api.guerrillamail.com/ajax.php?f=get_email_address&lang=en` → `{email_addr, sid_token}`,
  then `f=get_email_list&offset=0&sid_token=...`, then `f=fetch_email&email_id=<id>&sid_token=...`
  and regex the **`mail_body` HTML** for `\b\d{6}\b`. mail.tm also works; its token expires quickly,
  so re-`POST /token` rather than reusing a stale JWT.

## 5. The disposable-mailbox wall: OTP passes, wallet provisioning does not

Both disposable addresses in this session authenticated at Privy (`is_new_user:true`, real
`did:privy:` ids) and then the app answered `500 Failed to set up your Bankr wallet` on
`/user/bootstrap`, repeatedly, and `404 Wallet not found` on every subsequent call. The account exists
in the IdP but has no wallet — i.e. **the app's provisioning service treats the address as
untrusted, and no amount of retrying fixes it.**

Consequence for a cross-tenant (IDOR / BOLA) test that needs two identities: you may be stuck with
one. Options, in order: (a) a second **real** mailbox the operator controls (dot-variant of a
different address family, not a `+tag` of the same one); (b) ask the operator for a second mailbox
rather than fabricating one; (c) declare the cross-tenant leg NOT REACHABLE with the exact 500 as the
reason — never as "no findings". Do not manufacture KYC/KYB or a second identity by other means.

## 6. Tooling notes

- `python urllib` against `auth.privy.io` gets `403 error code: 1010` (Cloudflare fingerprint check on
  that host). Use **curl** for the Privy calls; the app's own API accepts urllib fine.
- App-side keys created via `POST /api-keys` are shown once. Persist immediately, then PATCH the same
  path to tighten them (`{"readOnly":true}`, `{"allowedIps":[...]}`) — that is also how you verify the
  key-control matrix later.
- Every account you create is a state change on the target. Log address, chain addresses, Privy
  `did:privy:` id and timestamps; the vendor's policy will likely require the full list in the report
  (see `report-writing/reportlab-security-pdf/references/account-wallet-inventory.md`).
