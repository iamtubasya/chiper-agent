# Immunefi Program Discovery — Practical Methods

## Problem
Immunefi website (immunefi.com/bug-bounty) is a **client-rendered Next.js SPA**. All traditional extraction methods fail:
- `curl` → returns empty `<div id="__next"></div>` (no server-side rendering)
- `web_extract` → returns empty HTML (same SPA problem)
- Browser automation → JS doesn't execute properly in headless mode
- `arkadiyt/bounty-targets-data` → `immunefi_data.json` does NOT exist

## Working Methods

### Method 1: SmartContractsHacking.com Aggregator (RELIABLE)
This site has a database of 340+ Immunefi programs with tier/chain/multiplier/TVL data.

```bash
# Get full JSON data (requires parsing)
curl -sL "https://smartercontracts.com/assets/data/immunefi_programs.json"
# or parse HTML table from the main page
```

**Programs available (as of Sep 2026):**
- Tier 1 ($250K-$10M): Hyperliquid, WorldChain, Babylon, Polymer, Lombard, EigenLayer, Astroports, Wormhole, Spark, Wormhole Foundation, Succinct, Sommelier, Gravity Alloy, Wander (FHE)
- Tier 1.5 ($100K-$1M): Morpho, Ondo Finance, Lido, Chainlink, Jupiter, StakeStone, DeFiHourGlass
- Tier 2 ($50K-$250K): Optimism, Blast, Gateway FM, Zora, Eigen Protocol, Defi.app, Instadapp, Safe, Sommelier, Reservoir, Ondo Finance
- Tier 3 ($25K-$100K): Across, Synapse, Hyperliquid, Synthetix, Sandbox, Gearbox, STFX, Goldfinch, Euler, Ethena, Ambient, Gearbox, Blueberry, Denet, Stargate
- Tier 4 ($10K-$25K): Pendle, 1inch, Ellipsis, Aavegotchi, Sky Mavis, Gearbox, Pangolin, Platypus
- Full list: 100+ programs, see smarthire ContractsHacking.com

### Method 2: Web Search (BROAD)
```bash
web_search("immunefi bug bounty programs 2026 active")
web_search("immunefi top tier DeFi programs highest payout")
```
Search results often contain cached/extracted data from aggregator sites.

### Method 3: Individual Program Pages (VERIFICATION)
For specific program details (scope, rules, severity):
```bash
curl -sL "https://immunefi.com/bounty/PROGRAMSLUG/"
# Often returns partial HTML with <title> and meta description
# Not reliable for full scope data
```

**Better:** Search `immunefi.com/bounty/PROGRAMSLUG` via web_search for cached/indexed content.

### Method 4: Programmatic API (LIMITED)
No official Immunefi API exists for program listing. The website is fully client-side rendered.

## Key Data Points Per Program
- **Tier** ($250K/$1M/$10M max bounty)
- **Multiplier** (e.g., 10x for critical)
- **Chains** (Ethereum, Solana, BSC, etc.)
- **TVL** (Total Value Locked)
- **Status** (Active/Paused/Closed)
- **Program URL** (immunefi.com/bounty/SLUG)

## Tier Classification (Immunefi)
- **Tier 1** ($250K+): Major DeFi protocols, significant TVL
- **Tier 2** ($100K-$250K): Established protocols, moderate TVL
- **Tier 3** ($25K-$100K): Growing protocols, smaller TVL
- **Tier 4** ($10K-$25K): Newer/smaller protocols
- **Tier 5** (<$10K): Micro-protocols, testing grounds

## Common Immunefi Program Patterns
1. **Multi-chain programs**: Same scope across Ethereum + L2s
2. **Per-fork bounties**: Separate bounties per chain/fork
3. **Wildcard scope**: `*.protocol.com` covers all subdomains
4. **Exclusions**: Usually governance tokens, frontends, documentation sites
5. **Severity criteria**: Based on direct/indirect fund loss, not just code bugs

## Severity Mapping (Quick Reference)
- **Critical**: Direct fund loss, protocol insolvency, permanent asset freeze
- **High**: Temporary DoS of critical functions, contract upgrade without timelock
- **Medium**: Oracle failure, MEV extraction, griefing with financial impact
- **Low**: Non-critical function DoS, gas griefing, best practice violations
