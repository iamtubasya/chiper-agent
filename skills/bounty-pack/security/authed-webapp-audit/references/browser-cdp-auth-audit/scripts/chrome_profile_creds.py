#!/usr/bin/env python3
"""Recover saved logins and cookies from a local Chrome/Edge profile directory.

Use when an engagement needs authenticated access and the operator either does not
remember the password or only has a still-logged-in browser profile lying around.

    python chrome_profile_creds.py --profile-dir "~/.local/share/Google/Chrome/User Data" --match quarterwise
    python chrome_profile_creds.py --profile-dir "~/qw_chrome_cdp_b3" --cookie-name qw_session

Two extraction paths, both from the SAME user-data-dir:

  1. SAVED PASSWORDS  -> <profile>/Login Data        (SQLite; value encrypted v10)
  2. COOKIES          -> <profile>/Default/Network/Cookies   (SQLite; value encrypted v10)

Both are AES-256-GCM where the key lives in  <user-data-dir>/Local State
(json -> os_crypt.encrypted_key, base64, with a 5-byte "DPAPI" prefix that must be
stripped before CryptUnprotectData).

READ THIS BEFORE TRUSTING THE OUTPUT
------------------------------------
- The PASSWORD path is the reliable one: plaintext comes back as clean ASCII.
- The COOKIE path frequently decrypts to NON-ASCII garbage even though GCM auth
  PASSES (so you cannot tell it apart from success by catching an exception). If the
  decrypted session value contains bytes >127 it is NOT a cookie a browser ever sent
  (HTTP header values are latin-1). Do not try to make it work. Instead:
      copy the whole profile dir -> launch headless Chrome on it -> hit the app via
      CDP and check whether the session is still alive.
  Cookies live in the profile dir, so a copied profile stays logged in and that path
  is strictly more reliable than DB decryption. See SKILL.md
  "Recovering an authenticated identity from the operator's own Chrome profile".

Profile layout gotcha (cost a retry): "Local State" sits in the profile ROOT, while
"Login Data" and "Network/Cookies" sit under Default/. Getting this wrong throws
FileNotFoundError on a path that looks right.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    sys.exit("pip install cryptography   (also needs pywin32 on Windows for the DPAPI unwrap)")

WIN = sys.platform.startswith("win")


def master_key(user_data_dir: Path) -> bytes:
    """Unwrap the AES key stored in <user-data-dir>/Local State (NOTE: root, not Default/)."""
    ls = user_data_dir / "Local State"
    if not ls.exists():
        raise FileNotFoundError(f"no Local State at {ls} (it lives in the profile ROOT, not Default/)")
    data = json.loads(ls.read_text(encoding="utf-8"))
    blob = base64.b64decode(data["os_crypt"]["encrypted_key"])
    if blob[:5] == b"DPAPI":
        blob = blob[5:]
    if WIN:
        import win32crypt  # pywin32
        return win32crypt.CryptUnprotectData(blob, None, None, None, 0)[1]
    raise RuntimeError("non-Windows: key is inside the OS keyring; read it with secretstorage/keyring")


def decrypt(value: bytes, key: bytes) -> bytes:
    if value[:3] in (b"v10", b"v11"):
        return AESGCM(key).decrypt(value[3:15], value[15:], None)
    if WIN:  # very old Chrome: raw DPAPI blob
        import win32crypt
        return win32crypt.CryptUnprotectData(value, None, None, None, 0)[1]
    raise RuntimeError("unsupported cookie/password encryption scheme")


def _rows(db: Path, query: str):
    """Copy the SQLite file first — Chrome holds a lock while running."""
    tmp = Path(tempfile.mkdtemp()) / "copy.db"
    try:
        shutil.copy2(db, tmp)
        con = sqlite3.connect(str(tmp))
        try:
            yield from con.execute(query)
        finally:
            con.close()
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def profile_dirs(root: Path):
    """The user-data-dir itself (if it has Local State) plus each Default/Profile* subdir."""
    cands = [root]
    cands += sorted(root.glob("Default")) + sorted(root.glob("Profile*"))
    for c in cands:
        if (c / "Local State").exists() or (c.parent / "Local State").exists():
            yield c


def dump_logins(user_data_dir: Path, match: str | None):
    try:
        key = master_key(user_data_dir)
    except Exception as exc:
        print(f"  ! key: {exc}")
        return
    for prof in profile_dirs(user_data_dir):
        db = prof / "Login Data"
        if not db.exists():
            continue
        # Local State is at the user-data-dir root even when the DB is in Default/
        try:
            key = master_key(prof) if (prof / "Local State").exists() else key
        except Exception:
            pass
        print(f"  [{prof.name}]")
        for origin, user, pw in _rows(db, "SELECT origin_url, username_value, password_value FROM logins"):
            if match and match.lower() not in origin.lower():
                continue
            try:
                plain = decrypt(pw, key).decode("utf-8", "replace")
            except Exception as exc:
                plain = f"<decrypt failed: {exc}>"
            # username_value is often a DISPLAY NAME ("Mr Fz"), not the email — do not filter on it
            print(f"    {origin}\n      user={user!r}\n      pass={plain!r}")


def dump_cookies(user_data_dir: Path, match: str | None, name: str | None, show: bool):
    try:
        key = master_key(user_data_dir)
    except Exception as exc:
        print(f"  ! key: {exc}")
        return
    for prof in profile_dirs(user_data_dir):
        db = prof / "Network" / "Cookies"
        if not db.exists():
            db = prof / "Cookies"
        if not db.exists():
            continue
        print(f"  [{prof.name}]")
        q = "SELECT host_key, name, encrypted_value, expires_utc FROM cookies"
        for host, cname, enc, exp in _rows(db, q):
            if match and match.lower() not in host.lower():
                continue
            if name and cname != name:
                continue
            note = ""
            if show:
                try:
                    pt = decrypt(enc, key)
                    ascii_ok = all(32 <= b < 127 for b in pt)
                    note = (f"  value={pt.decode('ascii')!r}" if ascii_ok
                            else f"  NON-ASCII {len(pt)}B -> DO NOT TRUST; use the live copied profile")
                except Exception as exc:
                    note = f"  <decrypt failed: {exc}>"
            print(f"    {host}  {cname}  exp={exp}{note}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile-dir", required=True, help="user-data-dir, e.g. .../User Data or a dedicated --user-data-dir")
    ap.add_argument("--match", default=None, help="substring filter on origin_url / host_key")
    ap.add_argument("--cookie-name", default=None, help="only this cookie name, e.g. qw_session")
    ap.add_argument("--show-values", action="store_true", help="attempt cookie decryption (see warnings)")
    a = ap.parse_args()

    root = Path(os.path.expanduser(a.profile_dir)).resolve()
    if not root.exists():
        return print(f"no such dir: {root}") or 2
    print(f"# profile dir : {root}")
    print(f"# saved logins")
    dump_logins(root, a.match)
    print(f"# cookies")
    dump_cookies(root, a.match, a.cookie_name, a.show_values)
    print(
        "\n# Reminder: a still-valid session is proven by driving the COPY of this profile\n"
        "#   cp -r <profile> <copy>  ->  chrome --user-data-dir=<copy> --remote-debugging-port=9333 \\\n"
        "#   --remote-allow-origins=* --headless=new  ->  CDP Page.navigate <app> -> read the landing page\n"
        "# Delete lockfiles (lockfile, SingletonLock, Default/Network/Cookies-journal) in the copy first.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
