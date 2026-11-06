---
name: reportlab-security-pdf
description: Use when generating PDF bug-bounty reports with reportlab.
---

# Reportlab Security PDF Generation

## RULE 0 (operator-mandated, applies to every disclosure deliverable)

**1 finding = 1 draft e-mail (its own thread/subject) + 1 PDF PoC ATTACHED to that
draft. Never combine two findings into one draft or one PDF, even when they share a
target or a root cause.** A combined draft is a rejected deliverable — the operator
has said this twice, verbatim: *"1 draft 1 temuan ... lengkapi dgn pdf poc"* and
*"kan sy udh blg 1 draft 1 email 1 poc"*. Build the pipeline so the rule is
structural: one findings store → a loop that emits one attachment + one draft per
entry, never a "tidy" bundle. Validate every finding 3x BEFORE drafting. Then keep
going — a new finding gets its own draft + its own PDF immediately, and the deepdive
continues until the surface is exhausted.

**The "secondary observation" trap — this is how the merge actually happens.** The rule
above is easy to agree with and still easy to break, because the violation does not look
like a merge at the time. What it looks like is a *section*: a report that is cleanly
single-finding through sections 1-7, and then closes with

```markdown
## 8. Secondary observation (same contract, lower impact)
```

and a second, unrelated root cause described inside it. Observed live 2026-10-08: a
reentrancy-guard finding (High) carried a dangling-`approve` finding (Low) as section 8
of the same PDF, justified as "same contract, weaker variant". The operator's own rule
has no such exception — **"same asset" is explicitly NOT a reason to merge, and neither
is "it is only a note".** By the time the section exists, the PDF is already a
two-finding deliverable and the draft is already a rejected deliverable.

Guard against it structurally, because you will feel reasonable while doing it:

- Before building, list the findings as separate ids. If the list has two entries, there
  are two PDFs and two drafts — **do not open the report with one and append the other**.
- Treat the words *secondary / related / also noticed / weaker variant / same contract* in
  a planned heading as a hard stop. Each phrase means "this is its own finding".
- If a second finding is too weak to stand alone, the honest move is to **drop it**, not
  to attach it to a stronger one. Padding a credible High report with a Low observation
  dilutes it and invites a downgrade of the whole submission.
- A genuine CHAIN is the only merge, and it is a *dependency* (`A` enables `B`, and the
  impact needs both), not co-location on one asset.

The concrete harness (store schema, the two thin scripts, the recurring-loop prompt,
the four verification gates) is in **`references/disclosure-draft-pipeline.md`**.
Read it before building a new engagement's pipeline rather than re-deriving it.

**When the operator's wording asks for ONE combined artefact** — e.g. *"masukkan f1-f3 jd draft
report"* — that phrasing collides with RULE 0. Do not silently pick a side. Build the literal
combined artefact they asked for **and** flag the conflict in one line of the hand-off (*"this is one
combined draft; say the word and I'll split it into N per-finding drafts + PDFs"*). Silently splitting
ignores a direct instruction; silently bundling is the deliverable the operator has rejected before.
Reserve the automatic N-way split for when *you* are choosing the shape — when the operator names the
shape, respect it and surface the rule. Bundling stays unacceptable for an unsolicited submission.

> Mechanics for running RULE 0 at engagement scale — the findings store → PDF per
> finding → one Gmail draft per finding with the PDF attached → read-back
> verification, how to make the drafts idempotent, how to drive it from a cron loop
> (and the schedule argument that silently turns a recurring loop into a one-shot),
> plus the harness-writing traps that bite: `references/per-finding-draft-pipeline.md`.

## STRENGTHENING PASS — the operator asks you to deepen findings you already staged

Operator request, 2026-10-11 (aekktn engagement), verbatim: *"kalau ada hal yg memperkuat temuan
diatas, kamu tambahkan k draft gmailnya, pastikan berdampak pada user, dana, sistem, dan keuangan"*.

Read that precisely, because it is **not** a request for new findings and **not** a request for new
drafts. It is: go find more evidence for the findings that exist, and fold it into the drafts already
staged — and the evidence has to land on one of the four impact axes the operator names.

**The four axes, and what counts as evidence for each.** The operator works in Indonesian; the axes are
his words and they are the triage language he wants the impact written in:

| axis | what proves it | example that landed (aekktn) |
|---|---|---|
| **user** (pengguna) | a named page/flow a real person uses breaks, or their data leaks | patient-facing on-call page (`bereitschaftsdienst`) returns 503 over IPv6 → a caller on an IPv6-only mobile link cannot get the doctor's number |
| **dana / keuangan** (money, finance) | the data or the control feeds a fraud/abuse chain with a value figure | 1 315 practitioners with 422 mobile numbers, obtainable in 1 request → the target list for invoice/callback fraud against practices |
| **sistem** (system) | the mechanism is broader than the one endpoint, or it changes what the server does | the token is skipped by the **whole RPC layer** (a second endpoint returns session state with no token), and the same layer answers a plain GET with a foreign `Origin` |

A strengthening claim that cannot be assigned to one of these is padding — drop it.

**Where it goes (never a new draft, never a merge):**

- New section **`4b. Supporting evidence`** after the existing "4. Observed result", containing the
  paste-ready transcript of the new proof.
- An added impact paragraph (`impact_extra`) after "5. Impact" when the new evidence is an argument
  rather than a command.
- If the new evidence reveals a *separate root cause*, it is a **new finding with its own draft and its
  own PDF** — RULE 0 is not suspended by a strengthening pass. (In this session the strengthening pass
  did surface genuinely new findings, and they were staged as their own drafts, not appended.)
- Update the boundary section if the new work narrows what is still unproven; a stronger report usually
  means a *smaller* honest gap, not a bigger claim.

**Method — hunt for impact evidence, never for volume.** The pattern that produced all of the above in
~30 minutes: (1) enumerate every route/host/verb of the surface already touched and diff their
behaviour; (2) take each finding's own endpoint and vary *how* it is called (GET vs POST, with/without
body, with a foreign `Origin`/`Referer`, alternate route spellings) — request-shape variation is what
turns "this endpoint has a bug" into "this layer has a bug"; (3) count the real-world objects the
finding touches (rows, numbers, pages, hosts) rather than describing them qualitatively.

**Bounded load measurement for an availability finding — do this and stop.** When the finding is a
per-request cost (a slow handler, a thread held open), the honest way to show it matters without
attacking a live public service:

```
probe a harmless GET on the same server  ->  BEFORE, DURING, AFTER
burst: N small concurrent requests (N=6), then stop
report: burst wall time, and the probe timings
```

