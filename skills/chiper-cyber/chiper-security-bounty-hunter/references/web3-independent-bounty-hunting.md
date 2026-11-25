# Web3 Independent & Direct Bug Bounty Hunting

Guide and reference for discovering high-impact Web3, blockchain, and smart contract bug bounty programs outside major third-party aggregators (Immunefi, HackerOne, Bugcrowd, Intigriti, YesWeHack).

---

## 1. Dorking & Search Strategy

To locate independent programs, construct queries that exclude platform domains and focus on self-hosted disclosure portals, RFC 9116 `security.txt`, or repository `SECURITY.md`.

### A. Search Engine Dorks (Google / DuckDuckGo)

**Direct Self-Hosted Bug Bounty Pages:**
```text
("Bug Bounty Program" OR ("Vulnerability" AND "Reward")) ("smart contract" OR web3 OR blockchain OR defi OR crypto) inurl:(security OR bounty OR vulnerability) -site:immunefi.com -site:hackerone.com -site:bugcrowd.com -site:yeswehack.com -site:intigriti.com -site:medium.com
```

**RFC 9116 `security.txt` Discovery:**
Finds Web3 organizations publishing responsible disclosure and bounty terms directly on their domains:
```text
inurl:"/.well-known/security.txt" ("crypto" OR "blockchain" OR "web3" OR "ethereum" OR "solana") ("bounty" OR "reward") -site:immunefi.com -site:hackerone.com -site:bugcrowd.com
```

**Scope & Policy Document Dorks:**
```text
filetype:pdf ("Bug Bounty" OR "Vulnerability Disclosure Policy") ("smart contract" OR "token" OR "blockchain") -site:immunefi.com -site:hackerone.com
```

---

## 2. GitHub Reconnaissance for Web3 Bounties

Many Web3 projects define bounties exclusively in their GitHub repositories without listing them on aggregators.

### A. GitHub Code Search Dorks

Search for `SECURITY.md` containing reward clauses in Solidity, Rust, or Vyper codebases:
```text
path:SECURITY.md ("bug bounty" OR "vulnerability reward") ("smart contract" OR "solidity" OR "anchor" OR "cosmwasm") -site:immunefi.com
```

### B. Automated GitHub API Discovery Script

```python
import urllib.request, urllib.parse, json

def search_github_web3_bounties(token=None):
    query = '("bug bounty" OR "vulnerability reward") ("smart contract" OR "solidity" OR "anchor") path:SECURITY.md'
    url = f'https://api.github.com/search/code?q={urllib.parse.quote(query)}&per_page=30'
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github.v3+json'}
    if token:
        headers['Authorization'] = f'token {token}'
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print(f"Total matching repos: {data.get('total_count')}")
            for item in data.get('items', []):
                repo = item['repository']['full_name']
                print(f"[*] {repo}: {item['html_url']}")
    except Exception as e:
        print(f"Error querying GitHub: {e}")

if __name__ == "__main__":
    search_github_web3_bounties()
```

---

## 3. Verified Tier-1 Self-Hosted Web3 Programs (Direct Core Dev)

These organizations operate their own triage pipelines and bounty pools with zero platform mediation:

| Target / Ecosystem | Primary Scope | Max Bounty | Disclosure / Portal URL |
| :--- | :--- | :--- | :--- |
| **Ethereum Foundation** | Core Consensus (Prysm, Lighthouse, Teku) & Execution (Geth, Nethermind, Besu), Specs, Solidity compiler | **$250,000 – $1,000,000+** | https://bounty.ethereum.org/ |
| **Uniswap Labs** | Universal Router, Permit2, Uniswap v3/v4 Core & Periphery | **$3,000,000** | https://uniswap.org/bug-bounty |
| **Solana / Anza** | Agave validator client, BPF loader, core runtime | **$1,000,000 (USDC)** | https://anza.xyz/security |
| **Web3 Foundation (Polkadot)** | Polkadot Host, Substrate runtime, Kusama implementation | **$250,000** | https://web3.foundation/bounty/ |
| **Chainlink** | Core node software, oracle feeds, smart contract suite | **$100,000+** | https://chain.link/bounty |
| **Binance SRC** | Exchange infra, Web3 wallet services, BNB Chain native apps | **$100,000** | https://bugbounty.binance.com/ |
| **OKX SRC** | Exchange platform, OKX Web3 Wallet, DEX aggregator | **$50,000** | https://security.okx.com/ |
| **Kraken** | Exchange custody, trading engines, mobile API | **$100,000+** | https://kraken.com/features/security/bug-bounty |
| **Ledger Donjon** | Hardware wallet firmware, Ledger Live, secure element applets | **€50,000+** | https://donjon.ledger.com/bounty/ |
| **Trezor (SatoshiLabs)** | Trezor Core, Trezor One/T/Safe firmware, Trezor Suite | **Variable** | https://trezor.io/support/a/responsible-disclosure |

---

## 4. Alternative Web3-Native Platforms (Beyond Immunefi)

When hunting outside Immunefi and conventional Web2 crowdsourced platforms:

1. **Hats Finance (`https://hats.finance/`)**
   - **Model**: On-chain decentralized bug bounty protocol.
   - **Advantage**: Reward vaults are locked on-chain in smart contracts. Triage disputes are judged transparently with programmatic payout execution.

2. **Cantina (`https://cantina.xyz/competitions`)**
   - **Model**: Elite competitions and private bug bounties for top-tier EVM and Solana protocols.
   - **Advantage**: Direct access to high-profile Web3 audit contests and continuous coverage bounties.

3. **Sherlock (`https://sherlock.xyz/audits/contests`)**
   - **Model**: Time-boxed audit contests backed by capital coverage policies.
   - **Advantage**: Transparent escalation process and guaranteed payout pools.

4. **Code4rena (`https://code4rena.com/contests`)**
   - **Model**: Competitive audits and bug hunting for upcoming and deployed smart contracts.
   - **Advantage**: High frequency of weekly contests with public consensus judging.

5. **BugRap (`https://bugrap.io/bounties`)**
   - **Model**: Dedicated Web3 bug bounty platform focused on APAC and global protocols.

6. **CodeHawks (`https://codehawks.cyfrin.io/contests`)**
   - **Model**: Cyfrin's competitive audit and bounty platform focusing on Solidity and Rust codebases.

7. **HackenProof (`https://hackenproof.com/programs`)**
   - **Model**: Hybrid Web3 and crypto-focused bug bounty platform covering centralized exchanges, DeFi protocols, and Web3 apps.

---

> **Digabung dari `references/web3-independent-bounty-recon.md` (2026-11-25) — konten dipertahankan utuh.**

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
