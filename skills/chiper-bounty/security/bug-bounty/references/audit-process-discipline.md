# Audit process discipline — operator-enforced corrections

Four corrections the operator made directly during the moneta.cz engagement (2026-10-26). These are
process rules, not techniques; they govern *how* an audit is run and written up. Read this before
starting any engagement where the operator says "gas", "jangan berhenti", or "pakai semua tools".

---

## 1. Chain the leads before judging them

Operator: *"km udh cb lead ny dcek via chain attack?"*

The failure mode: evaluating each lead in isolation. A lead judged alone looks dead; the same lead
chained can become account takeover. On this engagement the chain that mattered was:

```
exported deep-link activity  ->  raw URI params into a Bundle  ->  fragment arguments
   ->  sink (WebView / server call / local read)
```

Every link in that chain had to be walked in code, and the *termination point* recorded precisely.

**Rule:** for every lead, write the chain to its final sink and record **where it dies**. Two
different death points:
- *dies at a local read / UI-only hint* → genuinely closed, write the reason.
- *dies at a server endpoint that needs an account* → **still open**. Write it as one concrete
  blocker, never as a negative.

A lead that dies at "the server would have to validate X" is not a verified negative. Saying so is
the difference between an honest report and a fabricated one.

## 2. Verify at least 3× with *different* methods

Operator: *"yakin kamu udh cek lagi rantai chain 1-5 ini minimal 3x? jgn berhenti secara prematur."*

One partial decompile is not verification. The pattern that satisfied this:

| claim | check 1 | check 2 | check 3 |
|---|---|---|---|
| `arg_script_file` set in only one place | decompile the owning dex | regex over **all** dex concatenated (94 MB) | enum/fragment-mapping check |
| QR token not derivable | SHA-1 vs session id | SHA-1 vs uuid / counter / timestamp | cross-session poll oracle |
| debug menu unreachable | layout `visibility` | grep every `setVisibility` on that id | listener reachability analysis |

If one of the three checks cannot be performed, that is a **gap to disclose**, not a pass.

## 3. A tool marked "N/A" without being RUN is a violation

Operator: *"sy lihat kamu td pakai toolsnya byk stgh jalan, jd kurang maksimal."*

Writing `dalfox: N/A — no reflected parameter` without ever running dalfox is disposal dressed as
coverage. The ledger rule (rule 23) already demands tool→result; this sharpens it:

- If a test class was not executed, write **"BELUM dijalankan"** + the reason.
- `N/A` is only legitimate **after** the tool ran and came back negative, with the evidence.
  Good example: `graphql-cop` → probed 8 GraphQL path variants, all 404 → *now* N/A, with proof.
- "I judged it unnecessary" is not a result. Run it, or label it unrun.

## 4. Read the real telemetry before writing the ledger

Self-correction, prompted by the operator's challenge on tool usage.

I wrote "nuclei killed at 1%" in the coverage ledger. The log actually showed **26,648 requests,
77% of 34,410, 43 minutes, 0 matches**. A comfortable number that is wrong is more damaging than an
uncomfortable number that is right.

**Rule:** before writing any volume / result / status into `COVERAGE.md`, grep the tool's
`.err`/`.log` and quote the actual figures. If an earlier claim of mine turns out to be wrong,
correct it in an addendum rather than quietly editing — the audit trail of my own errors is part of
the deliverable.

Related: on a bank/fintech target, disclose disproportionate request volume rather than hiding it.
The moneta run totalled ~31,300 automated requests against two in-scope hosts. No clause was broken
literally (the 100-request cap is specific to rate-limit testing, which was never performed), but
proportionality was not met and that belongs in the ledger.

---

## What "done" looks like for a verified-negative engagement

When the unauth perimeter is genuinely clean, the deliverable is **not** "no findings" — it is:

1. A tool→result ledger including every tool that was *not* run and why.
2. Per-class verified negatives with the evidence that closed them.
3. Every lead walked to its termination point, with the point named.
4. Explicit coverage gaps (usually: the authenticated surface, which needs a test account).
5. One concrete blocker + one concrete unlock, stated once — not a menu of options.

And no draft report. Submitting an unproven lead to get a "finding" on the board is overclaiming and
gets rejected under any programme's "hypothetical flaw without PoC" rule.
