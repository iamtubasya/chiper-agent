---
name: bwallet-audit
description: bWallet/bWalletX (b-Aware) — scope, email channel, reward tiers, the ~40-row dedup map of already-fixed reports, and what round 1 verified sound. Load when resuming the bwallet engagement.
---

# bWallet / bWalletX — b-Aware bug bounty

Program v3 (25 Oct 2026). Source-code track: the asset is the repo, not a host.

## Channel and rules (exact)
- **Email `support@bwalletx.com`, subject MUST be `b-Aware`.** Not GitHub issues, not a web form.
  Put the whole report in the mail. "Steps we can run beat a video."
- **Check `https://bwalletx.com/bugs` first** — listed = credit only, not money. Unfixed serious ones are
  deliberately NOT listed, so absence proves nothing.
- Never send a seed / private key / password. Demo on a throwaway wallet. Own wallets, own funds only.
- Rewards in BSV, **pool 20 BSV/quarter**, first valid report wins. Reward table:
  **Critical 10** (steal/spend funds, extract keys or recovery phrase, sign without owner approval) ·
  **High 3** (bypass an approval or permission, forge a pairing or connection, drain via a dApp endpoint) ·
  **Medium 0.5** (leak private data, **defeat the safety filter**, deny a user their own wallet) ·
  **Low = credit only** (no money at all). Under 1 BSV a handle+paymail is enough; High/Critical need
  real name + country.
- Out of scope: marketing sites, rate limiting, missing headers, self-XSS, rooted/jailbroken device,
  physical access, social engineering, and **services they do not run** (indexers, exchanges incl.
  `txblaster.xyz` / the Memepool server, HandCash, the Yours Wallet upstream).

## Known-and-accepted (do NOT report)
1. DNS rebinding of an app's own origin (browser cannot pre-resolve DNS; fetch pinned to the site's own
   HTTPS origin, no redirects).
2. "Connected wallets hold operating balances" — a BRC-100 wallet signs what its owner approves.

