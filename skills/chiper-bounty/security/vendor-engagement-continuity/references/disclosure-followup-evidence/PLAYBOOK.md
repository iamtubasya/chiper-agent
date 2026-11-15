---
name: disclosure-followup-evidence
description: "Use when a vendor asks for your tested commit or repro."
version: 1.0.0
author: Hermes Curator
license: MIT
metadata:
  hermes:
    tags: [disclosure, bug-bounty, evidence, reproduction, vendor-followup]
    related_skills: [bug-bounty-disclosure, evidence-hygiene, triage-validation, report-writing]
sources: operator_experience
---

# DISCLOSURE FOLLOW-UP EVIDENCE

## When to Use

Load this skill when **any** of these fired:

- A vendor/triager replied asking for the **exact source commit** you tested.
- A vendor/triager asked for a **standalone reproduction script**, raw evidence, or a PoC they can run.
- You are replying **in an existing disclosure thread** (threading headers, attachments, boundary statement).
- A vendor claimed **"we fixed it"** and you need to re-verify — especially across every write path.
- You are preparing a **bundle/manifest** (commit pin, hashes, captured run) for a security team.

Not for: deciding whether a finding is worth filing (`triage-validation`), writing the initial
report (`report-writing`), or redacting secrets in evidence (`evidence-hygiene`).

> Load this when a report is already filed and the vendor or triager comes back asking for
> *more* — the exact tested commit, a standalone reproduction script, raw evidence, or
> confirmation that a claimed fix actually holds.

A vendor asking *"could you share the exact source commit you tested and the standalone
reproduction script so our security team can compare your results?"* is a **good** outcome:
they are trying to reproduce. It is simultaneously the moment an unpinned, unreproducible
report gets downgraded to Informative. The reply is a deliverable — ship a bundle, not a
paragraph.

---

## 1. Answer the request literally, item by item

| Asked | What to send | Where it comes from |
|---|---|---|
| Exact source commit | full SHA + repo + branch + subject + date | `git rev-parse HEAD`; `git log -1 --format='%H%n%s%n%ad' --date=iso` |
| Proof that commit is what you tested | "working tree clean" + per-file SHA-256 | `git status --porcelain` (empty) + `sha256sum <files>` |
| Where the defect lives | `file:line` references, verbatim | `grep -n` against the source at that commit |
| Standalone repro | one self-contained script (§2) | runs with no repo checkout |
| Runtime version | exact framework + runtime version | the pinned version from `package.json` / lockfile |
| Boundary confirmation | explicit statement of what was NOT touched | your own test log |

**Pin the commit and hash the files at the time you review — not when asked.** You cannot
reconstruct "which commit did I look at last week" once new commits land. For a public repo the
SHA is a permanent anchor: the vendor can `git checkout` it and diff their own tree.

Build a `COMMIT.txt` so the whole answer survives being forwarded internally:

```
repo / branch / commit / subject / date / author
audited paths
line references (file:line : verbatim snippet)
per-file SHA-256 at that commit  (+ "working tree clean")
runtime versions (framework, language, OS where run)
exact run command
expected observable result
```

---

## 2. The reproduction script must be self-asserting

A script that prints output is not a repro. A script that **fails loudly when the bug is
absent** is.

- **Include the controls.** At minimum: the guarded path *without* the key must be rejected,
  and the *same* path *with* the key must be allowed. Without controls the output proves
  nothing — nobody can distinguish a bypass from a misconfigured harness. The controls are the
  part triagers quote back when they write "confirmed".
- **Assert expected status per case and exit non-zero on any deviation.** Then it drops into
  their CI and can be run against the fix branch. Print `VERDICT: ... CONFIRMED` only when
  every assertion held.
- **Transcribe the vulnerable code verbatim** and say so in the header comment, with the
  `file:line` it came from. A paraphrased reproduction invites "that is not our code".
- **Bind loopback only** (`127.0.0.1`, ephemeral port via `listen(0)`). State it in the output
  banner and in the email — this is what lets you honestly write "all testing was local".
- **Print the environment it ran on** (resolved module version + `require.resolve` path /
  `pip show` path) so a version mismatch is visible instead of silently changing the result.

Canonical shape (assert-then-verdict):

