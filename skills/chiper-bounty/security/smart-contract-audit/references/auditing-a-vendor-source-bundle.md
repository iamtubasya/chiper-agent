# Auditing a vendor source bundle (you were handed the code, not a repo)

Practical setup for the case where scope is "the deployed contracts and their source in
`contracts/`" and the code arrives as a ZIP or a `/source/` page rather than a cloneable repo.
Learned building an audit workspace for a deployed DEX + prize-game on Arbitrum Sepolia.

## 1. Get the code, and note which build you got

- Prefer the bulk index / archive the project itself serves (`/source/`, a `*-source.zip`, a
  `contentIndex.json`) over crawling their HTML — it is one fetch and it is the exact artifact they
  publish.
- Grep the source for its own commit marker (e.g. a served bundle states a commit hash). Record it.
- **The bundle may not match what is deployed.** Do not assume. Verify with
  `scripts/deployed_vs_source_selector_diff.py` before you report anything; several contracts in one
  engagement were pre-fix builds while others matched the source exactly.
- If the project's public repo is unreachable (404 / suspended), say so in the write-up and audit the
  served bundle — that bundle is what the deployment was built from. Try the obvious mirrors
  (jsdelivr, statically, raw.githack, codeload tarball, Wayback) once each, record the status codes as
  evidence, and move on rather than re-trying.

## 2. Stand up a Foundry project around it

```
<audit-dir>/
  foundry.toml
  contracts/            <- the bundle's contracts, verbatim
  test/                 <- your PoCs
  lib/                  <- forge-std + the OpenZeppelin version it expects
  evidence/             <- captured forge/cast output
```

`foundry.toml` that works for a bundle like this:

```toml
[profile.default]
src = "contracts"
test = "test"
out = "out"
libs = ["lib"]
solc = "0.8.24"
optimizer = true
optimizer_runs = 200
via_ir = true
fs_permissions = [{ access = "read", path = "./" }]

remappings = [
  "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/",
  "forge-std/=lib/forge-std/src/",
]
```

Dependencies:

```bash
git init -q .
forge install foundry-rs/forge-std
forge install OpenZeppelin/openzeppelin-contracts
```

### Pitfalls that cost a cycle each

- **`remappings` is a single key.** Appending a second `remappings = [...]` block to an existing
  `foundry.toml` fails with `TOML parse error ... duplicate key`. Rewrite the whole `[profile.default]`
  block instead of appending.
- **A bundle often will not compile without `via_ir`.** "Stack too deep" on one large contract is the
  usual symptom. Enabling `via_ir` fixes it, but compilation then takes minutes — see the batching rule
  below. If a single out-of-scope file is the only blocker, exclude it rather than abandoning the build.
- **`via_ir` makes every change expensive (~minutes).** Batch your test edits: write all PoCs, then
  compile once. Do not iterate one assertion at a time unless you have time to burn.
- **Slither is impractical under `via_ir` on some setups.** If it will not run, do not record that as
  a tool limitation — manual review plus live-state reads plus a runnable PoC covered the ground here.
  Re-test slither if the target stops needing `via_ir`.

## 3. Write PoCs that a triager can re-run

- **Prefer a self-contained test over a fork when the claim is about code.** With local mocks for a
  token/factory/pair you get zero RPC dependence and full control of the numbers, and the test doubles
  as the reproduction recipe.
- **In a staking/farm PoC, approve the STAKED token, not the reward token.** `deposit(pid, amt)` pulls
  the pool's LP token; approving the farm's reward token instead fails with
  `ERC20InsufficientAllowance(spender=farm, allowance=0, needed=amt)`. You usually need both approvals
  (LP for `deposit`, reward token for `notifyRewardAmount`).
- **Funding by direct `transfer` does not move accounting variables.** `notifyRewardAmount` pulls the
  tokens itself and is what updates the contract's reserve counter; a plain `transfer` inflates the
  balance only and makes your logged numbers confusing. Fund the way the keeper does.
- Capture output verbatim into `evidence/*.txt` (`forge test ... -vv > evidence/x.txt`) and embed it in
  the report — a screenshot of the same text plus the raw text is the strongest pairing.

## 4. Reading live state as evidence

- Declare every live address once (a shell associative array or a JSON map) and loop over
  `name|getter-signature` rows so one command produces the whole wiring/state table.
- A getter that reverts is information, not noise — see the wiring-first and selector-diff sections in
  SKILL.md.
- **Check the base invariant numerically, not just by eye.** For a prize/escrow system, assert
  `escrow_balance == live_pot + unclaimed_pool + accrued_protocol_cut` from live reads; when it holds
  exactly, you can say so in the report and it is worth as much as a finding (it pre-empts "did you
  even check the accounting?").
