#!/usr/bin/env python3
"""Render a plain-text disclosure e-mail body from typed blocks.

Why this exists: hand-wrapping long prose produces either 200-character lines
that triage teams cannot read, or a re-wrap pass that silently merges separate
bullets into one paragraph (both happened). Typing the body as blocks and
letting this renderer wrap makes the layout deterministic and keeps one idea
per paragraph.

Provenance: the structure mirrors the format Deeper Network handed back as the
model report after rejecting dense prose ("Please use numbered lists and bullet
points", "Please separate sections properly", "Next time, please consider the
reader"). See references/vendor-triage-proofread-structure.md.

Usage
-----
    from render_email_body import render, meta_block
    blocks = []
    blocks += meta_block("YARBO-2026-001", "Title here", "POST /api/x",
                         "Medium, CVSS:3.1/... = 6.5", "CWE-287 ...")
    blocks += [(0, "h", "1. Summary"), (0, "blank", ""),
               (3, "p", "One paragraph, one idea."),
               (3, "bullet", "A list item."),
               (3, "num", "Step 1. Do the thing."),
               (15, "code", "POST /path HTTP/1.1")]
    open("body.txt", "w", encoding="utf-8").write(render(blocks))

Block kinds
-----------
  (indent, "h",    text)   section heading, printed verbatim
  (indent, "p",    text)   paragraph, wrapped to `width`
  (indent, "bullet",text)  "- " bullet, continuation aligned under the text
  (indent, "num",  text)   "Step 3." or "3." marker, hanging indent
  (indent, "code", text)   verbatim, never wrapped (requests, JSON, logs)
  (indent, "meta", text)   verbatim aligned "Field : value" header block
  (indent, "blank","")     paragraph break (idempotent: never doubles)

Rules the renderer enforces automatically
----------------------------------------
  * a blank line between two consecutive paragraphs, and between a bullet list
    and a following paragraph
  * a blank line between a step and the code block that illustrates it, and
    between a code block and the next step
  * signature stays tight (no blank lines inside "Best regards," block)
  * nothing is wrapped above `width` (default 76) except code/metadata
"""

INDENT_BODY = 3
INDENT_CODE = 15
WIDTH = 76

__all__ = ["render", "meta_block", "INDENT_BODY", "INDENT_CODE", "WIDTH"]


def meta_block(report_id, title, endpoint, severity, weakness, contact="RESEARCHER_EMAIL"):
    """The aligned Field : value header that opens every report e-mail."""
    return [
        (2, "meta", "Report ID : " + report_id),
        (2, "meta", "Title     : " + title),
        (2, "meta", "Asset     : see Affected component below"),
        (2, "meta", "Endpoint  : " + endpoint),
        (2, "meta", "Severity  : " + severity),
        (2, "meta", "Weakness  : " + weakness),
        (2, "meta", "Contact   : " + contact),
    ]


def render(blocks, width=WIDTH):
    import re
    import textwrap

    out, prev = [], None
    for ind, kind, txt in blocks:
        pad = " " * ind
        if kind == "blank":
            if out and out[-1] != "":
                out.append("")
            prev = "blank"
            continue
        if kind == "p" and prev in ("p", "bullet") and out and out[-1] != "":
            out.append("")
        if kind == "bullet" and prev == "p" and out and out[-1] != "":
            out.append("")
        if kind == "code" and prev in ("num", "p") and out and out[-1] != "":
            out.append("")
        if kind == "num" and prev in ("code", "bullet") and out and out[-1] != "":
            out.append("")
        if kind == "h":
            out.append(pad + txt)
            prev = "h"
            continue
        if kind in ("meta", "code"):
            out.append(pad + txt)
            prev = kind
            continue
        if kind == "p":
            out.extend(textwrap.wrap(txt, width=width, initial_indent=pad,
                                     subsequent_indent=pad,
                                     break_long_words=False, break_on_hyphens=False))
            prev = "p"
            continue
        if kind == "bullet":
            out.extend(textwrap.wrap(txt, width=width, initial_indent=pad + "- ",
                                     subsequent_indent=pad + "  ",
                                     break_long_words=False, break_on_hyphens=False))
            prev = "bullet"
            continue
        if kind == "num":
            m = re.match(r'^(Step \d+\.|\d+\.)\s+', txt)
            if not m:
                raise ValueError("num block must start with 'Step N.' or 'N.': " + txt[:40])
            mk = m.group(1) + " "
            body = txt[len(mk):]
            out.extend(textwrap.wrap(body, width=width, initial_indent=pad + mk,
                                     subsequent_indent=pad + " " * len(mk),
                                     break_long_words=False, break_on_hyphens=False))
            prev = "num"
            continue
        raise ValueError("unknown block kind: %r" % (kind,))

    text = chr(10).join(out)
    tight = "Best regards," + chr(10) + "RESEARCHER_NAME" + chr(10) + "RESEARCHER_EMAIL"
    text = text.replace("Best regards," + chr(10) * 2 + "RESEARCHER_NAME" + chr(10) * 2
                        + "RESEARCHER_EMAIL", tight)
    return text


if __name__ == "__main__":
    demo = meta_block("ACME-2026-001", "Example", "POST /api/x",
                      "Medium, CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N = 5.3",
                      "CWE-306 Missing Authentication")
    demo += [(0, "h", "1. Summary"), (0, "blank", ""),
             (INDENT_BODY, "p", "A paragraph long enough to wrap so the renderer is visible."),
             (INDENT_BODY, "bullet", "A bullet item."),
             (INDENT_BODY, "num", "Step 1. Do the thing."),
             (INDENT_CODE, "code", "GET /path HTTP/1.1")]
    print(render(demo))
