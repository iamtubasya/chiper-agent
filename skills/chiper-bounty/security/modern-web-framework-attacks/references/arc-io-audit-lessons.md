# arc.io Audit Lessons (2026-09-20)

## Key Findings Summary
1. **MCP Server (docs.arc.io)** — Unauthenticated shell exec in sandbox. `env` works, `/proc` blocked, no exfil tools in sandbox.
2. **Onramp RSC Config Leak** — Socure SDK key + 12 internal API endpoints + full routing table exposed in Next.js RSC payload.
3. **Portal Feature Flags** — 17 flags + DynamoAuth SDK ID + 365+ token routes + nonce generation exposed without auth.
4. **Explorer API** — Full Blockscout API accessible via browser fetch (curl blocked by Cloudflare).

## Corrected: DynamoAuth Verify Endpoint (DEEP DIVE RESULT)

The `/verify` endpoint WAS found and tested:

```
POST https://app.dynamicauth.com/api/v0/sdk/f3386450-b803-4812-a05d-8e788e3e0ee8/verify
```

**Required schema** (discovered via 400 error):
```json
{
  "signedMessage": "<ECDSA signature>",
  "publicWalletAddress": "<wallet address>",
  "chain": "EVM",
  "walletName": "MetaMask",
  "walletProvider": "injected",
  "messageToSign": "<SIWE message>",
  "nonce": "<from DynamoAuth nonces endpoint>"
}
```

**What was proven end-to-end:**
1. ✅ Nonce generation — HTTP 200, valid nonce returned
2. ✅ SIWE message construction — valid EIP-4361 format
3. ✅ Wallet signing — ethers.js `signMessage()` produces valid ECDSA
4. ✅ Signature verification — `ethers.verifyMessage()` recovers correct address
5. ✅ /verify endpoint exists — HTTP 400 (schema validation) and HTTP 429 (rate limit), NOT 404
6. ❌ Full auth bypass — blocked by Cloudflare rate limit (error 1015) on my IP

**Critical lesson:** User DEMANDS actual PoC execution, not theoretical descriptions. "jgn teoritis sy blg, kamu harus buktikan kl ini bener bisa dilakukan" — if a step can't be completed (e.g., CF rate limit), say so HONESTLY rather than claiming "proven".

## DynamoAuth Nonce + SIWE Attack Chain

### What Works
- Nonce generation: unauthenticated, no rate limit on `/nonces?count=1`
- Nonces max 5 per request (error: "request/query/count must be <= 5")
- SDK ID `f3386450-b803-4812-a05d-8e788e3e0ee8` is public, hardcoded in portal.arc.io JS
- SIWE message follows EIP-4361 standard — victim sees legitimate "Sign in to Arc Portal" + valid URI

### What Blocks Full Exploit
- Cloudflare rate limits `/verify` endpoint aggressively (error 1015)
- In real attack: victim signs from their OWN IP (rate limit doesn't apply to them)
- Attacker captures signature from phishing page → submits to /verify from attacker IP (might get rate limited)

### Realistic Severity
- **P3-P4**: Information disclosure + theoretical phishing chain
- NOT proven ATO (rate limit blocks end-to-end test from single IP)
- Would need: separate victim IP + attacker relay infrastructure to fully prove

## What DIDN'T Work
- **Socure SDK key is NOT a finding** — It's a client-side public key (like Stripe pk_test_...). The SDK auto-initializes from the DOM `data-public-key` attribute. No abuse possible.
- **`browser_exec` cannot access localhost** — CDP via Python websocket is the only reliable approach on Windows.
- **Chrome CDP startup** — `subprocess.Popen` with forward-slash paths works. `cmd.exe /c start` and bash `&` backgrounding both fail. Path escaping with `\\\\` causes SyntaxError.

## Attack Vector Results (50+ tested)
| Vector | Result |
|--------|--------|
| XSS (reflected/stored/DOM) | Not reflected on any endpoint |
| IDOR | Explorer: public blockchain data (by design). Portal: requires auth. |
| SSRF | No URL-fetching endpoints found |
| Open Redirect | None on 15+ tested params |
| SSTI | No template injection |
| GraphQL | Returns HTML (not accessible via curl) |
| Prototype Pollution | `__proto__` accepted but no effect |
| Host Header Injection | Cloudflare blocks invalid hosts |
| CRLF Injection | URL-encoded in Location, not actual header injection |
| Subdomain Takeover | No dangling CNAMEs |
| CSRF | HubSpot forms have server-side validation |
| Race Condition | No rate limiting on RPC (public blockchain) |
| CORS | Only status.arc.io `*` (standard Statuspage) |
| Mass Assignment | No writable endpoints found |
| Business Logic | Onramp session properly validated |

## Severity Calibration Notes
- Config/SDK key leaks → P4 (Low) maximum
- MCP sandbox exec → P3-P4 (no escape, no exfil)
- DynamoAuth nonce + routing table → P3-P4 (theoretical phishing chain, not proven)
- Explorer API public data → P5/INFO (blockchain data is public by design)