```js
const cases = [ // [method, path, headers, label, expectedStatus]
  ["GET",  "/api/tokens", {}, "lowercase, NO key   (control: must be 401)", 401],
  ["GET",  "/api/tokens", { "x-api-key": SECRET }, "lowercase, WITH key (control: must be 200)", 200],
  ["GET",  "/API/tokens", {}, "case-varied, NO key", 200],
];
let failed = 0;
for (const [m, p, h, label, want] of cases) {
  const res = await fetch(base + p, { method: m, headers: { ...h },
    body: m === "POST" ? "{}" : undefined });
  const ok = res.status === want; if (!ok) failed++;
  console.log(`  ${res.status} ${m} ${p} | ${label}${ok ? "" : `  <-- UNEXPECTED, wanted ${want}`}`);
}
console.log(failed === 0 ? "  VERDICT: CONFIRMED" : `  VERDICT: FAILED -- ${failed} case(s) deviated`);
process.exitCode = failed === 0 ? 0 : 1;
```

**Do not silently change the reported finding when replying.** If re-testing refines the
payload or the affected route, say so in the same thread. A follow-up "clarification" that
quietly rewrites the finding reads as non-reproducible.

---

## 3. Bundle manifest

One ZIP, so nothing arrives half-missing, plus text in the email body for anyone who only
reads mail.

```
<finding>-repro_<shortsha>.zip
  <finding>-repro.js        the script that was run
  repro-output.txt          captured run, exit 0, controls visible
  COMMIT.txt                repo, commit, branch, date, file:line, per-file SHA-256,
                            runtime versions, run command, expected result
  SHA256SUMS.txt            hashes of every file in the bundle
  <original-report>.pdf     the report as submitted
```

Rules that keep the bundle trustworthy:

- **Hash the ZIP after building and give that hash in the email.** The vendor can then prove
  nothing was altered in transit.
- **Confirm the script *inside* the ZIP hashes identically to the script you actually ran.**
  Rebuild the archive after any edit. A stale archive whose hash does not match the tested
  script is worse than no archive at all.
- Send the **single script** as its own attachment too, so a reviewer who does not want to
  unpack anything is not forced to.
