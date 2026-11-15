# Immunefi Vulnerability Severity Classification System — **v2.3**

> **Source (authoritative):** https://immunefi.com/immunefi-vulnerability-severity-classification-system-v2-3/
> **Snapshot:** 2026-10-02 · extracted verbatim from the live page (the site is JS-rendered / Cloudflare-protected
> — `curl` + `web_extract` return nothing; use Playwright/Chrome headful or the CDP path to re-pull it).
> **Supersedes:** `immunefi-severity.md` (which documented **v2.2** in summary form). v2.3 is the operative system.
> **Scope:** Immunefi ONLY (Immunefi-hosted bug bounty programs + audit competitions).

---

## 0. The one rule that matters

**Immunefi does NOT use CVSS.** There is no CVSS vector, no calculator, no numeric score. A vulnerability is
classified on a **simplified 4-level scale by IMPACT**, and the level can be **downgraded or rejected** when the
exploit requires **elevated privileges** or **uncommon user interaction**.

```
4 = Critical      3 = High      2 = Medium      1 = Low
```

Two hard prerequisites before you even assign a level — miss either and triage rejects the report:

1. **The IMPACT must come from the program's official impact list** (the project's own in-scope impacts).
2. **The ASSET must come from the program's official asset list** (contract addresses / domains / repos).

> "The table below is mostly concerned with the consequence of a successful exploit. Keep in mind that if the
> exploit requires elevated privileges or uncommon user interaction, the level of the bug may be downgraded to
> reflect that or rejected."

---

## 1. Blockchain / DLT

| Level | Impact |
|---|---|
| **4. Critical** | • Network not being able to confirm new transactions (total network shutdown)<br>• Unintended permanent chain split requiring hard fork (network partition requiring hard fork)<br>• Direct loss of funds<br>• Permanent freezing of funds (fix requires hardfork) |
| **3. High** | • Unintended chain split (network partition)<br>• Temporary freezing of network transactions by delaying one block by **500% or more** of the average block time of the preceding 24 hours beyond standard difficulty adjustments<br>• Causing network processing nodes to process transactions from the mempool **beyond set parameters**<br>• RPC API crash affecting projects with **≥ 25%** of the market capitalization on top of the respective layer |
| **2. Medium** | • Increasing network processing node resource consumption by **at least 30%** without brute force actions, compared to the preceding 24 hours<br>• Shutdown of **≥ 30%** of network processing nodes without brute force actions, but does not shut down the network<br>• A bug in the respective layer 0/1/2 network code that results in unintended smart contract behavior with **no concrete funds at direct risk** |
| **1. Low** | • Shutdown of **> 10% but < 30%** of network processing nodes without brute force actions, but does not shut down the network<br>• Modification of transaction fees outside of design parameters |

---

## 2. Smart Contracts

| Level | Impact |
|---|---|
| **4. Critical** | • Manipulation of governance voting result deviating from voted outcome and resulting in a direct change from intended effect of original results<br>• **Direct theft of any user funds, whether at-rest or in-motion, other than unclaimed yield**<br>• Direct theft of any user NFTs, whether at-rest or in-motion, other than unclaimed royalties<br>• **Permanent freezing of funds**<br>• Permanent freezing of NFTs<br>• Unauthorized minting of NFTs<br>• Predictable or manipulable **RNG** that results in abuse of the principal or NFT<br>• Unintended alteration of what the NFT represents (e.g. token URI, payload, artistic content)<br>• **Protocol insolvency** |
| **3. High** | • Theft of **unclaimed** yield<br>• Theft of unclaimed royalties<br>• Permanent freezing of unclaimed yield<br>• Permanent freezing of unclaimed royalties<br>• **Temporary freezing of funds**<br>• Temporary freezing NFTs |
| **2. Medium** | • Smart contract unable to operate due to lack of token funds<br>• Block stuffing<br>• **Griefing** (e.g. no profit motive for an attacker, but damage to the users or the protocol)<br>• Theft of gas<br>• Unbounded gas consumption |
| **1. Low** | • Contract fails to deliver promised returns, but doesn't lose value |

> **The yield/fund line is the single most common severity dispute:** *principal* (at-rest or in-motion, outside
> unclaimed yield) = **Critical**; *unclaimed* yield/royalties = **High**; *temporary* freeze = **High**;
> *permanent* freeze = **Critical**.

---

## 3. Websites and Apps

