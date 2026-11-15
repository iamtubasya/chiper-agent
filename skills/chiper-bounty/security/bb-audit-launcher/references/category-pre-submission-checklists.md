# Category Pre-Submission Checklists

> Load at **0E** (before a candidate is called reportable) and again at **0F** (before the report is
> written). The universal gates (`triage-validation-7qgate.md`, `evidence-state-ladder-and-reachability-gate.md`)
> answer *"is it real, in scope, reachable, deduped?"*. This file answers the category question a
> triager asks in the first minute: *"did you check the thing that always breaks in this kind of
> code?"* Tick the matching section in the workspace — never in your head, never "obviously yes".

Rule: **only the section that matches the finding.** A vault finding does not need the bridge list,
and a ticked box you did not actually verify is worse than an empty one.

---

## Bridge / cross-chain

- [ ] Message verifier + threshold identified and documented (who signs, how many, which contract)
- [ ] Replay blocked by a unique nonce **and** an id that cannot repeat across chains
- [ ] Initial state after deploy/upgrade verified safe (no pending owner, no live mint authority)
- [ ] Token whitelist enforced on **both** legs (deposit/burn and release/mint), not just one
- [ ] Off-chain control (RPC, relayer, sequencer) named explicitly if the program excludes it

## Lending / perps / money market

- [ ] Every price source validated: staleness (`updatedAt`), deviation bound, and the *correct* market's feed
- [ ] Caps / LTV / fees / liquidation thresholds consistent across **all** entry paths (open, increase,
      modify, partial close) — one path missing a cap is the bug
- [ ] Interest accrual happens before any balance-changing branch (an early return that skips accrual
      is an accounting desync)
- [ ] Admin setters validate their own inputs (no config that bricks solvency)

## Vault / pool / ERC-4626

- [ ] First-depositor / share-inflation path checked (donation attack; `_decimalsOffset`, dead shares,
      or virtual offset present)
- [ ] State-update vs external-call ordering verified (CEI), including read-only reentrancy through a
      `convertToAssets` consumer
- [ ] Rounding favours the protocol on deposit **and** on withdraw/redeem
- [ ] Share transfer moves the lock/stake/record too, not only the balance

## Signature / permit / auth

- [ ] Every security-relevant field is inside the signed payload (amount, spender, deadline, nonce,
      chainId, verifying contract, policy id)
- [ ] Nonce consumed and non-reusable; a cancellation path exists
- [ ] `ecrecover` result checked for `address(0)` and malleability (`s` bound)
- [ ] Domain separator recomputed when chainId changes / on a fork

## Upgradeability / proxy

- [ ] `initialize` cannot be re-called or reached by an unauthorised party (`_disableInitializers`,
      versioned `reinitializer`)
- [ ] Storage layout compatible across versions (no slot shift, no new variable inserted mid-layout)
- [ ] The implementation contract itself cannot be initialized or upgraded directly
- [ ] `upgradeTo` / `upgradeToAndCall` guarded; timelock / multisig noted honestly, not as a finding

## Web2 / API

- [ ] Two-account authorization replay done (horizontal **and** vertical) on every object endpoint in
      scope — read, write, delete, export
- [ ] Session invalidated on logout **and** on password / e-mail / credential change
- [ ] CSRF: sensitive state changes need a token the attacker cannot obtain; SameSite posture checked
      rather than assumed
- [ ] File upload: type **and** content validated, stored outside webroot or served non-executable
- [ ] SSRF: allowlist or internal-range block proven with out-of-band evidence; redirects re-validated
      at each hop
- [ ] OAuth: `redirect_uri` strictly matched, `state` present and bound, PKCE where supported, code
      single-use and short-lived
- [ ] GraphQL: per-field / per-resolver authorization tested, not just endpoint-level; batching and
      alias amplification measured against the rate limit
- [ ] Export / report endpoints honour the same filters as the UI (an export that ignores a filter is
      mass disclosure)

## Mobile (Android / iOS)

- [ ] Credentials only in the platform keystore (Android Keystore / iOS Keychain) — no tokens or
      refresh secrets in SharedPreferences / NSUserDefaults / plain files / local DBs
- [ ] No tokens in URLs, logs, or telemetry attributes — check what the client actually sends
- [ ] Exported components permission-gated; deep links / URL schemes validate caller and parameters
      before any privileged action
- [ ] WebView: JS bridge scoped to trusted origins, file access off unless required, remote content
      never reaches a privileged bridge unvalidated
- [ ] TLS: platform default validation intact (no permissive challenge handler / trust manager);
      pinning present, or its absence a documented decision
- [ ] Backup / app-data extraction posture checked (backup flags, app-group containers, pasteboard)
- [ ] Shipped artifact diffed against the audited source (store binary == repo) before claiming
      anything about either

## LLM / AI feature

- [ ] Injection reaches a **sink that matters** (tool call, fetch URL, code exec, data store) — a
      prompt that produces rude text is not a finding
- [ ] System-prompt / secret extraction shown with the actual leaked value (redacted)
- [ ] Cross-user or cross-tenant context leak demonstrated (history, embeddings, RAG namespace)
- [ ] Guardrail bypass has a reproducible trigger and a control test showing the guard works without it

## Self-hosted / appliance

- [ ] Behaviour attributed to a specific in-scope binary/assembly, not to the lab or the host
- [ ] Control test: the same action by an authorised actor behaves correctly
- [ ] Redaction / masking control attacked on **every** render surface, not just the main log
- [ ] Version + build number recorded; the finding states which build was tested

---

## Why this file exists

Most downgrades are not arguments about severity — they are a missing checkbox. "Did you test the
other HTTP method?" "Did you check the export honours the filter?" "Did you verify the binary is the
one in scope?" Each of those is one line here, and each one has cost a real report.
