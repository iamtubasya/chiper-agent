# Severity Scorer False Positives — text heuristics and their guards

Any scorer that reads *prose* to grade a finding is a heuristic, and heuristics on security
notes lie in predictable ways. Every entry below was a **real wrong grade on live data**
(RunONFlux + local fixtures, 2026-10-27). Read this before trusting a score, and before
adding a new marker to a scorer.

The failure mode is symmetric and both directions are expensive:
**over-claim** burns validity ratio with the triager; **under-claim** makes you drop a real
High as "Info".

---

## A. Substring collisions — the marker matches inside another word

The single most frequent bug. A short token like `rce`, `hash`, `root`, `shell`, `credit`
appears inside ordinary English.

| Marker | Matched | Real meaning | Consequence |
|---|---|---|---|
| `rce` | `enfo**rce**`, `resou**rce**` | nothing | IDOR classified as **RCE** |
| `hash` | `signature**Hash**` | a signature, not a credential | read-only IDOR → **Critical** |
| `credit` | `first**Credit**` | a date field | fake money-impact signal |
| `root` | `web **root**` | a path | `.env` exposure → **RCE** |
| `shell` | `Next.js **shell**` | the SPA catch-all page | empty page → **STRONG** |

**Guard.** Short tokens require a word boundary, never a bare `in` test:

```python
SHORT_TOKENS = {"rce", "iam", "pii", "root", "header", "hash", "secret",
                "balance", "financial", "billing", "payout", "earnings"}

def _has(t, m):
    if m in SHORT_TOKENS:
        return re.search(r"(?<![a-z0-9])" + re.escape(m) + r"(?![a-z0-9])", t) is not None
    return m in t
```

And prefer **specific multi-word forms** over generic nouns: `root shell` / `uid=0(root)`
instead of `root`; `webshell` / `reverse shell` instead of `shell`; `password hash` /
`bcrypt` instead of `hash`.

**Ask of every new marker:** could this string appear inside a longer word that means
something else? If yes, bound it or make it multi-word.

---

## B. Negation — "no X" counted as X

Every adversarial note contains phrases like *"no identity, no credential, no session
token"* precisely because the author is asserting safety. A naive scorer reads the marker
and grades the lead as if the artifact were present.

Observed three separate times, each producing a wrong grade:

- `"no secret"` → the public-bucket lead scored STRONG
- `"no identity"` → an on-chain-only leak kept its High
- `"no session token"` → a payout-bookkeeping lead kept Critical

**Guard.** A negation window before the marker invalidates it:

```python
NEGATORS = ("no ", "not ", "without ", "tanpa ", "bukan ", "non-",
            "tidak ada ", "cannot ")

def _negated(t, marker):
    i = t.find(marker)
    while i != -1:
        if not any(n in t[max(0, i-14):i] for n in NEGATORS):
            return False        # at least one un-negated occurrence -> valid
        i = t.find(marker, i + 1)
    return True
```

**Apply the same window to every derived predicate**, not just the strength score —
`creds_inside`, `used`, `wrote`. Forgetting one of them re-introduces the bug (this exact
omission kept a lead at Critical after the strength fix landed).

---

## C. Plan text read as evidence

`lead-escalation.json` carries fields that describe **what you intend to do**:
`technique` reads *"169.254.169.254 -> cloud credentials; gopher://redis -> cron"*. A
scorer that concatenates every field grades **every** lead as if the metadata service had
already been read. Every plan came out STRONG.

**Guard.** Split the field sets explicitly and only ever score the evidence half:

```python
PLAN_FIELDS = ("technique", "escalations", "to_class", "probes",
               "primitive", "depth_target")
EVIDENCE_FIELDS = ("title", "vuln_type", "reason", "signal", "evidence", "payload",
                   "description", "url", "endpoint", "class", "lead", "notes")
```

Generalisable rule: **a plan is not an artifact.** Whenever a data model mixes intended
actions with observed results, the scorer must be told which is which.

---

## D. Credential "used as a tool" vs credential "leaked"

`"GET invoice with user A token returned a foreign invoice"` — the token is **the
researcher's own**, the instrument of the request. A naive scorer sees `token` and jumps the
lead to Critical ("object contains credentials").

**Guard.** A credential counts only when an explicit exposure construction exists, and the
credential is not the caller's own:

```python
CRED = r"(?:token|session|cookie|jwt|api[_ -]?key|password|private[_ -]?key|" \
       r"reset[_ -]?link|secret|credential)"

exposure_patterns = [
    rf"(?:leak|expos|disclos|contain|includ|reveal|carr(?:y|ies)|return|"
    rf"exfiltrat|dump|embed)\w*\s+(?:[a-z'_-]+\s+){{0,6}}{CRED}",
    rf"{CRED}\s+(?:is\s+|was\s+|are\s+)?(?:exposed|leaked|returned|readable|"
    rf"present|in the (?:response|body|payload))",
]

OWN_CREDENTIAL = ("with token", "with my", "using my", "own token", "my own",
                  "authorization:", "with user a", "with account a",
                  "token returned", "token to fetch", "authenticated as")
```

