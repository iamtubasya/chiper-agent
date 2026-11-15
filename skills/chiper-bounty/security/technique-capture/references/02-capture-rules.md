# 02 — Capture rules

## The gate: evidence or it does not exist

`technique-log.py add` **refuses** a candidate with no `--evidence`. This is the same standard as a
finding: a technique you did not reproduce is a claim, and claims do not belong on a method shelf.

Good evidence is one line that lets someone else re-derive the technique:

```
--evidence "curl -x sock5 ... returned 200 while the direct request 302'd to the WAF page"
--evidence "self.__next_f carried the marker \\u003c-escaped; the unquoted href sink executed"
```

Bad evidence (will not survive review):

```
--evidence "looks like it could be bypassed"
--evidence "the vendor's changelog says they fixed it"
```

## Confidence

| value | meaning |
|---|---|
| `observed` (default) | you saw it happen in this run |
| `inferred` | you reasoned it from a signal; say so |

An entry can be promoted on `inferred` **only** if the note says what would confirm it.

## Dedupe, and what its two flags mean

`technique-log.py dedupe --atlas <atlas>/references` emits two kinds of flag:

| flag | meaning | action |
|---|---|---|
| `class-overlap` | the *class* already exists in the atlas index | expected and fine — the **technique** may still be new. Continue. |
| `duplicate-of` | this staged entry overlaps another staged entry (tokens > 60%) | **merge them.** Do not distil two entries for one technique. |

Class overlap is not a rejection. Only `duplicate-of` is.

## What is out of scope

- **Payloads.** The shelf is methods. Record the method; keep the payload in the engagement artefact.
- **Malware / scam tooling.** Filtered out by the atlas pipeline — do not stage it.
- **Anything you cannot describe in one sentence.** If you cannot, you do not understand it yet.

## Closing an entry

Every entry ends as `promoted` or `rejected --why "…"`. A ledger with open entries is a to-do list,
not a record. `stats` shows what is still open.
