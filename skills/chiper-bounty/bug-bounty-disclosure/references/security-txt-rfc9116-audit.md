# security.txt (RFC 9116) audit — and the surface it points at

When the request is *"audit https://&lt;host&gt;/.well-known/security.txt"*, the artefact is public, so reading
it is always in scope. It usually resolves into two deliverables: (a) the file's own RFC 9116
conformance, and (b) a review of the public edge that the policy it links to actually authorises.

## 0. Read the linked policy FIRST — it is the scope

The `Policy:` field leads to the vendor's VDP, which states what testing is authorised. Bind to it
before touching anything else (see `vendor-vdp-submission.md` §1, including the AI-agent clause). The
security.txt review itself needs no authorisation — the file is public — but everything past it does.

## 1. Field conformance

Required (RFC 9116 §2.5):
- `Contact` — one or more, typically `mailto:`.
- `Expires` — MUST be a future ISO 8601 timestamp; the file is meant to expire within a year.

Recommended / common:
- `Canonical` — the URL it is served from; must match reality.
- `Policy` — link to the disclosure policy; must resolve.
- `Acknowledgments` — link, often with a `#hall-of-fame` anchor. Verify the anchor exists in the HTML.
- `Preferred-Languages` — BCP 47 tag(s). `en-NZ` beats bare `en` for an NZ-registered org.
- `Encryption` — see §3.
- `Hiring`, `CSAF` — optional.

`#` comment lines are legal and often carry the useful context (e.g. "we do not support PGP").

## 2. Transport + serving checks (cheap — do all of them)

```bash
curl -sI  https://<host>/.well-known/security.txt     # 200, Content-Type: text/plain
curl -sI  http://<host>/.well-known/security.txt      # expect 30x -> https
curl -sL  https://<host>/.well-known/security.txt     # fields parse, one per line, no dupes
curl -s   https://<host>/.well-known/security.txt | grep -c '^Encryption:'
```
- Canonical must serve directly (no redirect). `Content-Disposition: inline` is fine.
- Confirm each linked URL 200s, and that a fragment anchor really exists.

## 3. The two findings that actually matter

1. **Unsigned file.** `.well-known/security.txt.asc` and `.sig` both 404. RFC 9116 §3.1 recommends
   PGP-signing precisely so a reader can detect tampering — without it, DNS/BGP interception or a
   compromised origin can swap the `Contact:` value and silently redirect reports to an attacker.
   PoC = the two 404s + the served file's sha256 (the only integrity value, and it is served over the
   very channel it is meant to protect) + a tamper test: a swapped `Contact:` line parses identically.
2. **No encrypted channel.** No `Encryption:` field and `/.well-known/openpgpkey` 404s, so the
   reporter's first contact — PoC, credentials, exploit chain — must travel in the clear until a
   channel is arranged (RFC 9116 §2.5.3).

## 4. The contact mailbox is part of the finding — check its own mail auth

The file names an address as THE trusted report channel. If that mailbox is spoofable the finding is
severity-relevant, not cosmetic:

```bash
nslookup -type=MX  <domain>
nslookup -type=TXT <domain>                 # SPF: ~all = softfail, -all = hard fail
nslookup -type=TXT _dmarc.<domain>          # p=none = no action; quarantine/reject = enforced
for s in default google selector1 dkim cf mail; do nslookup -type=TXT $s._domainkey.<domain>; done
```
`~all` + no DKIM + `p=none` ⇒ a message claiming `From: security@<domain>` is **delivered**. That is the
ideal kit for phishing a researcher who has *just* filed a report ("re-send the PoC", "move it to our
secure portal"). Lead with this when present. Contrast with the rest of the estate: the apex may carry
2-year HSTS + preload while the identity/login host carries `max-age=86400` — an outlier among
otherwise-strong hosts is worth one informational line.

## 5. Cross-check DNS claims before reporting them

Third-party mail/DNS checkers can be wrong. A DMARC bundle reported `<domain>` DNSSEC as broken
("parent publishes DS but the zone did not answer with DNSKEY"); three independent rounds found no DS
and every validating resolver resolved the name fine — a false positive. Confirm via DNS-over-HTTPS
before it reaches a report:

```bash
curl -s -H 'accept: application/dns-json' \
  'https://cloudflare-dns.com/dns-query?name=<domain>&type=DS'     # also DNSKEY; A with &do=true
```
`AD: true` on the answer means the resolver validated the chain — DNSSEC is fine. Record the *check*,
not the tool's claim.

## 6. The broader public surface (still policy-bound)

`security.txt` is an entry point, not the whole target. A no-auth sweep that stays inside a vendor VDP:
sub-domain map (certificate transparency via `crt.sh` / certspotter, plus a passive host pass), the
published OpenAPI / `llms.txt` / docs surface, security headers + TLS per host, in-scope public source
repos (secret sweep — `example.env` placeholders are a *good* sign, not a finding), and `/.well-known/*`
across every resolving host. Two outcomes recur and belong in the report as explicit negatives rather
than padding: **leftover sub-domains that no longer resolve are not takeoverable**, and **dev
sub-domains behind an SSO gate or refusing connections are not exposed**.
