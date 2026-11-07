# Prior-Submission Recon — recovering what was already sent

Purpose: know, in under ten minutes, exactly what this vendor has already received from
you, what they answered, and which surface is therefore still open.

Worked against RunONFlux (77 vendor messages, 60 unique outbound reports) on 2026-10-27.

---

## 1. Refresh the mailbox token first

Gmail access tokens expire in ~1h. Refresh before the first call, or every query 401s:

```python
import json, urllib.parse, urllib.request
from pathlib import Path

TOK = Path.home()/"~/.chiper/skills/bounty-pack/google_token.json"
d = json.loads(TOK.read_text(encoding="utf-8"))
data = urllib.parse.urlencode({
    "client_id": d["client_id"], "client_secret": d["client_secret"],
    "refresh_token": d["refresh_token"], "grant_type": "refresh_token"}).encode()
with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data, timeout=30) as x:
    d["token"] = json.loads(x.read().decode())["access_token"]
TOK.write_text(json.dumps(d), encoding="utf-8")
```

Confirm the scope includes `gmail.modify` (or at least `gmail.readonly`). A
`calendar`-only token will 403 here — use the token under
`~/.chiper/skills/bounty-pack/google_token.json`, not `~/.hermes/`.

## 2. Three queries, metadata only

Metadata is enough to build the map and costs a fraction of full-message fetches.

```python
BASE = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
H = {"Authorization": "Bearer " + d["token"]}

def q(query, limit=100):
    url = BASE + "?" + urllib.parse.urlencode({"q": query, "maxResults": limit})
    r = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(r, timeout=40) as x:
        return json.loads(x.read().decode())
```

| Query | What it gives you |
|---|---|
| `to:security@<vendor>.com` | your own submissions |
| `from:<vendor>.com` | every vendor reply |
| `subject:<product>` | whether that exact surface was adjudicated |

**Search the domain, not one address.** A vendor with `security@x.com` and `security@x.io`
has two mailboxes; a `to:` query against one silently misses the other.

## 3. Classify direction by sender, then dedupe

Do not assume "in the thread" means "vendor wrote it". Classify on the `From` header:

```python
outbound = "your-own-address-fragment" in hd.get("from", "")
```

Dedupe case-insensitively on the first ~60 chars of the subject, and **collapse
supplements/corrections into their parent** — `"Supplement to Low: X"` and
`"Correction to F37"` are not new reports.

Measured: 77 messages → 60 unique outbound reports after collapsing duplicates.

## 4. Cross the reported-map against the scope list

```python
reported = Path("_reported.txt").read_text(encoding="utf-8").lower()
scope    = [l.strip() for l in Path("inscope_subs.txt").read_text().splitlines() if l.strip()]

untouched = [h for h in scope if h.lower() not in reported]
```

A host whose name appears nowhere in 60 reports is surface the vendor has not adjudicated.
That set difference is the defensible novelty claim.

Measured: 263 in-scope hosts → 75 name-matched → **188 never named**.

## 5. Subtract before probing (this is where the wins disappear)

The 188 is not a target list. Remove, in order:

1. **Policy-excluded third parties.** Docs, wiki, games panels, status pages, SaaS
   dashboards, mirrors, and anything whose policy wording excludes third-party operation.
   RunONFlux excluded these explicitly; most briefs do.
2. **Thin services.** A host whose only live route is `/health` yields nothing.
3. **Wrong-owner hosts.** Verify by DNS + TLS + the API base the bundle calls:
   - DNS: `socket.getaddrinfo(host, 443)` — is the IP in the vendor's range?
   - TLS: `openssl s_client -connect host:443 -servername host` — what CN does it present?
   - Bundle: grep for absolute URLs; the real backend may be another company entirely.

Worked example — `awx.<target>.com` resolved to a Hetzner IP, presented a certificate with
`CN=topy.az`, and served a byte-identical copy of `topy.az`. That is **not** the target's
software: it is a third-party site on a target subdomain. Reportable as a DNS-delegation
finding about the target; **not** as "we found an admin panel".

Counter-example — `admin.<target>.com` served a Next.js panel whose bundle called
`https://api.<othercompany>.tv`. The panel is a third-party product. OUT of scope, not
tested, not reported.

## 6. Read the vendor replies as an acceptance taxonomy

Not a summary — quote it. The replies contain the program's real payout logic.

From 7 RunONFlux replies, the paying shape and the four non-paying shapes:

| Reply fragment | Verdict |
|---|---|
| "valid, and you were the first to report it ... reward is N FLUX" | **pays** |
| "already covered by our internal security audit" | never pays (severity irrelevant) |
| "reported before you" / "already known to us" | duplicate |
| "by design" / "deliberate compatibility mode" | not a bug |
| "hardening rather than a vulnerability" | not a bug |
| "valid, but another researcher reported it before you" | duplicate |

Practical consequence: **novelty dominates severity.** Ten reports can be rejected on
adjudication status while one Low is paid because it was first. Allocate effort to
un-adjudicated surface, not to re-arguing grade.

## 7. Extract the conduct constraints too

The same batch reply that graded Titan Low also said: *"please keep live testing to your
own accounts and data ... For the Titan report you queried other users' staking and payment
records on production. Please don't do that, and please don't keep or share that data."*

That is a hard boundary for every following round. It also reframes the next step: the
correct response is not to stop the engagement, it is to (a) stop reading other users'
objects, (b) provision an own account, and (c) if provisioning is closed, move to surface
that does not require one — stating plainly why the authenticated surface is unreachable
rather than implying it was tested.

## Pitfalls

- **A "Bug Bounty Report - PGP Encrypted" subject carries no product name.** It will not
  name-match a host. Open the body (or the attachment list) to learn which product it was,
  otherwise its surface looks untouched when it is adjudicated.
- **`resultSizeEstimate` is an estimate.** It read 201 for queries returning 15. Use the
  returned message ids, never the estimate, for counts you intend to quote.
- **`in:anywhere`** is needed when a report may have been archived or filed by a filter.
- **Do not trust a body parsed out of HTML mail without stripping `<style>`/`<script>`
  first** — tracking pixels and font tables inject digits that look like content.
