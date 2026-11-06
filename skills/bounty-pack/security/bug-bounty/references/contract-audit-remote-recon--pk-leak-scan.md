# PK Leak Scan — did recon material leak the owner/buyback wallet key?

When the client (or you) asks "cek apakah ada leak PK <wallet>" — the question is whether any
recon material (JS bundles, verified source, scraped HTML/JSON, reports, logs) contains the
private key of a fund-recipient wallet (owner, buyback, requestSigner). This is a legitimate
audit check: hardcoded keys in frontends/backend bundles are a real leak class.

## Methodology (in order)

1. **Collect every file**: JS chunks, HTML scrapes, JSON, .sol/.txt source, .md reports,
   .py audit scripts, .env*, .log. Scan the whole working dir, not just "the interesting files".

2. **Regex pass 1 — raw 64-hex**: `(?<![0-9a-fA-F])(0x)?[0-9a-fA-F]{64}(?![0-9a-fA-F])`
   across everything. Then CLASSIFY each hit before reporting:
   - **Solidity bytecode** → starts `6080604052` / `608060405234`, or first byte is a push
     opcode (0x60–0x7f). Whitelist: multicall3 bytecode, ERC-6492 signature validator,
     deployless-call bytecodes (all ship inside wagmi/viem bundles).
   - **Crypto curve constants** (NOT keys): secp256k1 p
     `ffffffff...fffffc2f`, secp256k1 n `ffffffff...4141`, P-256 `ffffffff...fffff93b`,
     ed25519 base-point coordinate arrays (`8e38e38e...`, `4bda12f6...` patterns), BLS params.
     These appear as `BigInt("0x...")` literals in noble/viem bundle code.
   - **Real key candidates** → apply the [REDACTED] rule (below).

3. **Regex pass 2 — key-pattern**: `(private[_\- ]?key|secret[_\- ]?key|mnemonic|seed[_\- ]?phrase|wallet[_\- ]?key|api[_\- ]?key|PK)\s*[=:]\s*["']?(64-hex|base64{60,})`
   case-insensitive. Also grep variable names: `signer|signingKey|secretKey|seedPhrase`.

4. **Regex pass 3 — long base64**: `[A-Za-z0-9+/]{80,}={0,2}` — check context. Usual false
   positives: Solidity bytecode, sourceMappingURL data URIs, GitHub/Google visitor-payload
   cookies, X/Twitter session cookies (`auth_token`, `ct0` — those are YOUR scraping session's
   tokens, not the target's wallet key; flag as "not a wallet key" in the report).

5. **Address presence check**: search the target wallet address (owner/buyback) across all
   files. If it appears ONLY in your own audit scripts/reports, that's a self-reference, not a
   leak — say so explicitly so the client knows you checked.

6. **Public surface check**: GitHub code search (requires login for API; the HTML search page
   returns 0 code matches without auth) + DuckDuckGo/Google for the address. Expect 0 hits for
   an un-leaked EOA.

## Classification decision tree
```
64-hex found?
 ├─ starts 0x6080604052 / first byte 0x60-0x7f  → bytecode (skip)
 ├─ matches known curve constant                 → crypto param (skip)
 ├─ context has privateKey/secret/mnemonic/seed  → LEAK — [REDACTED], report file+line
 └─ random-looking, no key context               → inspect context; likely hash/constant
```

## Safety rule (non-negotiable)
If a REAL private key value is ever found: **write [REDACTED] in every output** — report,
chat, summary, memory. NEVER copy the value, not even "for verification". This is a standing
constraint for all audits.

## UPONZI worked example (2026-08-18)
- Target: buyback wallet `0x6ee3eefb...` + owner `0x21e16d...` on Robinhood Chain 4663.
- Scanned 107 files (JS bundle incl. viem chunk, 4 verified contracts, HTML scrapes, JSON,
  reports, audit scripts).
- All 25 non-bytecode 64-hex hits were secp256k1/P-256/ed25519 curve constants inside the
  wagmi/viem bundle — NOT keys. Zero key-pattern matches. Zero key-store JSON.
- Addresses appeared only in our own audit files. GitHub/DDG: 0 hits.
- Verdict: NO PK leak in recon material. The only "secrets" present were X scraping session
  cookies (x_cookies.json) — unrelated to UPONZI wallets.

## Companion: Base chain RPC fallbacks
`mainnet.base.org` rate-limits hard. Working alternates (verified): `https://base-rpc.publicnode.com`
(primary fallback), also `base.llamarpc.com`, `1rpc.io/base`, `base.drpc.org`. Always send a
User-Agent on urllib requests; add retries when a public RPC starts returning all-zeros —
first confirm the RPC is actually answering (eth_chainId + eth_getCode), THEN trust zeros.
