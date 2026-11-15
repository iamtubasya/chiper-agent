# Owned second factor: QR decode, OTP automation, grant matrix

Companion to `modern-webapp-auth-hunting`. All of this assumes the tester legitimately holds the
second factor (client supplied the QR / secret for their own test account). Never use it against
an account whose 2FA you were not given.

---

## 1. Decode a Google Authenticator export QR

`otpauth-migration://offline?data=<base64 protobuf>` is the *export* format. The secret is not in
the URL in plaintext — parse the protobuf.

```python
import cv2, zxingcpp, base64, urllib.parse, re

def decode_qr(path):
    img = cv2.imread(path)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hits = []
    def try_(im, tag):
        for r in zxingcpp.read_barcodes(im):
            hits.append((tag, r.text))
        return bool(hits)

    if not try_(gray, "raw"):
        for s in (2, 3, 4, 5, 6, 8):
            if try_(cv2.resize(gray, (w*s, h*s), interpolation=cv2.INTER_CUBIC), f"x{s}"):
                break
    if not hits:
        for th in (100, 120, 140, 160, 180, 200):
            _, b = cv2.threshold(gray, th, 255, cv2.THRESH_BINARY)
            if try_(b, f"thr{th}"):
                break
    if not hits:
        ad = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 10)
        try_(ad, "adaptive")
    if not hits:
        try_(cv2.bitwise_not(gray), "invert")
    if not hits:
        bl = cv2.GaussianBlur(gray, (3, 3), 0)
        _, o = cv2.threshold(bl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        try_(o, "otsu")
    return hits
```

### Confirm a QR is even in the image (do this FIRST)

Cheap, and prevents grinding decoders on a screenshot that contains no QR at all — a real failure
mode when the user sends the *wrong* screenshot, or when a photo is a dark UI rather than a QR.

```python
cols, rows = 76, int(76 * (h / w) * 0.5)
small = cv2.resize(gray, (cols, rows), interpolation=cv2.INTER_AREA)
chars = " .:-=+*#%@"
for y in range(rows):
    print("".join(chars[min(len(chars)-1, int(small[y, x] / 256 * len(chars)))]
                  for x in range(cols)))
```

A QR shows **three compact high-contrast finder squares** in three corners. A UI screenshot shows
long horizontal bands of text. If it looks like text, you have the wrong file — ask for the QR
rather than tuning thresholds.

### Parse the protobuf (no protobuf lib needed)

```python
def read_varint(buf, i):
    shift = val = 0
    while True:
        b = buf[i]; i += 1
        val |= (b & 0x7f) << shift
        if not (b & 0x80):
            return val, i
        shift += 7

def parse(buf):
    i, out = 0, []
    while i < len(buf):
        key, i = read_varint(buf, i)
        field, wt = key >> 3, key & 7
        if wt == 0:
            v, i = read_varint(buf, i); out.append((field, "varint", v))
        elif wt == 2:
            ln, i = read_varint(buf, i); out.append((field, "bytes", buf[i:i+ln])); i += ln
        elif wt == 5:
            out.append((field, "32bit", buf[i:i+4])); i += 4
        elif wt == 1:
            out.append((field, "64bit", buf[i:i+8])); i += 8
        else:
            raise ValueError(f"wiretype {wt}")
    return out

uri = "otpauth-migration://offline?data=...."
raw = base64.b64decode(urllib.parse.parse_qs(
    urllib.parse.urlparse(uri).query)["data"][0] + "==")

top, _ = parse(raw)
for f, t, v in top:
    if f == 1 and t == "bytes":                 # otp_parameters (repeated)
        fields, _ = parse(v)
        d = {}
        for ff, tt, vv in fields:
            d.setdefault(ff, []).append(vv)
        secret = base64.b32encode(d[1][0]).decode().rstrip("=")
        print(d.get(2, [b""])[0].decode(), d.get(3, [b""])[0].decode(), secret)
```

Field map inside `otp_parameters`: 1 secret · 2 name · 3 issuer · 4 algo(1=SHA1) · 5 digits(1=6)
· 6 type(2=TOTP) · 7 counter.

### Verify