| Level | Impact |
|---|---|
| **4. Critical** | • Execute arbitrary system commands<br>• Retrieve sensitive data/files from a running server, such as: `/etc/shadow`, database passwords, blockchain keys<br>  *(this does **not** include non-sensitive environment variables, open source code, or usernames)*<br>• Taking down the application/website<br>• Taking down the NFT URI<br>• Taking state-modifying authenticated actions (with or without blockchain state interaction) **on behalf of other users without any interaction by that user**, such as: changing registration information, commenting, voting, making trades, withdrawals, etc.<br>• Changing the NFT metadata<br>• Subdomain takeover **with** already-connected wallet interaction<br>• Direct theft of user funds<br>• Malicious interactions with an already-connected wallet, such as: modifying transaction arguments or parameters, substituting contract addresses, submitting malicious transactions<br>• Direct theft of user NFTs<br>• Injection of malicious HTML or XSS through NFT metadata |
| **3. High** | • Injecting/modifying the static content on the target application **without JavaScript (persistent)**, such as: HTML injection without JavaScript, replacing existing text with arbitrary text, arbitrary file uploads, etc.<br>• Changing **sensitive** details of other users (including modifying browser local storage) **without already-connected wallet interaction and with up to one click** of user interaction, such as: email or password of the victim, etc.<br>• Improperly disclosing **confidential user information**, such as: email address, phone number, physical address, etc.<br>• Subdomain takeover **without** already-connected wallet interaction |
| **2. Medium** | • Changing **non-sensitive** details of other users (including modifying browser local storage) without already-connected wallet interaction and with up to one click of user interaction, such as: changing the first/last name of user, enabling/disabling notifications<br>• Injecting/modifying the static content on the target application without JavaScript **(reflected)**, such as: reflected HTML injection, loading external site data<br>• Redirecting users to malicious websites (open redirect) |
| **1. Low** | • Changing details of other users (including modifying browser local storage) without already-connected wallet interaction and with **significant** user interaction, such as: iframing leading to modifying the backend/browser state (must demonstrate impact with PoC)<br>• Taking over broken or expired outgoing links, such as social media handles, etc.<br>• Temporarily disabling user access to the target site, such as: locking up the victim from login, cookie bombing, etc. |

> **Web2 notes that change payouts:**
> - **XSS paid via NFT metadata** = Critical. **XSS in normal web UI** is not listed at all → it is judged by the
>   *action* it enables. **State-changing action on behalf of another user with zero interaction** = Critical;
>   with up to one click and sensitive detail = High; non-sensitive = Medium.
> - **HTML injection without JS** is High when *persistent*, Medium when *reflected*. **Plain-text reflected
>   injection** is explicitly **out of scope**.
> - **Confidential info disclosure** (email/phone/address) = High. **Non-confidential** (IPs, server names, most
>   stack traces) = out of scope.

---

## 4. Out of Scope & Rules (Immunefi's default recommendations to projects)

These are the **default** impacts Immunefi recommends programs mark out of scope — the actual list differs per
program, so always read the program's own page first.

**General**
- Impacts requiring attacks that the **reporter has already exploited themselves**, leading to damage
- Impacts caused by attacks requiring access to **leaked keys/credentials**
- Impacts caused by attacks requiring access to **privileged addresses** (incl. governance and strategist
  contracts) **without additional modifications** to the privileges attributed
- Impacts relying on attacks involving the **depegging of an external stablecoin** where the attacker does not
  directly cause the depegging due to a bug in code
- **Mentions of secrets, access tokens, API keys, private keys in GitHub** are out of scope **without proof that
  they are in-use in production**
- Best-practice recommendations · Feature requests
- Impacts on **test files and configuration files** unless stated otherwise by the program
- Impacts requiring **phishing or other social engineering** against employees/customers

**Smart Contracts / Blockchain DLT**
- Incorrect data supplied by **third-party oracles** *(does not exclude oracle manipulation / flash loan attacks)*
- Impacts requiring **basic economic and governance attacks** (e.g. 51% attack)
- **Lack of liquidity** impacts
- Impacts from **Sybil** attacks
- Impacts involving **centralization risks**

**Websites and Apps**
- **Theoretical impacts with no proof/demonstration**
- Attacks requiring **physical access** to the victim device, or access to the **victim's local network**
- **Reflected plain text injection** (url parameters, path, etc.) — *does not exclude reflected HTML injection
  with or without JavaScript, and does not exclude persistent plain text injection*
- **Self-XSS**
- **Captcha bypass using OCR without impact demonstration**
- **CSRF with no state-modifying security impact** (e.g. logout CSRF)
- Missing **HTTP security headers / cookie flags** (X-FRAME-OPTIONS, `httponly`…) **without demonstrated impact**
- **Server-side non-confidential info disclosure** (IPs, server names, most stack traces)
- Impacts **only enumerating/confirming existence** of users or tenants
- Impacts from **un-prompted in-app user actions** outside normal app workflows
- Lack of **SSL/TLS best practices**
- Impacts that **only require DDoS**
- **UX/UI impacts** that do not materially disrupt use of the platform
- Impacts primarily caused by **browser/plugin defects**
- Leakage of **non-sensitive API keys** (e.g. Etherscan, Infura, Alchemy)
- Any vulnerability exploit requiring **browser bugs** (e.g. CSP bypass)
- SPF/DMARC misconfigured records · Missing HTTP headers without demonstrated impact
- **Automated scanner reports without demonstrated impact** · UI/UX best-practice recommendations
- Non-future-proof NFT rendering

