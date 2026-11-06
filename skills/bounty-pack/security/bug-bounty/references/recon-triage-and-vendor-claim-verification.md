# Recon triage + verifying a vendor's own advisory

Worked example: Superstate (2026-09-30 / 10-01). Rules here are class-level — they apply to any
SaaS/web3 disclosure target, and each one prevented a false report in that engagement.

## 1. One vendor ≠ one environment — enumerate environment codenames

Never assume the documented host is the only deployment. On Superstate the docs named `api.superstate.com`;
plain `subfinder -d <apex>` + `httpx` surfaced **`api.devddx.superstate.com`** — a fourth live environment
absent from every published page (its frontend `devddx.superstate.com` was Access-gated like the others, its
API was not).

- Fingerprint environments by **distinct data**, not by hostname. Pull the same public record from each host and
  diff it: prod `11.22883000` / staging `11.22883000` / dev `11.16069700` / devddx `11.01815200` proved four
  separate live deployments rather than DNS aliases.
- Enumerate environment codenames as subdomains: `dev`, `staging`, `test`, `preview`, `qa`, `uat`, plus
  whatever the org's own naming hints at (`devddx` came from their internal naming, not a wordlist).
- A cheap env-divergence detector: routes that exist **only** outside production. Here
  `POST /v1/accounts/onboard/{evm,svm}/mock` returned 404 on prod and 401 on all three non-prod hosts.

## 2. Wildcard DNS test — run it BEFORE trusting any subdomain hit

Two random labels decide whether your whole subdomain list is real:

```bash
python -c "import socket;socket.gethostbyname('zzz-nope-12345.<apex>')"   # expect NXDOMAIN
python -c "import socket;socket.gethostbyname('totally-random-9f3a.<apex>')"
```
- **NXDOMAIN ⇒ no wildcard ⇒ resolved hosts are real.**
- **Resolves ⇒ wildcard DNS ⇒ every scanner hit is suspect** and needs a content-level check.

This single test demoted 10 subfinder hits on Superstate (`eks.ci`, `eks.security`, `app`, `test`, `preview`,
`bbs`, `doc`, `mail`, `openpgpkey`, `assets-worker.devddx`) to NXDOMAIN false positives that would otherwise
have been written up as "internal hosts discovered". Report the list of dismissed FPs explicitly — it is part
of the evidence, not noise.

## 3. "DNS resolves" ≠ "service exists", and ≠ "takeover"

- `eks.dev.superstate.com` + `mail.eks.dev.superstate.com` DO resolve (Cloudflare edge IP) but serve no working
  HTTPS (`000`) — a dangling Cloudflare-**proxied** A/AAAA record.
- `nslookup -type=CNAME <host>` returning no CNAME answer means there is no third-party pointer. A dangling
  proxied record is **not** a subdomain-takeover candidate; only a dangling CNAME to an unclaimed third-party
  service is. Call it informational and move on.
- Run the takeover scan anyway and report the zero: `nuclei -l subs.txt -t "<mirror>/http/takeovers"`
  (77 templates here) → **0 findings** is a real, quotable deliverable.

## 4. S3/CloudFront: read the XML body, not the status code

A 403 on a bucket tells you nothing on its own:

```
<Error><Code>AccessDenied</Code>…      -> bucket EXISTS and is private. No takeover, no listing.
<Error><Code>NoSuchBucket</Code>…      -> bucket is GONE but DNS still points at S3 -> takeover candidate.
```
Probe `/?list-type=2` and read the body; never infer from the 403 alone. Here all four `assets.*` buckets
returned `AccessDenied` = correctly configured.

## 5. Before calling anything an exposure, check auth parity

An unauthenticated endpoint is only interesting if it *should not* be unauthenticated. Confirm the same
rejection appears on every host before writing "weaker auth on non-prod":

```bash
for h in api.<apex> api.dev.<apex> api.staging.<apex> api.devddx.<apex>; do
  curl -s -m 15 -w " [%{http_code}]" "https://$h/v2/transactions"; done
```
All four returned the identical `Missing API key [401]` → the finding is the *access-policy inconsistency*
(frontends behind Cloudflare Access, APIs open), severity Low, not an auth bypass.

## 6. Verify the vendor's OWN advisory independently

When a vendor publishes a SECURITY.md / incident note, verify it rather than repeating it. Recipe used on the
`superstateinc/request-with-api-key` supply-chain advisory:

1. Publish dates per version — `curl -s https://registry.npmjs.org/<pkg> | python -c "…print(d['time'])"`.
   Claim was "last published 2025-08-01, before the 2026-01-16 malicious commit" → dates confirmed it.
2. Download **every** affected tarball, extract, and grep for the payload's fingerprints
   (`atob(`, `eval(`, the C2 hostnames): `api-key-request-0.1.{0..4}.tgz` → 0 hits in all five.
3. Check for smuggled secrets — `.env.example` in 0.1.0 contained only empty placeholder keys.
4. Report **VERIFIED / NOT VERIFIED / CANNOT DETERMINE** — with the version list and the counts. A vendor claim
   you confirmed is worth reporting back; one you cannot confirm must be labelled, not parroted.
5. Secret-scan the full history, not HEAD: `trufflehog git file://<repo> --json` plus a regex pass over
   `git log --all -p`. Distinguish placeholder from real value for every hit.

## 7. Handling a malicious artifact you have to look at

