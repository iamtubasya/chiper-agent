# Pre-submission self-review gate

Run this AFTER the report/PDF is built and BEFORE staging any draft. It exists because the
expensive failure is not a bad PDF — it is emailing a real vendor two findings that do not
survive re-reading them 30 seconds later. Hit 2026-10-14 on an open-source target: two reports
were fully built and layout-clean, and both failed this gate. Neither was staged.

Five questions. Any "no" means do not stage yet.

## 1. Does the vendor's own source describe the behavior as intentional?

Read the docstring/comment at the exact site you are reporting. If it states the behavior is a
deliberate design choice, you have found a documented decision, not a bug.

Concrete case: an early-return gate was reported as "the scope gate skips 38 tools." The file's
own doc comment said, verbatim, it "gates only on a valid key of the company (today's MCP
behavior for account/shared)." The code was telling us it was intended.

Two valid outcomes:
- **Reclassify** as an informational/design note, or drop it.
- **Reframe honestly**: the gap becomes "documentation promises X, code documents not-X" — a real
  (lower) finding about a contract mismatch. Reportable; the original claim is not.

Never cite code as evidence of a bug when that same code explains why it is not one.

## 2. Does my severity rest on a question I never answered?

Grep the report for doubt-phrased assertions: "whether X adds a scope check", "if the proxy
enforces Y", "unresolved". Each is a variable that decides severity. If unresolved, the severity
is unsupported. Either resolve it with one focused read/test, or downgrade to what the *proved*
column supports. A High whose own caveat list contains the deciding unknown is a contradiction
in terms.

## 3. Is the "proved / argued" table actually filled in?

The two-column honesty table is the gate's evidence, not decoration. If "Proved" is empty or
merely restates "Argued", the finding is not ready. Write the proved column first: file paths,
line numbers, counts you personally produced, commands that ran.

## 4. Did I run this against the target, or only against a clone?

State it plainly. Static analysis of a public repo is legitimate and valuable, but it is a
different claim than a live reproduction. Confusing them turns a defensible report into an
overstated one. Name the commit/clone as the evidence base when that is the base.

## 5. Does the honesty block survive reading aloud?

If any sentence would embarrass you when the vendor replies "we checked and that is by design,"
fix it now. Keep: what you did NOT do, no reward mention, no claims beyond the proved column.

## Ordering

Build PDF -> layout gate -> **this gate** -> only then stage the draft. Staging is the last step,
not a way to pressure-test findings. A staged draft to a real vendor address is near-irreversible;
re-staging is delete-then-append and a vendor may read it in between.

If the gate fails, the correct output to the operator is "not ready, here is the specific open
question" — not a draft.