```python
import pyotp, time
code = pyotp.TOTP(secret).now()
print(code, "valid", 30 - int(time.time()) % 30, "s")
```

Assume one secret = many systems. In the source engagement the same TOTP opened the SaaS identity
provider **and** the on-prem appliance console; we nearly requested a second enrolment for nothing.

---

## 2. Always submit inside a fresh TOTP window

A code generated at T+28s can be rejected for reasons unrelated to the control under test.

```python
rem = 30 - int(time.time()) % 30
if rem < 8:
    await page.wait_for_timeout((rem + 2) * 1000)
code = pyotp.TOTP(secret).now()
```

---

## 3. OTP prompt hidden in an iframe (JSF / PrimeFaces appliances)

Symptom: after submitting a correct password the page says "please enter your Authentication
Code", but `query_selector_all("input")` on the main page shows no OTP field, and clicks fail with
`<iframe id="otpAuth"> … subtree intercepts pointer events`.

The prompt is a modal iframe. Find it by URL fragment and drive the frame, not the page:

```python
frame = next((f for f in page.frames if "otpAuthDlg" in f.url), None)
await frame.wait_for_load_state("networkidle")
await frame.fill("#form1\\:fldCheckAuthNumber", pyotp.TOTP(secret).now())
await frame.click("#form1\\:actionBtn")
```

Notes that cost time if missed:
- JSF element ids contain `:` — escape as `#form1\\:userId` in CSS selectors.
- `wait_until="networkidle"` **times out** on console apps that long-poll. Use
  `domcontentloaded` + an explicit wait.
- Install `page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))` — EULA / confirm
  dialogs otherwise swallow the flow silently.
- First login to an appliance often runs a wizard (EULA → initial setup). Accept and step through;
  the console frame only appears after it.

---

## 4. Keycloak grant matrix + DCR probe

```bash
KC=https://<idp>/realms/<realm>
curl -s $KC/.well-known/openid-configuration | jq '.grant_types_supported'
```

```python
# each of these should be REFUSED when MFA is properly enforced
post(f"{KC}/protocol/openid-connect/token",
     {"grant_type":"password","client_id":APP_CLIENT,"username":U,"password":P,"scope":"openid"})
post(f"{KC}/protocol/openid-connect/token",
     {"grant_type":"password","client_id":"admin-cli","username":U,"password":P})
post(f"{KC}/protocol/openid-connect/token", {"grant_type":"client_credentials","client_id":APP_CLIENT})
post(f"{KC}/protocol/openid-connect/auth/device", {"client_id":APP_CLIENT,"scope":"openid"})
```

DCR reachability probe — `400` with a Keycloak schema error proves the endpoint is live:

```python
post(f"{KC}/clients-registrations/default", {"clientId":"probe"})
# -> 400 {"error":"Invalid json representation for ClientRepresentation. Unrecognized field ..."}
#     endpoint LIVE.  A static branded "Not Found | <vendor>" page with 403 = edge WAF blocking.
```

---

## 5. SAML tamper harness (fresh token per variant)

Single-use assertions make a shared token useless after the control run — every variant needs its
own capture.

```python
async def capture_unused(page):
    """Intercept the SSO POST so the browser never consumes the assertion."""
    box = {}
    async def handler(route):
        pd = route.request.post_data or ""
        if "SAMLResponse=" in pd:
            box["saml"] = urllib.parse.unquote(pd.split("SAMLResponse=")[1].split("&")[0])
            if "RelayState=" in pd:
                box["relay"] = pd.split("RelayState=")[1].split("&")[0]
        await route.fulfill(status=200, content_type="text/html",
                            body='<script>var redirectUrl="#";</script>{"result":true}')
    await page.route("**/samlauth", handler)
    return box
```

Build variants, then post each to the ACS/`samlauth` endpoint. Verdict heuristics:

- success marker differs per product: `"result":true`, a `Set-Cookie` session, or a redirect URL.
- `strip response-level signature only` succeeding is **expected and legal** for SAML WebSSO when
  the assertion itself is signed — do not report it as XSW.
- `strip all signatures` succeeding, or a swapped `NameID` succeeding, is the actual finding.
