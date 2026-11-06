# Turning a Low authorisation primitive into High: sibling enumeration + identifier-consumer chaining

Worked from the Hivenet engagement (2026-10-26), where a "missing ownership check" that scores
Low on its own became a High with a full confidentiality chain. Two moves did it. Both are
reusable on any web2 SaaS with a resource-identifier API.

---

## Move 1 — enumerate the sibling generations and same-shaped endpoints

A missing authorisation check is rarely alone. When you find one on endpoint X, immediately test:

| Sibling to test | Why it matters |
|---|---|
| The **other API generation** of the same resource (`/records` vs `/records/v2`, `/v1/x` vs `/v2/x`) | Legacy routes are often kept for old clients and never got the ACL the rewrite added. Hivenet: `POST /mutablerecords/v2` returned `403 User does not have access to this V2 document`; `POST /mutablerecords` (v1) accepted any `volumeMid`/`parentMid` and returned `201`. |
| The **bulk / batch** variant (`/x/bulk`, `/x/batch`) | Sometimes only the single-object path checks. |
| The **read** and **update** paths of the same object | Hivenet v1 GET/PUT were correctly authorised (`403`), which proved the gap was create-only — a much sharper root cause for the report. |
| The **same field name on a different resource** | `shareRecordId` was checked on `/sharerecords/*` but not on `/metadata`. |

Record the contrast in the report ("the current API enforces it, the legacy one does not"). It is
the difference between "authz bug" and "authz bug with a precise root cause and a one-line fix".

## Move 2 — chain the identifier to a consumer that amplifies it

The primitive is usually "I can name an object I do not own". Ask: **what else consumes that
identifier, and does that consumer trust it?** Enumerate the consumers before scoring the finding.

Hivenet chain (proved, 4 runs):

```
POST /metadata {shareRecordId: <victim's>}      -> 200   (no ownership check)
  sender identity taken from the CALLER's token -> attacker recorded as sender
  recipients in the same request                -> Hivenet e-mails an arbitrary third party
                                                    from no-reply@hivenet.com, subject names
                                                    the attacker, link resolves to the victim's
  third party (anonymous public token, link only)
    readKey  = PBKDF2-SHA512(pw = share.name, salt = share.rootMid, it = 1e6)
    blockKey = AES-GCM-decrypt(readKey, share.users[0].encryptedReadKey)
    GET /mutablerecords/{root}/children -> chunk CID + encrypted chunk key
    GET /p2p/storage/chunk/{cid}        -> ciphertext
    AES-GCM decrypt                     -> the victim's file, byte for byte
```

The amplifier was the **vendor's own e-mail infrastructure**: a trusted, DKIM/SPF-aligned sender,
attacker-chosen recipient list, attacker-chosen subject line, and a working link. That is what
moved the score from "integrity nuisance" to High.

### Named patterns worth grepping for

- **Claim-then-lock** — a resource with *no row yet* is claimable by the first caller, and the real
  owner is then locked out (`409 duplicate` afterwards, including for them). Always test the
  "row does not exist yet" state; it is a different code path from "row exists and is mine".
- **Public-identifier-as-capability** — if the identifier is handed to every recipient and returned
  by a public read, it is not a secret, so any endpoint that treats it as an authorisation token is
  broken by construction. Check whether the id leaks through a public read before claiming the
  attacker "could not have known it".
- **Vendor-infrastructure amplification** — mail, webhooks, notifications, PDF/report generation.
  Any of these reachable with an attacker-supplied identifier turns a write primitive into a
  phishing or spam channel with the vendor's domain reputation.
- **Key derivation from public metadata** — `PBKDF2(public_field, public_field)` means "anyone with
  the record can decrypt". If the record is readable with an anonymous token, the encryption is
  decorative. Test it by actually deriving and decrypting.

## Verifying the async hop properly (a false negative that cost a round)

The e-mail in the chain above was reported as "not sent" because the verification searched the last
8 messages with a `from_` substring filter — the mailbox was full of verification codes and the
transfer mail sat outside the window. Correct pattern:

```python
from imap_tools import MailBox, AND
with MailBox("imap.gmail.com").login(user, pw) as mb:
    for m in mb.fetch(AND(from_="hivenet.com"), reverse=True, limit=40, mark_seen=False):
        links = re.findall(r'https://send\.hivenet\.com/dl/[0-9a-f-]+', (m.html or "") + (m.text or ""))
        if any(poison_id in l for l in links): ...
```

Search **by a unique id you planted** (the metadata id, the record id), with an explicit IMAP
criteria and a generous window. Never conclude "the side effect did not happen" from a short
reverse-order scan.

## The chain table for this engagement (what died, and the fact that killed it)

```
CHAIN A — anonymous public token -> enumerate machine-account share records -> mass decrypt
  Step 1 token reachable by an unauthenticated visitor?        HOLDS (/auth/download-token, 200)
  Step 2 does the machine account have share records to list?  DIES
         GET /sharerecords (with and without ownerAccountId) -> 404 "share records not found";
         the 93 volumes / 41 dirs / 282 files it does own carry no key material
  => DIES AT STEP 2. The shared "public" account is a download-only identity, not a content owner.

CHAIN D — cross-tenant record create (F1) -> victim storage-quota exhaustion (DoS)
  Step 1 can the attacker write into another tenant's volume?  HOLDS (201)
  Step 2 is the quota charged to the volume owner?            DIES
         verbatim: 403 "adding 3221225472 bytes to the 3091202586 used of 3221225472 bytes"
         while the victim's own 5 MB writes still returned 201
  => DIES AT STEP 2. Quota is charged to the creator, so F1 stays an integrity finding, not a DoS.

CHAIN C — metadata claim -> vendor e-mail relay -> third-party content read
  Step 1 attacker can name a shareRecordId it does not own?  HOLDS (200, no ownership check)
  Step 2 does the vendor act on it (send mail)?              HOLDS (mail to arbitrary recipient)
  Step 3 can the recipient reach the content?                HOLDS (derived key, decrypted)
  => L5 PROVED. Reported as its own High.
```

Note the shape: the chain that paid was the one where the *identifier* was the entry point and the
*vendor's own service* was the amplifier. The two that died both died on a fact I could quote
verbatim from a response body — which is what makes a "DIES" defensible rather than a guess.
