# AI-Slop Patterns in Bug Bounty Reports

> **Source:** adapted from YesWeHack `claude-kit`
> `skills/triage/references/ai-slop.md` (GPL-3.0-or-later), 2026-10-26.
> Category structure and severity mapping are theirs; **[ours]** notes are
> additions from this estate's engagements.
>
> Read the draft report and flag everything that looks like unverified LLM
> output. Be strict. Reports get rejected for these patterns all the time.

## Critical red flags (any one of these → DO NOT SUBMIT)

### 1. Hallucinated facts
- A **CVE ID** that doesn't exist or doesn't match the described bug.
  → Verify every CVE referenced. Wrong CVEs are the #1 giveaway.
- **Endpoints or parameters** that don't exist on the target.
  → If the hunter says `/api/v2/admin/users?debug=true`, that path must
  resolve. Generic API paths invented by an LLM are a red flag.
- **Library/version** claims without a fingerprint.
  → "The target uses lodash 4.17.20 which is vulnerable to..." — was that
  actually fingerprinted, or did the LLM guess based on the year?
- **Headers or cookies** that don't actually appear in the response.
- **Function or class names** copy-pasted from generic exploitation guides.

### 2. Theoretical-only impact
- "An attacker **could potentially** gain access to..." — without proof.
- "This **may lead to** RCE" — without showing RCE.
- "An attacker **with the right conditions** could..." — what conditions?
  Are they present here?
- Impact escalations that are not demonstrated in the PoC.
  → If the report claims session hijack, the PoC must show a session being
  hijacked. Not "and therefore session hijack is possible."

### 3. PoC that is not actually a PoC
- Pseudocode instead of real requests.
- `curl https://target.com/vuln?payload=<XSS>` with no real payload.
- "Send this request and you will get..." without the actual response shown.
- Steps that skip over the interesting part with "..." or "as shown above".
- Screenshots described in text but not actually attached.

## Strong red flags (any → NEEDS FIXES)

### 4. AI structural tics
- Excessive H2/H3 sectioning for a simple bug (Introduction / Background /
  Vulnerability Details / Technical Details / Impact / Recommendations /
  Conclusion — for a 1-step XSS).
- "**In conclusion**", "**It is important to note**", "**This vulnerability
  highlights**" phrases.
- Bullet lists where prose would be clearer, especially three-item lists that
  paraphrase each other.
- Closing paragraph that summarizes the whole report ("In summary, this report
  has demonstrated...").
- Excessive bold/italic for emphasis on generic terms.

### 5. OWASP boilerplate
- **Multi-paragraph** generic definitions of the vulnerability class
  copy-pasted from OWASP / PortSwigger / MDN → delete. One short sentence of
  context for non-specialist reviewers (program managers, devs reading
  post-triage) is fine; a 5-line OWASP intro on a 1-step bug is slop.
- "Cross-Site Scripting (XSS) is a type of injection attack where..." as a
  standalone paragraph → delete.
- "Mitigation: validate all user input, use parameterized queries..." → generic
  advice not tied to the actual code path of this bug. Either give a fix
  specific to the bug, or omit the section.

### 6. Confidence without evidence
- Severity rated Critical/High with no impact demonstration.
- CVSS vector whose metrics contradict the stated preconditions or proven
  impact. Scoring must be **CVSS 3.1, Base metrics only** — flag any
  Environmental/Temporal metrics the hunter set themselves (those are the
  program's to weigh; setting them inflates the score). The classic LLM
  pattern is the "max-severity" vector
  (`AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H` = 9.8) defaulted onto a bug it
  doesn't fit. Common mismatches:
  - `PR:N` claimed when auth has a real gate (paid tier, admin invite, org
    membership) — `PR:N` is only correct when self-registration is open.
  - `UI:N` claimed when the victim must click / paste / load.
  - `S:C` claimed without an actual trust boundary crossing.
  - `AC:L` claimed when the resource ID is a non-guessable UUID (that's
    `AC:H`).
  Check each metric against what was actually verified.
- "Easily exploitable" / "trivially exploitable" without showing the exploit
  working in one step.

### 7. Suspicious neutral tone
- The whole report reads like a textbook, not a hunter's lab notes.
- Zero mention of what the hunter tried, what failed, what they had to bypass
  — only a polished narrative.
- No mistakes, no dead ends. Real exploitation rarely looks this clean.

## Minor red flags (any → MINOR ISSUES)

- Unicode arrows, em dashes used in code blocks, smart quotes in payloads
  (these break copy-paste reproduction).
- Mentioning "the AI assistant" or "as an AI language model".
- Markdown that wasn't rendered (literal `**bold**` in submitted text).

## Output

For each red flag found, output:

```
[CRITICAL|STRONG|MINOR] - <category>: <quote or paraphrase from the report>
→ Fix: <concrete instruction to the hunter>
```

If no red flags found, say so explicitly. Do NOT pad with caveats.

---

## [ours] Estate-specific additions

These are patterns seen in this operator's engagements that the upstream
reference does not cover. They map onto the same three severity tiers.

### CRITICAL — attachment/self-containment defects
- Body references a file the recipient does not receive ("attached PoC
  `foo.py`" while only the PDF is attached). Grep the final body for
  "attached", "see the PoC", "appendix", and every filename; each must resolve
  to something actually attached or inlined in that same artifact.
  (`report-writing` THE DELIVERABLE MUST BE SELF-CONTAINED.)

### STRONG — count/aggregation slop
- Scanner "POC" count presented as a finding count. A scanner emits one POC
  per (URL, parameter), not per vulnerability. Write "N POC on 1 parameter, M
  false positive", never "N findings". (`audit-runbook` RULE 24b.)
- A negative result from a run where every request was rejected
  (`400`/`401` throughout) — that is a tooling failure presented as coverage.
- "Clean" / "mature" / "locked down" as a conclusion. Unprovable claim; use
  "module X verified sound this round; remaining queue: Y, Z" instead.

### STRONG — scope drift in the writeup
- Severity claimed above the program's published cap for that class.
- Asset described as in-scope when it is a locale mirror / sister domain the
  program does not name. (`target-pool` levoit.au lesson.)

### MINOR — channel/tone
- Email body opening with "Summary" and no introduction. The first contact
  must carry: name, role, the policy URL the work is based on, what was
  reviewed and how, the core finding in one sentence, and an explicit
  "no data taken / no state changed / stopped once clear" statement.
  (`bug-bounty-disclosure` first-contact structure.)
- Generic mitigation paragraphs in a program whose policy explicitly excludes
  "best practice recommendations".
