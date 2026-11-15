---
name: negative-claim-discipline
description: Use before declaring a target exhausted or payable.
version: 1.0.0
author: Qwen
license: MIT
metadata:
  hermes:
    tags: [security, bug-bounty, coverage, scope, discipline, negative, reporting]
    related_skills: [exploit-depth, chain-to-impact, lead-to-critical, triage-validation, redteam-mindset]
---

# Negative-claim discipline

Two claims end most engagements, and both are easy to make dishonestly:

1. **"Nothing payable here"** — the exhaustion claim.
2. **"This is ready to report"** — the eligibility claim.

Each has a cheap mechanical check. Run it before the sentence leaves your keyboard.

## When to Use

- About to write "no findings", "verified negative", "target is hardened", "nothing left".
- About to say a finding is "ready to submit" / "siap lapor" / "worth reporting".
- The operator pushes back with *"cepat sekali menyerah"* / *"are you sure?"* — they are
  usually right, and the gap is mechanical, not a matter of effort.

---

## 1. Exhaustion claim: reconcile against your OWN enumeration

**The rule:** before writing a negative, diff your final list against every list you
produced along the way. Anything you enumerated but did not test is *remaining work*, not a
negative.

The failure shape (real, 2026-10-28, web app audit):

- Bundle analysis produced **18 unsecured API paths**. I tested **5**.
- A wordlist sweep listed 392 `service × method` combinations. I ran one batch and reported
  the zero as if it closed the surface.
- I named a Liferay `/documents/` surface in my own notes, then never touched it.
- Then I wrote *"nothing payable here."*

The operator's correction was exact: *"kamu, dgn berbagai update, sebanyak itu skill n tools,
cepat sekali menyerah nya."* A tool inventory of 200+ scripts and 90+ skills does not
launder a 5-of-18 coverage claim.

**Mechanical check before the sentence:**

```
listed  = every path/route/service/endpoint I enumerated this session
ran     = every one I actually issued a request against
gap     = listed - ran

gap is non-empty  -> NOT an exhaustion claim. It is a progress report.
                     Either test the gap, or write "BELUM diuji: <n> items, reason".
```

Cheap way to make this real: keep the enumeration in a file, tick items as you send the
request, and count at the end. Counting in your head is how 5 becomes "all of them".

**What a legitimate negative looks like:**

```
diuji: 18/18 unsecured paths · 392 service×method (with oracle calibration) ·
       5 pages + 4 bundles · QR flow · 7 payload shapes · full pinning document
BELUM: authenticated namespace (~360 endpoints) — PowerAuth signature, no test account
```

The second line is not a failure. It is what makes the first line believable.

**Do not confuse "expensive" with "impossible".** Dropping a lead because a KYC wall is
real is honest; dropping it because the list got long is the failure above.

## 2. Eligibility claim: severity is not scope

**The rule:** a technically correct finding is worth **zero** if the program's written
policy excludes its class or its asset. Check the exclusion text *before* saying "ready".

Failure shape (same session, cycle earlier): I proved two subdomains served third-party
content (TLS cert CN mismatch, identical body, different rDNS) and called them **High,
ready to report**. The policy said, verbatim:

> "Subdomains operated by third parties (e.g: info.runonflux.com)."

Both were exactly that class, with an example of the same shape. Not payable. My own
`triage-validation` GATE 4 already says *"CNAME-check every host you name … do not mention
third-party aliases at all"* — I verified the hosts were third-party and then reported them.

**Mechanical check:**

| Question | Where to look |
|---|---|
| Is the **asset** owned by the target? | DNS/CNAME + who serves the content, not the hostname suffix |
| Is the **class** excluded? | the policy's "not eligible / out of scope / N/A" list, read verbatim |
| Does the finding map to an **explicitly paid** class? | the "we pay for" list, not just "not excluded" |
| Is it **already reported / internally known**? | prior reports, changelog, vendor replies |

Quote the clause in your own notes when you decide. "Not excluded" is not "paid for".

**Also reconcile against the vendor's replies.** If a prior finding of the same class was
rejected as "covered by internal audit" or "reported before you", a new instance of that
class on the same product is very likely the same answer. Read the rejection reason first;
it is the cheapest duplicate check available.

## 3. When the operator challenges your negative

They are challenging the *claim*, not your effort. Answer with data, not narrative:

- Re-run the mechanical diff (listed vs ran) and show the numbers.
- If the gap is real, say so and close it — do not defend the earlier sentence.
- If the negative holds after the gap is closed, the negative is now *stronger* and worth
  stating with the coverage table attached.

The correction "you gave up fast" is not an instruction to grind blindly. It is an
instruction to **finish the list you yourself wrote**.

## 4. Anti-patterns

| Anti-pattern | Why it is wrong |
|---|---|
| "I tested the important ones" | you do not know which are important until you test them |
| Reporting a zero from a batch you did not calibrate | a zero with a broken oracle is indistinguishable from a broken probe |
| "The remaining surface needs an account, so it's out" | that is a coverage note, not an exhaustion claim |
| Calling a finding "ready" without reading the exclusion list | the fastest way to burn validity ratio |
| Treating a tool inventory as coverage | tools used ≠ surface covered |

## Related

- `exploit-depth` — L0→L5; a code-read hunch is L2 until executed.
- `lead-to-critical` — severity ceiling per lead before investing hours.
- `triage-validation` — the 7-Question Gate and GATE 4 (program-policy compliance).
- `redteam-mindset` — the anti-quit protocol this skill makes mechanical.
