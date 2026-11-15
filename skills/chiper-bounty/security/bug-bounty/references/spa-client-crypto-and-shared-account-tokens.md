# SPA client-crypto replication and shared service-account tokens

Companion to `spa-api-envelope-reverse-engineering.md` (envelope + field names) and
`js-bundle-recon.md`. This file covers what to do **after** you have the endpoint map, when the
product's security model is client-side crypto plus a shared anonymous account. Worked on
Hivenet Send/Store (2026-10-26).

## 1. The shared service-account pattern

A constant like `VITE_PUBLIC_ACCOUNT_SUB` in the inlined env config, plus an unauthenticated
`GET /auth/download-token`, means the product mints a real JWT for a **fixed service account**
and hands it to every anonymous visitor. Decode it and check:

```python
p = tok.split('.')[1]; p += '=' * (-len(p) % 4)
claims = json.loads(base64.urlsafe_b64decode(p))
# claims seen: iss, sub=<fixed service account>, aud=[<client id>], scope="openid",
#              act={iss, sub=<same fixed account>}
```

Then test, in this order:
1. **Does the token satisfy ownership checks on reads?** Probe an object you know belongs to a
   *different* tenant. A 200 here is the finding.
2. **Can it list the service account's objects?** `GET /<records>/type/VOLUME` and friends
   often return everything that account owns — including other sessions' leftovers.
3. **Can it create?** Check whether quota/accounting is charged to the *caller* or to the
   *target volume's owner*. Verbatim evidence decides this:
   `403 "adding 3221225472 bytes to the 3091202586 used of 3221225472 bytes"` — the numbers are
   the caller's, so a cross-tenant write burns the attacker's own quota and a
   "fill the victim's disk" claim dies right there.

## 2. Replicating the client crypto

"Zero-knowledge" storage products typically derive keys like this (read it out of the bundle —
look for `PBKDF2`, `AES-GCM`, `generateDerivedKey`, `encryptRaw`):

```
readKey  = PBKDF2-SHA512(password, salt, iterations=1_000_000, len=32)
blockKey = AES-GCM-decrypt(readKey, users[0].encryptedReadKey)      # hex(nonce)||hex(ct)
chunkKey = AES-GCM-decrypt(blockKey, chunks[0].encryptedBlockKey)
plain    = AES-GCM-decrypt(chunkKey, GET /p2p/storage/chunk/{cid})
```

```python
import hashlib, os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def pbkdf2(password, salt, it=1_000_000):
    return hashlib.pbkdf2_hmac("sha512",
        password.encode() if isinstance(password, str) else password,
        salt.encode() if isinstance(salt, str) else salt, it, 32)

def dec_hex(key, hexstr):
    raw = bytes.fromhex(hexstr)
    return AESGCM(key).decrypt(raw[:12], raw[12:], None)   # 12-byte nonce prefix

def enc_hex(key, data):                                    # inverse — for forging objects
    n = os.urandom(12)
    return (n + AESGCM(key).encrypt(n, data, None)).hex()
```

PBKDF2 at 1e6 iterations is ~1 s in Python; fine for a handful of derivations, so derive once
and reuse.

**The question that decides severity: what are the KDF's `password` and `salt` made of?**
If both are values the API returns to any link holder (a folder name + a record id), then
"holds the link" == "can decrypt everything", and any endpoint that leaks the link's metadata
leaks the content. That is what turns a "share link" into a full read primitive.

## 3. Building real objects to test authorization

To test cross-tenant authz you need genuine objects, which means replaying the client's create
flow. The order matters and each step is a separate call:

```
1. token                       (passwordless or public)
2. POST /user  (profile)       {clientProtocolVersion, encryptedReadKey, keyRoot}
3. POST /mutablerecords/v2     (VOLUME record, self-referencing volumeMid)
4. POST /mutablerecords/v2     (DIRECTORY record, parentMid = volume)
5. POST /p2p/storage/chunk     (raw ciphertext, Content-Type: application/octet-stream)
6. POST /mutablerecords/v2/bulk (FILE record with chunks[].cID + encryptedBlockKey)
7. POST /sharerecords          {expiry, name, ownerAccountId, rootMid, users:[{userAccountId:"*"}]}
8. POST /metadata              {shareRecordId, ...}   -> the /dl/{id} link
```

Notes that cost time:
- `ownerAccountId` must be the caller's own `userAccountID` from `GET /user`; a mismatched or
  null value returns 403/400 and the error text names the field.
- Content-addressed CIDs are computed by the **server**; a client-supplied `HashCID` header is
  ignored (verified: uploading different bytes with a victim's CID left the victim's chunk
  intact). So chunk poisoning via header spoofing is a dead end — record it as a negative.
- A 5xx on step 8 usually means a **missing prerequisite**, not a server fault. `503 "Could not
  verify the share record contents"` disappeared once the caller had a profile.

## 4. Provisioning accounts and reading the verification mail

Passwordless signup is the cheapest path and needs no manual step:

```
POST /auth/passwordless/start/   {"email": "you+alias@gmail.com"}  -> 200 EMAIL_VERIFICATION_SENT
POST /auth/passwordless/verify/  {"code": "<6 digits>", "email": …} -> 200 {"access_token": …}
```

**IMAP pitfall (cost three debug cycles):** `mb.fetch(reverse=True, limit=N)` scans only the N
most recent messages, and a mailbox busy with verification codes hides the one you want — the
script then reports "mail not found" for mail that was delivered. Search by sender:

```python
from imap_tools import MailBox, AND
with MailBox("imap.gmail.com").login(USER, PW) as mb:
    for m in mb.fetch(AND(from_="vendor.com"), reverse=True, limit=40, mark_seen=False):
        ...
```

Codes are bound to the e-mail and single-use (verified: another address's code → `INVALID_CODE`;
replay → `INVALID_CODE`), so there is no cross-account code reuse.

## 5. Evidence hygiene for this class of work

Script logs contain lines that *look* like failures and are not. Seen live, all four:

| log line | real cause |
|---|---|
| `mail to third party: False` | search window too small (§4) |
| `503 Could not verify the share record contents` | caller had no profile yet (§3) |
| `400 ownerAccountId is not nullable` | victim's profile did not exist |
| `403 Storage quota exceeded` on the attacker's token | quota charged to the creator; the cross-tenant write itself succeeded |

**Rule:** next to any artefact a future reader could misquote, write `<name>_NOTE.txt` listing
each misleading line, its real cause, and the file holding the authoritative evidence. Without
it, a "0 of 2 successful" log gets read as a failed validation days later — which is exactly how
a proven finding loses its own proof.
