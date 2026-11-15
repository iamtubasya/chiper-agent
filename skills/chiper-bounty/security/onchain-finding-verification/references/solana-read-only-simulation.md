# Solana read-only execution — prove what the PROGRAM enforces, not what state says

An account-state read tells you what was *recorded*. Only execution tells you what will be
*rejected*. On Solana the zero-cost execution is `simulateTransaction` with `sigVerify:false`:
the program runs for real, you get its Anchor error code and its own `Program log:` lines, no
signature is required and no state changes. Use it for any hypothesis of the form "the program
rejects X after time T / for caller Y / without proof Z".

Companion builder: `scripts/simulate_solana_ix.py` (JSON ix spec → legacy wire format → simulate).

---

## The five-step loop

1. **Re-implement the client's own account parser** out of its JS bundle (minified parsers for
   Anchor structs live in the front end — grep for the field names, e.g. `startTs`, `maxTotalClaim`,
   `clawedBack`). Do not guess offsets from the IDL.
2. **Validate the parse against a field you already know before you read any timestamp.**
   Assert the discriminator bytes (`sha256("account:Name")[:8]`) match and that the `mint` field
   equals the token mint you expect. Only after that round-trip do the numeric fields mean
   anything.
3. **Rebuild the instruction** exactly as the client does: 8-byte instruction discriminator from
   the bundle, then fields in bundle order, `u64`/`i64` LE, and **`u32` LE for Anchor `Vec`
   lengths** (NOT shortvec — shortvec is only for message-level counts).
4. **Simulate** with `sigVerify:false` + `replaceRecentBlockhash:true`, `encoding:"base64"`.
5. **Read the `Program log:` lines as the primary artefact** and either state or drop the
   hypothesis.

## Wire format (legacy transaction) — the parts that are easy to get wrong

```
sig_block : u8 count (shortvec) + 64 zero bytes          # count = numRequiredSignatures
message   : header(3 u8: req_sigs, ro_signed, ro_unsigned)
            + shortvec(nkeys) + 32*nkeys
            + recent_blockhash(32)
            + shortvec(nix) + [ program_idx(u8) + shortvec(naccts) + acct_idx…
                                + shortvec(ndata) + data ]…
```

Account key order is fixed by the runtime: writable signers → writable non-signers → readonly
signers → readonly non-signers. Programs, token program, system program and the ATA program all
belong in the readonly non-signer tail; forgetting one produces an unexplained failure at
indexing time.

## Failure modes seen in the field (0.xyz / DFX distributor, 2026-10)

| Symptom | Real cause | Fix |
|---|---|---|
| `InstructionDidNotDeserialize (102 / 0x66)` right after `Instruction: <Name> invoke [1]` | instruction-data `Vec` length written as shortvec instead of u32 LE | `len(nodes).to_bytes(4,"little")` |
| `AccountNotInitialized (3012)` naming account `to` | account-creating instruction (ATA `CreateIdempotent`, opcode `0x01`) placed AFTER the instruction that reads it | put ATA-create first, claim second; mirror the client's own order |
| every path returns `429` from the public RPC | `api.mainnet-beta.solana.com` throttling after ~5 calls | pace 3–5 s between calls; a provider-specific pool (e.g. the app's own `rpcUrl` from its bundle) often 403s direct use — fall back to the public endpoint |
| `308 Location: <same path minus slash>` for `/.git/logs/` etc. | Next.js trailing-slash normalisation, not a live file | treat as a path-oracle artefact; the follow-up request is the real answer |
| hypothesis "window closed, users locked out" | the timestamps were **vesting/lockup** fields; `end` had already passed, and the program logged them as a lockup | simulation success log settles it — report the negative |

## Worked case (abridged)

Claim flow on `dfx-claim.0.xyz`, program `mERKcfx…`, distributor `5ppcq1…`:

- Client parser read `startTs=1791822372`, `endTs=1791822672` → exactly **300 s**, already in the
  past, while `maxNumNodes` = 138,123 and `numNodesClaimed` = 2. That looks like a Critical:
  "claim window shut after 5 minutes".
- Offset validation first: discriminator matched, `mint` == the DFX mint, `clawbackStart` == the
  2027-10-12 date the FAQ quotes. Parse trusted.
- Then simulate the claim for an **eligible, unclaimed** wallet (its Merkle proof came from the
  site's own unauthenticated `/api/proof/{wallet}`; its `ClaimStatus` PDA did not exist yet).
- Result: `ERR: None`, and the program's own log said
  `Created new claim with locked 0 and 2985147 unlocked with lockup start:1791822372 end:1791822672`.
- Verdict: **hypothesis disproved** — those fields are a lockup schedule, not a claim window.
  The bug does not exist. This negative went in the report with the same prominence as a finding.

## What a successful simulation does and does not prove

- Proves: discriminator, account list/order, data layout, and that the program's business gates
  (time, proof, ownership of the target account) accept the call.
- Does **not** prove: that the call can be landed. The missing signature is the real gate — for
  a claim instruction the claimant is `isSigner:true` and the destination is the claimant's own
  ATA, so a public Merkle proof is not a bearer credential. Say both halves explicitly; "the
  program accepted it in simulation" without the signature caveat reads as an exploit.

## Safety

Simulation moves nothing. Never substitute `sendTransaction` to "confirm" — a submitted claim
writes a `ClaimStatus` PDA for a real wallet. Keep every probe read-only, and stop at the first
contradiction (§2 of the SKILL.md).
