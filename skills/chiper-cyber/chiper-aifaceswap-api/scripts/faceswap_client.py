#!/usr/bin/env python3
"""
aifaceswap.io guest (no-login) client — reverse-engineered.

STATUS:
  upload + Aliyun OSS PUT   = ✅ WORKING (verified)
  generate_video_face       = ⚠️ returns 641 from pure Python (server binds theme/fp to a
                              JS-runtime session minted on page load).
                              → For a guaranteed 200, drive the request from the live browser
                                using the site's own crypto.subtle.signx() +
                                MYGLOBAL.encrypt_aes_gcm() + MYUtils.userFP (see SKILL.md).

Crypto (from cryptojsencudx.bundle.js):
  signux (upload_img):  AES-CBC( "aifaceswap_v1:"+nonce+sk, key=aes, iv=aes )
  signx  (generate):    AES-CBC( "aifaceswap_v1:"+SECRET+":"+t+":"+nonce+":"+sk, key=aes, iv=aes )
  secret_key header  =  b64( RSA_PKCS1v15(aes, RSA_PUBLIC_KEY) )        [128 bytes -> 172 b64]
  fp1 header         =  AES-CBC( "aifaceswap_v1:"+fp, key=aes, iv=aes )
  body              =  b64( iv12 || AES-GCM(json, key=SHA256(theme)) )

Quota: code 637 = 3 free videos/day limit (per fp/session, server-side, not IP).
       code 641 = permission check failed (unknown fp / bad theme/session).
"""
import os, re, time, json, uuid, base64, hashlib, random, string, sys
import requests
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad

BASE = "https://aifaceswap.io"
OSS_DOMAIN = "https://yimeta-ai-face-swap.oss-us-west-1.aliyuncs.com/"
APP_ID_V1 = "aifaceswap_v1"
SECRET=*** = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCwlO+boC6cwRo3UfXVBadaYwcX
0zKS2fuVNY2qZ0dgwb1NJ+/Q9FeAosL4ONiosD71on3PVYqRUlL5045mvH2K9i8b
AFVMEip7E6RMK6tKAAif7xzZrXnP1GZ5Rijtqdgwh+YmzTo39cuBCsZqK9oEoeQ3
r/myG9S+9cR5huTuFQIDAQAB
-----END PUBLIC KEY-----"""
ALPH = string.ascii_letters + string.digits


def _mkid(n): return "".join(random.choice(ALPH) for _ in range(n))


def _cbc(pt, key, iv):
    return base64.b64encode(AES.new(key.encode(), AES.MODE_CBC, iv.encode())
                            .encrypt(pad(pt.encode(), 16))).decode()


def _signux():
    aes = _mkid(16)
    sk = base64.b64encode(PKCS1_v1_5.new(RSA.import_key(RSA_PUBLIC_KEY))
                          .encrypt(aes.encode())).decode()
    nonce = str(uuid.uuid4())
    return sk, _cbc(f"{APP_ID_V1}:{nonce}:{sk}", aes, aes), aes


def _signx():
    aes = _mkid(16)
    sk = base64.b64encode(PKCS1_v1_5.new(RSA.import_key(RSA_PUBLIC_KEY))
                          .encrypt(aes.encode())).decode()
    nonce = str(uuid.uuid4()); t = int(time.time())
    return sk, _cbc(f"{APP_ID_V1}:{SECRET}:{t}:{nonce}:{sk}", aes, aes), aes


def _gcm(obj, theme):
    key = hashlib.sha256(theme.encode()).digest()
    iv = os.urandom(12)
    c = AES.new(key, AES.MODE_GCM, nonce=iv)
    ct, _ = c.encrypt_and_digest(json.dumps(obj).encode())
    return base64.b64encode(iv + ct).decode()


class FaceSwapGuest:
    def __init__(self, proxy=None, fp=None):
        self.s = requests.Session()
        if proxy:
            self.s.proxies = {"http": proxy, "https": proxy}
        self.s.headers.update({"User-Agent": "Mozilla/5.0 Chrome/130.0",
                               "Origin": BASE, "Referer": BASE + "/"})
        self.theme = None
        self.fp = fp or hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

    def boot(self):
        r = self.s.get(BASE + "/video-face-swap-ai/")
        self.theme = re.search(r'data-kt-theme-version="([^"]+)"', r.text).group(1)
        return self.theme

    def _hdr(self, extra=None):
        h = {"theme-version": self.theme, "X-code": str(int(time.time() * 1000))}
        if extra: h.update(extra)
        return h

    def _presign(self, fn, typ="image"):
        sk, sign, _ = _signux()
        h = self._hdr({"x-guide": sk, "x-sign": sign, "x-type": "0",
                       "Content-Type": "application/json"})
        r = self.s.post(BASE + "/api/upload_file", headers=h,
                        data=json.dumps({"file_name": fn, "type": typ}))
        return r.json()["data"]["url"]

    def upload(self, path, typ="image"):
        data = open(path, "rb").read()
        ext = os.path.splitext(path)[1].lstrip(".") or ("webp" if typ == "image" else "mp4")
        fn = f"{typ}_{int(time.time())}_{random.randint(1000,9999)}.{ext}"
        purl = self._presign(fn, typ)
        self.s.put(purl, data=data, headers={"Content-Type": f"{typ}/{ext}",
                                             "x-oss-storage-class": "Standard"}).raise_for_status()
        return purl.split("?")[0].replace(OSS_DOMAIN, "")

    def generate_video(self, source_video, face_image, start=0, end=5, task_type=1, enhance=0):
        body = {"source_video": source_video, "face_image": face_image,
                "start": start, "end": end, "type": task_type}
        if enhance: body["enhance"] = enhance
        enc = _gcm(body, self.theme)
        sk, sign, aes = _signx()
        fp1 = _cbc(f"{APP_ID_V1}:{self.fp}", aes, aes)
        h = self._hdr({"Content-Type": "application/json", "fp": self.fp, "fp1": fp1,
                       "x-guide": sk, "x-sign": sign})
        r = self.s.post(BASE + "/api/v1/generate_video_face", headers=h,
                        data=json.dumps({"request_type": 2, "data": enc}))
        return r.status_code, r.json()

    def poll(self, task_id, timeout=300, interval=6):
        h = self._hdr({"Content-Type": "application/json"})
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(interval)
            j = self.s.post(BASE + "/api/check_status", headers=h,
                            data=json.dumps({"task_id": task_id, "is_batch": False,
                                             "is_vip_queue": False})).json()
            d = j.get("data", {})
            if d.get("status") in (2, 3, -1): return d
        return {"status": "timeout"}


if __name__ == "__main__":
    c = FaceSwapGuest()
    print("theme:", c.boot()[:20], "...")
    if len(sys.argv) >= 3:
        face = c.upload(sys.argv[1]); print("face cdn:", face)
        st, j = c.generate_video(sys.argv[2], face); print("generate:", st, j)
        if j.get("data", {}).get("task_id"):
            print("poll:", c.poll(j["data"]["task_id"]))
