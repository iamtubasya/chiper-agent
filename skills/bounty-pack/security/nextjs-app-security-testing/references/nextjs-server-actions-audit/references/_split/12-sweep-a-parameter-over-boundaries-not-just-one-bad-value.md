## Sweep a parameter over boundaries, not just one bad value

Testing `?ty=<year>` with a single junk value ("abc") returned a normal page, which looked like
"the parameter is ignored". Sweeping the whole boundary set found the real behaviour:

```
ty=abc  -1  0  2026.5  99999  20261   -> 200 (graceful fallback to the default year)
ty=1900  9999                          -> 500  (Next.js error page, no stack trace, no data)
ty=1900%00                             -> 200  (null byte truncates the parse)
```

One 500 on one odd value of one form field is a **P5 robustness note** (CWE-248), not a hole —
but it only surfaces if you enumerate boundaries. Cheap default list for any numeric-or-shape
parameter: `abc`, `-1`, `0`, `1e3`, `<min-1>`, `<max+1>`, `<valid>.5`, an empty string, a null
byte suffix, and a very large integer. Note where it is reachable (session required? any source
type?) and whether anything leaks — those two answers decide P5 vs something worse.

**Re-verified harder (2026-09-30), so treat this as settled for this class:** the review
queue's `Confirm` was driven with REAL Playwright clicks (not JS `.click()`) on three fresh
entries with three different values — `otherIncome`, `periodAmount` and the forbidden
`taxDeducted`. Every POST carried `txnId` + `category`, returned **200**, and the row's
category read back **null** afterwards in all three cases. So it is inert, not
discriminating. Two extra signals worth capturing: entries created through the FORM with the
app's own "✨ Suggest one for me" option never appeared in the queue at all (only
API-written rows did), which is a plausible explanation; and the queue dropdown still lists
the forbidden category for that source type. Report as *product bug + UI inconsistency*,
never as bypass.

