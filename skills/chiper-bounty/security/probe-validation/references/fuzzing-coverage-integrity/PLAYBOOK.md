---
name: fuzzing-coverage-integrity
description: Use when a wordlist/fuzzer sweep returns "0 hits" — proves the harness can actually see a known-live endpoint before any negative claim is written.
metadata:
  hermes:
    tags: [fuzzing, ffuf, coverage, false-negative, bug-bounty]
version: 1.0.0
---

# Fuzzing Coverage Integrity

A sweep that returns zero is not evidence. It is evidence only after you prove the
same harness catches an endpoint you KNOW exists.

Learned the hard way on binobi.com (2026-10-28): two silent harness bugs produced
"0 hits" on every sweep, and the negative was written into a report before it was
caught.

## The two bugs that make ffuf lie

### 1. Default matcher ignores HTTP 400

ffuf's default `-mc` is `200-299,301,302,307,401,403,405,500`.

**400 is not in that list.** Every endpoint that validates a DTO answers a
malformed body with 400 — which is most authenticated API endpoints. They vanish
from the results entirely.

```
ffuf ... -mc all           # mandatory for API sweeps
```

### 2. Leading slash in the wordlist doubles the path

With `-u https://host/FUZZ`, a wordlist entry written as `/exchange` produces
`https://host//exchange` → uniform 404 → silent false negative.

```
sed 's|^/||' wordlist.txt > wordlist_ns.txt   # normalise before every run
```

Symptom: the API returns 404 with a `Cannot POST //exchange` body. If you see a
double slash in an error message, your wordlist is wrong, not the target.

## Mandatory sanity gate (run before trusting any sweep)

Put 1-2 endpoints you already know are live into a tiny probe wordlist and run the
exact same ffuf command. If they do not appear, the harness is broken — fix it,
do not interpret the empty result.

```bash
printf 'exchange\nexchange/rate\nknown/callback\n' > sanity.txt
ffuf -u https://api.host/FUZZ -w sanity.txt -X POST -d '{}' \
     -H 'Content-Type: application/json' -mc all -fc 404 -rate 5 -t 1 \
     -o sanity.json -of json -s
# expect the known endpoints in results
```

Observed proof of the gate working: with `-mc all` + normalised paths the
1,934-path sweep returned 20 live endpoints instead of 0, and the entirely new
`/exchange` shadow API surfaced.

## Auth level changes the status code

The same path returns different codes anonymously vs authenticated:

| path | anon | authed |
|---|---|---|
| /moneygrator/callback | 401 | 401 |
| /notifications | 401 | 400 (dumps required DTO) |
| /exchange | 401 | 400 (dumps required DTO) |

So an anonymous sweep and an authenticated sweep are two different datasets. Run
both, and diff them. The authenticated 400s are what hand you field names, enums
and types.

## Corroborate a negative three independent ways

Never state "no other endpoint exists" from one tool. On binobi the negative was
only defensible after three methods agreed:

1. wordlist sweep (`-mc all`, normalised)
2. plain Python parallel HTTP probe (no ffuf in the path — immune to both bugs)
3. a side-channel oracle, not path guessing at all

## Side-channel oracle beats wordlists

When a service exposes metrics, use them as a detector instead of guessing paths:
send a candidate request, then diff the relevant counter.

```python
# baseline, send, re-read metric, delta > 0  ==  route exists
binobi_moneygrator_callback_events_total{outcome="received"}   +1
binobi_moneygrator_callback_events_total{outcome="invalid_signature"}  +1
binobi_rate_limit_decisions_total{...rule="callback-burst"...}  +1
```

This found `POST /moneygrator/callback` after wordlists (even corrected ones)
never surfaced it — because no wordlist contained that exact provider/callback
pair.

## Reporting rule

If a sweep was run with a broken harness, the correct output is not "0 findings".
It is: fix the harness, re-run, and state the corrected tally. Withdraw the wrong
negative explicitly in the report. A vendor forgives "I fixed my method"; it does
not forgive a coverage claim that was never true.

## Pitfalls

- `-ac` (autocalibration) can mask 404 templates but does not fix the 400 gap.
- `-fs`/`-fl` filters keyed to a 404 body length break when the 404 body length
  changes between hosts — prefer `-fc 404` plus `-fr` on the error message.
- Case-insensitive routing (`/Exchange` == `/exchange`) means dedupe by handler,
  not by path string.
- Do not key on response length alone: success bodies of 1.65 MB (a dumped
  article corpus) and 43-byte auth errors both "exist".
