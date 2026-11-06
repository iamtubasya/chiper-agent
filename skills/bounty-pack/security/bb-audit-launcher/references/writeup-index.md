# Writeup Index — Bug Bounty Case Studies

## Web2 Writeups
- Bitso 2026: auth bypass + IDOR chain → $5K
- Chime 2026: business logic → price manipulation
- Kinsta 2026: SSRF → cloud metadata → RCE
- NASA VDP: info disclosure → credential leak
- Neony Exchange: race condition → double-spend
- Adafruit 2026: API key leak → account takeover
- Fireblocks 2026: session hijack → fund access
- Crowdstrike: OAuth misconfig → token theft

## Web3/DeFi Writeups
- Compound V2 fork: reentrancy → fund drain
- ERC4626 vaults: share inflation → deposit theft
- LayerZero OFT: message replay → cross-chain attack
- Paxos Cantina: oracle manipulation → price exploit
- TON/Torch Finance: flash loan → governance attack

## Smart Contract Patterns
- Access control modifier mismatch
- Unchecked return values (低级错误)
- Integer overflow in fee calculation
- Front-running in DEX operations
- Flash loan + oracle manipulation chain

## Attack Chains (Cross-Vector)
- SSRF → cloud metadata → IAM role → S3 access
- XSS → session steal → privilege escalation → admin
- Race condition → balance manipulation → fund extraction
- GraphQL introspection → hidden mutation → mass assignment
- CORS misconfig → CSRF → account takeover
