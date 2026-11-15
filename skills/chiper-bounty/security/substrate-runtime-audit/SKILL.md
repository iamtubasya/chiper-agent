---
name: substrate-runtime-audit
description: "Audit Substrate/FRAME runtimes and pallets white-box: weight, storage, reachability."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [security, substrate, frame, rust, pallet, weight, polkadot, bug-bounty, web3]
    related_skills: [web3-audit, probe-validation, lead-to-critical, rust-substrate-zk-toolchain]
---

# Substrate / FRAME Runtime Audit

White-box audit of a **live** Substrate chain: clone the runtime, read the pallets that
move funds, prove a finding with a mock-runtime test, and gate it against the deployed
`spec_version` before writing a word of report.

Companion skills: `rust-substrate-zk-toolchain` owns the *tool map* (Kani/Miri/cargo-fuzz
/CodeQL install state). `web3-audit` owns contract-level classes. This skill owns the
**pallet/runtime method** those two do not cover.

## When to Use

- A bounty target ships a chain ("DeeperChain", "our native blockchain built on Substrate").
- You have a Rust repo with `pallets/`, `runtime/`, `Cargo.toml`, `rust-toolchain`.
- The web surface is gated behind an account you cannot create, but the chain is
  source-available — **that is the payable surface you can actually reach.**
- You found an `unwrap()` / unbounded `iter()` / unchecked arithmetic and need to know
  whether it is a finding or noise.

## Doctrine: exhausted ≠ listed

An operator caught this the hard way: *"kamu, dgn berbagai update, sebanyak itu skill n
tools, cepat sekali menyerah nya"* — the run had written "nothing payable" while its own
artefact still listed untested surface (13 paths, 392 service×method combinations, an
entire `/documents/` endpoint family).

**Rule: you may not write "no findings" while your own notes contain a "BELUM diuji" item
you could still run.** Either run it, or name the hard gate (no account, out of scope,
needs a device) that makes it unreachable. Every COVERAGE section must distinguish:

| state | meaning |
|---|---|
| `diuji` | actually executed, artefact on disk |
| `BELUM — hard gate` | unreachable for a named structural reason (KYC, hardware signature, OOS) |
| `BELUM` | **does not belong in a closing statement** — go run it |

When a reviewer can point at a line in your own notes you did not execute, the report
loses its authority regardless of how many tools ran.

## Step 1 — Recon the repo before reading code

```bash
ls pallets/ runtime/ primitives/
for d in pallets/*/; do
  n=$(find "$d" -name '*.rs' | wc -l)
  l=$(find "$d" -name '*.rs' -exec cat {} \; | wc -l)
  echo "$(basename $d): $n files, $l lines"
done
```

Rank by LOC and by whether the pallet touches money. Deeper Chain, for example:
`staking` 10,811 · `credit` 4,364 · `elections-phragmen` 4,564 · `deeper-node` 1,947 ·
`micropayment` 1,690 · `adsc` 1,520 · `operation` 1,439. Read `staking` and `credit` first.

Then list the attack surface properly — **extrinsics**, not functions:

```python
re.findall(r"#\[pallet::call_index\((\d+)\)\][\s\S]{0,260}?pub fn (\w+)\(", src)
```

39 in `staking`, 21 in `credit` on that target. For each, the first question is the origin
check: `ensure_signed` (anyone) vs `ensure_root`/privilege-gated.

## Step 2 — The seven classes, in the order they pay

1. **Weight mis-declaration** — O(N) iteration charged a constant. Highest-yield on
   FRAME; full method in `references/substrate-pallet-weight-audit.md`.
2. **Panic DoS** — `unwrap()`/`expect()`/`[i]`/`len()-1` reachable from an extrinsic.
   *Prove reachability before reporting*: most are preceded by `ensure!(is_some())`,
   an early `return`, or an `is_empty()` guard. Nine candidates died on this check in one
   session — see the reject table below.
3. **Unchecked arithmetic on `Balance`** — in Substrate a plain `+`/`-` **panics** on
   overflow/underflow (unlike Solidity wrap), so the impact is DoS, not inflation.
   Look for a missing `saturating_`/`checked_` where a sibling has it.
4. **Bad origin checks** — an admin-gated function whose sibling is not. Same "read all
   siblings" rule as `web3-audit`.
5. **Unbounded storage growth** — user-writable `StorageMap` with no cap. This is the
   *precondition* for class 1, not a separate finding.
6. **Non-atomic money path** — transfer + credit update + fallible call, with no
   `#[transactional]` on that extrinsic while a sibling has it.
7. **Signature/replay in the signed-call layer** — `sr25519_verify` over a message built
   from global `StorageValue`s rather than per-device keys.

## Step 3 — The reject table (what almost always dies, and on what)

Record the kill fact, not just "not a finding". These were all checked on Deeper Chain:

| suspicion | killed because |
|---|---|
| `len() - 1` / `[i-1]` underflow | guarded by `if !is_empty()` / `if i == 0 { continue }` |
| `a + b` on Balance | capped by a `Max…` constant (`MaxBurnCreditPerAddress = 50`) |
| `-= amount` in a claim path | guarded by `if balance < amount { …; Err }` above it |
| `rate.unwrap() * reward` overflow | `rate` is `Perbill`, bounded at 12 % |
| `credit_score.unwrap()` panic | preceded by `ensure!(credit_score.is_some())` |
| `x / adsc_rate` div-by-zero | setter is privilege-gated; genesis value is `(2,1)` |
| `mint_into(to, amount)` arbitrary mint | `ensure!(has_privilege(CreditAdmin))` |
| bridge transfer | `ensure!(has_privilege(BridgeAdmin))` |
| faucet `deposit_creating` | `ensure!(is_payment_address(setter))` |