- **Decode in memory and print. Do NOT write a decoded payload to disk.** On Windows, Defender quarantines it
  out from under you: `open()` on the file you just wrote fails with `OSError: [Errno 22] Invalid argument`
  (and a later `os.remove()` raises `WinError 2`). Errno 22 on a file that `os.path.getsize()` says exists is
  the AV tell.
- Never execute it, and **never contact the attacker's C2 or the chains it reads from** — resolving a dead-drop
  address is interacting with attacker infrastructure. Say in the report that you did not.
- Read the loader honestly: a downloader that fetches stage 2 from a chain does **not** prove the vendor's claim
  that "it read credentials and exfiltrated them" — that behaviour lives in stage 2 you cannot retrieve. State
  what the loader does and label the rest unverified.
- Keep the *base64 source* (public repo blob) as evidence, not the decoded form.

## 8. Scanner label ≠ finding — triage before it reaches findings.json

aderyn reported 3 × "High" on Superstate's contracts; **all three were false positives**, each killed by
reading the code:

| aderyn finding | why it is a false positive |
|---|---|
| "ETH transferred without address checks" | flags the `redeem()` functions; they pull tokens from `msg.sender` and pay USDC, and `receive()`/`fallback()` revert so the contract holds no ETH |
| "Arbitrary `from` passed to `transferFrom`" | `ERC20Upgradeable.transferFrom({from: src, …})` inside a standard `transferFrom(src,dst,amount)` that spends the allowance first |
| "Storage array edited with memory" | the helper is `internal pure` and only compares keccak hashes; the real write is on the next line |

Also seen this engagement: a tool's failed run overwriting the evidence file of a successful one — give each
attempt its own filename and verify by content marker + mtime (see pitfall 8 of `onchain-source-recovery`).

## 9. Close the loop on your own findings

Before drafting a report, adjudicate by-design from the vendor's own tooling. A "fresh deploy is broken"
finding collapsed once their deploy scripts showed the flow is v1-then-upgrade only (full recipe in the
`onchain-source-recovery` skill). Withdrawing your own severity claim with cited evidence costs nothing;
shipping a false positive costs credibility on the next report.

## 10. Three more recon false-positive classes (Cabify engagement, 2026-10)

### 10a. A wildcard at the REGISTRABLE-DOMAIN level means the domain is not your target's at all
§2's random-label test normally demotes individual scanner hits. Its stronger reading: if a random label
resolves, the *whole domain family* may belong to a third party, and then **none** of it is in scope.

```bash
python -c "import socket;print(socket.gethostbyname('zzz-definitely-not-real-92731.<domain>'))"
```
On Cabify, `zzz-definitely-not-real-92731.cabify.net` resolved to `185.53.179.200` — the same parking IP
every `*.cabify.net` name resolved to. Confirmation: `https://www.cabify.net/` returned 200 titled
*"cabify.net - Domain For Sale"*, and RDAP showed an unrelated registration (2020-01-08, expiry 2027-01-08).
So `gitlab.cabify.net`, `phpmyadmin.cabify.net`, `backstage.cabify.net`, `connectvpn.external.cabify.net`
were **not Cabify assets** and were never tested. `*.cabify.com` in the same run had **no** wildcard, so its
resolved names were real.

Recipe: random-label test per registrable domain → if it resolves, fetch the apex and read the title, then
check the registry RDAP for registration dates before spending a single request on any host under it. Write
the dismissed family into the scope section — a scope correction you documented is evidence of discipline.

### 10b. A generic-name bucket hit is not ownership evidence — read the object keys
Name-guessing S3 (`<stem>-{assets,backup,dev,logs,data,media,…}` plus bare words like `brand`, `exports`,
`videos`) produced 51 "interesting" responses. Reading the bodies settled all of them:

- `403 <Code>AccessDenied</Code>` on a **generic** name proves a bucket exists *somewhere* — not that it is
  your target's. It is not a finding and not even useful signal.
- Four buckets returned a real `ListBucketResult` (publicly listable). Their contents belonged to **other
  companies**: `brand` → another firm's favicons, `marketing` → a US bootcamp's testimonials, `videos` →
  Portuguese media, `exports` → empty. **None were reported.**
- Rule: before writing "publicly exposed bucket", pull `?list-type=2&max-keys=8`, print the `<Key>` values,
  and look for the target's own name/brand/data in them. Only same-org content counts.

### 10c. Archive sources (gau / waybackurls) are historical — verify every lead before planning around it
`gau --subs <apex>` returned 21,749 URLs and the four juiciest patterns were exactly what you would chase
first: `api.<apex>/.well-known/ai-plugin.json`, `tableau-legacy.<apex>` (legacy BI with SAML endpoints),
`assets-fix-me.<apex>` (a host leaking the app's JS source tree — `Login.js`, `epics/`, `reducers/`), and
`www.test.<apex>`. **Three of the four were already dead**: the ai-plugin manifest 404'd, the other two were
NXDOMAIN. Only the archive said they ever existed.

So treat the archive as a *hypothesis list*, not an endpoint list: batch-resolve the hostnames
(`socket.gethostbyname`) before touching them, then spend one request per survivor. Same rule the sibling
skills apply to `httpx` output — a hit is a candidate until a live response confirms it.

### 10d. Bonus: an egress-scoped block looks exactly like a hardened target
If the apex 429/403s while sibling hosts answer normally, that is an *address* problem, not a target
posture — and it will make every target look hardened until fixed. Classification table + the pre-flagged
VPN-pool check live in the `bot-protected-target-testing` skill (§3a-0).
