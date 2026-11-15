---
name: perp-dex-protocol-audit
description: "Audit live perp-DEX / exchange APIs via real positions."
version: 1.0.0
author: "[K]vk (curator)"
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, perp-dex, exchange-api, eip712, liquidation, margin, trading-protocol, testnet]
    platforms: [linux, macos, windows]
---

# Perp-DEX / Trading-Protocol API Audit

Audit a **live trading protocol** through its own read/write API — not its bytecode, not its web UI.
You open real positions with programmatic keys, control the account's risk precisely, and watch how
the matching engine, margin engine, and liquidation engine actually behave.

The deliverable is never "the docs say X" — it is **observed engine behaviour**, captured live.

## When to Use

Load when the target is any of:

- a **perpetuals DEX / exchange / trading platform** exposing a documented REST exchange API
  (`/info` reads + signed `/exchange` writes), whether testnet or mainnet;
- a trading venue where you can create keys and fund a test account from a faucet;
- a bounty/VDP target whose program covers trading-engine behaviour — **including testnet-only
  features** when the program says so.

Also load for **mainnet-only** targets to drive the read + economics path (price-feed sourcing,
margin arithmetic, settlement bias) without live writes; see also `cex-event-contract-audit` for
binary-option / prediction-market settlement analysis, which this skill complements.
Do **not** use for auditing on-chain contract bytecode — that is `smart-contract-audit`.

---

## ⛔ The four rules that make this class work

1. **Signing must be proven against the vendor's published test vectors BEFORE the first live call.**
   Reproduce `signingHash`, `r`, `s`, `v` byte-for-byte. If they match, every later anomaly is the
   engine's, not yours. Skip this and you will burn hours chasing your own serialisation bug.
2. **The submit response is not the truth.** An order action can return `{"status":"ok"}` while the
   engine silently cancelled or partially filled it. **Always reconcile against the ledger**
   (`historicalOrders`, `userFills`). This single discipline is how the real finding in this class
   gets found.
3. **Control equity precisely — that is your lever.** Transfers in/out move the account's margin
   ratio at will, which lets you drive a position *to* a boundary instead of hoping the market does.
4. **Map the price limits before designing any manipulation test.** The buy cap and sell floor are
   asymmetric and usually oracle-anchored; a whole class of "push the price" ideas is impossible by
   construction (see Pitfalls).

---

## Phase 0 — Recon (mostly free, do it all first)

**The fastest path to the entire API spec is the vendor's own LLM docs file.**
Marketing docs sites ship `llms.txt` / `llms-full.txt`. Fetch them:

```bash
curl -sSL https://docs.<target>/llms-full.txt -o llms-full.txt   # often the WHOLE spec
curl -sSL https://docs.<target>/llms.txt
```

If that 404s, the search index of a Vocs/Mintlify docs site contains the **fully rendered** page text,
including fields that a React component (`<ExchangeBody id="order" .../>`) would have rendered into
the page *client-side* and which therefore never appear in the raw HTML:

```bash
# find the asset, then parse storedFields -> {html, text, title, href}
curl -sS https://docs.<target>/.vocs/search-index-<hash>.json -o si.json
python - <<'PY'
import json,re,html
d=json.load(open('si.json',encoding='utf-8'))
for k,v in d['storedFields'].items():
    s=json.dumps(v)
    if 'reduceOnly' in s or '<field-of-interest>' in s:
        t=re.sub(r'(?s)<[^>]+>',' ',v.get('html','')); print(v.get('href'), html.unescape(t)[:2000])
PY
```

**Front-end bundle mining** (config + the real API host):

```bash
curl -sS https://<target>/ -o idx.html
grep -oE 'src="[^"]+\.js[^"]*"' idx.html
for f in <bundles>; do curl -sS https://<target>/assets/$f -o $f; done
grep -oE '"[A-Z_]{3,}:[^"]*"[^"]*' *.js | sort -u | head -60     # VITE_* / config constants
grep -oE 'https?://[a-zA-Z0-9./_-]+' *.js | sort -u              # API hosts, ws hosts
grep -o -E '"(/api/[a-zA-Z0-9/_-]+)"' *.js | sort -u
```