Two transfers of the same pattern: one gated, one not — **that** is the finding. Nine
gated ones are not.

## Step 4 — Prove with a mock-runtime test, measure don't assert

Never ship a pallet finding on a code read. Build the test:

```bash
rustup toolchain install <channel-from-rust-toolchain> --profile minimal --component rust-src
cargo fetch                       # polkadot-sdk is a git dep; first fetch is many minutes
cargo test --offline <prefix> -- --nocapture --test-threads=1
```

- Run `cargo fetch` and the first build **in the background** (`background=true`,
  `notify=true`). A Substrate test build is 300+ crates; a foreground call times out and
  the empty `target/` then reads as a code failure.
- Print numbers (`per-entry`, `elapsed`, `declared vs real reads`) — a curve at 6 sizes
  beats one assertion.
- Full worked PoC + all five harness traps: `references/substrate-pallet-weight-audit.md`.

## Step 5 — Gate: audited commit == deployed runtime

The class is worthless against a stale clone. This is the Substrate form of
`web3-audit`'s "source ≠ deployed bytecode".

```bash
git fetch --depth 1 origin master && git log -1 --format='%H %ad' FETCH_HEAD
```

```python
# substrate answers HTTP 405 to plain JSON-RPC — websocket is mandatory
async def spec(url):
    async with websockets.connect(url, open_timeout=30) as ws:
        await ws.send(json.dumps({"id":1,"jsonrpc":"2.0",
                                  "method":"state_getRuntimeVersion","params":[]}))
        return json.loads(await ws.recv())["result"]
```

Compare `specVersion` with `spec_version` in `runtime/src/lib.rs`. Equal → the finding is
against live code. Different → re-clone at the deployed version first.

**No published RPC?** Docs and `security.txt` rarely list one. The block explorer's JS
bundle carries the endpoint it dials itself. This is automated:

```bash
python scripts/spec_version_gate.py --explorer https://explorer.example.io --compare 76
# scrape candidates from the explorer bundle, connect over ws, print specName/specVersion,
# exit 0 on match / 1 on mismatch / 2 if unreachable
python scripts/spec_version_gate.py --rpc wss://mainnet.example.network --repo ./repo
```

Manual fallback for the scrape step: read the explorer's `main.<hash>.js` with
`search_files` for `wss?://` patterns, then keep only endpoints containing `rpc`, `chain`,
`node` or `api`.

## Step 6 — Severity is decided by reachability, not by the gap

A constant weight for O(N) work is real, but the tier depends on who can drive it:

1. **Trigger authority** — does the path need a device signature, a privileged origin, or
   nothing? Deeper Chain's `staking_delegate` needed an AtomOS signature over a message
   built from a **global** `StorageValue`, so an internet attacker could not submit it.
2. **Repeatability** — a level/era gate (`CreditLevel = Zero..Eight`) can cap an account
   to 8 triggers, removing any spam loop.
3. **Is the cost already paid elsewhere** — if `elect()` walks the same set each era, a
   large set is not entirely new.

Authenticated trigger → **Medium**. Unauthenticated/self-service → High/Critical.
Writing "remote chain halt" for the former is the overclaim that gets the report closed.

## Reporting shape that survives triage

```
1. Summary            one sentence: declared X, actually does Y
2. The code           exact file + line, quoted
3. Author's own contrast   the sibling that DOES cap/guard it  <- strongest section
4. PoC                the test, its raw output, the measured curve
5. Impact             arithmetic from the runtime's own constants
6. Honest limits      the three reachability checks above
7. Reproduction       commit hash, toolchain, exact commands
8. Appendix           your own harness traps, so a reviewer can re-run
```

Section 3 is what makes the finding hard to dismiss: it proves the authors knew the
pattern and missed one site, rather than choosing the behaviour.

## Pitfalls

- **`re.split(r"#\[cfg\(test\)\]", src)` truncates a pallet at its header.** FRAME declares
  `#[cfg(test)] mod mock;` at the top, so this returned 903 bytes for a 138 KB file — and
  every later grep read as a clean negative. Use the LAST occurrence or don't split; assert
  `len(body) > 0.5 * os.path.getsize(path)`.
- **MSYS `grep` with `::<T>::` patterns silently matches nothing.** A `grep -rn "for .* in
  .*::<.*>::iter"` returned 0 and read as "no unbounded loops". Use Python `re`.
- **CRLF checkouts break `include_str!` comparisons** — `.replace('\r', "")` first.
- **`ExtBuilder` vs `new_test_ext()`** differ per crate; read `tests.rs` imports before
  writing a test in a new pallet.
- **`cargo test` accepts one name filter** — `cargo test a b` errors; use a shared prefix.
- **A stale clone is not a finding.** Step 5 is not optional.

## Related

- `rust-substrate-zk-toolchain` (user-owned) — tool install state, ToB scanner skill set.
  If its 7-pattern list is out of date, `hermes curator adopt rust-substrate-zk-toolchain`
  so it can be maintained.
- `web3-audit` — contract-level classes, harness-fault reflex, economics-before-theft.
- `probe-validation` — measurement artefacts that fabricate a negative; the same
  discipline applied to web probes.
- `lead-to-critical` — severity ceiling scoring once you have a candidate.

## Absorbed playbooks (complete sub-packages under `references/`)
- `references/substrate-pallet-audit/PLAYBOOK.md` — the pallet-level drill-down: weight
  mis-declaration (cheapest to prove), missing `#[transactional]` on a sibling, unbounded storage
  growth, severity bounding in three reads, and a build-and-PoC recipe
  (`references/substrate-pallet-build-and-poc.md`). Use it once Step 2 names the suspect pallet.