Observed in this session: 6 concurrent rejected logins all completed in 16.0 s wall clock — i.e. served
in **parallel, not queued** — while the same-host probe held 0.82 s before / 0.85–0.90 s during / 0.85 s
after. Two things that make this defensible: state the total extra load in the report (*"6 requests +
5 GETs, less than one browser loading the page"*), and say plainly that you stopped deliberately because
locating the exhaustion threshold means degrading a live service. **Never** escalate to finding the
threshold. If the site had degraded, the write-up changes from "per-request cost" to "I broke it", which
is a different and much worse deliverable.

**Close the loop — a strengthened PDF is a CHANGED PDF, so the draft is now stale.** Per finding:
rebuild → `pdf_layout_check.py --tokens` must be `problems=0` → re-run the entity / literal-markup /
non-English scans → **re-stage the draft** → verify attachment `%PDF-` + sha256 against the local file.
Then re-count drafts and assert one per subject (rule 17). Full recipe with the evidence transcripts:
`references/strengthening-an-existing-finding.md`.

Proven workflow for building triager-ready PDFs (Bugcrowd/H1 style) that survive review feedback. Each lesson below came from an actual delivery whose reviewer/user rejected the first draft — fix them BEFORE generating, then VERIFY after.

## Hard rules (violating any of these caused rework)

1. **Escape `&` in every Paragraph/Table string.** reportlab treats `&` as the start of an HTML entity: `&startDate=2026` renders as `&startDate;=2026` in the PDF. Curl/repro URLs become un-copy-pasteable and reviewers fail reproduction.

   **CORRECTION (2026-10-15): this rule applies to `Paragraph`/`Table` cells only — never to `Preformatted` code blocks.** `Preformatted` renders its text literally, with no XML/entity pass, so `esc()`-ing code makes the PDF print `&lt;` `&gt;` `&amp;amp;` where the code says `<` `>` `&&` (caught by `pdf_layout_check.py` as `RAW ENTITY`, and it is your escaping, not a leak — do not "fix" it by escaping harder). In `scripts/md_to_report_pdf.py` the code branch therefore calls `Preformatted("\n".join(wrapped), CODE)` with raw text, while `build_story`'s table cells go through `inline()` → `esc()`. Entities belong only in strings that skip `esc()`.
   ```python
   def esc(s):
       return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
   # use esc() on EVERYTHING passed to Paragraph / Table cells
   # for code blocks use a dedicated code_para() that builds Paragraph(esc(text), CodeStyle)
   ```
   VERIFY after build (see below) — `re.findall(r'&[a-zA-Z]+;', full_text)` must be empty.

   **Two-way trap when your `tbl()` helper auto-escapes.** If `tbl()` calls `esc()` on plain-string
   cells, then a cell that needs **markup** (`<b>`, `<font>`) must be passed as a ready `Paragraph`
   object instead (the helper can detect this with `hasattr(c, "wrap")`), or the tags render
   literally. And a cell whose *text* contains an HTML entity (`&lt;empty&gt;`, `&lt;tenant&gt;`) gets
   double-escaped into a visible `&lt;` — write the literal `<` `>` in that cell and let `esc()` do
   the conversion. Both defects survive a visual read and are caught only by the geometry checker's
   `RAW ENTITY` check (this session: 2 problems, both this class). Conversely, `Paragraph(...)`
   strings that are NOT passed through `esc()` — narrative prose, code blocks built by hand — must
   keep their entities as-is. Rule of thumb: **entities belong only in strings that skip `esc()`;
   everything else gets raw `<` `>` `&`.**

2. **No watermark.** User requirement for this user's reports. Pillow screenshot style from the reference generator includes a "Reporter @ Bugcrowd | Timestamp" watermark footer — remove it. Keep evidence authentic, not decorated.

3. **Single-source-of-truth constants.** Define ALL target values (endpoints, IDs, cookies, dates, prices) as Python constants at the top of ONE generator script; drive PDF text, code blocks, AND screenshots from the same constants. Never hardcode different values in different generators — triagers catch mismatches instantly.

4. **Mandatory report metadata.** Include in the header meta table (and fill into the Bugcrowd form):
   - Date/time found + timezone (e.g. `2026-09-27 17:37–18:37 (UTC+07:00 / Asia/Jakarta)`) — many VDP programs (RACV) REQUIRE this.
   - IP address used when found (check via `curl api.ipify.org` + `ip-api.com/json`).
   - Researcher name (for this user: **Mr Fz** — see user memory).

5. **Severity honesty built-in.** Include an explicit severity-justification table with "What I proved" vs "What I argue (not proven)" and a "Scope honesty / appeal foundation" paragraph. If triager downgrades, that paragraph is the appeal basis. Also state the manual CVSS math (Impact/Exploitability → score) so the number isn't just asserted.

6. **Wrap EVERY table cell in `Paragraph` — never pass a raw string.** This is the #1 cause of the overlap defect the user calls *"tulisan tertimpa"* (text printed on top of itself / running off the page). A raw `str` in a `Table` does NOT word-wrap: a long value (a URL, a hostname list, `400 INVALID_ARGUMENT — "API key not valid"`) overflows its column and physically leaves the paper (measured at x1=594.8pt on a 595.3pt-wide A4 page). It reads as struck-through/collided text in any viewer that clips at the frame.
   ```python
   CELL   = ParagraphStyle("CELL", fontName="Helvetica", fontSize=8.3, leading=10.6, alignment=TA_LEFT)
   CELL_H = ParagraphStyle("CELLH", parent=CELL, fontName="Helvetica-Bold")
   def tbl(rows, widths, head=True, fs=8.3):
       cs = ParagraphStyle("cellx", parent=CELL,   fontSize=fs, leading=fs*1.28)
       hs = ParagraphStyle("cellh", parent=CELL_H, fontSize=fs, leading=fs*1.28)
       # esc() HERE, inside the helper. See the warning below — this is the one place the
       # escaping is easy to forget, and forgetting it silently corrupts every URL in a table.
       wrapped = [[ (c if hasattr(c, "wrap") else
                     Paragraph(esc(str(c)).replace("\n", "<br/>"), hs if (head and ri == 0) else cs))
                    for c in row] for ri, row in enumerate(rows)]
       # colWidths are POINTS in reportlab: a bare millimetre-number list gives microscopic columns.
    t = Table(wrapped, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0, hAlign="LEFT")
       # ... GRID / VALIGN TOP / padding only — do NOT add ("FONTSIZE", ...): it is ignored
       #     once cells are Paragraphs, and misleads you into thinking sizes are applied.
       return t
   ```
   **The `tbl()` helper must call `esc()` itself.** A helper that does
   `Paragraph(str(c), style)` looks harmless and passes every visual review, but every `&` in a
   table cell then reaches reportlab unescaped — and reportlab appends the missing `;`, so
   `/download?blobId={blobId}&name={name}` renders on the page as
   `...&blobId={blobId}&name;={name}`. It is not visible in a screenshot and not visible in a
   page count; it is caught only by the `&[a-zA-Z]+;` scan in the verification script, so **run
   that scan on every build**. Curl/repro/endpoint-map cells are exactly where the `&`s live.
   **The `hasattr(c, "wrap")` escape hatch is a two-edged sword:** a pre-built `Paragraph` cell
   bypasses `esc()`, which is what you want for a cell that needs markup
   (`Paragraph("<b>control</b> AIza…", SMALL)`) and a silent injection risk otherwise. Rule of
   thumb: strings go in raw and get escaped; only cells that genuinely need `<b>`/`<font>` become
   `Paragraph` objects, and those cells must `esc()` their own data by hand.
   Also wrap key/value cells: `[Paragraph(k, KEY), Paragraph(v, SMALL)]`. Passing a *style object* where text belongs (e.g. `P("x", SMALL)`) raises `'Paragraph' object has no attribute 'name'` — use the style directly.
   **The wrapper and escaping must agree — decide per cell.** Symptom seen in a shipped report: a
   cell holding `/download?blobId={blobId}&name={name}&accountId={accountId}` rendered as
   `/download?blobId={blobId}&name;={name}&accountId;={accountId}`, because the local `tbl()`
   wrapper built `Paragraph(str(c))` and never ran the module-level `esc()`. `pdf_layout_check.py`
   reports it as `RAW ENTITY &accountId; present in rendered text` — that check is why you always
   run it before delivering. Fix in the wrapper once:

   ```python
   wrapped = [[(c if hasattr(c, "wrap") else
                Paragraph(esc(str(c)).replace("\n", "<br/>"), hs if (head and ri == 0) else cs))
               for c in row] for ri, row in enumerate(rows)]
   ```

   **Follow-on trap:** once the wrapper escapes, every cell that intentionally used markup
   (`<b>bold</b>`) renders the tags literally. Pass those as **pre-built `Paragraph` objects** —
   the `hasattr(c, "wrap")` branch exists for exactly that, so a single row can mix both safely:

   ```python
   [Paragraph("403: <b>(gate passed)</b>", SMALL), "plain text cell"]   # markup cell + escaped cell
   ```
   Apply the same rule to every `KV()`-style helper. Note: unlike rule 1 (`&` escaping), HTML entities like `&mdash;` / `&ldquo;` ARE safe inside `Paragraph` — they are parsed. They are NOT safe on a canvas (rule 7).

7. **Canvas header/footer draws plain text — no HTML entities.** `canvas.drawString` does not parse markup, so `header_left="Atmail Bug Bounty &mdash; Finding 2"` prints the literal string `&mdash;` in the running header. Use ASCII/unicode escapes instead: `"Atmail Bug Bounty Program: Finding 1"` or `"\u2014"`. Same for the footer string. (Text-layer checks for `&[a-zA-Z]+;` catch this only if you scan the *rendered* PDF, so put it in the verify script — see below.)

8. **One finding per PDF.** This user requires a separate PDF per finding, not one combined document. Build a shared style module (`att_style.py`: palette, styles, `tbl()`, `kv()`, `C()`, `B()`, `KT()`, `make_docs()`) and one small generator per finding that imports it. Share the module, never the story list.

   **The same applies to the delivery: 1 finding = 1 PDF = 1 draft = 1 email = 1 PoC.** Do not bundle
   twelve findings into one email with one combined PDF "to keep it tidy" — the operator rejected that
   (2026-10-04: *"perbaiki draftnya dulu, kan sy udh blg 1 draft 1 email 1 poc"*). Stage N separate
   drafts, each carrying its own PDF attachment, and give every attachment a finding-scoped filename
   (`TrustLend-TL-07-Medium.pdf`) so nothing gets mismatched.

   **The count is irrelevant — even TWO findings on the same asset are two drafts.** A later session
   combined two low-severity disclosure findings (same product, same evidence bundle) into a single
   draft and the operator rejected it again (*"kalau buat draft email, itu 1 draft 1 temuan dan lengkapi
   dgn pdf poc"*, 2026-10). "They are the same class of bug / the same asset" is NOT a reason to merge.
   Two findings → two drafts → two attached PDFs. When in doubt, split. The generator should loop a shared
   findings list to emit all N, so the story and the attachment can never diverge.

   **The single exception — a genuine CHAIN — restated by the operator 2026-10-07:** *"pastikan 1
   temuan 1 draft lengkap dgn poc, jgn gabung temuan dalam satu draft email kecuali ada kaitan dgn
   chain attack."* So the rule is now: **default = 1 draft per finding; group ONLY when the findings
   are dependent links of ONE chain** — B needs A, and the final impact (C/I/A/ATO/RCE) is reachable
   only through that sequence. Legal: `open-redirect + OAuth misconfig → ATO` as a single draft
   ("chain" in the subject, body walking A→B→C, one PDF PoC recording the whole chain). Illegal:
   three unrelated IDORs at three endpoints = **three separate drafts**. Anything not part of the
   chain stays in its own draft. Do not treat "related topic" or "same target" as a chain — only
   demonstrated dependency counts.

9. **A PDF whose PoC is one line of "ok" is not evidence — make the PoC print the values.** The
   operator's follow-up on the same engagement was *"perbaiki pocnya supaya menjelaskan detail
   langkah2 reproduksi nya, jgn hanya keterangan singkat, lengkapi dgn ss evidence"*. Two changes
   cover it: (a) the PoC itself prints the exploited values (balances before/after, the stored
   record, the counter that got zeroed) so the transcript is self-explaining; (b) the PDF embeds a
   rendered screenshot of that transcript (see the Pillow section below). A finding's PDF then reads
   3 pages: summary, impact, asset **plus vulnerable-code excerpt**, root cause, environment,
   numbered reproduction steps, expected/observed output, **the screenshot**, impact boundary,
   remediation, references.

9. **No orphan headings.** A section heading landing as the last flowable on a page (content spilled to the next page) is a defect. Set `keepWithNext=True` on every heading style, and wrap short whole sections in `KeepTogether([...])`. `keepWithNext` alone does not bind a heading to a *list of bullets* — wrapping the section is what actually fixes it. Verify by scanning the last body block per page for a heading pattern (script below).

    **Two ORPHAN HEADING reports that are self-inflicted, not layout bugs — both hit on a live
    multi-finding build, and both are checker-signature problems:**
    - **A numbered list matches the heading pattern.** The checker matches the last body block
      against `^\d{1,2}\.\s+\S`, so a remediation list emitted as `1. … 2. … 3. … 4. …` trips it
      whenever item 4 lands last on a page (observed: `p2 ORPHAN HEADING '4. Publish MTA-STS +
      TLS-RPT to protect the transport as wel'`). `keepWithNext` does not help, and a
      `KeepTogether` around the *items only* does not help. Fix the marker shape: emit
      remediation / step items as `(1) … (2) …` — the regex stops matching and the checker
      returns `problems=0`.
    - **`KeepTogether` must contain the HEADING, not just its content.** `A(Paragraph("6.
      References", H2))` followed by `A(KeepTogether(refs))` still orphans the heading: the
      heading is its own flowable and `keepWithNext` binds it only to the next flowable, which
      can be the page break. Put the heading inside the group —
      `A(KeepTogether([Paragraph("6. References", H2)] + refs))` — and do the same for every
      short section (remediation, references).
    Both leave the document visually correct. Fix the source, never relax the checker — the
    checker is what catches the real overlap defects.

    **Two refinements from a live build (2026-10, CISO360AI) — both cost a rebuild cycle:**

    - **The orphan rule false-positives on numbered prose.** `pdf_layout_check.py` flags any *last body block on a page* matching `^\d{1,2}\.\s+\S`. So a numbered remediation list whose final line is `4. Publish MTA-STS ...` is reported as `ORPHAN HEADING` even though it is ordinary body text. Do **not** chase it by shoving content around — that just moves which item lands last. Change the in-body list marker to `(1)`, `(2)`, … so the block stops matching the heading pattern. Keep the real section headings numbered (`1. Summary`) — only the in-body lists need to differ.
    - **Put the heading INSIDE the `KeepTogether`, not beside it.** `KeepTogether([Paragraph("5. Remediation", H2), *items])` is what actually binds the two. A heading left outside as its own `Paragraph(..., keepWithNext=True)` still orphaned on the live build — the heading sat alone at the bottom of page 2 with its content stranded on page 3. The checker caught it both times; a visual read would not have.

10. **Constant quotation/typography.** Don't mix en-dash in code comments, em-dash in prose, and a raw entity in the header. Normalise on one convention per document; it is the same root cause as rule 7.

    **Concrete fix for the `esc()`'d paths.** In any string that goes through `esc()` — every
    table cell, every `kv()` value — an HTML entity gets DOUBLE-escaped (`&` → `&amp;`) and
    renders as literal text; the geometry checker reports it as `RAW ENTITY &mdash; present in
    rendered text`. Use the raw Unicode character there instead; reportlab passes Unicode
    straight through:

    | entity | write instead |
    |---|---|
    | `&mdash;` / `&ndash;` | `—` U+2014 / `–` U+2013 |
    | `&lsquo;` / `&rsquo;` | `‘` / `’` U+2018 / U+2019 |
    | `&ldquo;` / `&rdquo;` | `“` / `”` |
    | `&hellip;` | `…` U+2026 |
    | `&rarr;` | `→` U+2192 |
    | `&middot;` | `·` U+00B7 |
    | `&bull;` | `•` U+2022 |

    Exception — entities you inject AFTER escaping, or markup you intend reportlab to parse,
    must stay as they are: `code()` appending `&nbsp;` for indentation, and `<br/>` / `<b>` /
    `<font>` tags. Cheapest pre-build sweep: `grep -nE '&[a-zA-Z]+;' gen_*.py` and check which
    hits sit inside an `esc()`d argument (a hit inside a hand-built `Paragraph(...)` is fine).
    Note the reportlab-side trap this creates: `&gt;` inside a hand-built `Paragraph` renders
    `>`, but the same `&gt;` inside an `esc()`d cell renders the literal `&gt;`.

11. **Vendor-facing documents are ENGLISH — including every string that is not body prose.** This
    operator's working notes, briefs and evidence files are Indonesian and that is expected; nothing
    that leaves the machine for a target/vendor is. That covers the PDF title, running header/footer,
    the email subject, the email body and the attachment filename — all of them, in the same language.
    The observed failure: a fully English body shipped with an **Indonesian subject and PDF**, because
    the internal-language filename was reused as the subject and the PDF had been drafted with the
    internal heading conventions. Derive the subject from the deliverable first and name the file after
    it; keep any internal-language copy under an `_INTERNAL_id_` prefix so it cannot be attached by
    accident; and add the language check to the same post-build pass as the entity scan —
    `re.search(r"\b(yang|tidak|adalah|dengan|untuk|pajak)\b", text, re.I)` must be `None` on the
    rendered PDF text, and re-check every staged draft's subject/body the same way.

12. **A disclosure e-mail OPENS WITH AN INTRODUCTION — the operator rejected a draft that went straight
    into the technical content** (*"draft email nya tidak ada perkenalan, lengkapi dulu"*, 2026-10-03).
    A technically complete body is still a rejected deliverable. Required shape, in this order:

    1. Greeting + **who is writing**: name, "independent security researcher", and the channel
       ("I am writing to you through your Responsible Disclosure Program", with its URL).
    2. **Context**: how it was found (assessment of the in-scope asset), that only the operator's own
       test account/data was used, and that nothing is published before remediation.
    3. **"In short:"** — two or three sentences of the issue in plain language, *before* any numbered
       section. The reader must be able to triage from the first screen.
    4. The numbered technical sections (summary, affected asset, root cause, reproduction, evidence,
       impact, remediation).
    5. A closing that offers the reproduction scripts / exact values / a walkthrough, states the
       confidentiality commitment, then signature and contact address.

    The attached PDF does not replace this — the e-mail body must stand alone, because some triage
    queues read the body before they open an attachment.

    **Two additions to that shape, both from an operator rejection (2026-10-12).** Verbatim:
    *"kamu perkenalan, terus jelaskan temuannya, tutup dgn sopan, tanpa tanya reward, kasih nama saya …
    pakai skill humanizer"*. So: (a) the body **never asks for a reward** — no bounty, credit,
    Hall-of-Fame or swag mention anywhere, the programme handles that; (b) the signature is the
    operator's **real name** (this operator: RESEARCHER_NAME, RESEARCHER_EMAIL), not a handle and not
    a bare "researcher".

    **Never ship the staging script's default body.** A generator that still carries a generic stub
    ("Hi, / Findings attached…") produces a rejected deliverable even when the PDF is perfect and every
    verification passed. Fix the *generator*, not just the prose rule: `bug-report-delivery` now makes
    `--body` a required argument and refuses to stage a body missing the intro/channel/signature
    markers, or containing a reward word or an AI-ism. Skeleton to copy:
    `bug-report-delivery/templates/disclosure-email-body.md`. Generalises — when the operator corrects
    an *output shape*, embed the correction in the default the tool falls back to; a rule the agent can
    forget will be forgotten, a required argument it cannot omit will not be.

    **The body has ONE required shape, and the default stub from `stage_finding_draft.py` is NOT it.**
    Operator correction, 2026-10-12, verbatim: *"kamu perkenalan, terus jelaskan temuannya, tutup dgn
    sopan, tanpa tanya reward, kasih nama saya … jgn lupa pdf pocnya yg lengkap dan rapi, pakai skill
    humanizer"*. Staging with the script's generic body ("Hi, / Findings attached. / … / RESEARCHER_NAME
    Susanto") is a rejected deliverable even when the PDF is perfect. Required order:

    1. greeting, who you are, and the channel: "My name is <operator's real name>. I am an independent
       security researcher, and I am sending this report through your responsible disclosure programme
       at <policy URL>."
    2. what you found, with the exact command and the exact value it returned.
    3. an explicit sentence that nothing was changed and the report is not shared with anyone else.
    4. a polite close offering the raw evidence / a walkthrough / to retest a fix, then the operator's
       **real name and contact address** as the signature.

    Hard bans in the body: no reward, bounty, credit or Hall-of-Fame request; no "I hope this helps";
    no placeholder identity. Pass every body through the `humanizer` skill and assert it mechanically
    before staging — `[t for t in ["\u2014","\u2013","delve","pivotal","leverage","seamless"] if t in body] == []`.
    **Run the banned-word list against the body with the program's own URLs removed first.** A scanner over
    the raw body flags `bounty` inside the policy URL every time (`…/en/bounty-terms`), and a naive fix
    (dropping the channel sentence) removes the very reference the introduction is required to carry. Strip
    URLs before the assertion — `scan = re.sub(r"https?://\\S+", "<url>", body)` — then require the intro's
    channel sentence separately (`"responsible disclosure programme" in flat`). Same rule for `credit`
    (matches "credits" in a product name) and `reward` (matches "rewarding"): scope the check to
    *request-shaped* phrasing, not the substring.
    The signature is the operator's real name (this engagement: **RESEARCHER_NAME**, RESEARCHER_EMAIL),
    never a handle and never the word "researcher" on its own.

    **The reward gate must scan a URL-STRIPPED copy with WORD BOUNDARIES — the naive substring version
    rejects the most common correct body (false positive caught 2026-10-13).** Bare `in body.lower()`
    matching made the gate fire on the program's own policy URL:

    ```
    BODY REJECTED (rule 0c) — banned tokens: ['bounty', 'swag']
    # ...the "bounty" was inside https://public-jsmd.s3.eu-central-1.amazonaws.com/Bug-Bounty-Policy-1.3.pdf
    # ...and "swag" was inside the product name "Swagger UI"
    ```

    Strip URLs first, then match whole words:

    ```python
    scan = re.sub(r"https?://\S+", " ", body.lower())
    reward = [t for t in ("bug bounty", "bounty", "reward", "hall of fame", "swag", "credit")
              if re.search(r"\b" + re.escape(t) + r"\b", scan)]
    ```

    Then re-run the same check over every body already written — it must come back `NONE` on all of them.
    When a gate rejects your own correct work, **fix the gate and validate the fix**; do not anonymise the
    policy citation to appease it. A gate that forces you to delete the program's own URL is broken, and
    leaving it broken costs the next session the same detour.

13. **Attach the PoC PDF to the staged draft, and verify the ATTACHMENT — not just the body.**
    (2026-10-03: an operator asked for the PoC as a PDF and it had to be attached to the *existing*
    draft, so staging must be repeatable.)

    **A read-back that checks the attachment but NOT the recipient is incomplete.** The verification
    list for every staged draft must include `To:` (see rule 13's sibling note above) alongside
    filename, `%PDF-` magic, sha256 and size — the operator caught a correct-attachment /
    empty-recipient draft that had passed all four attachment checks.

    - Add one sentence to the body pointing at the attachment ("The full proof of concept, with
      reproduction steps, evidence and impact, is attached as a PDF."). The operator noticed when it
      was missing; the body must not silently omit the deliverable it is covering.
    - Stage as `multipart/mixed`: `msg.set_content(body)` then
      `msg.add_attachment(pdf.read_bytes(), maintype="application", subtype="pdf", filename=pdf.name)`.
      Attachment filename in English (rule 11).
    - **Read the draft back** and compare `sha256(attached bytes)` against the local file, and assert the
      attachment begins with `%PDF-`. Equal sizes are not enough; a `%PDF-` magic check plus hash equality
      is the cheap pair that catches a stale attachment.
    - ⛔ **`stage_finding_draft.py` REBUILDS the PDF with its own `build_pdf()`, and that builder has no image
      support — a finding whose PoC needs the rendered screenshot silently ships WITHOUT it.** Measured
      2026-10-14 (Yandex DocViewer SSRF): the PDF built by `md_to_report_pdf.py` was 5 pages / 1 embedded image /
      166 052 B; the draft the staging script created carried 3 pages / **0 images** / 8 426 B. Every check the
      script itself prints still passed, because it compares the attachment to its own rebuild (magic `%PDF-`
      yes, hash "match" yes, `To:` and subject correct). The failure is invisible unless you look for pixels.
      Gate before calling a draft staged: `sum(len(p.images) for p in PdfReader(local).pages)` and
      `... for p in PdfReader(attached).pages` must be **equal and non-zero** when the report has a figure
      (`![Figure 1 …](evidence.png)`), and the page counts must match too. When they differ, **stage the draft
      on the Gmail REST path yourself** (build the raw MIME with `EmailMessage` + `Message-ID`/`Date`, attach your
      own PDF, `drafts().create`, then `?format=raw` read-back) so the file you verified is the file that travels.
      Corollary: reading back through the staging script proves the script is self-consistent, not that the
      deliverable is the one you built — always anchor the comparison to the **local** PDF's bytes and image count.
    - **Two readback traps that both look like a passing verification.**
      (a) `email.message_from_bytes(...)` returns an `email.message.Message`, **not** an `EmailMessage`,
      so `msg.get_body(...)` raises `AttributeError: 'Message' object has no attribute 'get_body'`.
      Walk the parts instead:
      ```python
      body = ""
      for part in got.walk():
          if part.get_content_type() == "text/plain" and not part.get_filename():
              body = part.get_payload(decode=True).decode("utf-8", "replace")
      ```
      (b) The body is **hard-wrapped** (~95 cols), so a phrase assertion silently fails when the phrase
      straddles a line break — e.g. `"accounts and data I created myself"` came back `FAIL` on a body that
      contains it verbatim. Collapse whitespace first and run every phrase check on that:
      ```python
      flat = " ".join(body.split())
      assert "accounts and data I created myself" in flat
      ```
      Report the readback as a per-check `OK/FAIL` list (greeting, intro, VRT path, attachment mention,
      signature, english-only, no placeholders) rather than one aggregate — the single-aggregate version
      hid which assertion failed and cost a re-run.
    - **A transient `imaplib` failure is a retry, not a verdict.** Connecting to `imap.gmail.com` a few
      times in quick succession returned `imaplib.IMAP4.abort: socket error: EOF`. Wrap login in a small
      retry loop (4 attempts, ~20 s apart) before concluding anything about the mailbox.
    - **Two traps inside the read-back step itself** (both hit 2026-10, Octopus engagement):
      (a) `email.message_from_bytes()` returns a `Message`, which has **no `.get_body()`** — calling it
      raises `AttributeError`. Walk the parts yourself:
      `for part in m.walk(): if part.get_content_type() == "text/plain" and not part.get_filename():`
      (b) the body is **hard-wrapped at ~95 chars**, so a phrase assertion like
      `"accounts and data I created myself" in txt` returns a **false FAIL** when the phrase straddles a
      wrap. Collapse whitespace first — `flat = " ".join(txt.split())` — and run every body check against
      `flat`; keep `txt` only for the character count. Otherwise you will "fix" a draft that was correct.
    - `IMAP4_SSL(...).append()` can raise `socket error: EOF` from Gmail when several logins happen
      back-to-back (stage → verify → re-verify). Wrap the connect in a small retry with a delay instead of
      treating it as a failed draft.
    - A staged draft with an **empty `To:` is a FALLBACK, not the default** — and the operator rejects it
      as one. Before leaving `To:` empty, go and look for a published address on the program's own page;
      a "web-form" program almost always also publishes a `mailto:`. **Correction from the operator
      (2026-10-08), verbatim: *"alamat email tujuannya mana, gkad d draft nya"*** — a draft was staged
      with an empty `To:` because the brief pointed at a Google Form, while the same brief page carried
      `support@<domain>` in its security section. The operator does not read an unsent draft with no
      recipient as "paste-ready"; he reads it as unfinished.
      ```bash
      curl -sL "<program-page>" | grep -oiE "(mailto:[^\"'<>) ]+|[a-zA-Z0-9._%+-]+@<domain>)" | sort -u
      ```
      Set `To:` to that address and keep the form URL in the BODY as the alternate channel — both
      channels are real and saying so costs one line. Only leave `To:` empty when the page genuinely
      publishes no address (a pure Bugcrowd/H1 web submission), and then say so explicitly in the
      hand-over.
    - Rebuild-and-replace (delete the old draft, append the new) whenever the PDF changes: a fixed build is
      a different byte size (16002 -> 16016 B in the session that found this).
    - **Stage idempotently from a KEYED state file, and self-heal by subject.** Keep one JSON state
      file mapping `finding-id -> {draft_id, subject, to, attachment}` and upsert per id, so re-running
      the whole batch updates drafts *in place* instead of appending duplicates. Two failure modes this
      fixes, both seen live: (a) if the state file is ever lost or rewritten, a blind upsert mints a
      **second** draft for every finding — so before creating, look the subject up
      (`drafts().list(userId="me", q='subject:"<exact subject>"')`) and ADOPT the existing draft id;
      (b) an autonomous loop that re-runs on a schedule otherwise accumulates duplicates silently.
      Print one line per finding on write —
      `[F1] draft=<id> att=<name> bytes=<n> magic=True hash=True` — so a partial run is visible in the
      transcript instead of inferred.
    - **"One finding = one draft + one PDF" is a structural property, not a habit.** Drive the batch from
      the findings store and have the renderer SKIP severities the operator excludes (e.g. skip INFO
      entirely, logging it only as a coverage note), so the rule cannot be broken by hand. The same loop
      emits one PDF per finding and attaches each to its own draft.
    - **When a scheduled loop feeds this pipeline:** a generic `schedule: '15m'`-style value can be read
      as a ONE-SHOT — the job runs once and reports `state=completed`. For a recurring autonomous audit
      pass, give an explicit cron expression (`*/15 * * * *`) and check the created job's
      `schedule`/`repeat` fields in the response before trusting it.

14. **A literal ampersand in a hand-built `Paragraph` needs `&amp;`.** `tbl()` escapes cells for you;
    `P()` / hand-built narrative paragraphs do **not**. Session case: the prose cell
    "the key SHARED_SECRET&CLIENT_SECRET" rendered as `SHARED_SECRET&CLIENT;` — reportlab appended the
    missing semicolon — and it was the *only* defect the validator found (the `&[a-zA-Z]+;` scan).
    It is invisible in a visual read, so treat it as the expected first failure on any new generator:
    write `&amp;` in hand-built strings, rebuild, re-run the scan until it reports `NONE`.

15. **Check the program's accepted report FORMAT before attaching anything, and render a PNG
    supplement when PDFs are rejected.** Some briefs state it outright: *"Reports must be PLAIN TEXT
    (images/videos ok as supplement). PDF/DOCX → rejected."* In that case the plain-text body **is**
    the submission and the PDF is only an internal record — attaching the PDF as the deliverable
    risks rejection for format, not for content. Produce per-page PNGs of the same PDF, which is the
    artifact such a program explicitly accepts, and state in the handoff which file goes where:

    ```python
    import pymupdf                      # NOT pdf2image - see Tooling notes
    doc = pymupdf.open(pdf_path)
    for i, page in enumerate(doc, 1):
        page.get_pixmap(dpi=150).save(f"{pdf_path.stem}-p{i}.png")   # A4 @150dpi = 1241x1754
    ```

    Sanity-check the renders by file size spread (a uniform-size set or a near-zero page means a
    blank render); do not use a vision model to QA them (see the geometry section).

16. **Draft read-back has three traps — all three produced a FALSE failure in one session.**
    Verifying a staged IMAP draft is mandatory (rule 13), but the verification script itself lies if
    written naively:
    - **`email.message_from_bytes` returns `Message`, not `EmailMessage`.** Calling
      `m.get_body(preferencelist=("plain",))` on it raises
      `AttributeError: 'Message' object has no attribute 'get_body'`. Walk the parts instead:
      `next(p for p in m.walk() if p.get_content_type()=="text/plain" and not p.get_filename())`.
    - **Collapse whitespace before phrase assertions.** A body wrapped at ~95 columns splits
      `"accounts and data I created myself"` across a newline, so a literal `in` test reports FAIL on
      a complete body. Assert against `" ".join(txt.split())`, not `txt`.
    - **IMAP throttling on rapid repeat logins.** Several back-to-back `IMAP4_SSL` login/logout
      cycles returned `imaplib.IMAP4.abort: socket error: EOF`. Wrap connect+login in a retry with a
      ~20 s backoff; do not conclude the mailbox is unreachable, and do not re-`append` (rule 13's
      replace-not-append exists for exactly this).
    Also verify the body carries what the program needs, not just that it exists: an external
    submission body must open with an introduction (rule 12), name the channel/program, and — when
    the platform rates by taxonomy — carry the category path, variant and default priority verbatim.

17. **Gmail draft mechanics — three traps that each look like a failed delivery.**

    - **`drafts().update()` can return `"Message not a draft"` (HTTP 400).** That means
      the id you stored is a *message* id, not a *draft* id — it happens when one code
      path records `messages().send/get` output into the same state file the draft path
      reads. Catch the 400 and fall through to `drafts().create()`, then write the new
      draft id back. Only ever persist the `id` returned by `drafts().create()/update()`.
    - **`format="metadata"` does NOT expose attachment parts.** Auditing a draft with
      `drafts().get(format="metadata")` and counting `payload.parts[].filename` returns
      **0** for a draft that genuinely carries the PDF — it reads as "attachment missing"
      and sends you chasing a non-bug. Attachment presence is only visible on
      **`format="raw"`**: base64-decode `message.raw`, walk the parts, compare
      `sha256(part.get_payload(decode=True))` against the local file, and check the
      `%PDF-` magic. That raw check is authoritative; use metadata for subjects only.
    - **Do not mix the two shapes.** `format="raw"` + `email.message_from_bytes()` is
      correct, but the result is a `Message` with no `.get_body()`.

    **State-loss self-heal (required for any multi-draft pipeline).** Before creating a
    draft, query the mailbox for one already carrying the same subject and adopt its id:

    ```python
    if not did:
        found = svc.users().drafts().list(
            userId="me", q=f'subject:"{subject}"', maxResults=5).execute()
        for cand in found.get("drafts", []):
            did = cand["id"]; break
    ```

    Without this, a single state reset silently mints a duplicate draft for every
    finding — and because both copies look correct, nobody notices.

    **After EVERY batch, count the drafts in the mailbox — do not trust per-finding ids.**
    The self-heal above is not sufficient on its own: observed 2026-10-08, a re-stage after the
    PDF changed reported `[F1] created` / `[F2] created` (not `replaced`), because the stored
    draft ids no longer resolved and the code correctly fell through to `drafts().create()`.
    Each individual write looked right; the *folder* was the thing that was wrong. Enumerate
    and assert the count, then also confirm no OTHER draft shares the subject:

    ```python
    all_d = svc.users().drafts().list(userId="me", maxResults=100).execute()
    n = len(all_d.get("drafts", []))                  # record this BEFORE and AFTER
    # per-finding: list by exact subject, assert exactly ONE id per finding
    for subj in SUBJECTS:
        hits = svc.users().drafts().list(
            userId="me", q=f'subject:"{subj}"', maxResults=25).execute().get("drafts", [])
        assert len(hits) == 1, f"{len(hits)} drafts share the subject: {subj}"
    ```

    Read each hit's `?format=raw` attachment size and keep the copy matching the CURRENT local
    file; delete the stale draft ids explicitly (`DELETE /drafts/<id>`). Two further notes:
    - **The mailbox is shared.** The operator's own drafts live in the same folder — scope every
      list/delete to your own subjects. A blanket "delete everything in Drafts" is never correct.
    - **Report the count in the handoff** (`N findings → N drafts`), not just the ids. `N` is the
      number that proves RULE 0 held; the ids only prove the files exist.

18. **Never name an audit helper after a Python stdlib module.** A file called
    `selectors.py` sitting next to the generator shadows the stdlib `selectors` module,
    so an unrelated script in the same directory dies with a stack trace that points at
    *its own* `import asyncio` — because `asyncio` imports `selectors`. The failure looks
    like a broken dependency, not a naming collision. Rename to something scoped
    (`dep_selectors.py`) and re-run. Same trap applies to `types.py`, `queue.py`,
    `token.py`, `code.py`, `test.py`, `json.py`, `email.py` and friends.

19. **If the program's policy requires PGP-encrypted submissions, encrypt the submission — don't send a plaintext PDF.** Read the policy text before staging; a sentence like *"please use our PGP public key to encrypt any email submissions"* changes the deliverable shape: encrypt the report body + its PDF into an ASCII-armored `.asc` and attach that, with a plaintext cover note (greeting, policy URL, their key fingerprint, "encrypted submission attached", signature — no vuln detail). The PDF therefore rides inside the encrypted payload, not as a `.pdf` attachment; say so in the hand-off. Full flow (armor-rebuild traps, MSYS `GNUPGHOME`, recipient-subkey check, stage-new-then-delete-old) in `references/pgp-encrypted-submission.md`.

### The `?rest_route=` bypass form must be tested before an authz claim — and reported as a control when it fails
**When claiming a REST route is exposed (or protected) on WordPress, test the same route through all three
reachable request shapes before writing a line.** `/wp-json/<route>`, `/?rest_route=/<route>` and
`/index.php?rest_route=/<route>` reach the same handler through different front-end paths, so a path-based
rule shows up as a 200 on one shape and a 404/403 on another. Observed 2026-10-13 (mydays/JSMG): the users
list answered **200 on all three shapes** (that is the real finding, MD-C5), while the embedded-MCP routes
answered **401 / 403 `invalid_nonce` on all three** — which is the *control* that proves the MCP permission
layer is genuine and not just a path rule someone forgot.

- Failing to test the alternate shapes is how a *missing path rule* gets written up as a *permission bug*.
- Passing this test is also how you refuse a finding honestly: "the `?rest_route=` form returns the same
  401, so the refusal is in the permission callback, not the path" is a sentence a triager will accept.
- Attach the alternate-shape evidence to the claim either way — it is the cheapest credibility you can add
  to a `rest_forbidden` / `404` / `200` statement.

### Verify the REPORT SECTION TITLES, not just that the content exists — an impact paragraph filed under a different heading scores as "no impact".
    Observed 2026-10-13 (mydays engagement, all four findings already staged and layout-clean): one
    report's impact prose lived under `## 6. Why the <component> matters`. Every content check passed —
    `problems=0`, entity scan, token round-trip, `Impact`-ish prose present — but a triager scanning the
    section list sees no Impact section, and the operator's own review question was *"dlm draft nya jg udh
    ditulis impactnya?"* (is the impact written in the draft?). It was, and the honest answer still had
    to be "the section is titled otherwise".
    Cheap gate, run it on the rendered text of every finding PDF before staging:
    ```python
    full = "\n".join((p.extract_text() or "") for p in PdfReader(pdf).pages)
    for need in ("Impact", "Remediation", "References"):
        assert need in full, f"{pdf}: no '{need}' section heading"
    ```
    Prefer renaming the heading to a plain `N. Impact` over adding a second section — and when you
    rename, say so to the operator, because the fix changes the PDF, which means the draft must be
    **re-staged** (delete the old draft, stage the new one) or the vendor receives the pre-fix copy.

21. **Wrap long CODE-BLOCK lines in the staging generator itself — an unwrapped curl line is an
    `OUT-OF-MARGIN` defect that the operator reads as an untidy PoC.**
    `stage_finding_draft.py`'s `Preformatted` code style is Courier 7.6 pt between an 18 mm / 16 mm
    margin, which fits about **92 characters**. A repro command longer than that leaves the frame and
    `pdf_layout_check.py` reports `p2 OUT-OF-MARGIN '160' x0=562.7 x1=576.4 (page W=595)` (observed
    2026-10-13). Fix it in the builder rather than by hand-wrapping every markdown block — wrap on the
    last space before the limit, indent the continuation, and leave short lines untouched:
    ```python
    CODE_WRAP = 92
    wrapped = []
    for cl in buf:
        while len(cl) > CODE_WRAP:
            cut = cl.rfind(" ", 0, CODE_WRAP)
            if cut < 40:
                cut = CODE_WRAP          # unbreakable token: hard split
            wrapped.append(cl[:cut])
            cl = "        " + cl[cut:].lstrip()
        wrapped.append(cl)
    ```
    Note the same fix was needed twice in one day across two different generators — if you write a new
    markdown→PDF path, port this loop into it before the first build, not after the first defect.

22b. **`stage_finding_draft.py` REBUILDS the PDF with its own `build_pdf()` — which has no image support.**
    Confirmed live 2026-10-14 (Yandex DocViewer SSRF, 1 finding): the report markdown carried
    `![Figure 1 - collaborator hits](ssrf_evidence.png)` and `md_to_report_pdf.py` produced a
    **5-page / 166 052 B** PDF with `images=1` — but staging through `stage_finding_draft.py`
    replaced it with a **3-page / 8 426 B** PDF, `images=0`, only the caption surviving as text.
    The script prints `PDF: … (8426 bytes)` before the draft id, so the size change is visible in the
    transcript if you look for it.

    Two consequences:
    - When the PDF is supposed to embed a rendered evidence PNG (rule 9), **do not stage through that
      script.** Build with `md_to_report_pdf.py`, then stage via the Gmail REST path yourself
      (`EmailMessage` + `make_msgid(domain=…)` + `Date` + `add_attachment`, `drafts().create`).
    - Verify the attachment by **downloading it back** (`format="raw"`, base64-decode, walk parts) and
      comparing `sha256` with the local file — `To`, subject, `%PDF-` magic, sha256, and
      "exactly 1 draft with this subject". A draft that passed the script's own `VERIFIED` line still
      carried the image-stripped PDF.

22. **Sending staged drafts: a spaced sequence needs a DISCONNECTED sender plus a send log — never a
    foreground sleep loop.**
    Operator instruction 2026-10-13: *"ok kirim, sesuai saran kamu, kasih jeda 30 menit setiap send
    draftnya, lalu lanjut deepdive lg"* — send the approved drafts in order, 30 minutes apart, and keep
    working. Shape that satisfies both halves:
    - **staging ≠ sending, and the sender is a separate script.** The stager already refuses a body that
      fails the shape gates; the sender's job is the *pre-send* gate: look the draft up by subject, assert
      exactly one hit, `format="raw"` read-back, assert `To:` and `sha256(attached) == sha256(local file)`
      — and **abort that item** if any check fails, so a stale draft can never ship (the send-vs-fix race
      in rule 13 is exactly this failure). Then `drafts().send(userId="me", body={"id": did})`.
    - **run it detached**, `background=true` with `notify_on_complete=true`, `SEND_GAP` from an env var,
      and append one timestamped line per send to `send-log.txt`. A foreground `sleep 1800` per draft ties
      up the session for 90 minutes and loses the log if the call is cut.
    - **the log is the deliverable to the operator** (`SENT <id> draft=… msg=… pdf=… <n>B sha=… to=…`),
      not a claim about what "should" have gone out. Report the schedule (`C2 ≈00:53, C3 ≈01:23`) so the
      operator can check the mailbox independently.
    - while it runs, keep doing read-only work (deepdive) — but do NOT hammer the same hosts hard enough
      to trip their edge protection; see the rate-limit note in `bug-bounty`'s WordPress reference.

## Layout: "readable, not cramped" (user rejected v1/v2 as mepet/overlapping)

Use these as the BASELINE, not the minimum:
- Body: `fontSize=11, leading=17, spaceAfter=8`
- Code style: `Courier, fontSize=9, leading=13.5, spaceBefore=6, spaceAfter=8, backColor=#f2f2f2, borderPadding=6`
- Headings: `Helvetica-Bold, fontSize=13, leading=17, spaceBefore=20, spaceAfter=8`
- Between steps: `Spacer(1,14)` (NOT 4)
- Table cell padding: `TOPPADDING/BOTTOMPADDING=6`, grid 0.5
- Embedded screenshots: cap at `w=400, hmax=240` so they don't dominate pages
- Result: expect ~5-6 A4 pages per finding **when screenshots are embedded**. Fewer pages usually means
  cramped — but the geometry checker is the gate, not the page count. A text+table+code report with no
  screenshots legitimately lands at 3-4 pages and still passes `problems=0` (2026-10: two findings at 3
  and 4 pages, both clean). Never pad a clean report to hit a page target.

## POC screenshots (Pillow) — legibility rules

Overlap happened because font 15 with 26px line pitch crammed 100+ char lines. Fix:
- Width 1400, font ~15, line pitch 34, title height ~58, generous top/bottom pad.
- WRAP long lines (110-120 chars) instead of clipping; put a small gap (0.5*line) between logical blocks.
- Verify after build: screenshot pixel height should scale with line count (~34px/line + header).
- `scripts/make_evidence.py` implements this (batch: `python scripts/make_evidence.py raw/` renders
  every `raw/*.txt` to `img/*.png`). Use it rather than re-writing a renderer.

**Strip ANSI before you filter the transcript.** vitest/jest colourise `console.log` output
(`\x1b[33mtrue\x1b[39m`). Those escapes are not whitespace, so `line.strip()` leaves them in place
and a filter like `line.startswith("PoC TL-")` then matches *nothing* — you get a screenshot that is
just a title bar, or `lines=0`, and it looks like the PoC produced no output. Run
`re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line)` first (the script does).

**`make_evidence.py`'s `extract()` DROPS plain shell transcripts.** The filter keeps only lines
starting with `PoC `, `[`, `RESULT`, `-----`, or `test test::...ok` — it is tuned for a test
runner's stdout. Feed it a hand-written curl/CLI transcript (commands beginning with `$`, raw output)
and it keeps just the two or three `RESULT` lines, producing a title bar with almost no body while
still reporting a successful render (`lines=2`). Symptom: a plausible-looking PNG whose byte size is
barely above an empty image, and `lines=` much lower than the transcript's real line count.

Do not mangle the transcript to satisfy the filter. Either append explicit `RESULT:`-prefixed lines
to a PoC script (correct when the PoC *is* a script), or render the transcript in full — for a shell
transcript the commands and their real output **are** the evidence, so a verbatim render is the
honest artefact. A minimal renderer: same legibility constants (W=1500, font 17, pitch 31, WRAP=118,
dark terminal), colour `$` command lines, `RESULT:` lines and `#` comments distinctly, and scale the
image height with the line count. Verify by pixel height (`~31px/line`) and by a non-uniform size
spread across the set — uniform sizes mean blank renders.


**Embedding:** the report markdown uses one line, `![Figure 1 — caption](path/to.png)`.
`scripts/md_to_report_pdf.py` renders it as a scaled image + caption (absolute paths and Windows
paths with spaces are fine). Check the built PDF actually contains it — count embedded images with
pypdf/PyMuPDF (`sum(len(p.images) for p in reader.pages)`), because a silently-missing image is
invisible in a text-layer read.

## Harness traps that cost a build cycle (aekktn engagement, 2026-10)

**Inline-code markup in prose leaks as literal tags when the paragraph helper escapes.** The pattern
`P("use <font face='Courier'>xc</font> here")` with a `P()` that calls `esc()` renders the tags as
text — 17 occurrences in one build. Do not fix it by dropping `esc()` (that re-opens the `&` bug) and
do not "fix" it by passing pre-built `Paragraph` objects for prose (the layout checker's literal-markup
scan still flags it, because it scans rendered text, not source). Use a **sentinel pair**: write
`[[C]]…[[/C]]` in the content module, have `P()`, `C()` and `B()` do `esc()` FIRST and then
`.replace("[[C]]", "<font face='Courier'>")`. The escapeth order matters — sentinel after escape, never
before, or the escape mangles the injected tag. Add a build gate:
`assert not re.findall(r'</?(?:b|i|u|font|br)\b[^>]*>', rendered_text)` and
`assert "[[C]]" not in rendered_text`.

**`WL="/d/some path/file.txt"` handed to a native .exe resolves to `C:\d\some path\file.txt`.** MSYS
path translation is disabled on this host, so a bash variable holding an MSYS-style path is passed to
`ffuf.exe`/`gobuster.exe` verbatim and the scan dies with
`CreateFile C:\d\data hermes\...: The system cannot find the path specified` — while the script still
exits 0 and writes a 7 KB *help text* into the output file. Always `cp` the wordlist to a native
`D:/…` path first and use that literal in the tool command; verify by line count
(`wc -l < wl`) and check the output file is not the tool's usage text.

**A background batch script whose tools write 0-byte outputs is not "running long", it is stalled.**
After ~25 min, `ls -la` on the evidence dir is the cheapest progress check: zero-byte output files
plus a live PID means a tool is waiting on something, not working.

**A *rebuild* re-leaks the tags if you only fixed the first content module.** The per-finding generators
written after the sentinel fix copied the old literal `<font face='Courier'>` into their own content
dicts, so the layout checker passed (it does not scan markup) while the rendered text carried 2–4 literal
tags. Whenever a finding gets its own generator file, run the literal-markup scan over the **whole
`pdf/` directory**, not just the PDF you were editing — and re-run it after every rebuild, because the
corrected draft's attachment changes size (9 513 → 9 478 B) and must be re-staged with the new file.

## Post-build verification (mandatory)

```python
try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader
r = PdfReader(path)
full = "\n".join((p.extract_text() or "") for p in r.pages)
assert not re.findall(r'&[a-zA-Z]+;', full), "URL artifact / raw entity!"
assert "watermark" not in full.lower()
assert researcher in full and ip_prefix in full
imgs = sum(len(p.images) for p in r.pages)   # screenshots actually embedded
```
Also confirm exact query strings appear correctly (`full.count("&startDate=") >= 1`).

#### Technical tokens can break MID-WORD inside a narrow cell — the geometry checker does NOT catch it

**First suspect on any fresh generator: `tbl()` feeding millimetre integers straight into `colWidths`.**
reportlab sizes columns in POINTS, so a `[30, 136]` "mm" list renders as 10.6 mm + 48 mm — every label
wraps mid-word (`Prog/ram`, `Findi/ng`, `Seve/rity`, `Asse/t`) and long URLs break at `http/s://`, while
`pdf_layout_check.py` still reports `problems=0` (each fragment fits its column, nothing leaves the
margin). Confirmed live 2026-10-13 on a shipped finding PDF. Fix inside the helper —
`colWidths=[w * mm for w in widths]` — then re-extract the rendered text and assert the labels survive
intact (`all(t in full for t in ["Program","Severity","Asset","Egress IP"])`; do not test single words
that also occur in body prose, e.g. "Program" matches "Programme" and gives a false PASS). A table that
looks plausible in a viewer can be silently mangling every label in it.

Found 2026-10 (Todoist DCR v2). A `Result` column 26 mm wide was too narrow for
`invalid_client_metadata`, so reportlab wrapped it as **`invalid_clien t_metadata`** across two lines.
`pdf_layout_check.py` reported `problems=0`: each fragment fits its column, so the `OVERSIZED WORD`
rule never fires, and nothing leaves the margin. It is invisible to geometry, to the entity scan and
to a visual read — but a triager grepping for that token finds nothing, and it looks careless in a
document whose credibility rests on exact values.

Add a token round-trip assertion to the verify pass. Choose the strings a reviewer will search for —
error codes, identifiers, hostnames, endpoint paths, credential ids — and require each to appear
**intact**:

```python
TOKENS = ["invalid_client_metadata", "client_secret_expires_at", CLIENT_ID,
          "api.target.com/oauth/register", "app.target.com/oauth/authorize",
          "todoist.com/oauth/authorize"]
for t in TOKENS:
    assert t in full, f"token broken or missing in rendered text: {t}"
```

**`--tokens` matching is CASE-SENSITIVE, and a case mismatch is YOUR check failing, not a document defect.**
Session case: `pdf_layout_check.py --tokens ... "Taiko"` reported `REQUIRED TOKEN MISSING: 'Taiko'` on a
report that prints `taiko (167000)` — the document was correct and the check was wrong. Two rules follow:
(i) take each token's exact casing from the rendered text, not from how you would write it in prose —
proper nouns, chain names and product names are routinely lowercased inside generated tables and code
blocks; (ii) when a token check fails, **grep the extracted text for a case-insensitive match before
"fixing" anything.** Rewriting the document to satisfy a broken assertion is how a correct report acquires
a defect.

### Verify RULE 0 compliance by GREPPING, never by recall

Before stating that a report bundles two findings (or before splitting one "for safety"), extract the PDF
text and grep for the *other* finding's distinctive tokens:

```python
for kw in ("dangling", "approve", "amounts[i]", "secondary"):
    print(kw, full.lower().count(kw.lower()))
```

Session case: a confession that a staged PDF violated 1-finding-1-draft was made **without checking** —
the counters came back `dangling 0x / approve 0x / secondary 0x`. The report was already compliant. A
false self-accusation is as damaging as a missed defect: it triggers unnecessary rebuilds, re-staging and
re-sends (each of which is its own risk — see the stale-send race in rule 13). The rule is symmetric:
**verify before claiming a violation, exactly as you verify before claiming a finding.**

Widen the offending column rather than shortening the token — these are the exact values the reader
needs, so the token is not the thing to compromise. Rule of thumb: a Courier 8.3 pt cell needs about
`len(longest_token) * 5 pt` ≈ `len(longest_token)/5.6 mm` of width.

#### THE UNIT TRAP — `colWidths` is in POINTS, so a "mm" table is silently ~2.8x too narrow

The most common cause of mid-word breaking is not a badly chosen width, it is a **unit mix-up inside the
`tbl()` helper**. Every hand-written width list is naturally authored in millimetres (the skill's own
budget is "sum ≤ 168 mm"), but `Table(colWidths=...)` takes **points**. Passing the mm numbers straight
through renders each column at `mm/2.835`, so the label column collapses to ~30 pt (10.6 mm) and every
label breaks mid-word.

Observed 2026-10-12 (Blink F1): `tbl(META, [30, 136], head=False)` produced

```
Prog     Findi     Seve      Asse      Foun
ram      ng        rity      t         d
```

and `pdf_layout_check.py` still reported **`pages=4 problems=0`** — each fragment fits its now-tiny
column, so the OVERSIZED-WORD rule never fires and nothing leaves the margin. Invisible to geometry and
to the entity scan; only a read of the extracted text shows it. It also survived one whole "fix" round
where the label column was widened from 30 to 34 *while still being points*.

Fix once, inside the helper — then every caller's mm list is correct by construction:

```python
assert sum(widths) <= 168, "colWidths sum %s mm exceeds frame" % sum(widths)
t = Table(wrapped, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0, hAlign="LEFT")
```

Detection (add to the post-build pass, since the geometry checker cannot see it):

```python
# every label / heading word that lives in a table must appear INTACT in the rendered text
LABELS = ["Program", "Finding", "Severity", "Asset", "Egress IP", "Researcher", "Status"]
broken = [w for w in LABELS if w not in full]
# and check the residue shape explicitly, because a word can also appear elsewhere in prose:
residue = [p for p in ("Prog\nram", "Seve\nrity", "Affec\nted", "Findi\nng", "Egre\nss") if p in full]
assert not broken and not residue, f"table cell mid-word break (units?): {broken} {residue}"
```

Beware the false pass in `w in full`: `"Program"` matched because the body prose contained
"Programme", so a broken label still looked present. Check the **residue pattern** (the split form) or
scope the search to the extracted text of the table's own page — do not treat a bare substring hit as
proof the label rendered intact.

#### Patching a generator with masked literals silently no-ops

When the harness masks a token-shaped literal in your tool arguments (`***`-shaped strings, session
tokens, `Bearer …` fragments), a `str.replace()` whose **pattern** contains that shape never matches, so
the "fix" reports success while the file is unchanged — and a follow-up build reproduces the same defect.
Observed three times in one session on the same two transcript files. Workaround: never type the masked
shape as a literal. Build it (`STAR = chr(42) * 3`) and run the replacement from a Python heredoc in
`terminal` rather than `execute_code`, then **read the file back** and print the line counts of the
matched lines (`"stars-left:", text.count(STAR)`) as the assertion. Same rule as the tripwire note at the
top of this skill: fragment the literal, or derive it.

**Substring traps (use word boundaries).** `if "confidential" in text.lower()` fires on the CVSS word
*confidentiality* and on `"draft"` inside prose. Check with regex word boundaries, e.g.
`re.search(r'\bconfidential\b', text, re.I)` — otherwise you "fix" a watermark that does not exist.

### Literal markup tags — the entity scan does NOT catch these (add to every verify pass)

The `&[a-zA-Z]+;` scan above catches *unescaped* entities. It does **not** catch the opposite defect:
a cell that genuinely needed markup was passed as a plain string, so `esc()` converted it and the tags
printed **as text**. Observed in a shipped report: 12 tags rendered literally in the body
(`<b>7.5 (High)</b>`, `<font face='Courier'>`, `<font color="#1155cc">`), i.e. the reader saw the
markup instead of bold/monospace. `pdf_layout_check.py` stays at `problems=0` because geometry and
entities are both fine — only a tag scan finds it.

```python
tags = re.findall(r'</?(?:b|i|u|font|br)\b[^>]*>', full)
assert not tags, f"literal markup rendered as text: {tags[:5]}"
```

Root cause is always the same two-way branch: `tbl()`/`ktv()` escape plain strings, so **any cell
containing `<b>`/`<font>` must be handed in as a pre-built `Paragraph`**, and the helper must
pass a flowable through instead of re-wrapping it:

```python
def ktv(k, v):          # WRONG: Paragraph(Paragraph(...)) crashes; esc(v) prints tags
    return [Paragraph(esc(k), CELLH), Paragraph(esc(v), CELL)]
def ktv(k, v):          # RIGHT: flowables pass through, strings get escaped
    return [Paragraph(esc(k), CELLH), (v if hasattr(v, "wrap") else Paragraph(esc(v), CELL))]
```

Then call it with a Paragraph for markup cells only:
`ktv("CVSS 3.1", P(f'<b>{CVSS_SCORE}</b> — <font face="Courier">{CVSS_VEC}</font>'))`.
Also remember `esc()` must **not** be applied to strings inside `P()` — those keep raw `<` `>` `&`.
Because fixing this changes the rendered text, the PDF byte size changes — so **re-stage the email
draft** and re-verify the attached size against the newly built file (a stale draft carrying the
broken render is exactly the class the replace-not-append rule exists for). 

**Confirmed live, and the trap is worse than "stale draft": the operator can SEND the old version
while you are still fixing it.** Observed 2026-10-02 (TimbSwap F1): a report PDF with 12 literal
markup tags was staged; the operator sent that draft; the defect was found afterwards, the PDF
regenerated (88,033 -> 87,918 B) and the draft folder entry replaced — but the mailbox already held
the broken copy. Two habits follow, and both are cheap:

1. **The send can race your fix. After ANY correction to a PDF that was ever staged, read the SENT
   folder and compare the sent attachment's decoded byte size against the corrected local file.**
   Do not infer "the draft was replaced, so the send is fine" — the operator may have pressed send
   minutes earlier. Verified sizes were the only thing that revealed it:
   `sent F1 att ... = 88033 bytes <== MISMATCH (local 87918)`.
2. If the sent copy is the stale one, the remedy is a **short threaded correction** (reply on the
   captured Message-ID) attaching the corrected file and stating plainly that only the rendering
   changed — never a silent resend, and never a second un-threaded copy of the same finding.
   Reconcile by listing the Sent folder per message (subject + date + Message-ID + attachment
   sizes); that list is the deliverable to the operator, not a claim about what "should" be there.

### Sum of `colWidths` must fit the FRAME, not the page (caught 2026-10-07)

`Table(colWidths=[...])` is sized in points/mm and is **not** auto-clamped to the frame. A table
whose column widths sum to more than the frame width silently overflows the right margin — every
cell in the last column is reported `OUT-OF-MARGIN` by `pdf_layout_check.py` while the document
looks plausible in a viewer that clips at the page edge.

Budget for A4 with the 20 mm margins this skill's generator uses:

```
frame width = A4 width - left margin - right margin
            = 210 mm - 20 mm - 20 mm
            = 170 mm        <- keep sum(colWidths) <= 168 mm for headroom
```

Session case: an "affected asset" table used `[30, 36, 28, 86] mm = 180 mm` → checker reported
`p OUT-OF-MARGIN 'remoteAddress=::ffff:100.64.0.x' x0=444.9 x1=565.1 (page W=595)`.
Reducing the same table to `[26, 32, 24, 86] mm = 168 mm` gave `problems=0`. The same pass also
had to shrink `[42,130]` → `[40,128]` and `[34,20,116]` → `[32,20,116]`.

Rule: **add up every `colWidths` list before building and assert the total ≤ 168 mm.** Widening a
column to stop mid-word token breaks (`invalid_clien t_metadata`) *adds* to that total, so re-check
the sum whenever you widen one — those two fixes fight each other.

#### `colWidths` are POINTS — a table built with "mm numbers" shreds every label and still reports `problems=0`

Confirmed live 2026-10 (Blink F1). The generator's `tbl()` helper took human-sized numbers
(`tbl(META, [30, 136])`, meaning mm) and passed them straight to
`Table(..., colWidths=widths)`. reportlab reads `colWidths` in **points**, so the label column was
30 pt ≈ 10.6 mm and the value column 48 mm: every key in the meta table broke **mid-word** —
`Prog` / `ram`, `Findi` / `ng`, `Seve` / `rity`, `Asse` / `t`, `Foun` / `d`, `Egre` / `ss` — and URLs
split as `http` / `s://www.blink.sv/en/bounty-terms`. `pdf_layout_check.py` reported
`problems=0`: nothing left the margin, each fragment fit its (tiny) column, and the ORPHAN/OVERSIZED
rules never fired. It reads as the "mepet" defect the operator rejects, and only a text-layer read
catches it.

Fix it once, inside the wrapper, never per call site:

```python
def tbl(rows, widths, head=True, fs=8.4):
    ...
    assert sum(widths) <= 168, "colWidths sum %s mm exceeds frame" % sum(widths)  # keep the check on mm
    t = Table(wrapped, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0, hAlign="LEFT")
```

Then assert the labels survived — this is the check the geometry script cannot do for you:

```python
full = "\n".join((pg.extract_text() or "") for pg in PdfReader(pdf).pages)
for k in ("Program", "Severity", "Egress IP", "Researcher"):      # every meta key, exact casing
    assert k in full, "meta label shredded or missing: " + k
assert not re.search(r"(Prog|Seve|Findi|Asse|Foun|Egre)\s*\n\s*(ram|rity|ng|t|d|ss)\b", full)
```

Keep the ≤168 mm assertion on the **mm** list (it runs before the conversion); a table that is now
correct can still overflow the frame if the widened column pushed the sum over.

### `colWidths` are POINTS, not mm — and the geometry checker cannot see the damage (2026-10-13)

`Table(colWidths=[30, 136])` is **30 pt and 136 pt** (≈ 10.6 mm and 48 mm), not 30/136 mm. A helper that
takes widths "in mm" per the frame budget above must multiply:

```python
def tbl(rows, widths, head=True, fs=8.4):        # widths listed in mm, as the budget above assumes
    ...
    t = Table(wrapped, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0, hAlign="LEFT")
```

Symptoms of forgetting it, all of which survive a visual glance and **all** of which
`pdf_layout_check.py` reports as `problems=0` (narrow columns are not out-of-margin, and each fragment
fits its cell):

- meta/label cells break **mid-word**: `Prog` / `ram`, `Findi` / `ng`, `Seve` / `rity`, `Asse` / `t`;
- long URLs in a value cell split at `http` / `s://www.example.com/...`;
- tables look cramped/"mepet" in a way no numeric check flags.

Detection that actually works: extract the rendered text and **assert the label words survive intact**
(`assert "Program" in full and "Severity" in full`), or read the first ~20 extracted lines and look for a
2-line fragment where one word should be. Do NOT trust a `"Program" in full` check that can be satisfied by
an unrelated body string ("…Disclosure **Program**me") — pick tokens that appear ONLY in the table, or print
the extracted lines and read them.

**Two-way trap:** the fix changes the rendered text, so a PDF that was already staged is stale — re-stage
the draft and re-verify the attachment (`%PDF-` + sha256) after any column-width change.

## Geometry verification — the only reliable layout check (run `scripts/pdf_layout_check.py`)

Text-layer inspection does NOT reveal overlap; only word rectangles do. This is what caught the
real defects in the shipped report (cell text leaving the page at x1=594.8pt of 595.3pt) after a
visual pass had missed them:

- **Collision**: compare word bounding boxes across *different* text blocks; `ix>1.2 and iy>1.2` ⇒ overlap.
- **Out-of-margin**: any word with `x0 < left_margin-7` or `x1 > page_width-right_margin+7`.
- **Orphan heading**: the last body block on a page matches `^\d{1,2}\.\s+\S` ⇒ heading with no content under it.
- **Wrap sanity**: any word wider than its column ⇒ a non-wrapping cell.
- **Raw entity**: `&[a-zA-Z]+;` present in the extracted text.
- **Tokens**: `Page X of Y`, researcher name, each finding keyword present.
- **Neighbour sanity**: `float(metrics['Page hp']) / hpt ≈ 1.0`, `rate ≈ 1` (0 means a sticky `Fit` size).

**Do NOT rely on an auxiliary vision model to QA PDF renders.** In this session a vision pass on a
correctly-rendered page returned a confident description of a *completely different, unrelated
document* ("Quarterly Report &mdash; Q3", fabricated metrics). Treat vision output on rendered PDFs as
unreliable hearsay; the deterministic geometry/token checks above are the source of truth. Render
pages with PyMuPDF (`get_pixmap(dpi=115).save(...)`) when you need to eyeball something yourself.

## Generator API + verification traps (learned the hard way)

- **Pass the story explicitly to the document factory.** The multi-finding section above shows
  `make_docs(out, header_left, header_right, title, subject)` returning `run(story)`. If your `run` closes over a
  module-level `story`, calling it from a generator whose story lives in *another* module raises
  `NameError: name 'story' is not defined`. Use the explicit signature
  `make_docs(out, header_left, header_right, title, subject, story) -> (path, pages)`.
- **`pdf_layout_check.py` bans WORDS, not just geometry.** `BAD_WORDS` is whole-word matched for `watermark`,
  `draft`, `template`, `evaluation copy`, `sample`. So the report prose must avoid them: do not call your own
  document a "draft", and watch domain vocabulary — Morpho's "conversion sample" trips `sample`. Fix the prose, never
  relax the checker.
- **Always pass `--tokens`** with the researcher name, `Page 1 of`, and the finding id. That turns the run into a
  content check as well (metadata actually rendered, two-pass footer actually applied, finding id present).
- **Record the egress IP honestly.** Metadata must carry the IP used when the finding was made. If the egress
  rotates, record the `api.ipify.org` value and label it as the egress — do not silently pick one. Real case:
  Cloudflare WARP gave `104.28.226.245` from ipify while `ip-api.com/json` reported a *different* `query` value in
  the same session; the honest entry is
  `104.28.226.245 (Cloudflare WARP egress, Medan, Indonesia)`.
- **Run the language gate on the RENDERED text**, not the source file: extract per-page text with pypdf/fitz and
  assert no non-English words survive (`\b(yang|tidak|adalah|dengan|untuk|laporan|temuan|silakan)\b` for
  Indonesian). Source-only checks miss strings that reach the page through a table cell or a running footer.
- **For a bounty submission, give the PDF a section that pre-empts the platform's exclusion clause.** A report that
  answers the triager's rejection argument inside the document is worth far more than one that only states the bug.
  Clause and two-prong rebuttal pattern: `bug-bounty/references/sherlock-program-rules.md` §4.

## Markdown-derived reports (MD -> PDF generator)

When the deliverable already exists as a markdown report (common in code-review engagements), do NOT
hand-transcribe it into the generator — parse the markdown so the PDF cannot drift from the source.
`scripts/md_to_report_pdf.py` is a working reportlab generator (headings, bullets, bold / inline code,
fenced code with automatic wrapping, two-pass "Page X of Y"). Build it, then run the geometry checker.
Three defects it hit, all invisible in a visual read:

1. **Orphan heading caused by a Spacer after the heading.** `keepWithNext=True` binds a heading to the
   *next flowable*. If you emit a `Spacer` for every blank line, the heading binds to the Spacer and can
   still land alone at the page bottom (checker: `ORPHAN HEADING`). Fix: track `last_heading` and never
   emit a blank-line Spacer directly after a heading.
2. **Long unbreakable tokens overflow.** Fenced code containing a long path/identifier has no whitespace
   to wrap on. It surfaces only as `OVERSIZED WORD` / `OUT-OF-MARGIN` in `pdf_layout_check.py`. Fix:
   hard-split any token longer than the code-column width, and for long INLINE code spans insert explicit
   `<br/>` breaks (split after `/`). Courier 9 pt fits ~89 chars between 20 mm margins — set the wrap
   width below that (84).
3. **The literal-markup scan false-positives on quoted source.** The `</?(b|i|u|font|br)>` check flags any
   enrichment tag printed as text — but a report that QUOTES production code whose javadoc contains `<b>`
   (e.g. `/** Temporary, <b>insecure</b> ... */`) is faithful quoting, not a render defect. Print the
   matching line and confirm it sits inside a code block before "fixing" anything.

Gate after every build: `scripts/pdf_layout_check.py <pdf> --tokens "Page 1 of" "<finding-id>"` must report
`problems=0`, plus the rendered-text scans (non-English words absent, `&[a-zA-Z]+;` absent).

### `md_to_report_pdf.py` has NO markdown-table support — that is a silent mangle, not a warning

Confirmed on a live engagement (CodeRabbit VDP, 2026-10): table-heavy reports are the norm once you
include a metadata block, an asset table and a severity table. `build_story()` in
`scripts/md_to_report_pdf.py` matches only `#/##/###`, bullets, `\d+.`, ```` ``` ````, `---` and
`![img]()`. A line starting with `|` falls through to the **paragraph** branch, which then greedily
absorbs every following non-heading line — so a 5-row table renders as one run-on paragraph of
`| Field | Value | | --- | --- | | Program | ... |`. Nothing errors; the page count barely moves;
only a human read of the PDF catches it. The layout checker cannot see it (no geometry violation).

Fix: add a table branch **before** the paragraph branch, and render a real `Table` of `Paragraph`
cells. Copy the `tbl()` discipline from rule 6 — escape plain strings yourself, distribute column
widths proportionally to the longest cell with a floor, `repeatRows=1`, `VALIGN TOP`:

```python
if ln.strip().startswith("|") and _is_sep(lines[i+1]):
    header = _split_row(ln); i += 2; rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows.append(_split_row(lines[i])); i += 1
    story.append(build_table(header, rows)); last_heading = False; continue
```

Two follow-on traps once tables render:
- the paragraph branch's continuation regex must also refuse to swallow `|` lines
  (`r"^(#|\s*[-*]\s|\s*\d+\.\s|```|---|\|)"`), or a table immediately after a paragraph body merges;
- the token round-trip check must include values that appear **only inside a table or only inside an
  embedded screenshot**. A UUID that lives solely in the evidence PNG is absent from the text layer,
  and the checker reports it as a missing token — that is a true positive. Add a verbatim excerpt
  block (fenced code with the real values) so the exact strings a reviewer greps for are in the text
  layer, rather than relaxing the check.

## Emitting a generator from `execute_code`: two traps that each cost a build cycle (2026-10)

**The output-masking tripwire rewrites token-shaped literals in files you write.** A line meant to read
`TOKEN = "google_token.json"` came back as `TOKEN="***" + "gle_" + "token" + ".json"` — still valid
Python, so `ast.parse` passed, but it resolves to `***gle_token.json` and every Gmail call then fails
with a file-not-found that looks like a revoked credential. Do not fight the masker by fragmenting the
name; **import the resolver from the script that already works** instead of re-deriving a path:

```python
import importlib.util
STAGE = r"C:\...\skills\bug-report-delivery\scripts\stage_finding_draft.py"
_spec = importlib.util.spec_from_file_location("sfd", STAGE)
sfd   = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(sfd)
creds = Credentials.from_authorized_user_file(sfd.token_path())   # proven resolver, no literal to mask
```

**Never use regex backreferences in emitted source.** A `re.sub(r'<b>\1</b>', …)` written through a
line-append emitter lands with the backslash doubled (`\\1`), so the page prints a literal `\1` instead
of the captured text; and a `face=\"Courier\"` lands with visible backslashes and reportlab dies with
`ValueError: Can't map determine family/bold/italic for \"courier\"`. Format inline markup with
`split()` — there is no escape to get wrong:

```python
def inline(t):
    parts = t.split('**')
    if len(parts) > 1:
        t = ''.join((p if i % 2 == 0 else '<b>' + p + '</b>') for i, p in enumerate(parts))
    parts = t.split(chr(96))                     # backtick
    if len(parts) > 1:
        t = ''.join((p if i % 2 == 0 else "<font face='Courier'>" + p + "</font>") for i, p in enumerate(parts))
    return t
```

Call it AFTER `esc()` (escape first, then inject markup). Same class of trap, already noted above for
`'''` code blocks — this is the version that bites when the generator is *emitted* rather than typed.

**`format="metadata"` hides attachments.** Auditing a draft with it prints `parts: []` for a draft that
genuinely carries the PDF — it reads as "attachment missing" and sends you chasing a non-bug. Verify with
`format="full"`, then `users().messages().attachments().get(...)`, base64url-decode and compare `sha256`
against the local file (plus the `%PDF-` magic).

**Gmail REST token dead (this user)? Stage drafts via IMAP App-Password — recipe + imap_tools traps: `references/imap-draft-staging-fallback.md`.**

## Staging traps (harness rebuilds the PDF; word-gate fires on prose)

`stage_finding_draft.py` **builds its own PDF from the markdown** (`build_pdf(a.md, a.pdf, …)`) — a
hand-built reportlab PDF that you already verified gets **overwritten**, so verify the file that is
actually attached, not the one you wrote. `pdf_layout_check.py` BAD_WORDS (`watermark / draft /
template / evaluation copy / sample`) fire on **ordinary domain prose** too — "matched by a public
misconfiguration *template*" reported `problems=1` on a clean report; rephrase, never relax the
checker. And a changed PDF makes the staged draft stale: delete the old draft **by subject**
(`format="full"`; ids come in two shapes and `format="metadata"` hides attachments), then re-stage
and re-run all four gates.

## Tooling notes
- reportlab + PIL exist in BOTH `C:/Users/WINDOWS10/AppData/Local/Programs/Python/Python314/python.exe` and `C:/Users/WINDOWS10/AppData/Local/Python/bin/python.exe` and the Hermes venv.
- On Windows, use native Windows paths in Python (MSYS `/c/...` paths break `open()`); write the generator with write_file and run via terminal (avoid execute_code for long reportlab scripts — escape/quote traps).
- **When `write_file` is not in the toolset, build the generator with `cat > gen.py <<'EOF'` in
  CHUNKS, not one long heredoc.** A single heredoc past ~110-120 lines silently truncates and the
  shell dies with a misleading `unexpected EOF while looking for matching '` (the heredoc never
  closed). Write the header/imports/styles first with `>`, then append the finding stories with
  `>>`, ~50-60 lines per chunk. Keep the source free of literal `&` in the *command* (the terminal
  tool scans the raw command for `&` and rejects it as backgrounding) — define `A = chr(38)` and
  build `esc()` from it (`s.replace(A, A+"amp;")`), and avoid `&` in any repro commands you embed.
  A `mkdir -p` in the same failed command never ran (parse-time failure), so create the output dir
  in a separate call.
- `pdf2image` is NOT installed — don't rely on it for visual preview; use `pypdf` text checks.
- Avoid style names already in `getSampleStyleSheet` (`Code`, `Bullet`, `Title`, `Normal`, `Heading1-6`, `BodyText`) — use custom names.

## PGP-required programs — encrypt the SUBMISSION, not just the attachment

Some programs state the requirement in the brief itself ("Please use our PGP public key to encrypt
any email submissions to us at security@<domain>"). That is a program FORMAT rule (rule 15 family).
When it applies, the finding PDF must travel **inside** an encrypted payload, not as a plaintext
attachment. This does NOT relax RULE 0 — still one draft per finding; "PDF attached" becomes "an
encrypted attachment that decrypts to the report body plus the PDF".

Three things to hold onto:
- **Confirm the requirement** and quote the sentence; if the brief does not ask for PGP, keep the
  plaintext PDF attachment — do not invent an encryption step.
- **The outer body is a plaintext cover note only** (greeting, policy URL, recipient key
  fingerprint, pointer to the encrypted attachment, signature). The vulnerability detail lives
  inside the encrypted payload. This deliberately overrides rule 12 for PGP programs; flag the
  trade-off in the hand-off.
- **Read-back is still mandatory** — for a `.asc` the magic check is `-----BEGIN PGP MESSAGE-----`
  (the analogue of `%PDF-`), plus size+sha256 against the local file and `gpg --list-packets`
  showing the recipient **encryption subkey**.

Full recipe (key extraction from the policy HTML, import, inner-MIME -> gpg -> `.asc`, cover note,
verification, and the MSYS `GNUPGHOME` + long-heredoc traps): `references/pgp-required-programs.md`.

## Supporting files

- `references/gmail-message-id-rest-path.md` — ⛔ **the Message-ID trap fires on the REST
  `drafts().create()` path too, not just IMAP `append`** (hit live 2026-10-13): staging report B with a
  raw MIME built by `EmailMessage()` and no `Message-ID` silently REPLACES report A — both `create()`
  calls return success. Fix (`make_msgid()` + `Date`), the "stage N then assert N subjects in one pass"
  rule, and why `Message-ID: NONE` in the metadata view is NOT evidence of a missing header.
- `references/per-finding-draft-pipeline.md` — running RULE 0 (1 finding = 1 draft = 1 PDF) at
  engagement scale: the `findings.json -> build -> sync_drafts` chain, draft-state idempotency,
  the **raw-REST drafting path** (when the google-workspace wrapper has no `draft` command and
  google-api-python-client is not installed), the `?format=raw` read-back trap, and the
  harness traps (MSYS paths, secret-shaped-assignment rewriting) that cost time.
- `references/sequenced-disclosure-sending.md` — the SEND phase (rule 22) in depth: how to recover a
  batch whose runner died mid-way **without double-sending to the vendor** (send-level idempotency via
  a SENT-folder check, not the runner's own log), the pre-send attachment re-hash, retrying
  `ConnectionAbortedError [Errno 10053]` host-side socket aborts, deduping drafts by which one matches
  the current local PDF, the final independent SENT audit, and the false-FAIL checker traps
  (`bounty` inside a cited policy URL; `swag` inside "Swagger UI").
- `references/pgp-encrypted-disclosure.md` — when the program's policy requires its PGP public key
  ("use our PGP public key to encrypt submissions"), encrypt the submission (report body + PDF) into
  an armored MIME and stage that as the draft attachment with a plaintext cover note. Includes the
  HTML-wrapped-armor extraction trap, the `GNUPGHOME` MSYS-path trap, and the RULE 0 adaptation
  (the PDF rides *inside* the ciphertext, not as an open attachment). Apply to EVERY finding's draft
  for a PGP-required program, not just the first.

**If the vendor comes back asking for a video PoC instead of / in addition to the PDF**, switch to the
`poc-video-production` skill. Two things carry over directly: (1) re-run the exploit chain before
building anything — a report can describe behaviour the live target no longer has, and a video
faithfully animating a stale claim is worse than no video; (2) the "do not QA rendered output with an
auxiliary vision model" rule applies to video frames too — sample pixels and read the DOM instead.

- `scripts/md_to_report_pdf.py` — reusable generator: markdown report -> PDF (headings, bullets, bold/inline code, wrapped fenced code, two-pass "Page X of Y"). Use it instead of hand-transcribing an existing markdown report; then run the layout checker.
- `scripts/make_evidence.py` — turn a raw console transcript into a legible dark-terminal evidence PNG (strips ANSI, auto-wraps, highlights RESULT lines). Batch mode: `python scripts/make_evidence.py raw/`.
- `scripts/render_transcript.py` — **verbatim** renderer for transcripts `make_evidence.py` mangles (shell sessions, `forge test` output, command/diff transcripts). Measured failure of the alternative: 35 lines rendered as 11, and a code-diff transcript rendered as **1 line** (title bar over an empty image) while still reporting success. Use `make_evidence.py` for test-runner stdout; use this for anything whose commands and raw output ARE the evidence. `python scripts/render_transcript.py <raw.txt> <out.png> "Optional Title"`. Verify by size spread across a batch — uniform sizes mean blank renders.
  **It only keeps lines matching `^PoC |^\[|^RESULT|^-----`** — right for a test runner,
  wrong for a shell transcript or a code diff, which it reduces to a near-blank image while
  still reporting success. For anything that is not a test-runner stdout use
  `scripts/render_transcript.py` instead (verbatim render, colour by role, same legibility
  constants). Pick by content, not by habit: a `forge`/`pytest` transcript → `make_evidence`;
  a curl session, a `git diff`, a before/after code comparison → `render_transcript`.
- `scripts/render_transcript.py` — verbatim shell/diff transcript → evidence PNG (`<raw.txt> <out.png> ["title"]`). Use when `make_evidence.py` would filter the evidence away. Verify by pixel height (`~31 px/line`) and a non-uniform size spread across the set.
- `scripts/reportlab_verify.py` — post-build verification snippet (artifact/metadata/image/watermark checks).
- `references/gmail-rest-draft-staging.md` — stage a report draft WITH its PDF attachment via the Gmail REST API (raw MIME) when the `gws`/`google_api.py` wrapper has no draft subcommand; `?format=raw` read-back and `%PDF-`+sha256 verification traps inside. IMAP App-Password fallback when the REST token is dead: `references/imap-draft-staging-fallback.md`.
- `references/pgp-encrypted-submission.md` — when the program's policy says *"encrypt submissions with our PGP public key"*: extract+import their key from the policy page (armor-rebuild traps), encrypt the body+PDF into an ASCII-armored `.asc`, stage the draft as a plaintext cover note + `.asc` attachment, verify the recipient subkey with `gpg --list-packets`. The PDF rides **inside** the encrypted payload, not as a `.pdf` attachment — note that deviation in the hand-off.
- `references/pgp-encrypted-disclosure-submission.md` — when the vendor's VDP REQUIRES PGP: encrypt the whole submission (body + PDF) into a `submission-<F>.asc` MIME and attach THAT to the draft (plaintext cover note only). Includes extracting a PGP public key from an HTML policy page (armor reconstruction), the MSYS `GNUPGHOME` path trap, encrypt-to-encryption-subkey + `gpg --list-packets` check, and the raw-read-back verification.
- `references/pgp-required-programs.md` — when a program's brief REQUIRES PGP-encrypted submissions: extract the inline key from the policy HTML, import, encrypt the inner MIME (body + PDF) to their key, stage a plaintext cover note + the `.asc`, and the verification pass. Includes the `GNUPGHOME`-must-be-MSYS-path trap and the truncated-heredoc trap.
- `scripts/pdf_layout_check.py` — deterministic geometry/token QA (collisions, out-of-margin text, orphan headings, oversized table-cell words, raw entities, watermark tokens, JPEG neighbour sanity). Run it on every generated PDF before delivering; it is what catches *"tulisan tertimpa"*.
- `references/disclosure-draft-pipeline.md` — the multi-finding harness that makes RULE 0 structural: a `findings.json` source of truth plus one PDF generator and one draft/attach sync script, the recurring-loop prompt shape, the four verification gates, and the cron `"15m"` one-shot trap that silently killed a loop.

## Non-security deliverables (product-correctness / calculation reports)

The same generator, styles, layout rules and verification pipeline carry over when what you are
writing up is not a vulnerability at all — wrong arithmetic, a missing compliance warning, a
disclosure/coverage gap. Two things change:

1. **Label it so it cannot be read as a vulnerability report.** Running header, document title and
   the email subject all say what it is, e.g. `… - tinjauan akurasi taksiran pajak (ronde kedua,
   bukan laporan keamanan)`, and the opening paragraph states that it is about whether the numbers
   are right and that no claim or payment request is attached. Keep the running header ASCII
   (rule 7) and keep the severity-honesty table in spirit: state the *direction* of each error
   (overstates vs understates the charge) and who is affected.
2. **Add a "what is correct" section.** A correctness report that lists only defects reads as an
   attack; listing the hand-computed matches next to the product's own figures is what makes the one
   real bug credible. Same table style as the severity table.

Everything else is unchanged: `esc()` inside every cell wrapper, no watermark, single-source-of-truth
constants, two-pass build for `Page X of Y`, then `scripts/pdf_layout_check.py`. A 3-page
non-security report built this way passed with `problems=0` on the first build.

Placement note: keep the generator beside the deliverable and resolve output paths from the script's
own directory (`ROOT / "laporan" / "x.pdf"`). If the draft/e-mail builder that attaches the PDF lives
in a different subdirectory, give it its own path constant — reusing a relative `ROOT` from the other
script silently points at a directory that does not exist.

## Multi-finding engagements (one PDF per finding)

Package as: one shared style module + one small generator per finding.
```
att_style.py     palette, styles, esc(), C() (boxed code), B() (bullet), tbl() (Paragraph cells),
                 kv() (meta table), KT() = KeepTogether, RULE_LINE(), make_docs() -> run(story)
att_f1.py        imports att_style; builds only Finding 1's story; run() writes its own PDF
att_f2.py        same for Finding 2
```
`make_docs(out, header_left, header_right, title, subject)` returns `run(story)` which does a
**2-pass build** so the footer can print `Page X of Y`. Two non-obvious requirements:
- `copy.deepcopy(story)` for EACH pass. reportlab mutates flowables during build; reusing the same
  objects on the second pass raises `LayoutError: Flowable ... too large on page N`.
- Never put HTML entities in `header_left`/`header_right` — those go to `canvas.drawString`, which
  does not parse markup (rule 7).

Per-finding section order that has held up: 1 Summary, 2 Impact, 3 Affected endpoints/assets,
4 Steps to Reproduce (numbered, paste-ready curl + python), 5 Observed Result / validation,
6 Proof (bypass or comparative evidence), 7 Impact boundary (honest limits), 8 Remediation,
9 References (CWE + program policy section).
## Absorbed playbooks (complete sub-packages under `references/`)
- `references/pdf-bug-report-generation/PLAYBOOK.md` — the canonical **default skeleton** (it
  overrides ad-hoc layouts), reportlab pitfalls (raw-HTML em-dashes, quote nesting in cells,
  generator-string syntax errors), Pillow PoC screenshot design, and the pre-delivery verification
  loop. Its `scripts/` carry `qa_pdf_layout.py`, `build_per_finding_reports.py`, `lookup_vrt.py`,
  `render_email_body.py`; its `references/` carry layout verification without a vision model and
  per-finding split/draft hygiene. Read this package first when starting a new report.
