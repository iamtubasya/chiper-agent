# Vulnerability-Class Gotchas

> **Source:** adapted from YesWeHack `claude-kit` `skills/gotchas/SKILL.md`
> (GPL-3.0-or-later), 2026-10-26. Class list and the three-block structure
> (minimum proof / common N/A / overclaim traps) are theirs. Operator notes
> marked **[ours]** are additions from this estate's engagements.
>
> Apply **only the section matching the claimed class**. For each class:
> **minimum proof** (what the PoC must show), **common N/A** (typical false
> positives that get auto-closed), **overclaim traps** (impact claims that
> need extra evidence).

---

## XSS

**Minimum proof**
- JS execution on **target origin** (`alert(document.domain)` proves it).
- Injection context stated: HTML body / attribute / JS / CSS / URL / JSON.
- Type stated: reflected / stored / DOM.

**Common N/A**
- `alert(1)` on `null` origin, sandboxed iframe, `data:` / `blob:` URL.
- Self-XSS.
- HTML injection without JS execution, unless tied to a real attack.
- XSS via a Markdown / template renderer the target doesn't actually use.
- `javascript:` href requiring the victim to manually paste the URL.

**Overclaim traps**
- "Session theft" claim but cookie is `HttpOnly` — JS can't read it.
- "Account takeover" without a PoC that actually takes over an account.
- "CSP bypass" without showing the CSP header and the bypass technique.

**[ours]** DOM-XSS: confirm the parameter actually *reaches a page* before
believing any hit — a 301/302 that drops the query string means the sink never
saw the payload (`bb-methodology` Redirect-Drop Rule). A run reporting
`interpreted=N` with `canary=0` is unconfirmed by definition.

---

## SQLi

**Minimum proof** (one of)
- Data extraction: sentinel value, table name, DB version returned.
- Time-based: controlled `SLEEP(n)` payload, multiple runs at varying `n`.
- Boolean-based: controlled true/false oracle with response differential.

**Common N/A**
- WAF blocked the payload → "SQLi confirmed". The WAF blocked; that's it.
- Error message mentioning SQL without controlled injection.
- Generic HTTP 500 on quote characters (could be many things).
- DB banner / version leaked without proving injection.

**Overclaim traps**
- "Full database compromise" without dumping a controlled sentinel row.
- Don't escalate the PoC into destructive or intrusive post-exploitation to
  "prove" impact. A confirmed injection (sentinel value, controlled
  time-delay, boolean oracle) is enough — stop there. Dumping the whole DB,
  chaining to `xp_cmdshell` / `INTO OUTFILE`, or writing files goes past proof
  into damage and can breach the program rules. Prove the primitive, describe
  the impact, don't exercise it.

**[ours]** A negative result is only valid if the request was *accepted*:
`400`/`401` across the whole run means the tooling was wrong (missing required
header / cookie), not that the target is safe. Re-run with correct headers
before calling it NEGATIVE.

---

## SSRF

