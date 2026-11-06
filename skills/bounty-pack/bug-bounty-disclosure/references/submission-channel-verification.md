# Verify the submission channel BEFORE writing the draft (there can be more than one)

Learned the hard way on **Vana (2026-10-12)**: the same vendor published **two different addresses on two
different TLDs** in two authoritative places. Sending to the wrong one costs days and can bounce.

## The Vana case (concrete)

| Source | Address | Governs |
|---|---|---|
| `https://docs.vana.org/security/overview` (fetch `.md` for clean text: add `.md` to any Mintlify docs URL) | **dev@vana.org** | contracts + infrastructure (verbatim: *"a security vulnerability in Vana contracts or infrastructure"*) |
| `https://raw.githubusercontent.com/vana-com/personal-server-ts/main/SECURITY.md` | **dev@vana.com** + subject `[SECURITY] personal-server-ts - <desc>`, SLA 48 h ack / 5 d assessment / 90 d fix / credit in release notes | that one repository and its workspace packages only |

Both domains had live MX (`nslookup -type=MX` -> `aspmx.l.google.com` Google Workspace), so both *can* receive
mail. Only the policy that covers **your asset class** is the right one. Docs policy also stated the required
report contents (component + version/commit, repro steps, impact/severity, logs/PoC) and *"do not disclose
findings publicly until the issue has been addressed"* — **no safe-harbour clause and no reward programme**.

## Checklist (run this before the first draft)

```bash
# 1) the policy page for YOUR asset class (docs sites often serve clean markdown at <url>.md)
curl -sL "<policy-url>" | sed -n '/[Rr]esponsible disclosure/,+25p'      # or fetch <url>.md
# 2) every SECURITY.md / security.txt in the estate - they can disagree with each other
curl -s https://raw.githubusercontent.com/<org>/<repo>/main/SECURITY.md
for h in <host1> <host2>; do for p in /.well-known/security.txt /security.txt; do
  curl -s -o /dev/null -w "$h$p %{http_code}\n" "https://$h$p"; done; done
# 3) does the address actually exist (null MX = domain cannot receive mail)
nslookup -type=MX <domain>
# 4) rule out a platform programme before assuming email
#    search HackerOne / Immunefi / Bugcrowd for the vendor; a security.txt absence + no program page => email
# 5) is there a submit portal?
curl -s -o /dev/null -w "%{http_code}\n" https://<apex>/security
```

## Rules that follow from it

1. **Use the channel named by the policy that covers the asset you tested.** A gateway/API/app finding goes to
   the docs-policy address; a finding inside a named OSS repo goes to that repo's SECURITY.md address.
2. **Prefer the security-prefixed subject.** If any published policy asks for a prefix (`[SECURITY] …`), use it
   on every draft even when the *other* policy does not ask — shared inboxes filter on it. Re-stage the drafts
   (delete the old ones first, then create with the new subject) rather than leaving two similar drafts.
3. **State in the email which policy you are submitting under** and quote its URL. It documents that you picked
   the right door and it makes the triager's job trivial.
4. **If the primary address bounces, the fallback is whatever the other published policy names** — never invent
   `security@`/`abuse@`, an unpublished address is a dead end.
5. **Record the decision**: write a `SUBMISSION-CHANNEL.md` in the engagement dir with the source URLs, the
   addresses, the MX evidence, the platform checks that came up empty, and which finding goes to which address.
   The next session (or the operator) then never has to re-derive it.
6. **Report the required fields the policy lists** (component + version/commit, repro, impact, logs/PoC) even if
   your own template is shorter — vendor policies get checked mechanically by triage tooling.

## Where the drafts live afterwards

`references/gmail-draft-via-api.md` (create) + `references/gmail-draft-rest-verification.md` (prove the PDF
attachment survived: `body.attachmentId`, not `body.data`; sha256 vs the local file; exactly one draft per
finding subject). Operator sends them one at a time — staging is not sending.