**Read the bug-bounty page early** — it states scope, severity bands, and (critically) *which
environments are testable*. Record it; it decides whether your testnet finding is payable.

---

## Phase 1 — Provision accounts and capital

- Generate **main key + agent key** per account (`eth_account`), `approveAgent` from the main key.
- **Fund first, then approve.** `approveAgent` on an unfunded/hypothetical account returns
  *"Account not found"*. Re-approve if you top up afterwards.
- Faucets are usually **rate-limited per address but generous for fresh addresses** — mint new
  addresses as needed rather than waiting out a cooldown. Check what the claim actually credits
  (testnet books may credit 999 while a docs example says 300).
- Consolidate capital with the protocol's own transfer action (`tokenSend`) — it is a real feature,
  not an abuse, and it is what lets you reach high margin tiers.
- **Hold at least one spare unfunded account.** Cross-margin liquidations wipe the whole account and
  cancel all its cross orders — your test infrastructure will get destroyed mid-experiment.

**Equity is your primary control variable.** You can move an account's balance to *any* value
(transfer out to a throwaway address). That means you can place a position at any margin ratio you
want — this is far more powerful than hoping the market moves.

---

## Phase 2 — Learn the margin/liquidation model from the API itself

```bash
POST /info  {"type":"perpMetaDetail","assetName":"<BASE>"}   # margin tiers: min/max size, lev, mmr
POST /info  {"type":"clearinghouseState","user":"<addr>","accountType":"perp"}
POST /info  {"type":"l2Book","coin":"<instrumentId>"}
POST /info  {"type":"activeAssetCtx","coin":"<instrumentId>"}   # mark, oracle, last
```

Facts you need before testing anything:

- **Tiered margin.** MMR and max leverage depend on position *size*; a bigger position sits in a
  stricter tier. A partial liquidation reduces size to the tier-below cap.
- **Partial liquidation usually only from tier 3 upward**; below that the position closes in full.
  ⇒ A "full close" on a tier-1/2 position is *documented-correct*, not a bug.
- **Mark price** drives liquidation; it is typically an EWMA that drifts toward the book mid —
  movable, but slowly and only as far as the **price limits** allow.
- **Oracle dislocates from the book** on illiquid markets. Measure it:

```
half_spread / mark  vs  (mmr + fee)     # this ratio IS the whole geometry of the test
```

---

## Phase 3 — The core test families

Each of these is a **hypothesis to falsify with live observation**, not a claim to assume.

| Family | Setup | What proves it |
|---|---|---|
| **Partial vs full liquidation** | Engineer a tier-3+ cross position at ratio <1 with equity *just* below the maintenance threshold. | Engine closes **only** to the tier-below cap → finding; full close → documented-correct. |
| **Reduce-only re-cap** | Long size S; fire **two** reduce-only orders of size S concurrently (burst), and a second variant with resting RO orders swept by a counterparty. | Both filling and flipping you net-short → finding. Engine rejecting the second ("will increase your position") → not vulnerable. |
| **Bankruptcy-price staleness** | Force a partial liquidation, then compare pre/post bankruptcy price and the settlement fill. | Spec: takeover happens *at* the bankruptcy price, so a stale price is only real if it demonstrably diverges from the computed bankruptcy price. |
| **IOC through a thin book** | Size an IOC to sweep the visible book on the thinnest non-halted market. | Slippage blows equity past the floor without going negative → not vulnerable. |
| **Unclosable / stuck position** ⭐ | Long at high leverage on a market where `oracle ≫ book bid` (often extreme, e.g. +60%). | See below — this is the finding class most likely to be real. |

### ⭐ The highest-yield finding: a position that is neither liquidatable nor closable

When environment price limits clamp order prices to an oracle that is far from the book:

- liquidation price can fall **below** what the engine will accept as a closing order price, and
- liquidation may still fire — but "additional margin" in the formula can keep equity *positive*
  through the entire liquidation sequence, leaving a residual position that

  **cannot be closed (order rejected) and cannot be liquidated (equity positive) → collateral is locked.**

Evidence chain to capture (this is the report):

