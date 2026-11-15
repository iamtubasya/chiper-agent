# Storage-level verification: when an accessor's `0` is not absence

Worked case, 2026-10-27, Tacit `TacVault` + `TacIntervalOracle` (Ethereum mainnet).
A first pass reported "the price oracle has no samples at all". Storage said 128/128 slots
were populated and ~540 intervals stale. The corrected finding was stronger and the
correction had to be stated to the operator and baked into the report.

---

## 1. The failure shape

```bash
cast call $PAIR "latest()(uint256)"                 # -> 0
cast call $PAIR "prices(uint256)" 28800             # -> revert 0xa889a81f (TooFewSamples)
# sweep "the last 140 intervals" from the EXPECTED index
for i in 0..140: cast call $VENUE "sampleOf(uint256)" $((expected - i))   # -> all (0,0)
```

Concluded: ring empty, oracle never recorded. Both statements false.

Two independent bugs in that sweep:

1. **Wrong anchor.** `expected` came from `(block-1-GRACE)/STEP-1`. The newest *recorded* value
   was ~540 intervals below it, so a 140-wide window never touched real data.
2. **Bounded negative read as universal.** "nothing in the last 140" became "nothing exists".

## 2. The method that settles it

### 2a. Read the ring from storage, not through the accessor

Solidity `uint256[RING] internal _samples;` occupies `RING` consecutive slots from its declared
position (slot 0 when it is the first state variable, as in `TacIntervalOracle`). No
`keccak` base — that is only for mappings and dynamic arrays.

```bash
RPC=https://ethereum-rpc.publicnode.com
A=0x...venue
for i in $(seq 0 127); do
  cast rpc eth_getStorageAt $A $(printf '0x%x' $i) latest --rpc-url $RPC
done | tee ring.txt
```

Then decode the packing the contract documents in its own comment:

```
_samples[i] = interval << 208 | ethPerTac << 104 | ethDepth      # MASK = (1<<104)-1
```

```python
MASK = (1 << 104) - 1
rows = [(i, int(h, 16)) for i, h in (l.split() for l in open("ring.txt"))]
populated = [(i, v >> 208, (v >> 104) & MASK, v & MASK) for i, v in rows if v]
print(len(populated), "/", len(rows), "slots populated")
print("newest recorded interval:", max(p[1] for p in populated))
```

### 2b. Compute the age against what the contract would use now

```
expected = (block_number - 1 - GRACE) // STEP - 1          # interval oracle convention
behind   = expected - newest_recorded
age_days = behind * STEP * 12 / 86400                      # 12 s slots
```

Tacit numbers: `STEP 50`, `GRACE 10`, `RING 128`, `MAX_WINDOW 28800`, `MIN_COVERAGE_BPS 6600`
(all read with `cast call`, not from docs).

| venue | slots | newest recorded | expected | behind | age |
|---|---|---|---|---|---|
| TacBlockOracle | 128/128 | 525184 | 525725 | 541 | 3.76 d |
| TacAmmOracle | 128/128 | 524672 | 525725 | 1053 | 7.31 d |

`MAX_WINDOW` is 8 h, so both were dark by 11x and 22x.

### 2c. Confirm with the accessor, at the boundary

```
sampleOf(newest)     -> a real sample   (63200656445905, 3885647450476945288)
sampleOf(newest + 1) -> 0
```

That pair is the sentence a report wants: *the last real sample and the first empty one*. It is
strictly better evidence than any single read, because it localises where recording stopped
rather than only observing that the read fails.

### 2d. Check what the *repairability* bound actually is

`record()` here reverts `BadBlock` for any interval more than `RING` behind the newest, so
intervals older than `RING * STEP * 12` (~21 h) can never be written again while the current
window is fully restorable if a recorder resumes. Say that split explicitly:
"history is permanently lost, the live window is not" — do not claim "permanently broken".

## 3. Provider constraints that shape the script

Measured, same session:

| RPC | `eth_getLogs` range | notes |
|---|---|---|
| `ethereum-rpc.publicnode.com` | wide | 403 for plain `urllib` (UA), fine for `curl` / `cast` |
| `1rpc.io/eth` | 100k, then **50 blocks** after the first refusal of that shape | rate-limit message changes mid-session |
| `eth.drpc.org` | 10k (free) | |
| `eth.llamarpc.com` | 525 | unstable |

Consequences: never build a finding on logs alone, and always state which provider produced a
number. `eth_getStorageAt` and `eth_call` are not range-limited, so the storage route works where
log-scanning does not.

## 4. Deploy block without an explorer

Binary search on `eth_getCode` returns `0x` before deployment:

```bash
lo=25000000; hi=$TIP
while [ $lo -lt $hi ]; do
  mid=$(( (lo+hi)/2 ))
  code=$(cast rpc eth_getCode $ADDR $(printf '0x%x' $mid) --rpc-url $RPC)
  if [ "$code" = "0x" ]; then lo=$((mid+1)); else hi=$mid; fi
done
echo "deploy block = $lo"
```

Beware: if `lo` is already after deployment (address is a CREATE3 predeploy or deployed earlier
than the seeded lower bound), the search converges on `lo` and silently returns your own bound.
Seed the floor below the deployment or sanity-check the first probe.

## 5. Casting this into severity

- Exits reverting for *every* caller (`TooFewSamples` out of a health read) is the defect that
  survives any "the recorder is monitored" reply. Keep it separate from the outage.
- Two thresholds disagreeing inside one contract is a code defect regardless of operations:
  here `depthMin()` demanded 100% window coverage while `prices()` accepted
  `MIN_COVERAGE_BPS = 6600`. One missed interval therefore disabled `borrow()` while pricing
  still worked. That asymmetry is the part worth a report line even if the outage is called ops.
- Quote the at-risk figure you can defend: collateral from `balanceOf(vault)` minus open debt
  from `totalDebt()`, valued at the contract's own `spot()`, not at an exchange price.
