# Web3 Independent & Direct Bug Bounty Reconnaissance

Methodology and workflows for discovering non-aggregator Web3 bug bounty programs (bypassing Immunefi, HackerOne, Bugcrowd, Intigriti, and YesWeHack).

## 1. Dork Formulations & Search Syntax Pitfalls

Standard Google/DuckDuckGo engines do not parse boolean `|` or `&` correctly.
- Use uppercase `OR`, whitespace for `AND`.
- Use `-site:<domain>` rather than bare negative keywords `-domain` (which erroneously exclude articles or disclosure pages simply mentioning the aggregator in footers, author bios, or citations).

### High-Yield Search Dorks:
```text
# Independent Web3 / Smart Contract Bounty Pages
("Bug Bounty Program" OR "Vulnerability Reward") ("smart contract" OR web3 OR blockchain OR defi OR crypto) inurl:(security OR bounty OR vulnerability) -site:immunefi.com -site:hackerone.com -site:bugcrowd.com -site:yeswehack.com -site:intigriti.com

# RFC 9116 / security.txt Discovery
inurl:"/.well-known/security.txt" ("crypto" OR "blockchain" OR "web3" OR "ethereum" OR "solana") ("bounty" OR "reward") -site:immunefi.com -site:hackerone.com

# GitHub SECURITY.md Active Policies
filename:SECURITY.md ("bug bounty" OR "vulnerability reward") ("smart contract" OR "solidity" OR "anchor" OR "cosmwasm") -site:immunefi.com
```

## 2. GitHub Independent Discovery Workflow

The community list `lissy93/bug-bounties` maintains `independent-programs.yml` specifically for self-hosted programs (excluding platform aggregators).

### Filter Commits by Date Window on `independent-programs.yml`:
```bash
python3 -c "
import urllib.request, json
url = 'https://api.github.com/repos/lissy93/bug-bounties/commits?path=independent-programs.yml&since=2026-10-01T00:00:00Z'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
commits = json.loads(urllib.request.urlopen(req).read().decode())
for c in commits:
    msg = c['commit']['message'].split('\n')[0]
    print(f\"{c['commit']['committer']['date'][:10]} | {msg}\")
"
```

### Keyword Filter over `independent-programs.yml`:
Web3 programs are identified by scanning company scope for: `solidity`, `smart contract`, `zk`, `evm`, `dex`, `crypto`, `blockchain`, `token`.

## 3. Alternative Web3-Native Platforms (Non-Immunefi)

When targeting Web3 outside of Immunefi and Web2 platforms:
- **Hats Finance (`hats.finance`)**: On-chain bounty vaults where funds are locked in smart contracts. Zero counterparty risk on validated PoCs.
- **Code4rena Continuous Bounties (`code4rena.com/bounties`)**: Continuous bounty programs (e.g. `code-423n4/<project>-bug-bounty` repos on GitHub) running parallel to competitive audits.
- **Cantina (`cantina.xyz`)**: High-tier protocol competitions and recurring bug bounties.
- **Sherlock (`sherlock.xyz`)**: Protocol coverage smart contract bounties.
- **BugRap (`bugrap.io`)**: Dedicated Web3 bug bounty platform for APAC/global crypto projects.

## 4. Tier-1 Direct Foundation Programs (Always Active)

- **Ethereum Foundation**: `bounty.ethereum.org` ($250k - $1M+) - Execution/Consensus clients, Solidity, cryptography specs.
- **Uniswap Labs**: `uniswap.org/bug-bounty` ($3M max) - v3/v4 contracts, hooks, Universal Router.
- **Solana / Anza**: `anza.xyz/security` ($1M USDC) - Agave validator, runtime, BPF loader.
- **Binance SRC**: `bugbounty.binance.com` ($100k max) - Web3 wallet, BSC infra, exchange core.
- **Kraken**: `kraken.com/features/security/bug-bounty` ($100k+ max) - Custody, APIs, exchange infra.
