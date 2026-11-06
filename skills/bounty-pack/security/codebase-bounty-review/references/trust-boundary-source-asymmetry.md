# Trust-boundary source asymmetry (same datum, two sources, opposite trust)

A white-box review pattern that pays on **any client that aggregates the same fact from more than
one source**. It is cheap to look for and it produces attribution/identity findings the memory-safety
and differential passes both miss.

## The shape

```
source A (authenticated / derived)   -> port correctly refuses it, or derives the datum itself
source B (a third party's claim)     -> port writes it into the authoritative field
```

Both sources are third-party *about the asset*, and yet one is distrusted and the other is laundered
into the "proven" slot. The asymmetry is the finding.

## Worked case (2026-10, Android wallet — F8)

File: `core/src/main/java/io/digibyte/core/ipfs/AssetMetadataService.kt` (+ `db/dao/AssetMetadataDao.kt`)

The wallet is explicit about the rule and then breaks it:

| path | datum | treatment |
|---|---|---|
| metadata document (IPFS, written by the minter) | `issuer` | **refused** — comment at :250-258: reading it "makes attribution the easiest thing in the file to forge" |
| provider JSON (`getAssetData`) | `issuer` | **trusted as proven** — `:180` / `:195` pass `remote.issuer` into the `provenIssuer` parameter |

```kotlin
// :69  the distrust rule, enforced by ignoring `claimed`
internal fun provenIssuerOnly(proven: String?, claimed: String?): String? =
    proven?.takeIf { it.isNotBlank() }          // `claimed` is @Suppress("UNUSED_PARAMETER")

// :180  Pass 2a — provider inlines the document
return@withContext storeFromJson(assetId, metadataCid ?: remote.cid, json, remote.issuer)
// :195  Pass 2b — provider returns a CID we then fetch
return@withContext storeFromJson(assetId, remoteCid, json, remote?.issuer)

// :317  inside storeFromJson — the provider string lands in the authoritative column
issuerAddress = provenIssuerOnly(proven = provenIssuer, claimed = null),
```
```sql
-- AssetMetadataDao.kt:35-48  updateIpfsFacts: unconditional
UPDATE asset_metadata SET name = :name, ..., issuerAddress = :issuerAddress, ... WHERE assetId = :assetId
```

Reachability / severity:

- All provider hosts are certificate-pinned (`core/network/DigiScopePins.kt`, `DigistampPins.kt`), so
  a network attacker cannot inject the response ⇒ the **provider itself must lie** ⇒ **MEDIUM**,
  stated as such.
- **No metadata trickery is needed for the cleanest case:** when the issuance's on-chain metadata hash
  exists and Pass 1 fails only because a gateway is down, Pass 2 runs with the *authentic* CID
  (name + image verified against the chain) **and** the provider's issuer. Authenticated content
  carrying forged attribution in one row.
- The wallet **cannot** verify the string: the native bridge exposes `deriveIssuanceAssetId`,
  `deriveAddresses`, `derivePrivateKeyWIF`, `deriveDigiDollarAddresses` — and **no** issuer
  derivation. So the only honest options were omit / label-as-claimed.

Fix framing: pass `null` for the proven issuer (absent beats wrong), or give the provider's value its
own column and a "claimed by the provider" label, or have the provider return something the wallet
can re-derive from the issuance and check it before storing.
CWE-345 / CWE-290.

## The sweep (run it on any aggregating client)

1. **List the sources** for each fact the UI shows as authoritative (identity, issuer, price, supply,
   balance, rules, jurisdiction). Grep the network/provider clients, document/parser readers, and the
   DB writers.
2. **List the sinks** — the columns/fields the UI renders *without* a "claimed/self-asserted" label.
   Read the DAO `UPDATE`/`INSERT` SQL; an unconditional `SET <authoritative> = :param` is the sink.
3. **Cross the two.** A source→sink edge that crosses the port's own stated distrust rule is the
   finding. `rg -n -i 'never .*(trust|read|believe)|do not trust|forg|self-asserted|claimed' <repo>`
   finds the rules the port wrote for itself; then follow each datum the rule names to its other
   sources.
4. **Migrations are a confession.** A migration that NULLs a column
   (`Migration_7_8.kt: UPDATE asset_metadata SET issuerAddress = NULL`) plus a comment explaining
   *why* ("used to be filled from the metadata document") tells you the class was already found once —
   so check whether **every** source of that column was closed, not just the one named.
5. **Severity = who must misbehave.** Pinned first-party provider ⇒ MEDIUM. Unauthenticated peer /
   unpinned endpoint / MITM-reachable ⇒ HIGH. Check the pinning table before writing the tier.

## Pairs well with

- PART 8 item 10 (this checklist) and PART 8 item 9 (spec-vs-code) — same family: *the port's own
  written rule vs what the code does*.
- The write-path-vs-credit-path asymmetry (PART 8 item 7) — the mirror question ("the port gates X
  before acting; does it also gate X before accepting state?").
