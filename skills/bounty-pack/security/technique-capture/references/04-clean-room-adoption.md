# Clean-room adoption of a licensed source

Use when the learning loop's input is an **external project you did not write** — a repo you want to
borrow mechanisms from, a skill pack under a copyleft licence, a defence guide, a rule set. This is a
**legal boundary, not a style preference**, and it is cheap to verify. Do the verification; do not
rely on the licence feel of the source.

## The licence ladder

| source licence | read & learn privately | ship / merge into our library | serve it over a network |
|---|---|---|---|
| MIT / Apache / BSD | free | free, with attribution | free |
| GPL | free | derivative must be GPL — obligations follow | obligations follow |
| **AGPL** | free | derivative must be AGPL | **obligations apply even as a hosted service** — no file transfer needed |
| proprietary / no licence | assume all rights reserved | ask first | ask first |

Key consequences to state plainly when reporting:

1. **Private use is free.** Reading a copyleft repo, running it, learning from it, keeping a private
   copy for a lab — no obligations attach.
2. **Copying source into a kit that will be redistributed contaminates the kit.** If the kit is kept
   private today but might be shipped tomorrow, the contamination is already baked in.
3. **AGPL reaches network-served use.** Hosting it for others is distribution for AGPL purposes, even
   though no file changes hands.

## What is protected vs what is free

- **Protected: expression.** Source code, prompt text, rule bodies, rule UUIDs, indicator/IOC values,
  literal marker strings, documentation prose.
- **Free: ideas.** Architecture, mechanisms, the shape of a data model, the sequence of a workflow,
  the fact that a technique exists, port numbers, protocol behaviour.

So *"they bridge two graphs with an anchor table and gate steps on a dependency ledger"* is an idea
you may reuse freely. *Their* table DDL, their prompt template, their rule file — are not.

## Procedure

1. **Read for mechanism only.** Write down what it does, in what order, with what inputs/outputs —
   in your own words, before you look at their code again.
2. **Re-implement in our idiom.** Adapt to our toolchain, our file layout, our naming. A
   re-implementation that differs because it fits us better is the *evidence* it is clean.
3. **Provenance header on every artefact.** One block: what it was inspired by, the licence, and the
   sentence **"clean-room re-implementation — no source copied."**
4. **Credit line where the technique originates with them:**
   `Approach inspired by <project> (<licence>); clean-room re-implementation.`
5. **Verify — grep your new files for their identifiers.** This is the step people skip:

```bash
# rule UUIDs, IOC values, user-agent strings, DB table names, framing/marker strings
for pat in "<their-uuid>" "<their-ioc-value>" "<their-ua>" "<their-table>" "<their-marker>"; do
  printf "%-28s hits=%s\n" "$pat" "$(grep -rI -- "$pat" <our-new-files> | wc -l)"
done
```

   Expect **0** for every one. A single hit means something was copied.

6. **Distinguish a citation from a copy.** Naming a fact in your own sentence with attribution —
   "their material lists equivalents (`:8787`, `:8788`); we do **not** reuse their values" — is a
   citation, not a copy. A port number or a protocol constant is a fact. What you must not do is
   reproduce their *expression*: their prose, their rule body, their identifier scheme.

## Pitfalls

1. **Don't paraphrase-just-enough.** Renaming variables and reordering paragraphs is not clean-room;
   it is a derivative work with extra steps. Write from your notes, not from their text on screen.
2. **Don't adopt by importing the pack wholesale.** Importing a licensed skill pack into the library
   is distribution, and it brings the licence with it — plus (see
   `skill-audit/references/orphaned-companion-set.md`) it usually arrives without its companion set
   anyway. Prefer re-authoring the technique.
3. **Don't assume "it's on GitHub so it's free to copy".** No licence is not a permissive licence.
4. **Record the decision in the report, not just in your head.** State the licence, the verdict
   (private use / re-implemented / not adopted), and the grep result. The next session should not have
   to re-derive the legal position.
5. **A deferred item is still an open question.** If something is licence-gated and you did not adopt
   it, write down *why* and *what would unblock it* — otherwise it gets re-evaluated from scratch.
