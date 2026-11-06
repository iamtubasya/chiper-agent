# When the video contradicts the written report

Making the video is often the first time the reproduction is executed *end to end, literally, in
order*. That is exactly when a written report's inaccuracy surfaces: a host that no longer works, a
step that was inferred rather than run, a claim about what the victim sees that nobody actually
looked at.

Real case (Todoist DCR, 2026-10): the report used `api.<target>/oauth/authorize` and stated the
victim is sent to the legitimate login page. The `302` was genuine and reproduced perfectly — but
the chain it started ended on a **404**, because the login SPA is only served from
`app.<target>` / the apex host. Nothing in the text was a lie; it just had never been checked past
the status code.

## Do not paper over it

The tempting move is to build a flattering video and leave the report alone. Don't. If a triager
reproduces the written steps and fails, a valid finding gets closed as Not Reproducible — the
report's accuracy is the thing being defended, not its tone.

## Produce three artifacts, together

### 1. The video, on the path that actually works

Use the host/steps that genuinely reproduce. Add an on-screen note only if the difference is
material to the viewer.

### 2. A corrected-steps file, ready to paste into the submission

Plain text, English, structured so the operator can replace the submitted reproduction data.
Include:

- A short **"WHAT CHANGED AND WHY"** section with a comparison table of old vs new behaviour.
- The full corrected reproduction, with the changed value flagged (e.g. `*** HOST CORRECTED ***`).
- A one-line statement of whether the **vulnerability** changed, or only the trigger. Usually it is
  only the trigger — say so explicitly, because that is what decides whether the finding still pays.
- The list of test artifacts to revoke, including anything created for the video.

### 3. A new PDF with the correction stated openly

Regenerate through the reportlab skill. Add a dedicated section, e.g.
`N. Correction to the previous submission`, containing:

- The comparison table (old chain → result, new chain → result).
- An explicit sentence: *"Impact of the correction: none on the vulnerability."* — or the honest
  opposite if the vulnerability really did weaken.
- The unchanged core evidence re-stated (the `201`, the missing auth gate, the working chain).

Keeping the correction visible is what makes the v2 credible. A silently edited v2 invites the
question "which version did you actually test?".

## Checklist before handing the set back

- [ ] Video, corrected steps, and PDF all describe the **same** commands and hosts.
- [ ] Every token that appears in the reproduction also appears in the PDF (`client_id`, exact URLs,
      error strings) — extract the PDF text and assert each one is present and not broken mid-word.
- [ ] The artifact created for the video is named in the revocation list.
- [ ] Anything the video asserts about the victim's experience was verified by rendering it, not by
      reading a status code.
- [ ] If the finding was already submitted, tell the operator plainly what to update and that a
      triager reproducing the old steps would fail. Let them decide; do not silently re-submit.

## Pitfall: narrow PDF table columns silently break tokens

A `Result` column too narrow for `invalid_client_metadata` renders it as `invalid_clien t_metadata`.
Cosmetic in appearance, corrosive in a report — it is a value the triager will grep for. After
generating, extract the PDF text and assert every technical token round-trips intact; widen the
column rather than shortening the token.