---

## 5. Prohibited Activities (platform-wide default)

Programs may add further restrictions; these are prohibited by default:
- **Any testing on mainnet or public testnet deployed code** — all testing should be on **local forks** of a
  public testnet or mainnet
- Any testing with **pricing oracles or third-party smart contracts**
- **Phishing / social engineering** against employees and/or customers
- Any testing with **third-party systems and applications** (e.g. browser extensions) as well as websites
  (e.g. SSO providers, advertising networks)
- **Any DoS attacks executed against project assets**
- **Automated testing of services that generates significant amounts of traffic**
- Public disclosure of an unpatched vulnerability in an **embargoed** bounty
- Any other actions prohibited by the Immunefi Rules

→ Pairs with `immunefi-rules.md` (32 prohibited behaviors) and `exploit-cookbook/references/…` for the PoC shape:
**Foundry fork test on a local fork, never a mainnet blind execution.**

---

## 6. Fast mapping (finding → level) — v2.3

| Finding | Level |
|---|---|
| Reentrancy → drain principal/user funds | **Critical** |
| Flashloan / oracle manipulation → funds at risk | **Critical** |
| Uninitialized proxy / upgrade hijack → funds or governance | **Critical** |
| Bridge message spoofing / attestation mismatch → funds | **Critical** |
| Access control bypass on a critical function | **Critical** |
| Unauthorized NFT mint / locked URI / manipulable RNG | **Critical** |
| Governance vote manipulation changing outcome | **Critical** |
| Protocol insolvency | **Critical** |
| **Theft / permanent freeze of unclaimed yield or royalties** | **High** |
| Temporary freezing of funds/NFTs | **High** |
| Persistent HTML injection without JS · arbitrary file upload | **High** |
| Sensitive user data disclosure (email/phone/address) | **High** |
| Subdomain takeover (no wallet interaction) | **High** |
| Griefing · block stuffing · unbounded gas · theft of gas | **Medium** |
| Reflected HTML injection · open redirect | **Medium** |
| Non-sensitive profile change (≤1 click) | **Medium** |
| Contract fails to deliver promised returns (no value lost) | **Low** |
| Broken/expired outgoing link takeover · login lockout · cookie bombing | **Low** |
| Theoretical impact, scanner output, self-XSS, logout CSRF, missing headers | **Out of scope** |

---

## 7. v2.2 → v2.3 delta (what to unlearn)

The old `immunefi-severity.md` summary is not wrong, but it is incomplete and loses the boundaries that decide
triage. v2.3 adds/formalises:

1. **Per-domain explicit impact tables** — Blockchain/DLT, Smart Contracts, Websites and Apps (v2.2 had a merged
   short list).
2. **NFT-specific Criticals** — unauthorized minting, manipulable RNG, unintended alteration of what the NFT
   represents, direct NFT theft, XSS via NFT metadata.
3. **Governance manipulation** → explicitly **Critical** (v2.2 short list implied High).
4. **Quantitative thresholds** in the DLT tier — 500% block delay, ≥25% market-cap RPC impact, ≥30% node
   shutdown, 30% resource, 10–30% node shutdown.
5. **The OOS + prohibited-activities appendix** — the part most likely to turn an "obvious Critical" into a
   rejection (scanner output, self-XSS, logout CSRF, header gaps, non-confidential disclosure, mainnet testing).

**Backwards compatibility:** anything filed against a program still running v2.2 should be argued with the v2.2
wording; v2.3 wording is the platform default now. Keep the **impact × asset list** precondition as the first
gate in both.

---

## 8. Operator checklist before filing (Immunefi)

```
[ ] Impact appears VERBATIM in the program's official impact list?
[ ] Asset appears in the program's official asset list?
[ ] No elevated privilege / uncommon interaction needed (else expect downgrade/reject)?
[ ] PoC = local Foundry fork (never mainnet/public testnet execution)?
[ ] No prohibited activity used (no DoS, no third-party systems, no phishing)?
[ ] Not a scanner dump, not theoretical, not self-XSS / logout-CSRF / header-only?
[ ] Level justified by IMPACT (not CVSS) + the boundary line (principal vs unclaimed yield, temp vs permanent)?
[ ] Severity dispute argument = concrete attacker scenario with numbers (funds, %, time)?
```
