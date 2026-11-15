# Immunefi

> tags: programs

> related: Attack-Surface/Web3, Programs/Platforms/YesWeHack, Programs/Platforms/HackerOne, Programs/Selection/Payout-Analysis, Programs/Selection/Competition-Assessment

Immunefi
Immunefi is where the highest single bounties in the industry live. A valid critical finding on a top-tier Web3 protocol can pay $1M+, and a handful of historical payouts have cleared $10M. The Wormhole bridge exploit disclosure paid $10M. Aurora paid $6M. Those numbers are real. The tradeoff is that you need a skill set most web2 researchers don't have, and the rules of engagement are stricter than anything on H1 or Bugcrowd.

Platform Focus
Immunefi is purpose-built for Web3 security. The scope categories map to the Web3 attack surface:

Smart contracts: The primary category. Solidity on Ethereum and EVM-compatible chains, Rust-based programs on Solana, Move on Aptos and Sui. This is where the largest bounties sit.
Blockchain infrastructure: Node software, consensus mechanisms, mempool handling, network-level vulnerabilities in the chain itself.
Web/app layer: The websites, frontends, and APIs that support a protocol. These are in scope on most Immunefi programs but pay lower than the smart contract category, and more in line with web2 bounty rates.

If you're a web2 researcher without smart contract skills, you can still find value on the web/app scope of Immunefi programs - but you're working the lowest-paying tier of a platform designed for a different skill set. Consider whether your time is better spent on web2-native platforms while you build Web3 skills on the side.
See Web3 for a detailed breakdown of the vulnerability classes relevant to Immunefi targets.

Primacy of Disclosure
Immunefi enforces a first-valid-report rule strictly. The first researcher to submit a valid, in-scope finding on a specific vulnerability wins the bounty. All subsequent duplicate submissions receive nothing.
This changes your incentives compared to H1:

Speed matters more. A report that would sit in draft for three days while you refine the write-up should go in as soon as it's clearly valid.
Quality still matters. A vague report that gets marked invalid while someone else submits a clear one on the same issue loses the race.
The balance: submit when you're confident it's valid and you have a working proof of concept, even if the write-up isn't perfect. You can add detail later.

Duplicate rates on popular protocols are high. The researcher population hunting Immunefi's top programs is skilled and fast. Don't sit on findings.

Rules of Engagement
This is where Immunefi differs most from web2 platforms, and where the consequences of getting it wrong are severe.
No mainnet exploitation. You cannot test by actually executing a transaction that affects mainnet funds or protocol state. Ever. Mainnet exploitation - even with intent to report and return funds - is not authorised testing. It's theft and it will be treated as such.
Use testnets and forked environments. Demonstrate your finding on a testnet deployment of the protocol, or fork the mainnet state locally and reproduce the vulnerability in the fork. Most mature protocols have testnet deployments specifically for this purpose. If they don't, a local fork is the standard approach.
Proof of concept on a local node. Your PoC should be runnable on a local environment without touching live funds. This is the expected format for a valid submission.
No accessing user data beyond proof. Same principle as web2: demonstrate the vulnerability exists, don't exfiltrate, don't expand access beyond what's needed to prove the finding.

Severity Classification
Immunefi doesn't use CVSS. Their severity system is based on a matrix combining the asset type and the impact:

Critical: Direct theft of funds, permanent freezing of funds, or breaking core protocol invariants. These are the high-value bounties.
High: Temporary freezing, griefing attacks, significant disruption to protocol function.
Medium: Partial protocol disruption, reversible issues, indirect financial impact.
Low/Informational: Minor issues that don't affect funds or core function.

The asset type matters too. A critical vulnerability in a smart contract handling $500M in TVL is assessed differently from the same class of vulnerability in a frontend. Programs specify their bounty caps per category. Read the program's specific bounty table because caps vary widely.

Protocol Teams as Reviewers
On web2 platforms, you submit to a triage team that then escalates to the company. Immunefi works differently: your report goes directly to the protocol's own security team or development team. There's no Immunefi triage middleman in the same way.
What this means in practice:

Review quality depends entirely on the protocol team's security competence
Decisions can be faster when the team is engaged and technically strong
Disputes are harder to resolve when the team is the decision-maker and also the organisation being reported on
Immunefi has a mediation process for disputes, but it's slower and less predictable than web2 escalation paths

Well-run protocol programs - typically those with dedicated security engineers rather than developers handling reports as a side task - give a reasonable experience. Programs where the dev team triages reports alongside building features can be slow and inconsistent.

Payout Currency
Immunefi programs pay in one of two forms:
Protocol token: The project pays in their own native token. For large, liquid tokens (ETH, SOL, BTC-backed assets) this is close to equivalent to fiat. For smaller or newer protocol tokens, you're taking price volatility risk. A $500K bounty paid in a token that drops 60% before you can convert it is not a $500K payout.
Stablecoin: Programs that pay in USDC or USDT denominate in USD effectively. This is the cleaner option where it's available.
Check which payout currency a program uses before prioritising it. Some programs specify stablecoin payment for critical findings only. Tax treatment of crypto payouts varies by jurisdiction - get advice specific to your location. In most jurisdictions, bounty payouts are taxable income regardless of the currency they're paid in.

Getting Started on Immunefi
Immunefi requires no formal vetting to register and view program scopes. You can browse all programs without an account. The barrier isn't platform access - it's the skill set.
If you're new to Web3 security, the realistic path is:

Learn Solidity to a level where you can read and reason about contract code
Understand the common vulnerability classes: reentrancy, integer overflow/underflow, access control flaws, price oracle manipulation, flash loan attack vectors
Practice on intentionally vulnerable contracts (Damn Vulnerable DeFi, Ethernaut) before hunting live programs
Start with the web/app scope of Immunefi programs while building smart contract skills - it builds familiarity with protocol architecture without requiring full smart contract expertise immediately

The researchers earning the large payouts have deep protocol-level knowledge. That knowledge takes time to build. Don't expect to cross over from web2 and immediately compete on top-tier smart contract programs.

Related

YesWeHack
HackerOne
Payout Analysis
Competition Assessment