- On Windows, `zip` may not exist — build the archive with Python `zipfile` and verify it
  (`zipfile.ZipFile(...).testzip()` returns `None` when every entry's CRC is intact).
- Capture the run output *from the real execution* (redirect the actual run to the file); never
  hand-edit or retype the transcript.

---

## 4. Thread the reply correctly

- Reply **inside the existing thread**: set `In-Reply-To` + `References` from the message being
  answered, and pass the thread id when creating the draft.
- Do not pick the thread's newest message by domain alone — transactional mail from the same
  domain ("Security alert", "your code is 123456") hijacks `In-Reply-To`. Select by
  **report-topic subject match**.
- Prefer creating a **draft** and letting the user review/send, unless told otherwise. Verify
  the draft afterwards (To, Subject, In-Reply-To, attachment names and sizes) before reporting
  it as ready.
- Reply **short and technical**. The vendor asked for two things; give those two things, plus
  the boundary sentence. No re-argument of severity.

---

## 5. Reaffirm the testing boundary explicitly

When the vendor adds *"please keep further reproduction local; there's no need to test
administrative endpoints on a live service"*, restate the boundary and describe what you did
**instead** of it:

> "Every probe I sent to a live host was a plain read-only GET; the privileged action was
> exercised only against the local harness. Nothing further will touch a live service."

This one sentence is what keeps a legitimate finding from being reclassified as a scope
violation. Confirm it going forward, not just retrospectively.

---

## 6. "We fixed it" → re-test across EVERY write path

A fix is usually applied where the report pointed, not everywhere the invariant applies. Re-run
the **same invariant** across create + edit + delete + import + API, not just the path named in
the fix. A fix that holds on the reported path and leaks on a sibling path is the finding
vendors value most — and it stays reportable.

When re-testing produces a variant, treat it as a **new standalone finding with its own file
and evidence** unless it is a genuine chain of the same root cause. Do not append a weak
variant as a "secondary observation" to a strong report.

---

## 7. Pitfalls

- **Unpinned commit** → the single most common reason a source-review finding cannot be
  reproduced by the vendor. Pin at review time.
- **Repro with no control** → looks conclusive, proves nothing. Always include the
  must-be-rejected and must-be-allowed pair.
- **Script that always exits 0** → unusable as vendor CI. Assert, and set a non-zero exit.
- **Repro that needs the repo checked out** → it is not standalone. Inline everything.
- **Silent restatement** of the finding in the reply → reads as a moving target.
- **Scope creep while being helpful** → running a "quick check" against the live privileged
  endpoint after the vendor asked you not to. The bundle exists precisely so you never need to.
- **Hand-written transcript** in `repro-output.txt` → if it does not match a fresh run, the
  whole bundle loses credibility.

---

## 9. When the vendor DISPROVES your claim — retract, don't re-argue

The follow-up that ends a finding. A vendor replies with a technical objection that shows your
evidence does not support your claim. This happened live (do.de ALTCHA PoW, 2026-10-26): the
vendor recomputed the derived key, pointed out the accepted solution matched the full prefix,
and noted the timestamps did not support the stated expiry. **They were right on both counts.**

The instinct to defend the submission is the wrong one. The sequence that preserves credibility:

**1. Re-run the discriminating test before replying.** Do not reply from the vendor's argument
alone, and do not reply from your original evidence alone. Construct the input that separates
your hypothesis from the boring explanation and let the system answer. In the live case that
meant hunting a **partial** match — a solution matching the claimed prefix length and then
diverging — and submitting it inside the TTL. It was **rejected**. That settled it.

**2. If the test confirms the vendor, withdraw the claim explicitly and in writing.** Name the
claim, attach the disproving run, and say what it replaces. A withdrawal that carries the
disproving evidence is worth more to your reputation than the finding would have been:

> "The verification-threshold claim is withdrawn. A solution matching only the first 2 bytes
> of keyPrefix, with byte 3 mismatched, submitted inside the TTL, is rejected:
> `keyPrefix=4212de7a…`, `counter=68368`, response `Bitte geben Sie alle Pflichtangaben an`.
> The earlier accepted example matched the full 16 bytes because that challenge was
> precomputed. Full capture attached."

**3. Audit every other number in the same submission.** A vendor who caught one error will
check the rest. In the live case the timing claim was also wrong — derived from the agent's own
polling loop rather than the target's `expiresAt`. Recompute each figure from the target's own
fields and restate the measurement basis ("as read at HH:MM:SS") wherever your clock was used.

**4. Check artifact-to-narrative association.** Every screenshot must come from the run the
paragraph describes. A mismatched artifact — describing state `expired` while the image shows
`Verified` — independently discredits the whole bundle even when the finding is sound. See
`video-poc-production` §VERIFY-also-the-contest.

**5. Keep what survives, reframed honestly.** Separate the disproven claim from the still-true
measurement, and relabel the latter as an observation rather than a vulnerability. In the live
case, "10/10 challenges are precomputed" remained factually true and was worth stating — but as
a design observation, not a bypass, with an explicit offer to drop it if the vendor preferred.

**6. Apologise once, briefly, without grovelling.** The vendor spent their time cleaning up
after a sloppy submission. One short paragraph naming what you got wrong is appropriate;
re-arguing severity is not.

**What not to do:** re-file the same claim with new wording, appeal on the grounds that you
still believe it, or quietly stop replying. All three read worse than the original error.

### The generalisable lesson — the precomputed-answer trap

A control that **generates its own expected answer** cannot be bypassed by producing that
answer. Before claiming any threshold ("the server only checks N bytes", "the server accepts a
short/partial solution"), you must submit a solution that satisfies your claimed threshold
**and demonstrably fails the full requirement**. Accept-at-N plus reject-at-(N-1) is **not** a
bisect — it is equally consistent with correct full verification.

For prefix-matching PoW/CAPTCHA specifically: sample the challenges and check whether a
full-prefix solution is reachable at a small counter. If it is (10/10 in the live case, counters
5,452–9,133), the target is precomputed, the server already knows the answer, and the
"N-byte threshold" framing is measuring nothing. Full proof bar:
`report-gotchas` → CAPTCHA/PoW class.

---

## 10. Related skills

| For this | Use |
|---|---|
| Deciding whether the finding should have been filed at all | `triage-validation` |
| Report body / platform template | `report-writing` |
| Redacting cookies, PII, leaked secrets before attaching | `evidence-hygiene` |
| Contact discovery, first-contact email shape, end-to-end disclosure flow | `bug-bounty-disclosure` |
| Full worked example (commit pin → controls → bundle → boundary reply) | `references/vendor-followup-evidence-pack.md` |
