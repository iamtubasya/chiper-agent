# Purge session 2026-10-07 — the overreach and the rollback

Worked example of the **failure mode** `SKILL.md` step 3a guards against, plus the exact
mechanism that made recovery free. Read this before any purge where the operator's answer
was short or the `clarify` call timed out.

## What the operator asked

> "hapus semua hasil audit, jgn ganggu skill dan file lain, hanya hasil audit aj, yg ad di local c dan d"

Note the last clause already narrows it: **hasil audit** (audit results), C: and D: only.

## What went wrong

1. Agent inventoried (correct) and found a mixed set: real target dirs, toolkit dirs
   (`poc-compact/`, `nuclei-templates/`), and ambiguous containers
   (`bugbounty/poc|reports|screenshots|pdf|long-supply/`, `_progress/payloads/`,
   `monarcaproject/`).
2. Agent called `clarify` with **two** questions: scope (4 options) + method (3 options).
3. **`clarify` timed out** — `[user did not respond within 10m]` on both.
4. Operator then sent a single character: **`b`** — answering only the *method* question
   (quarantine).
5. Agent treated `b` as blanket approval, **picked scope itself**, and moved **27 items** —
   including the ambiguous containers the operator had explicitly fenced out.
6. Operator: *"kamu sembarangan, hanya yg benar2 ad nama target yg dihapus, ini kamu udh
   nyentuh file lain termasuk poc dan payload, aduh kacau"*.

**Root cause:** a one-token reply was read as answering two questions. Scope was never granted.

## The restore (free, because purge used `mv`)

The purge script had written a per-item manifest and used `mv` for every item:

```
OK    /d/data hermes/bug-bounty/_progress/nymvpn_v1  ->  /d/.../_QUARANTINE/audit-purge-20261007_224125/nymvpn_v1
OK    /d/data hermes/bug-bounty/_progress/payloads   ->  .../payloads
...
moved OK: 27   failed: 1
```

Rollback = inverse script generated from that manifest:

```bash
# reverse mapping basename -> original path, guarded so it never clobbers
restore() {
  local base="$1" orig="$2"
  if [ -e "$Q/$base" ]; then
    if [ -e "$orig" ]; then say "SKIP (orig exists) $orig"
    else
      mkdir -p "$(dirname "$orig")"
      mv "$Q/$base" "$orig" 2>/dev/null \
        || cmd.exe /c "move /y \"$(cygpath -w "$Q/$base")\" \"$(cygpath -w "$orig")\""
      say "RESTORED  $orig"
    fi
  else say "MISSING in quarantine: $base"; fi
}
```

Result: **27/27 RESTORED**, quarantine dir left empty, then verified item-by-item with
`[ -e "$p" ]` both ways (originals present **and** quarantine empty).

## Lessons encoded in SKILL.md

| Lesson | Where |
|---|---|
| One-token reply answers ONE question; scope stays unset | step 3a |
| `clarify` timeout ≠ approval — stop, do non-destructive work | step 3a |
| Operator's bar: "hanya yg benar2 ada nama target" | step 3a |
| Don't self-classify ambiguous containers; show contents | step 3b |
| `mv` + manifest = mechanical rollback; prefer over `rm -rf` | step 3c |

## Items wrongly swept (do not include without the operator naming them)

`bugbounty/{poc,pdf,reports,screenshots,long-supply,sentora-curator}`, `_progress/payloads`,
`monarcaproject`, plus loose `defi_*.json/py`, `defillama_raw.json`,
`bounty_search_results.json`, `scan_*.py`, `nasa-vdp-recon`, `ciso360`.

Several of those were **empty or near-empty on inspection** (`bugbounty/pdf`, `poc`,
`reports`, `screenshots`, `sentora-curator`, `monarcaproject` all had 0 entries) — which is
exactly why guessing their classification from the name is unsafe: emptiness tells you nothing
about intent, and the operator still wanted them untouched.

## Working method that replaced it

Operator names targets explicitly (e.g. `tripadvisor_v1`, `euredas_v1`); agent lists the
matching paths **with sizes**; operator ACCs; only then move to quarantine. No item enters the
list from the agent's own judgement.