## Advisories already answered (dedup)
- 20 Oct 2026 SSRF hardening of BRC-100 manifest fetching (bsv-desktop#135) — **not affected**.
- 23 Sep 2026 GHSA-qp3j-h5xf-p2p7 (ts-stack trust boundary) — ships patched versions.
- 6 Jul 2026 GHSA-36f9-7rg5-cpf8 / CVE-2026-56744 createAction output redirection — patched
  (`@bopen-io/wallet-toolbox-client` 2.14.5).
- Public /bugs also lists: pairing channel takeover (fixed **server-side**), "show my 12 words asked for a
  password you never set" (5.2.41), coins-spent-elsewhere inflating balance (5.2.36). And the Chrome Web
  Store build runs **5.2.18**, older than the 5.2.38 fix — known, so credit only.

## The dedup map (≈40 closed b-Aware rows) — a candidate matching any of these is a duplicate
Rebuild it in one command before hunting; do not trust memory:
```bash
git clone --depth 1 https://github.com/bitcoin-corp/bwallet && cd bwallet
git fetch --unshallow --filter=blob:none        # depth-1 hides the history you need
git log --oneline -140 | grep -iE "fix|security|b-?aware|guard|cap|limit|race|grant|allow|permission|origin|sign|audit"
rg -n "security review [A-Z][0-9]|payment-safety audit|audit [A-Z][0-9]|b-Aware" src | head -40
```
Rows already closed include: admin-originator spoof (H1), pairing relay pinning + per-channel grants,
reserved wallet protocols (C1), level-0 and BRC-29 raw-hash signing (24 Oct), allowance per-payment cap +
payee allowlist (B2), stream-grant budget race (#102), paymail re-derive-before-sign (#97), master-restore
strand guard (#93), cross-site sign relay (#108/#81), bMail double-pay, sweep fee cap, reconnect gate,
late sheet join, token decimals bound, safety-filter nesting walk.

## Prior findings already staged — CHECK THE MAILBOX BEFORE HUNTING
`[Gmail]/Draf` already holds six earlier b-Aware drafts from previous sessions on this target:
`bwallet-L2-03-poc.pdf`, `bwallet-L2-04-poc.pdf`, `bwallet-L4-C1-poc.pdf`, `bwallet-L4-C2-poc.pdf`,
`bwallet-L4-C3-poc.pdf`, `bwallet-L5-C3-poc.pdf`. List them before deriving anything, or you will
re-discover a filed bug. Their subjects name the classes: L2 pre-ticked Remember / don't-ask-again storing a
90-day allowance; L4-C1 Memepool sells bypassing the spending kill switch; L4-C2 buy funding stranded on a
pre-submitted coin; L4-C3 proof-of-reserves gate self-attested; L5-C3 unverified paymail destination paid.

⛔ **Never delete drafts by the `b-Aware:` subject prefix.** The folder is shared with every other finding
for this program, so a prefix delete wipes unsent sibling reports. Delete by the **uid** of the draft you
just created, and assert the wanted set still exists afterwards.

## Spending kill switch coverage (verified 2026-10-25, still open at HEAD)
`src/mobile/config/killSwitch.ts` `guardSpending()` wraps exactly `createAction` and `signAction`.
A Memepool **sell** reaches neither: `prepareSell` → `prepareAndVerify` build the tx locally,
`executeTrade` → `signOurInputs` → `wallet.createSignature`, then `submitTrade`. So a sell is not paused while
a buy (which calls `createAction` in `fund`) is. Generalise the check: **for every money path, list which
guarded method it actually reaches** — a path that signs directly with `createSignature` skips a guard built
on `createAction`/`signAction`. That gap is already filed (L4-C1), so do not re-report it.

## Round 1 (2026-10-25) — what was verified SOUND (do not re-derive)
- `services/adminOriginator.ts` — `id` **and** `origin` must both match; web build is lenient on `url`
  only because the hub is the sole stamper; `reservedOriginatorRefusal` kills `http://<extid>/`.
- `background.ts` router — 8 ordered refusals before any prompt; `noAuthRequired` opens only
  `IS_AUTHENTICATED` + `GET_VERSION` to sites.
- `services/reservedProtocols.ts` — FNV-1a hashed reserved set; level-0 `createSignature` refused; BRC-29
  raw-hash refused; the **data path** (`sha256(data)` == sighash) covered.
- `bappFrame/frameBridge.ts` + `BappFrameHost.tsx` — `e.source === iframe.contentWindow` **and**
  `e.origin === session.origin`; exact-origin allowlist; CSP `frame-ancestors` parser.
- `vite.config.mobile.ts` `FRAME_SHIM` — injected only into non-shell overlay entries.
- `services/allowanceGuard.ts` — only ever escalates to a prompt; NaN-safe.
- `pair/protocol.ts` — ECDH+HKDF, AES-GCM, AAD binds `role|seq`, monotonic seq, relay pinned.
- `passkey/extHandoff.ts` + store — exact origin, one-time nonce, expiry, one attempt then burn.
- `ChromeStorage.service.ts` changePassword — refuses outright with USB security on, so a re-key can never
  silently drop the USB master factor; `verifyPassword` fails closed in the worker.
- Memepool (`src/mobile/exchange/memepool/*`): `validate.ts` treats the template as fully untrusted
  (canonical script rebuild, forced `SIGHASH_ALL|FORKID`, conservation, exact fees, pool pinning, 1 BSV
  cap, NaN-safe limits); `sign.ts` re-derives the key pkh against the coin lock before signing; `wallet.ts`
  uses fresh keys per trade.
- `dangerouslySetInnerHTML` = **0** occurrences in `src`; no innerHTML sinks in approval pages.

## Round 3 (2026-10-25) — paymail, sweep, kill-switch blast radius

### paymail — reviewed, defensible (do not re-derive)
`utils/paymailDestination.ts` `checkP2pDestination` re-derives each P2P script from the payee identity key and
refuses mismatches, mixed derived/underived output sets, and any derivation it cannot compute (b_feedback 67 /
GHSA-36f9 class). Missing derivation ⇒ `{ok:true, verified:false}`; `utils/guardedSendBsv.ts:178` refuses that
for OUR domain and passes it through as `unverified[]` for third parties.

ⓘ **Latent hazard worth remembering (not a bug today):** `checkedDestination` resolves the key as
`str(req.identityKey) ?? payeeKey(...)` — a request-supplied key beats the resolved one, which would make the
check circular (host's script + attacker's key both attacker-chosen, so re-derivation always "matches").
**No caller in the tree sets `identityKey`**, so it is dead. Re-check if a future change feeds it from a dApp.

`names.ts` checks the signed binding only when `!r.external && r.pubkey` (binding only exists for our domains);
`checkOrdProof` returns `'bad'` for a malformed proof and `'none'` only when the field is absent; `destinationCheck`
then marks a token send `unverified` and the pay sheet renders `NOT_VERIFIED_NOTE`. That is a documented design
decision ("'unverified' puts NOT_VERIFIED_NOTE on the pay sheet") — a warning-by-design, not a silent bypass.

### sweep — reviewed, destination cannot be attacker-influenced
`runGuard.ts` holds back Run-jig outputs (1 / 273 / 546 sats) by reading the source tx and treats an unreadable
source tx as unsafe (fail-closed). `sweepKeys.ts` signs each input with the WIF of the address it was found at
and throws — nothing signed — when an input has no known owner. Sweep destinations are locally derived keys
(`key.toAddress()` in `relayxListing.ts` / `relayxRecover.ts`), so no host or caller can steer swept value.
Still unread in depth: `scanner.ts`, `chainReads.ts`, `npgMelt.ts`, `runIdentify.ts`, the body of
`relayxListing.ts`.

### ⛔ Kill switch — the guard is on the wrong seam (amplification of filed L4-C1, do NOT re-file)
`config/killSwitch.ts` `guardSpending()` wraps exactly **two** wallet methods: `createAction` and `signAction`.
Ten money paths sign with `createSignature({hashToDirectlySign})` directly and therefore never reach
`assertNotPaused('spending')`:

    exchange/memepool/sign.ts            <- the filed L4-C1
    locks/tokenEscrow.ts
    locks/tokenEscrowApi.ts
    market/launchpad/tokens.ts
    placement/partnership/actions.ts
    placement/partnership/accountActions.ts
    placement/partnership/multisig.ts
    placement/partnership/partnerLock.ts
    btrust/sign.ts
    chat/issuerKey.ts

So "Stop spending" covers `createAction`-based sends only, while `docs/MONEY-GUARD.md` promises it pauses "one
feature in every shipped copy". Same root cause as L4-C1 ⇒ impact amplification for that report, not a new one.
**Generalised check for any wallet target:** for every money path, list which guarded method it actually
reaches. A path that signs directly with `createSignature` skips any guard built on `createAction`/`signAction`.

### Still queued
paymail · OpNS/Name Store covenant verification · pots+subscriptions · agent spend ledger ·
`src/sweep/` (3 095 lines) · backup/restore envelope deep pass · native Android/iOS plugins ·
Memepool `api.ts`/`curve.ts` · chat/feed/calls display paths · `src/mobile/btrust`, `locks`, `placement`.

### Highest-value hunting lanes on this target
1. **Newest merge wins.** `git show --stat HEAD` — the last money commit (was #118, Memepool, 2 630 lines)
   ships with no b-Aware row and no review marker. Run the money-module checklist on it.
2. **Sibling-of-a-fixed-bug.** Every closed row above has a sibling that might not have been swept:
   a guard added on the write path but not the read path, on one branch but not the other.
3. **The vendor's own review guide** `docs/SECURITY-REVIEW.md` names the trust boundaries and openly says
   "no automated security tests of the bridge or hub yet" — treat that as a map, and verify each claim in
   code rather than trusting the prose.

## Dependency layer (measured round 1, not reportable)
`bun audit` → 9 advisories. react-router GHSA-337j-9hxr-rhxg needs SSR hydration (this app is client-side
`react-router-dom ^6.16.0`, no `entry.server`). vite + launch-editor are dev-server/dev-tooling only.
elliptic comes in via `crypto-browserify` (node polyfill), not the BSV signing path. Program does not pay
"issues that need no exploit", and a dep CVE needs a reachable impact on funds or keys → one INFO line, never
part of a finding.

## Report shape that fits this program
One finding = one email = one PoC = one root cause. Lead with what moves money or reads keys; say plainly
what the bug is NOT (no funds move, no key read) — the program sets severity by impact on money and keys and
explains its reasoning, so honesty holds the tier. Include the version/commit tested and a runnable repro.

## Working artifacts
`D:\data\hermes\bwallet-audit-20261025\` — `00-scope/SCOPE.md`, `01-recon/PHASE_LOG.md`,
`01-recon/DEDUP-MAP.md`, `01-recon/repo` (keep `git status` clean), `04-evidence/`, `05-report/`.