Test pair that must discriminate:
`"with user A token"` → High · `"response contains the victim session token"` → Critical.

---

## E. Read-only scored as write

A read-only IDOR over a foreign object is **High**. Critical needs the ability to
change state, or an object that carries a live credential.

**Guard.** Gate on write markers before granting Critical:

```python
WRITE_MARKERS = ("put ", "patch ", "delete ", "updated", "modified", "state changed",
                 "wrote", "write succeeded", "deleted foreign", "berubah", "tersimpan")
```

Then: `if cls in ("idor","bola") and not wrote and not creds_inside: → High`.

---

## F. A gate that HELD scored as a lead

Eight bypass attempts on `/api/debug/*` all returned 403 — a clean verified negative. The
scorer still graded it High, because the note contained the word `secret` (from
`DEBUG_SECRET`) and a `403`.

This is the most dangerous class of false positive: it turns **your own failed attempts**
into a finding-shaped row.

**Guard.** Detect the gate-held phrasing and force `CAPPED-DROP`:

```python
GATE_HELD = [
    r"\ball (?:returned|gave|->|=>) ?40[13]",
    r"\ball returned 40[13]",
    r"gate (?:held|holds)\b",
]
```

**Keep the patterns numeric and specific.** A loose variant
(`r"no auth bypass proven"`) capped unrelated leads, because that phrase also appears as a
side note in reports that *do* have findings. A guard that over-fires silently deletes real
work — narrower is safer.

---

## G. Class mis-assignment from free text

Free-text scanning ran before the explicit field, so a lead with `vuln_type: "idor"` whose
evidence contained `"enforce"` was classified `rce` → graded Critical.

**Guard.** The explicit field always wins:

```python
def classify(text, explicit=""):
    e = (explicit or "").strip().lower().replace("_", "-")
    if e in CEILING and e != "default":
        return e
    ...  # only then fall back to text scanning
```

---

## H. Domain-specific: on-chain derivability (web3)

An unauthenticated IDOR exposed `payment_address`, `collateral`, `paid`, `tx`. The scorer
said High. The vendor said **Low** — *"payout bookkeeping that is largely visible on-chain
anyway"* — and the vendor was right.

**Guard.** If the evidence says the data is derivable from a public ledger and contains no
off-chain secret, drop one tier:

```python
ONCHAIN_DERIVABLE = [r"\bon[- ]?chain\b", r"\bderivable\b", r"\bpublic ledger\b",
                     r"\bblock ?explorer\b", r"\btxid\b", r"\bpayment_address\b"]
IDENTITY_SECRET   = [r"\bemail\b", r"\bkyc\b", r"\bsession\b", r"\bscoped?[_ -]?token\b",
                     r"\bapi[_ -]?key\b", r"\bpassword\b", r"\bpii\b"]
```

Only off-chain secrets — email, KYC, credentials, session tokens, identity linkage — hold
High/Critical on a ledger-visible dataset.

---

## I. Subdomain class: missing evidence, then over-claiming

Two failures in a row on the same lead:

1. **Missed it.** The evidence was "certificate CN=topy.az, Hetzner IP, byte-identical
   body" — none of the generic markers matched, so third-party content on a target
   subdomain scored Low.
2. **Over-corrected.** After adding those markers it scored **Critical**, with no OAuth or
   cookie impact demonstrated at all.

**Guard.** Third-party content on a target subdomain is **High**. Critical only with a
proven auth consequence:

```python
if cls == "subdomain":
    if re.search(r"redirect_uri|oauth (?:client|redirect)|cookie (?:scoped|scope)|"
                 r"set-cookie|session cookie", ev, re.I):
        reachable = "Critical"      # OAuth redirect_uri or parent-scoped cookie -> ATO
    else:
        reachable = "High"          # dangling/delegated content, no auth impact proven
```

---

## J. Counts that needed plural forms

`r"\b[1-9][0-9]+\s*(record|row|order|tenant)\b"` missed `"23 records"` — the singular form
silently disabled mass-evidence detection, so a 23-tenant BOLA read scored as thin evidence.
Always write `records?|rows?|orders?|tenants?`.

---

## Meta-rule

**Every one of these was found by running the scorer against real engagement notes, not
against fixtures.** The synthetic fixtures passed while the scorer was wrong thirteen times
on live data. Keep a real-notes fixture set, and re-run it after any marker change — several
of the fixes above regressed a different case until the regression set existed.

When a score disagrees with your judgement, the productive move is to read **which marker
fired**, not to override the verdict:

```python
import importlib.util
spec = importlib.util.spec_from_file_location("sc", "severity_ceiling.py")
sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)
print(sc.score(lead))          # markers are listed in the output row
```