**Minimum proof**
- Inbound request observed on hunter-controlled endpoint (Burp Collaborator,
  webhook.site, hunter's server). Include the inbound log.
- For blind SSRF: time-based confirmation with multiple controlled hosts.
- Reach demonstrated: at least one of internal hostname, cloud metadata
  (169.254.169.254), localhost service, or protocol smuggling (`file://`,
  `gopher://`, `dict://`). **Collab hit alone is not enough.**
- Response data exfiltrated if claimed (internal endpoint content shown).

**Common N/A**
- DNS resolution only — proves lookup, not HTTP request.
- Blind SSRF to attacker-controlled domain only, no reach demonstrated.
  Legitimate webhooks / link previews / image proxies make outbound HTTP too.
- SSRF to public domains only.
- Request blocked by WAF / library / network policy.

**Overclaim traps**
- "Cloud metadata access" without showing the metadata response body.
- "Internal network scan" without one successful internal hit.
- "Blind SSRF" claimed High/Critical without demonstrated reach → typically
  Low or N/A.

---

## IDOR / BOLA

**Minimum proof**
- Two hunter-controlled accounts, A and B.
- Account A reads / modifies / deletes a resource belonging to B.
- Response containing B's data shown, with B's identifier visible.

**Common N/A**
- Sequential / predictable IDs without showing actual access.
- Reading own data via someone else's ID (same effective access level).
- Resources that are public by design.
- Admin endpoints accessible only to admins (not broken).

**Overclaim traps**
- "Mass account takeover" without showing the takeover primitive on B.
- Single-account "discovery" with cross-tenant impact claims but no second
  tenant tested.
- Non-guessable identifier (random UUIDv4, HMAC, long opaque token) scored as
  if IDs were enumerable. If an attacker can't discover a victim's ID at
  scale, exploitation needs the ID to leak elsewhere — score `AC:H` and say
  where the ID would come from. Don't claim mass exploitation off a single
  self-owned resource whose ID you already knew. Sequential / short /
  predictable IDs are the ones that justify `AC:L`.

**[ours]** Reaching a protected **route** that only renders the client-side
app shell is not a bypass — the framework serves the bundle to everyone and
the API behind it still returns 401/403. Show a protected **action or data**
actually returned without auth. (Same trap as auth-bypass below.)

---

## CSRF

**Minimum proof**
- Working PoC HTML page (hosted or pasted in full) that, when visited by an
  authenticated victim, performs the sensitive action.
- The action must be sensitive (state change, privilege grant, data
  modification — not logout, not search).
- SameSite cookie status verified — `Lax` blocks most cross-site POSTs; the
  PoC must work despite it.

**Common N/A**
- CSRF on logout, search, or other low-impact actions.
- "No CSRF token present" without showing exploitation.
- `SameSite=Lax/Strict` cookies blocking the cross-site request.

**Overclaim traps**
- "Account takeover via CSRF" without a chain that actually takes over.
- Rating a CSRF by the *mechanism* rather than the *action*. The severity is
  capped by what the forced action is worth. CSRF on a reversible, low-value
  state change (add item to cart, toggle a UI preference, change display
  name) is **Low** even with a perfect PoC. High severity needs a genuinely
  sensitive action: email/password change, fund transfer, privilege grant,
  deletion of the victim's data.

---

## RCE

**Minimum proof** (one of)
- In-band command output (`id`, `whoami`, `hostname`).
- Out-of-band callback to hunter-controlled endpoint with a unique
  payload-specific marker.
- Injection point and payload shown literally.

**Common N/A**
- "Suspicious behavior on payload submission" without command execution.
- Stack trace mentioning `system()` / `exec()` without controlled execution.
- Theoretical RCE via a vulnerable dependency without proving reachability in
  the application's code path.

**Overclaim traps**
- "Full server compromise" without showing the privilege level. Prove
  execution with a harmless marker (`id`, `whoami`, `hostname`, or an OOB
  callback) and stop. Do not pivot, escalate privileges, move laterally, read
  other users' data, or run destructive commands to "demonstrate" reach —
  that's past proof and into damage, and it breaches most program rules.
  Report the execution primitive; describe the impact without exercising it.
- "RCE" that's actually code injection in a sandboxed context (sandboxed
  template engine, browser-side eval — that's XSS, not RCE).

---

## SSTI

**Minimum proof**
- Template syntax confirmed (`{{7*7}}` → `49`, `<%=7*7%>` → `49`, etc.).
- Template engine identified (Jinja2, Twig, Velocity, Freemarker, …).
- Sandbox escape shown if the engine is sandboxed.
- For RCE impact: see RCE section minimum proof.

**Common N/A**
- HTML / text reflection of `{{7*7}}` as a literal string (no evaluation).
- Math eval in a sandboxed expression engine without an escape path.

**Server-side vs client-side**
- `{{7*7}}` → `49` in a **client-side** framework (Angular, Vue) is **CSTI**,
  not server-side SSTI. Its impact is **XSS** (JS execution in the browser),
  not server RCE — report it as XSS and prove JS execution accordingly. Don't
  claim server compromise from a client-side template evaluation.

**Overclaim traps**
- Reporting **CSTI** (`{{7*7}}` → `49` in Angular/Vue) as server-side RCE. That is
  client-side code execution — report it as XSS and prove JS execution.
- Claiming RCE from a sandboxed engine without a demonstrated escape path. "The
  engine evaluates my expression" is not "I reached the OS".
- Scoring Critical on a template *reflection* when the rendered value is escaped at
  output — re-test with a payload that would produce a side effect if evaluated.

---

## XXE

**Minimum proof**
- External entity defined and resolved.
- File read: content of a known file returned (e.g. `/etc/passwd`).
- Or OOB: callback with file content base64'd or named entity.

**Common N/A**
- XML parser accepts external DTD references but does not resolve entities.
- Error mentioning entity processing without a controlled file read.

**Do not**
- Demonstrate impact with an entity-expansion bomb (billion laughs / quadratic
  blowup). That's a DoS against the target — excluded by most programs and a
  rules violation, not an XXE proof. Prove XXE with a controlled file read or
  an OOB callback instead.

**Overclaim traps**
- Claiming file read from a parser that merely *accepts* a DTD but resolves nothing.
  Show the file content, or an OOB callback carrying it.
- Using an entity-expansion bomb (billion laughs) as the proof — that is DoS against
  the target, excluded by nearly every program, and not an XXE demonstration.
- "XXE → RCE" with no execution path. XXE gives file read / SSRF; RCE needs a known
  gadget or an executable sink, proven separately.
- Reporting blind XXE with no callback log. DNS-only resolution proves a lookup, not
  that your entity was processed with the data you claimed.

---

## Open Redirect

**Minimum proof**
- Single URL that redirects to a hunter-controlled domain.
- The redirect mechanism sits on a security-relevant path: auth callback,
  OAuth `redirect_uri`, password reset link, login flow.
- A chain showing real impact (OAuth token theft, credential phishing
  leveraging the program's domain reputation).

**Common N/A**
- Open redirect on non-security-sensitive paths with no chain.
- Redirect requiring the victim to manually paste a URL.
- Same-origin redirects.

**Overclaim traps**
- Claiming token/code theft via an OAuth/OIDC `redirect_uri` you can't
  actually PoC. If proving the token leak requires an authenticated account
  (or the IDP's real consent flow) you don't have, the impact is **theoretical
  and non-reproducible** — a triager can't replay it, so it isn't valid.
  Either obtain an account and show the token landing on your endpoint, or
  report only the redirect you can prove (typically Low) and state plainly the
  ATO chain is unverified.

---

## Auth Bypass

**Minimum proof**
- Specific endpoint or flow accessed without the required auth state.
- Endpoint is sensitive (admin, paid feature, other user's data).
- Bypass mechanism shown (request manipulation, missing header, modified
  parameter, parser confusion).

**Common N/A**
- Endpoint returns data also available unauthenticated by design.
- "Bypass" using test credentials the program intentionally exposes.
- Public endpoints documented as such in API docs.
- Reaching a protected **route** that only renders the client-side app shell.
  Loading `/admin` and seeing the SPA's JS/HTML render is not a bypass — the
  framework serves the bundle to everyone and the API calls behind it still
  return 401/403. You must show a **protected action or data** actually
  returned without auth (an admin API responding with real data, a privileged
  operation succeeding). "The page loads" is not an impact.

**[ours]** Path-encoding variants (`%2e%2e`, `;param`, `//`, `%00`) that
resolve to an already-public path are **normalization, not bypass**. Resolve
where the path *lands* and diff against an unauthenticated baseline of that
landing target (`bb-methodology` Path-Normalization Rule).

**Overclaim traps**
- "Bypass" from loading a protected **route** that only renders the client-side app
  shell. The framework serves the bundle to everyone; the API behind it still returns
  401/403. Show a protected **action or data** actually returned.
- Reaching a page that is public **by design** (docs, status, changelog, marketing) and
  calling it a bypass.
- Path-encoding variants that resolve to an already-public path — that is
  normalisation, not access control. Resolve where the path *lands* and diff against
  an unauthenticated baseline of the landing target.
- A 403-vs-401 differential scored as a bypass. Different status codes are a
  *fingerprint*, not access.
- Claiming admin access from an endpoint that an admin would also use, without
  showing a non-admin reaching it.

---

## Information Disclosure / Secret Leak

Covers leaked secrets found anywhere: JS bundles, HTML/source comments, API
responses, `git`/config exposure, and **secrets hardcoded in mobile apps**
(decompiled APK/IPA, `strings`, `strings.xml`, embedded config).

**Minimum proof**
- The exact location the secret was found (file, URL, decompiled path).
- The secret is **still valid** — show one authenticated call that succeeds
  with it (a `200` on an endpoint that requires it), with the secret redacted
  in the report.
- The concrete access it grants: what data or action the key/token unlocks.
  Impact = what the *valid* credential can actually do.

**Common N/A**
- **Public / publishable keys that are meant to be client-side.** Google Maps
  browser keys, Firebase `apiKey` config, Stripe publishable `pk_...`, Sentry
  DSNs, reCAPTCHA site keys, Mixpanel/analytics tokens. These are *designed*
  to ship in the client — a leak isn't a finding unless you prove a real,
  non-intended capability (e.g. an unrestricted Maps key billing abuse, or a
  Firebase config with wide-open security rules — and then the finding is the
  open rules, proven separately).
- Expired, revoked, or already-rotated credentials.
- "A key is present in the JS" with no test that it's live or privileged.
- Placeholder / example / test values (`sk_test_...`, `changeme`, documented
  sample keys).

**Overclaim traps**
- Reporting the *presence* of a secret as impact. The impact is what the
  secret does when used — if you didn't (safely) confirm it works and what it
  reaches, you haven't proven a finding.
- Treating any long random string as a "leaked secret" without identifying
  what it authenticates.

---

## Race Condition

**Minimum proof**
- A broken invariant under concurrency: the same operation, sent in parallel,
  produces a result impossible under sequential execution (a one-time coupon
  applied N times, a balance credited twice, a single-use token consumed more
  than once, a limit of 1 exceeded).
- The concurrency method stated: single-packet attack (HTTP/2 last-byte sync),
  Turbo Intruder, or parallel clients — with the number of concurrent requests.
- Before / after state shown: the pre-state, the concurrent burst, and the
  **persisted post-state** that proves the invariant broke (final balance,
  ledger row, redemption count) — not just several `200`s.

**Common N/A**
- "Sent 100 requests fast, several succeeded" without showing a broken
  invariant. Multiple successes on an endpoint with no per-user limit are just
  multiple successes.
- Duplicate submissions on an idempotent endpoint (no state effect).
- Different response times / jitter mistaken for a race.
- Rate-limit bypass with no concrete state impact — that's a rate-limit
  finding, not a race, and is often out of scope on its own.
- Hammering that degrades the service — that's DoS (excluded), not a race PoC.

**Overclaim traps**
- Claiming double-spend / balance inflation from two `200` responses without
  showing the *persisted* state changed. The proof is the final ledger /
  balance, not the response codes.
- Reporting one lucky duplicate as reliable exploitation. A race needs a
  reproducible win — state the win rate and attempts to land it.
- Scaling the burst into thousands of requests to "prove" it. A small
  concurrent burst that breaks the invariant is the proof; volume past that is
  abuse, not evidence.

---

## CORS Misconfiguration

**Minimum proof**
- The response reflects an attacker-controlled `Origin` in
  `Access-Control-Allow-Origin` **and** returns
  `Access-Control-Allow-Credentials: true`.
- The endpoint returns **session-authenticated, sensitive data** tied to the
  victim's cookies (their profile, token, private records).
- A working PoC page hosted on the attacker origin that does
  `fetch(url, {credentials:'include'})`, reads the response cross-origin, and
  shows the victim's actual data exfiltrated — not just the headers.

**Common N/A** (this is where most CORS reports die)
- `ACAO: *` **without** `ACAC: true`. The browser refuses to send credentials
  to a wildcard origin, so a credentialed read is impossible — a public
  endpoint returning `*` leaks nothing an attacker couldn't already fetch
  server-side. Not a finding alone.
- Reflected `Origin` but the endpoint returns only public / unauthenticated
  data. No secret crosses the boundary.
- `ACAC: true` with a **fixed, trusted** `ACAO` (not reflected, not
  attacker-controlled).
- Preflight (`OPTIONS`) reflecting the origin while the actual `GET`/`POST`
  doesn't, or the real response body carries nothing sensitive.
- "`null` origin allowed" with no PoC — exploiting `null` needs a sandboxed
  iframe; show it working.
- API authenticated by a **bearer token in a header**, not cookies — CORS
  reflection doesn't hand the attacker the token, and the browser won't attach
  it cross-origin. No credentialed session to steal.

**Overclaim traps**
- "Account takeover via CORS" without a PoC page that actually reads victim
  data. The impact is exactly what the misconfigured endpoint returns to a
  credentialed cross-origin read — name the endpoint and show the data.
- Scoring High off header reflection alone. No credentialed sensitive-data
  read demonstrated = no impact = typically N/A.

---

## Path Traversal / LFI

**Minimum proof**
- A file **outside the intended directory** retrieved, content shown
  (`/etc/passwd`, `win.ini`, or an app config / source file the endpoint must
  not serve).
- The exact parameter and payload shown literally, including the encoding that
  worked (`../`, `%2e%2e%2f`, `....//`, absolute path, null-byte truncation).
- Traversal (arbitrary read via `../`) and LFI (include/execute a file) kept
  distinct. If code execution is claimed (log poisoning, PHP `php://filter` /
  wrapper chain, session-file inclusion), show the executed output — not just
  the file read.

**Common N/A**
- Reading a file **inside** the intended served directory (a download endpoint
  serving its own public files) — that's by design.
- `403` / `404` / `500` on `../` payloads with no file returned. An error is
  not a read.
- Filename reflected in an error message without content disclosure.
- Retrieving a non-sensitive file with no security value.
- Payload visibly blocked / normalized by the framework or WAF (show it
  actually resolving to file content).

**Overclaim traps**
- "Arbitrary file read = RCE" without a demonstrated execution path. LFI→RCE
  needs a proven include-and-execute primitive (log / session poisoning,
  wrapper chain); absent that, it's file disclosure, score it as such.
- "Any file on the server" inferred from one `/etc/passwd`. State what the
  process user can actually read — a private key or app secret proves impact;
  `/etc/passwd` alone is usually just the confirmation primitive.
- Dumping many sensitive files or other users' data to "prove" reach. One
  representative sensitive file proves it; mass exfiltration is past proof and
  into damage.

---

## Reentrancy / state-ordering (on-chain)

**Minimum proof**
- A Foundry test on a fork (or a local deploy of the real bytecode) that shows the
  **invariant break**, not just the re-entrant call landing:
  `forge test --fork-url <rpc> --match-test test_exploit -vvvv` lulus.
- State before vs after, in numbers: the balance/ledger/share the attacker walks
  away with, and the victim's delta.
- Name the ordering defect literally: *which* state write happens *after* the
  external call, and which check that invalidates.
- Control test in the same suite that does NOT fire on a correct implementation.

**Common N/A**
- A re-entrant call that reverts because `msg.sender` is the callee, not the owner.
  Reentering does not grant the caller's identity — if the guard checks the caller,
  the naive reentrancy is dead. (Measured: AA-modular `nonce-after-call` — the
  ordering bug is real and measurable, but the naive exploit path is blocked; you
  need a path that carries the *same* `msg.sender`, e.g. entryPoint batching or a
  multicall delegating back.)
- `nonReentrant` present on every external entry that touches the state.
- Reentrancy that only re-enters a `view` function (no state effect).
- A re-entrant call that succeeds but leaves the attacker with **negative** P&L
  after gas.

**Overclaim traps**
- "Reentrancy → drain all funds" from one successful re-entrant call. Show the
  amount actually moved; a re-entered `withdraw` that returns the same balance
  twice is a proof, a re-entered `view` is not.
- Scoring Critical on a reentrancy that needs the victim to be the attacker
  (self-inflicted) or needs an admin-set state.
- Claiming a **cross-contract** reentrancy from a test that only exercises one
  contract — the second contract must exist in the PoC.

---

## On-chain access control (unprotected privileged function)

**Minimum proof**
- The privileged function called from an account that holds **no role**, on a fork
  of the live deployment (or the exact deployed bytecode), and the effect observed:
  `diamondCut` swapped a facet, `installModule` registered a module, `setOwner`
  changed the owner, `mint` created supply.
- The **selector / function signature** named exactly, plus the guard that is
  missing (`onlyOwner`, `msg.sender == owner`, `facetAddress(0)` check).
- Before/after state in numbers — the asset or permission the attacker gained.

**Common N/A**
- The function is protected by a guard **in a base contract** — walk the
  inheritance chain before reporting. Most `unprotected-upgrade` analyzer hits die
  here.
- The "privileged" function only changes a parameter that a timelock can revert, or
  only affects the caller's own position.
- An `initialize()` that is already called on the proxy (initializer spent).
- Admin is an EOA — that is a centralization observation, not an access-control
  bug, unless you can show the EOA is compromised.

**Overclaim traps**
- Reporting "admin is a single EOA" as Critical. Centralization is a design
  property; it becomes a finding only when paired with a demonstrated path (leaked
  key, upgrade without timelock *and* a fund-draining action).
- "Anyone can call it" without executing the call and showing the effect.
- Analyzer output (`unprotected-upgrade`, `suicidal`, `arbitrary-send`) shipped as
  a finding. These have high false-positive rates; each hit needs the inheritance
  walk plus a fork PoC.

---

## Price oracle manipulation (stale / confidence / sequencer)

**Minimum proof**
- A **privileged action that reads the bad price**, executed in the PoC, with the
  financial consequence quantified: bad debt, unfair liquidation count, borrowed
  amount against over-valued collateral.
- Three sequencer states tested on L2: down + before grace, down + after grace, up.
- For Chainlink: `updatedAt` staleness, `answeredInRound < roundId`, `answer <= 0`.
- For Pyth: `getPriceUnsafe` used, `conf` interval ignored, `publishTime` stale.

**Common N/A**
- A stale price with **nothing acting on it** — no borrow, no liquidation, no swap.
  That is a hardening note, not a finding.
- The consumer contract has a freshness check that reverts (then the "stale" read
  is unreachable).
- Fork-state staleness: a feed that has not updated on the fork because the fork is
  old. That is a **fork artefact**, not a target bug — mock or warp explicitly.
- An oracle whose price is only used in a `view` for display.

**Overclaim traps**
- "Oracle can be manipulated → funds at risk" without showing the manipulation
  cost vs the extractable value. If moving the price costs more than the profit,
  there is no economic exploit — show both numbers.
- Treating a wide `conf` interval as exploitable without showing the consumer
  ignores it.
- Claiming a spot-price manipulation on a protocol that uses a TWAP with a window
  longer than your test's manipulation duration.

---

## Signature replay (EIP-712 / Permit2 / ERC-3009)

**Minimum proof**
- Two executions from **one** signature, or one signature replayed on a second
  `chainId` / second contract — the **second call succeeds** and moves value.
- The delta: token amount transferred, allowance consumed, or state flipped, with
  before/after balances.
- The missing binding named: `chainId`, `verifyingContract`, `salt`, `nonce`,
  `witness`, `validBefore`.
- Signature produced inside the test with `vm.sign` (a private key the test owns),
  never a signature scraped from production.

**Common N/A**
- Adding a field to the domain separator without producing a working replay.
  "`chainId` is missing" is a hypothesis until the cross-chain call executes.
- A second call that **reverts** — that means the control works; record it as a
  verified negative, do not ship it as a finding.
- A signature whose `nonce` is consumed by the same transaction that would replay
  it.
- `permit()` front-running griefing with no value loss (the victim's tx reverts;
  nobody loses funds).

**Overclaim traps**
- "Signature replay → unlimited mint" from one replay. One replay moves one
  allowance's worth; say how much and how many times.
- Scoring Critical on a replay that needs the victim to sign twice, or that only
  works after the allowance was already spent.
- Forgetting that a relayer can be the attacker's own account — if the exploit
  needs a *third party* to submit, that is a precondition to state.

---

## Vault share accounting (inflation / rounding / desync)

**Minimum proof**
- An attacker P&L that is **positive after gas**, computed explicitly in the PoC
  (`test_Probe4_AttackerPnL_EconomicsGate` pattern).
- The victim's loss quantified as a share of their deposit: "deposited 9,999 USDC,
  received 0 shares" is proof; "received slightly fewer shares" is dust.
- The full sequence: mint → donate → victim deposit → redeem, with each step's
  state printed.
- Duplication check first: git history, CHANGELOG, published audit reports. If the
  mitigation (dead shares, virtual offset, `totalSupply == 0` guard) is already in
  the bytecode, there is no finding.

**Common N/A**
- Rounding dust that is proportional and recoverable (a few wei).
- `totalSupply == 0` deposit blocked by the contract → the classic inflation vector
  is closed.
- Fee-on-transfer desync that the vault already accounts for by measuring the
  actual received amount.
- An attack that requires the attacker to hold a majority of the vault.

**Overclaim traps**
- "Inflation attack" from a single-party test only. Run the single-party kill test
  first: if one actor cannot trigger it, discard before writing the PoC.
- Claiming insolvency without showing `totalAssets < totalSupply`-equivalent
  backing after the sequence.
- Reporting a rounding direction as a bug when the protocol rounds in its own
  favour deliberately (that is by design, and usually disclosed).

---

## AMM / swap accounting (hook trust, fee mutation, JIT)

**Minimum proof**
- Who pays, named: LP, taker, or protocol. For most AMM findings it is the **LP**,
  so the loss is measured against pool TVL, not against protocol revenue.
- The fee/price delta measured before vs after within the PoC, with numbers.
- For hook trust: the hook registered by the attacker and the swap executed
  through it, showing the extracted value.
- For JIT: net P&L inside one transaction = fees earned − gas − inventory risk.
  A JIT that "works" but nets negative is not a finding.
- For cross-pool effects: both pools present in the PoC, sharing the actual
  singleton manager.

**Common N/A**
- "Hook owner can change the fee" — the hook belongs to the integrator by design.
  Without a harmed third party there is no bug.
- JIT liquidity that only earns the fair fee for the block it provides.
- Price impact that is exactly the expected AMM curve behaviour.
- A rounding difference that the pool's own accounting absorbs.

**Overclaim traps**
- "Price manipulation" without showing who transacts at the manipulated price and
  how much they lose.
- Quoting the manipulated price's *potential* impact across all TVL when the PoC
  only moved one small pool.
- Scoring a hook-permission finding Critical without an actual extraction path.

---

## Restaking / slashing accounting

**Minimum proof**
- The self-sufficiency test: the PoC gathers everything the exploit needs (register
  operator, stake, trigger) and **no privileged external dependency** ("requires the
  DAO to stake first" = unavoidable external dependency → not actionable).
- Two ledgers compared: **delegation ledger** (how much each operator is owed) vs
  **asset ledger** (tokens actually backing the LRT). A mismatch is the primitive.
- Attack **witness** of ≈100 lines, not an abstract description: on-fork PoC
  demonstrating the invariant break with real token contracts
  (`forge test --fork-url <rpc> -vvvv`).
- Where the reward lands: for a proven unstake/pending
  user both the lost 1:1 right **and** the claimed asset. Reentrancy described
  once, not repeatedly — root cause = absence of `nonReentrant` on that function.

**Common N/A**
- A "safe" strategy that behaves exactly as designed (control test passes).
- A rate desync that can be arbitraged back with no net loss.
- A withdrawal-delay observation with no path to bypass it.
- Centralization of the operator set — a design property, not a bug.

**Overclaim traps**
- "Bank run possible" without an insolvency number (backing < obligations).
- Extrapolating one operator's slashing to the entire TVL.
- Claiming a double-count without tracing **one** unit of stake through every
  registry and showing the total.

---

## Intent / solver settlement

**Minimum proof**
- Who is harmed, named: the **user** (`minOut` not enforced), a **competing solver**
  (front-run / griefed), or the **protocol** (double mint). Then the amount.
- The signed struct field that is not binding, named exactly (`chainId`, `nonce`,
  `solver`, `recipient`, `deadline`, `witness`).
- Attestation replay shown with **two** executions, or across two `chainId`s — the
  second must succeed and mint/transfer again.
- Partial fill accounting: 50% + 50% + the third fill that should revert but does
  not, with the running total.

**Common N/A**
- "Solver can choose the price" — that is the intent model. Without a `minOut`
  violation there is no bug.
- An allowlist that is permissionless by design (open solver set).
- Divergence that the user accepted by signing a loose limit.
- Cross-chain replay claimed from a same-chain test.

**Overclaim traps**
- "Users get shorted" without measuring the shortfall against `minOut` for a
  specific fill.
- Claiming protocol insolvency from an accounting drift that nets to zero across
  fills.
- Reporting the absence of an allowlist as Critical when the design is
  permissionless and the docs say so.

---

## OTP / magic-link brute-force (broken rate-limit → account takeover)

**Minimum proof** — before touching severity, measure three numbers, don't assume them:
- **Space** = code length (`10^length`: 4-digit = 10^4, 6-digit = 10^6). Confirm from the client bundle (`maxLength`, `.slice(0,6)`, placeholder) since the server rarely tells you.
- **TTL** — send one OTP, then probe it with a wrong value over minutes. The error flips `INVALID_OTP` → `OTP_EXPIRED` (or the code is single-use / rotated on re-request). This is the window a single brute must beat.
- **Sustained rate** — the *server's* ceiling, not your client's. A per-verify slow hash (bcrypt/scrypt/argon2, ~1 s latency) caps you at ~tens of verify/s no matter how many connections you open. Measure with a real threaded/asyncio burst; "parallel = fast" is false when the server serialises on crypto.
- Then compute: `time ≈ space / rate`; if `TTL < time`, it's `per-window = rate × TTL` accumulated over repeated windows. Only a *practically small* time justifies High/Critical.

**Common N/A**
- "Rate limit on login/signup/password-reset" listed OOS with a "we return 302 not 429" note — but that note describes the *redirect* app (Devise/Rails), not necessarily a sibling app (Better Auth / Auth.js) whose OTP endpoint returns JSON 400/403. Verify **which stack the OOS clause actually names** before self-censoring, and frame as *account takeover via a broken verification limit*, not "the limiter looks odd" (measured 2026-10: dash `/users/sign_in` throttles via 302 exactly as the clause says; the Lead-Retrieval OTP endpoint does not).
- `type=email-verification` / `forget-password` returning `{"success":true}` for unregistered emails **but not sending mail and not creating a session** is a *false-positive* success (anti-enumeration by design), NOT a gate bypass. Confirm delivery to a throwaway inbox AND `get-session` stays `null` before calling it auth bypass.

**Overclaim traps**
- ⚠️ **"Unlimited attempts + 6-digit OTP = Critical ATO in a few hours"** — the number-one trap here. Unlimited attempts ≠ fast. The two silent caps are the **OTP TTL** (5–15 min default) and the **slow verify hash** (~50 verify/s). A realistic single-IP takeover is ~half a day or more; a botnet only scales it linearly. Say "High — feasible but slow" until you either complete a takeover or prove a small / long-lived / weakly-random space.
- "Lockout is broken" (proven by `too many attempts` firing *once* then never again — a `count == MAX` instead of `count >= MAX` signature) is a real rate-limit bypass, but a rate-limit *bypass* is not itself ATO; the takeover feasibility still needs the TTL+rate math above, stated explicitly.
- Never claim you took over a real account when you only *measured* feasibility. Write precisely what was proven (e.g. "lockout fires 1 in 4,000") versus what is inferred ("eventual ATO").
- "admin@ is registered on every tenant" + brute-force = cross-tenant dump: fine to describe, but only *after* the single takeover is established. Do not stack cross-tenant impact onto an unproven primitive.

---

## Class not listed?

Apply general PoC and impact rigor (see `triage-validation`). The report
should clearly explain the class and its impact model in its first paragraph,
since the triager won't have a class-specific mental model to fall back on.
