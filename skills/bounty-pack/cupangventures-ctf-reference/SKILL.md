---
name: cupangventures-ctf-reference
author: RESEARCHER_NAME
description: "Cupang Ventures CTF 50-Gate Writeup: complete solution walkthrough, rank #1 reference."
category: security
version: 1.0.0
metadata:
  hermes:
    tags: [cupangventures-ctf-reference]
---

# Cupang Ventures CTF — 50 Gates Writeup

## Reference
- Target: `https://event.cupangventures.com/dashboard`
- Handle: `irish-codex`
- Result: **50/50 gates solved, Rank #1**
- Reward gates: 6, 19, 23, 34, 41, 47, 49

## Hints Used
| # | Hint |
|---|------|
| 1 | Warm-up keeps nothing |
| 2 | None before Gate 06 |
| 3 | Five wallets scattered |
| 4 | Two Claude accounts deep |
| 5 | No adjacent rewards |
| 6 | RSA slot, strict wallet slot, Gate 50 glory only |

## API Patterns
```
GET  /api/gates/:n     → Get gate challenge
POST /api/gates/:n     → Submit answer
GET  /api/leaderboard  → Current rankings
```

## Gate Solutions (Key Gates)

### Gate 1 — Caesar Cipher
ROT-13 or shift-based cipher. Decode shifted text.

### Gate 2 — Vigenere Cipher
Key: `watch` — standard Vigenere decryption.

### Gate 3 — Multi-XOR
Key: `GATE` — XOR each byte with repeating key.

### Gate 4+ — Affine Cipher
Parameters: a=5, b=8
Decrypt: `D(x) = a_inv * (x - b) mod 26`
`a_inv = modular_inverse(5, 26) = 21`

### Gates 6-50 — Multi-step RSA Transforms
Pattern:
1. Read RSA ciphertext + public key from gate
2. Factor N (varies: Fermat, Wiener, factordb, small-e)
3. Decrypt → intermediate value
4. Apply transform (hex decode, base64, wallet derivation, etc.)
5. Submit final flag

### Wallet Verification Gates
- Derive Ethereum address from private key
- Match against expected address
- Submit matching address as flag

## Reward Gates
| Gate | Reward Type |
|------|-------------|
| 6 | First leaderboard reward |
| 19 | Second reward |
| 23 | Third reward |
| 34 | Fourth reward |
| 41 | Fifth reward |
| 47 | Sixth reward |
| 49 | Seventh reward |

## Lessons
- **Warm-up gates teach nothing** — skip analysis, solve fast
- **No hints before Gate 06** — brute force early gates
- **Five wallets scattered** — wallet-based gates need address derivation
- **RSA is the bottleneck** — factoring strategy selection is key
- **Gate 50 is glory only** — no reward, pure prestige

## Pitfalls
- API rate limits — add delays between submissions
- Flag format varies per gate — check response carefully
- Some gates need external tools (SageMath for lattice attacks)
- Wallet derivation needs correct BIP-44 path (m/44'/60'/0'/0/0)
- Leaderboard updates may lag behind submissions
