# Genians — second-account recipe, plugin action matrix, adjacent hosts

Session-specific detail for `genians-engagement`. Read this when you need a **second tenant** for
cross-account testing, or before re-testing any `csm.demo` AJAX action.

---

## 1. Second account on `my.demo.genians.co.kr` (the working path)

Only the Keycloak SPA signup completes. Everything else either needs manual approval or mails a
link that leads nowhere.

### 1.1 Address choice — dot-variant, never `+`

`gov` rejects `+` outright (`입력 가능한 특수문자는 하이픈(-)과 쉼표(.)`), and a `+` address also
never receives the mail elsewhere. Gmail ignores dots, so:

```
RESEARCHER_EMAIL  ==  fz.susanto@  ==  f.zs.usanto@  ==  f.zs.us.anto@  ==  f.zs.us.anto@
```

Each is a *different* identifier to Genians but lands in the same inbox you can read. This is the
single trick that unblocked account #2 after several dead ends.

### 1.2 Full automated flow (one process — the token expires fast)

```python
# a) Sign up on the Keycloak SPA
await page.goto("https://my.demo.genians.co.kr/app/home")   # domcontentloaded
await page.click("text=Sign up")                            # -> csmauth.demo.../auth?prompt=create
await page.fill("#email", DOT_VARIANT_EMAIL)
await page.fill("#firstName", "RESEARCHER_NAME"); await page.fill("#lastName", "Susanto")
await page.fill("#CompanyName", "Independent Security Research")
await page.select_option("select", label="Asia/Jakarta")
await page.check("#TermsAgree"); await page.check("#PrivacyAgree")
await page.click("input[type=submit]")
# -> login-actions/required-action?execution=VERIFY_EMAIL

# b) poll Gmail for the action-token link, then open it IMMEDIATELY
link = fetch_link(gmail_service, DOT_VARIANT_EMAIL, tries=25, gap=2)
await page.goto(link)
# -> required-action?execution=CONFIGURE_TOTP

# c) TOTP secret comes from the QR rendered as a base64 <img>
html = await page.content()
src  = re.findall(r'src="(data:image/[^"]+)"', html)[0]
img  = cv2.imdecode(np.frombuffer(base64.b64decode(src.split(",",1)[1]), np.uint8), cv2.IMREAD_COLOR)
uri  = zxingcpp.read_barcodes(img)[0].text        # otpauth://totp/...
secret = re.search(r"secret=([A-Z2-7]+)", uri).group(1)

rem = 30 - int(time.time()) % 30                    # wait out the window
if rem < 8: await page.wait_for_timeout((rem + 2) * 1000)
await page.fill("#totp", pyotp.TOTP(secret).now())
await page.fill("#userLabel", "bbtest2")
await page.click("input[type=submit]")
# -> required-action?execution=UPDATE_PASSWORD

# d) set password
await page.fill("#password-new", PW)
await page.fill("#password-confirm", PW)
await page.click("input[type=submit]")
# -> https://my.demo.genians.co.kr/common/home-logined   DONE
```

Save `{email, pw, totp_secret}` to a JSON file and have every later script read it from there —
never hard-code the password into generated code (redaction mangles it).

### 1.3 Then order the trial on the new account

Log in → `/common/services` → `csm.demo.genians.co.kr/try-cloud-gsp` → POST
`action=gn_cloud_start_subscribe` with `product=nac`, `edition=pro`, `nodes=10`.
Expect `{"result":true,"message":"success"}` and a site like `acc2iwp9s.demo.genians.co.kr`.

Provisioning is **not instant**: DNS resolves within seconds but the `/mc2/` vhost 404s for a while.
Poll `GET /mc2/faces/adminlogin.xhtml` and look for `form1:userId` in the body before driving login.

---

## 2. `csm.demo` AJAX action matrix (two self-owned subscriptions)

Session on account #2; `subscription_id` 14668 = own, 14662 = the other account (also mine).
All POSTs to `/wp-admin/admin-ajax.php`, each needs a fresh `csrf_token` from
`action=gn_async_create_csrf_token`.

