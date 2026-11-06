# Scraping Cantina Bounty Pages (cantina.xyz/bounties/<uuid>)

Session-proven recipe (Paxos bounty, 2026-09). Use when a bug-bounty target hosts its program on Cantina and you need scope/rewards/assets without the browser stack.

## Why not browser tools
Camofox/browser stack intermittently fails on cantina.xyz (`500 Server Error for localhost:9377/tabs`). Plain `curl` works fine — the page is fully server-rendered (Next.js RSC payload), so all bounty data is already in the initial HTML. Default to curl first.

## Fetch
```bash
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  "https://cantina.xyz/bounties/<uuid>" -o ~/cantina_<slug>.html
```

## Data format
Bounty JSON is embedded inside `<script>` RSC chunks with **double-escaped quotes** (`\\"` for `"`, `\\n` for newline). Not `__NEXT_DATA__` — the payload is split across `self.__next_f.push(...)` chunks and raw `\"...\"` fragments.

**One-line unescape** makes it regex-friendly:
```python
clean = html.replace('\\"', '"')
```

## Key fields to extract (all confirmed present)
- `"totalRewardPot":"1000000"`, `"currencyCode":"USDG"`, `"start":"2026-03-27T06:30:00Z"`
- Asset groups: `"name":"<Group>","description":"...","outOfScope":true|false`
- Subgroups (nested under groups, also carry `name/description`): e.g. `Production Web Interfaces`, `Sandbox API Endpoints`, `Production FIX Protocol`
- Assets inside group/subgroup: `"name":"<repo-or-host>","description":"...","reference":"<url-or-endpoint>"` — references may be GitHub URLs, https endpoints, or raw `host:port` strings (e.g. FIX gateways)
- Rewards per group: `"severity":"critical","minReward":null,"maxReward":"1000000.00"` — note `minReward` is often `null`; only trust `maxReward`. `informational` may have `maxReward: null` (= no payout)

## Gotchas
- Simple `re.findall(r'"field":"([^"]+)"', clean)` is enough; avoid complex patterns like `(?:[^"\\]|\\.)*` inline on Windows Python (heredoc/CLI escaping produces `unterminated character set` errors). If the parser grows, write it to a `.py` file with write_file and run it — don't inline it in bash heredocs.
- Windows Python cannot see MSYS `/tmp/...` paths. Save curl output to `~/file.html` and open with `os.path.expanduser("~/file.html")`.
- `grep` on the raw file must match the escaped form (`\\"name\\"`) — easier to just do all extraction in Python after unescaping.
- Descriptions contain `\\n` sequences; replace with newline for readability.
- Sandbox assets are listed alongside prod. Cantina rules: sandbox findings only pay out if reproducible against the production equivalent.

## Verified example: Paxos (live, $1M pot)
- Groups: `Core Smart Contracts` (Crit $1M / High $250K / Med $25K / Low $5K) and `Web Interface / Application / Backend` (Crit $50K / High $15K / Med $5K / Low $1K)
- Contracts: paxos-token-contracts (ERC20+SupplyControl base), pyusd-contract, usdg-contract, usdp-contracts, paxos-gold-contract (legacy, standalone), cross-chain-contracts (LayerZero OFT EVM+Solana), solana-programs (SPL minter controller)
- Web: dashboard/account/pax-admin .paxos.com (+sandbox), api/auth-api/oauth/ws .paxos.com, FIX: `{comp_id}.exchange.gfix.prod.itbitprod.com:4198` (mTLS stunnel)
- Out-of-scope group exists as its own group entry with `outOfScope:true` — filter it.
