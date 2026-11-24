# Captured artifacts & raw evidence — aifaceswap.io guest flow

All values below were captured live from a real browser session (CDP HAR + in-page hooks).
Treat secrets as rotating — re-extract from `cryptojsencudx.bundle.js`.

## Bundle locations
- App JS:  `https://temp.aifaceswap.io/aifaceswap/static/js/custom/feature/videoswap.<hash>.js`
- Secrets: `https://temp.aifaceswap.io/aifaceswap/static/js/plugins/custom/cryptojs/cryptojsencudx.bundle.js`
- Auth/axios wrapper: `.../static/js/util-pinia-auth.bundle.<hash>.js`

## Where the crypto helpers are defined
In `cryptojsencudx.bundle.js` at the tail:
```js
const RSA_PUBLIC_KEY = "-----BEGIN PUBLIC KEY-----\nMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCwlO+boC6cwRo3UfXVBadaYwcX\n...\n-----END PUBLIC KEY-----";
const APP_ID = "aifaceswap", APP_ID_V1 = "aifaceswap_v1";
const SECRET=***",  // NOTE: literal value lives here; extract between quotes at runtime
function encrypt(t,e,r){ /* CryptoJS AES-CBC pkcs7, key=e, iv=r */ }
function uuidv4(){...}
const t=()=>{...}   // signx  : "APP_ID_V1:SECRET:t:nonce:secret_key"
const u=()=>{...}   // signux : "APP_ID_V1:nonce:secret_key"
crypto.subtle.signx=t; crypto.subtle.signux=u; crypto.subtle.e=(t,e)=>encrypt(APP_ID_V1+t,e,e);
```
- `x-guide` header = `secret_key` = `b64(RSA_PKCS1v15_encrypt(aesSecret))` (128 bytes → 172 b64)
- `x-sign` length: signx→344, signux→300 (b64). Use length to identify which was used.
- `fp1` = `crypto.subtle.e(":"+fp, aesSecret)` = `AES-CBC("aifaceswap_v1:"+fp, key=aes, iv=aes)`.
  Verified byte-exact against a live capture.

## Body encrypt (verified by decrypting a live request)
```python
import base64, hashlib, json
from Crypto.Cipher import AES
key = hashlib.sha256(theme_version.encode()).digest()   # theme from data-kt-theme-version on load
raw = base64.b64decode(data_field); iv, ct = raw[:12], raw[12:]
pt  = AES.new(key, AES.MODE_GCM, nonce=iv).decrypt(ct).decode()   # -> JSON, trailing 16 bytes = tag
```
Decrypted plaintext of a real guest request:
```json
{"source_video":"aifaceswap/upload_res/2026-11-15/<hash>_0_5.mp4",
 "face_image":"<date>/<hash>.webp","start":0,"end":5,"type":1}
```

## Aliyun OSS presign + upload
```python
# POST /api/upload_file  (headers: theme-version, X-code, x-guide, x-sign, x-type:0)
#   body: {"file_name": "...", "type": "image"|"video"}
# -> {"code":200,"data":{"url":"https://yimeta-ai-face-swap.oss-us-west-1.aliyuncs.com/aifaceswap/upload_res/<date>/<file>?OSSAccessKeyId=...&Expires=...&Signature=..."}}
# then: PUT <url> with header x-oss-storage-class: Standard
# cdnUrl (relative path used in generate) = url.split('?')[0].replace(OSS_DOMAIN, '')
```
The presigned URL leaks a scoped Aliyun AccessKeyId (`LTAI...`) — rotate/expire quickly scoped.

## Guest config (from `localStorage.common_globalConfig`, decoded)
```
faceswap.video_free_points = 10,  max_free_points = 150,  claim_free_points = 30
```
→ Daily free limit is **3 videos**, tracked per fingerprint/device (server-side).
10 points covers one 5-second / 2-credits-per-second swap exactly.

## check_status response at completion
```json
{"code":200,"data":{"error":"","queue_len":0,"rank":0,
  "result_image":"aifaceswap/generate_temp/<date>/target_<task_id>.mp4","status":2}}
```
- `status` 0=queued, 1=processing, 2=**done**, 3=failed, -1=expired/not found.
- Final download host: **`https://art-global.ezmaker.ai/`** + `result_image`
  (`https://temp.aifaceswap.io/` + `result_image` → `404 NoSuchKey`).

## Error codes
| code | message | meaning |
|---|---|---|
| 200 | OK | task accepted |
| 637 | you don't have enough free counts | daily 3/day limit hit for this device/fp |
| 641 | Permission check failed | fp/theme not recognized by the JS-runtime session |
| 601 | Permission check failed | missing sign headers on a protected endpoint |
| 429 | Too many requests | rate limited |