1. live `l2Book` bid + `activeAssetCtx` oracle/mark, in one snapshot;
2. the *rejected* close attempt, with the engine's own numbers (`Minimum price: … ≥ oracle·floor`);
3. `historicalOrders` showing the engine's real handling: `status: Canceled`,
   `cancelSource: CancelByPriceLimitRule`, `cancelReason: "… price moved beyond slippage protection"`
   — **this is why a `status:"ok"` response is worthless as evidence**;
4. `userFills` proving a forced liquidation reduces but does not fully close;
5. the resulting `clearinghouseState` position, still open, with locked collateral.

---

## Phase 4 — Verification discipline (non-negotiable)

- **Re-read the ledger, not the response.** `historicalOrders` / `userFills` are the ground truth for
  fills, cancels, and liquidation. A submit `ok` means "accepted for processing", nothing more.
- **Never report a negative from a submit response alone.** "Order failed" wording is part of the
  evidence (it shows the engine *did* guard) — quote it verbatim.
- **A null field is not "not vulnerable".** `liquidationPx: null` on a cross position just means the
  engine isn't publishing it; cross-mode liq depends on whole-account equity.
- **A monitor sample with the WHOLE summary missing is a transient read failure, not a state change.**
  The read API intermittently returns a body with no `marginSummary` / no `assetPositions` while the
  position is still open. Hit live: a sampling run whose last row was `eq=None MM=None ratio=None
  pos=[]` got recorded as "FLAT — full liquidation" — false; the account was still open minutes later.
  Before any read becomes evidence, **re-read it**: if the *whole* summary is absent (not just
  `liquidationPx`), retry until the fields populate, and only trust an empty `assetPositions` that you
  confirmed on two consecutive fresh reads. A false "flat" manufactures a liquidation result that
  never happened and it will silently flip a non-event into a "finding".
- **Tier math is ordinary arithmetic — do it before the run — and your debt is the live value.** The
  window in which a position sits between "below maintenance" and "unrecoverable" is often only wide
  enough under specific `leverage / mmr / half-spread` combinations. Silence is usually *your* numbers,
  not the engine.
  - **Never assume the MMR/fee.** The `perpMeta` summary often lists only tier 1; the per-tier
    `mmr` lives in `perpMetaDetail` → `instruments[0].marginTable.tiers`, and `takerFeeRate` sits
    alongside it. Hit live: every run used an assumed `mmr+fee ≈ 0.0156` while the real tier-2 LDO
    value was `0.0106`. Equity was over-set on every attempt, so the ratio never approached 1.0, the
    engine never had a reason to act, and five "we tried liquidation" runs proved nothing.
  - **Compute the target equity from the position's actual tier**, then verify by reading back the
    live `marginRatio` (the API returns it per position). If `ratio` is far from your target instead
    of near 1.0, stop — the arithmetic is wrong, not the engine.
  - **Once the engine has acted, stop removing equity.** Removing more margin after the first
    reduction can force the *next* tier's liquidation and destroy the evidence you just captured.
- **Repeat an unstable candidate.** A candidate that does not reproduce is not a finding.
- **Every negative must also survive the 3× re-verify — not just the positive.** The expensive failure
  mode in this class is a negative produced from a *contaminated* run: wrong margin constant, a
  transient null read, or leftover state carried over from an earlier probe. Hit live: "the engine
  always full-closes" was reported to the operator from the submit response while the monitor was
  dropping whole samples; the accounts were still open afterwards, and the claim had to be formally
  withdrawn. **Before stating any verdict (negative included), re-read the live state and state your
  coverage in one line** — what was run, against which instrument/tier, and which numbers you used.
- **Reducing a tier-N position to the tier-(N-1)-below cap is documented-correct, not the L1 finding.**
  See it as *protective*: if the requested size would not fit the available margin the engine may trim
  the position down to what does, leaving the ratio ≥ 1.0. Observed live: an IOC buy for `N=99000`
  opened a position of `21806` and the `historicalOrders` record showed the residual as
  `Canceled — remaining size … beyond slippage protection`; the account was left *open at 21806*, not
  liquidated. That is the engine refusing an unaffordable order and keeping the account solvent. The
  real finding requires the *opposite* shape: a tier-3+ position that is demonstrably below
  maintenance and is closed in **full** when a *partial* reduction would have sufficed.

