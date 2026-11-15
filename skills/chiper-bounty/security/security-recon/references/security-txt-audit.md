# security.txt (RFC 9116) Audit

Two uses, same checklist:

1. **Standalone deliverable** — user says "audit https://target/.well-known/security.txt".
2. **Start-of-engagement surface read** — you fetch it anyway for the `Policy:` line
   (see `references/program-scope-intake.md`). While you're there, audit it.

The file is short; the findings are almost never IN the file — they're in what it
*connects to*. Lead with those.

---

## Step 1 — Conformance (fast, mostly PASS)

Fetch `https://<host>/.well-known/security.txt` (and `http://` — must 3xx to https).

| Field | RFC 9116 | Check |
|---|---|---|
| `Contact` | required | valid `mailto:` / `https:` URI, resolves |
| `Expires` | required | valid ISO-8601, **in the future**, ≤ ~1 year out |
| `Preferred-Languages` | recommended | valid BCP-47 tag |
| `Canonical` | recommended | matches the URL you actually fetched |
| `Policy` | recommended | **fetch it** → 200, and its anchors resolve |
| `Encryption` | recommended | usually missing → see Step 3 |
| `Acknowledgments` | extension | fetch + resolve the `#anchor` |

Transport: `Content-Type: text/plain; charset=utf-8`; no redirect at the canonical URL;
served from `/.well-known/`. Comments (`#`) are legal — don't flag them.

A clean file scores **nothing**. Move to Steps 2–4 for the real findings.

## Step 2 — The contact mailbox is the finding surface (do this every time)

The file advertises an address the world is told to trust with vulnerability reports.
**Audit that address's mail authentication** — this is the highest-value check and it is
routinely missed:

```bash
nslookup -type=MX <domain>
nslookup -type=TXT <domain>                 # SPF
nslookup -type=TXT _dmarc.<domain>          # DMARC
for s in default google selector1 selector2 dkim cf cloudflare mx key1 k1 s1 s2; do
  nslookup -type=TXT $s._domainkey.<domain> | grep -c 'v=DKIM1'
done                                        # DKIM selector sweep
nslookup -type=TXT _mta-sts.<domain>        # MTA-STS
```

Score the posture:

| Result | Verdict |
|---|---|
| `DMARC p=none` | **no enforcement** — spoofed mail from the report address is delivered. Finding. |
| SPF `~all` | softfail only — contributes to the above |
| no DKIM on any selector | messages unsigned — strengthens the above |
| no MTA-STS / no TLS-RPT | transport unprotected — informational |

**Why it matters:** the natural target is a researcher who just filed a report. A
follow-up "from the security team" asking them to re-send the PoC, move to a "secure
portal", or open an attachment is exactly the phishing kit a spoofable report address
enables. For a security/GRC vendor this is the one to lead with — the irony is the point,
state it factually, don't gloat.

## Step 3 — The file itself: encryption + signature

- **No `Encryption` field** and no `/.well-known/openpgpkey` → sensitive reports travel
  cleartext until a channel is arranged by back-and-forth. Low.
- **No signature** — `security.txt.asc` / `.sig` both 404 → a researcher cannot
  authenticate the file; DNS/BGP interception or a compromised origin could swap the
  `Contact` value and silently redirect reports to an attacker, undetectably. Low.
- A comment saying "we don't support PGP" is not a pass — it's the finding, stated by them.

## Step 4 — Dangling pointers and inconsistencies

- Does the `Policy` page actually contain the VDP, or does it 404 / redirect? (A `308`
  from a legacy path like `/security-policy/` to `/legal/security` is fine.)
- Does the documented location match the `Canonical`? An agent-facing index (e.g.
  `api./llms.txt`) pointing at `app.<host>/.well-known/security.txt` when the file lives
  at the apex — and the app host is behind a bot wall returning `429` — is a real finding:
  the documented location is unreachable.
- Hall-of-fame / credit mismatches between the repo `SECURITY.md` and the live policy
  (named in one, "anonymous" in the other) → privacy/consistency, informational.

---

## Reporting shape

This is a **document audit**, so results are Low/Info — that doesn't make them noise.
Order them: (1) mail-auth on the report mailbox, (2) encryption, (3) signature,
(4) dangling pointers, (5) consistency nits. Pair every finding with the concrete
remediation (add DMARC enforcement + DKIM; publish an OpenPGP key and add `Encryption:`;
sign and publish `.asc`; align the documented URL).

## Pitfall — reading the target's policy is not an authorization bypass

Auditing a *published public file* is always fine. But the same policy page often carries
scope rules and sometimes an explicit **"note for AI agents"** clause (this class of
target frequently adds one). Read it, quote it in your report, and stay inside it — if it
bans automated scanners, the deep dive goes manual/curated. See
`references/program-scope-intake.md` for the scope extraction this feeds.
