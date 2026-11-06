# Auth-boundary differential + "is this code deployed?" — the two honesty moves

Measured 2026-10-12/13 (Blink VDP, `voucher.staging.blink.sv`, Galoy `apps/voucher` stack).
Companion to the "deteksi ≠ bukti" family: both moves exist to stop a true observation from being
written up as a bigger claim than it is.

## 1. Proving a resolver is genuinely reachable without a session

`HTTP 200 {"data":{...}}` on an unauthenticated request proves nothing on its own — caches,
catch-alls and static hosting all answer 200. Send **three** probes with **no credentials at all**:

```
TARGET    POST /api/graphql {"query":"{ getWithdrawLink(voucherSecret:\"ZZZ…Z\") { id identifierCode voucherSecret } }"}
          -> 200 {"data":{"getWithdrawLink":null}}

SIBLING   POST /api/graphql {"query":"{ getWithdrawLinksByUserId(status: ACTIVE) { withdrawLinks { id } } }"}
          -> 200 {"errors":[{"message":"Unauthorized",…}],"data":null}

PIPELINE  POST /api/graphql {"query":"{ getWithdrawLink(voucherSecret:\"ZZZ…Z\") { noSuchFieldXyz } }"}
          -> 400 {"errors":[{"message":"Cannot query field \"noSuchFieldXyz\" on type
                    \"WithdrawLinkWithSecret\".","code":"GRAPHQL_VALIDATION_FAILED"}]}

THROTTLE  12 consecutive anonymous TARGET calls -> 200 ×12, no 429, no lockout
```

| probe | what it actually buys |
|---|---|
| TARGET 200 + `data` key | the resolver **executed** for an anonymous caller |
| SIBLING `Unauthorized` (same type, same session, also unauthenticated) | an auth check **exists** on that type and is simply absent on the target field — the gap between the two IS the finding |
| PIPELINE 400 `GRAPHQL_VALIDATION_FAILED` | a live query pipeline, not a permissive cache — the validator still rejects unknown fields |
| 12/12 no 429 | the unguarded read is usable at speed, which is what makes any future prediction testable |

Generalises past GraphQL: for any endpoint, find a **sibling resource on the same host that
correctly demands auth**, hit both anonymously in one session, and keep both raw responses. The
pair is the evidence; either one alone is not.

**Free schema intel even with introspection disabled.** This deployment answered
`"GraphQL introspection is not allowed by Apollo Server"` to `__schema`/`__type`, yet the PIPELINE
probe's error text leaked the full type name `WithdrawLinkWithSecret`, and validation errors leak
field names. The error-shape oracle keeps working when the schema dump is refused.

### The sentence that must not be written

`null` for a guessed value is **reachability**, never a valid-object read. Write
*"the lookup is reachable without a session and is not rate limited"* — **not** *"unauthenticated
access to withdraw links"*. The object itself was never obtained. One word of overclaim turns a
kept finding into a retraction.

## 2. Is the vulnerable code in the DEPLOYED build?

A public repo / OSS snapshot is a hypothesis generator, not the running code. One cheap check:

```bash
curl -s https://host/ | grep -o '/_next/static/chunks/[^"]*\.js' | sort -u   # 13 chunks
# then grep each chunk for a constant UNIQUE to the code path
```

**Pick the unique constant, not a generic token.** The path's `generateCode()` alphabet contained
the distinctive substring `jkmnpqrtuvwxyz`; grepping for it → **0 hits in 13/13 chunks**.
Grepping the generic token `Math.random()` → 4 hits, every one inside bundled retry/polyfill
jitter (`Math.random()*t`). The generic query returns a **confident false positive**; this check
exists precisely to prevent that class.

How to report each outcome:

| result | what you may claim |
|---|---|
| unique constant ABSENT from all chunks | nothing about the deployed build. Stand the finding on (a) source analysis + (b) live behaviour you actually observed, and say the bundle did not corroborate it |
| unique constant PRESENT | quote the chunk URL + surrounding bytes as the evidence line |
| a *sibling* artefact found (e.g. chunk `218-*.js` carries the `createWithdrawLink` operation text, whose selection set includes `identifierCode` + `voucherSecret`) | "the feature exists in the deployed app" — a separate, weaker claim. NOT evidence about how the secret is generated |

Keep those two claims apart in the write-up. They are adjacent, and merging them is how a bundle
grep becomes an imaginary PoC.

## 3. Why a bounded claim is the deliverable

The weak-generator half was reportable on its own terms: `Math.random()` used for a bearer secret
that redeems bitcoin from a shared escrow wallet, ≈18 consecutive xorshift128+ outputs per creation
(6-char `identifierCode` + 12-char `voucherSecret` over a 56-symbol alphabet ≈5.81 bits/char,
≈69.7 bits of secret). State recovery was **not** executed and was **not** claimed. The report
carried a two-column table — *what was proved* vs *what is argued* — and severity was scored for
the code weakness as it stands (AC:H), with a note that the unauthenticated read alone is Medium.

Both deliverables (email body + PDF) carried that same table. The operator reads the email first;
the triager reads the PDF; a claim that appears in one and not the other is the failure mode
`bug-report-delivery` calls cross-artifact disagreement.