---

## Pitfalls (all hit for real)

- **Price limits are asymmetric and oracle-anchored.** Typical observed shape: buy accepted up to
  ~`1.05 × oracle`, sell only from ~`0.846 × oracle`. Corollaries that kill naive tests:
  - You **cannot** push price up beyond the oracle — so "mark manipulation to force liquidation"
    is impossible whenever the oracle sits *above* the book (dislocated markets).
  - You **cannot** sell below the sell floor — so on a market where `book bid < 0.846 × oracle`,
    closing a long is *impossible*. That is the stuck-position finding, and it will also sabotage
    your own cleanup.
  - `Market` order type is **not** exempt: it is subject to the same limits and is silently
    `Canceled` beyond them.
- **Do not assume `5 × oracle` or any "generous" bound** — probe and read the actual
  `Minimum price: …; Maximum price: …` string; parse it back into your tests.
- **Tick-size precision.** Format prices by rounding to the instrument's `priceTick`, not with a
  float formatter. `f"{px:.10g}"` produces strings the engine rejects with
  *"Price precision does not match the tick size"*.
- **Position-size caps count the current position.** A leftover dust position makes a new order fail
  with *"Maximum position size at Nx leverage is X"* even when the new order is smaller than the cap.
- **Dust positions below the sell floor cannot be closed by market order and cannot be closed by
  limit order.** Clear them with a counterparty: rest a reduce-only sell at the floor, have a second
  wallet sweep it. If even that fails, drain the account's equity until the engine liquidates it.
- **Size floors matter.** A "flatten everything" helper must respect min order size or it loops
  forever on a rejected micro-order.
- **In cross margin, one liquidation takes the account and all its cross orders with it.** Run risky
  tests on a dedicated account; expect collateral damage elsewhere.
- **Halted instruments** (`haltTrading`) still appear in metadata and books — filter them out.

---

## Tooling shape

Keep the client as a small importable module so runs are reproducible:

- `client.py` — domain constants, canonical MessagePack encoder, EIP-712 signer, `info()`/`exchange()`.
- `actions.py` — per-action builders (`order`, `cancelByCloid`, `updateLeverage`, `updateMarginMode`,
  `updateIsolatedMargin`, `tokenSend`, …).
- `ops.py` — `cleanup()`, `add_equity()`, `remove_equity()`, `rpx(px,tick)`.
- `monitor.py` — thread sampling `clearinghouseState` + `l2Book` + `activeCtx` to JSONL at 0.06–0.4 s
  so a sub-second liquidation leaves a time series, not a single observation.

A ready signing harness is in `scripts/eip712_msgpack_client.py`.

---

## Reporting hooks

- **State a verdict per lead: FINDING or NOT-A-FINDING.** Ambiguous half-states ("belum", "probably",
  "not proven yet") read as hedging and the operator will push back. If a lead is exhausted, say
  **not a finding** and name the evidence. If it genuinely is pending, say *why* it is pending and
  what single run would close it — never leave a lead sitting in limbo across replies.
- **If a previously-stated verdict turns out to be wrong, retract it explicitly and immediately** —
  name the claim, name the cause (e.g. "transient read failure, not a liquidation"), and show the
  corrected state. Do not quietly drop it or bury the correction in a later table. Observed live: a
  "the engine always full-closes" claim had to be publicly withdrawn in this exact class.
- One finding = one draft + one PDF PoC; demonstrated impact only (see `bug-report-delivery`).
- **Testnet-only findings are payable when the program scopes the testnet** — check the bounty page
  and quote it. Severity may be lower than the equivalent mainnet finding.
- The strongest framing for the stuck-position class is economic, not "an order failed":
  *collateral becomes irrecoverable*. Compute the actual locked notional from the live state.
- Include the raw ledger rows (`cancelSource`, `cancelReason`) as the PoC — they prove the engine's
  behaviour, which is the whole point.

## References

- `references/txflow-testnet-case.md` — full worked case: endpoints, signing test vectors, the four
  leads tested with their verdicts, and the stuck-position finding.
- `scripts/eip712_msgpack_client.py` — validated EIP-712 + MessagePack signing/transport harness.