| action | parameters | OWN | FOREIGN | verdict |
|---|---|---|---|---|
| `gn_license_download` | `subscription_id` | `{"result":true,"serverid":"K7KC-GJBM-CFHO-A2GG"}` | `no permission` | ownership ✅ |
| `gn_start_stopped_site` | `subscription_id` | `{"result":true}` (really starts it) | fails, no data leak | ownership ✅ |
| `shop_license_reissue` | `subscription_id`, `new_serverid` (19 chars) | `no permission` (trial ineligible) | `no permission` | plan-gated |
| `get_acl_ajax` | `sitename`, `ec2_ip` | `ACL IP could not be collected` (site still provisioning) | `invalid access` | ownership ✅ |
| `cloud_console_acl_modify_ajax` | `acl`, `sitename`, `sitefullname`, `ec2_ip`, `userpassword` | not run cross-account — same gate as `get_acl_ajax` | — | inferred gated |
| `shop_card_info_modify_ajax` | `card_number`, `cvv`, `expiry_*`, `target_id`, address | **deliberately not tested cross-account** | — | see note |
| `gn_deal_check_purchase_state` | `subscription_id` | `{"result":true,"data":true}` | **also `true`, incl. id `1` / `99999999`** | boolean-only oracle |
| `gn_gdpi_reissuance` | `subscription_id`, `restid`, `plan_code` | `GDPI REST API CURL : Wrong access` | — | no PI entitlement |
| `gn_site_publicip_check` | `subscription_id`, `sitefullname`, `sitename` | `{"result":true,"public_ip":"…"}` | — | value is already public via DNS |
| `search_company_name_by_siteid` | `siteid` | `invalid access` | — | gated |

**`shop_card_info_modify_ajax` note:** writing fake card data into any account (own or foreign) is
unethical and unnecessary. There is also no read-back endpoint that leaks card data, so there is no
exposure to demonstrate. Leave it alone and say why.

**`gn_deal_check_purchase_state` note:** returning `true` for non-existent ids means the parameter
is not used for authz — but the response is a single boolean with no data behind it. That is
Art.7.3 "extremely minimal attack value". Record it as an anomaly, do not dress it as IDOR.

---

## 3. Adjacent hosts found by DNS brute (they are NOT product surface)

`crt.sh` alone misses these — they have no CT-log entry of their own. Brute the label space
(`auth`, `api`, `tech`, `sso`, `partner`, `dashboard`, `sase`, `pi`, `logs`, `monitor`, `dl`,
`download`, `beta`, `old`, …) across `genians.com` / `genians.co.kr` / `my.*`.

| host | what it is | scope call |
|---|---|---|
| `tech.genians.com/jira` | Jira Server 9.12.4, **publicly reachable**, `/rest/api/2/dashboard` returns 18 internal dashboard names unauthenticated | internal IT, **not** a product → out of Art.3 product scope |
| `sso.genians.com` | AWS API Gateway → custom Lambda (`bp_lambda_bpaws_007842_…`) → Atlassian **Crowd** SSO fronting the same Jira | internal identity plane, same call |
| `partner.genians.com` | partner portal; OIDC to `auth.my.genians.co.kr/realms/ztna-sase`, client `client-partnerportal-oidc` | product-adjacent, in scope |
| `auth.my.genians.co.kr` | separate Keycloak; realms `ztna-sase`, `partner`, **`master`** | in scope (`*.my.*`) |
| `api.genians.com`, `api.my.genians.co.kr` | same WordPress CSM app, older build | in scope |

**Already handled:** the Jira anonymous-dashboard disclosure was reported to `bugbounty@genians.com`
by the operator as a good-faith note, explicitly inviting them to say if the host is out of scope.
Do **not** re-report it, and do not build a bounty expectation on internal-IT findings."

Measured negatives on those hosts so they are not re-burned: `redirect_uri` on the `ztna-sase`
realm is strictly validated (14 bypass variants all 400), DCR is WAF-blocked (403 on every
well-formed body), Crowd `redirectTo` is reflected-but-unused (no open redirect) and escaped
(`<\/script>`), Crowd `step=2` needs a server-issued `cookie` param (unprovable without a valid
login), Jira login errors are uniform (no user enumeration), Jira project/search endpoints return
empty to anonymous callers.
