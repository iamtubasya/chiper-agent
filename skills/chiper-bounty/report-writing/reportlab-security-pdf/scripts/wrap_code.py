"""Wrap source text so it fits a reportlab Preformatted block.

`Preformatted` renders lines verbatim — it never wraps and never raises, so a long PoC line simply
overhangs the frame. This wraps at a fixed column with a hanging indent for continuations, and maps
the non-ASCII characters code comments always carry onto ASCII.

Usage:
    from wrap_code import wrap_code
    CODE_W = 84          # Courier 9pt inside a 482pt frame, minus padding
    flow.append(Preformatted(wrap_code(poc_src, CODE_W), CODE))

Verify after build with the block-bbox gate in references/embedded-poc-layout.md.
"""

_NON_ASCII = {
    0x2014: "-",    # em dash
    0x2013: "-",    # en dash
    0x2019: "'",    # right single quote
    0x2018: "'",    # left single quote
    0x201C: '"',    # left double quote
    0x201D: '"',    # right double quote
    0x2026: "...",  # ellipsis
    0x00A0: " ",    # nbsp
}

CODE_W_DEFAULT = 84


def wrap_code(text, width=CODE_W_DEFAULT):
    """Wrap `text` to `width` columns, hanging-indenting continuation lines."""
    for cp, repl in _NON_ASCII.items():
        text = text.replace(chr(cp), repl)

    out = []
    for line in text.split(chr(10)):
        line = line.replace(chr(9), "  ").rstrip()
        if len(line) <= width:
            out.append(line)
            continue

        indent = len(line) - len(line.lstrip())
        hang = " " * min(indent + 2, width - 8)
        rest = line
        first = True

        while len(rest) > width:
            cut = rest.rfind(" ", 0, width)
            # no usable break point (e.g. a long base64 blob) -> hard cut at the column
            if cut <= (0 if first else len(hang)):
                cut = width
            piece = rest[:cut]
            out.append(piece if first else hang + piece)
            rest = rest[cut:]
            if rest.startswith(" "):
                rest = rest[1:]
            first = False

        out.append(rest if first else hang + rest)

    return chr(10).join(out)


if __name__ == "__main__":
    import sys

    src = open(sys.argv[1], encoding="utf-8").read()
    w = int(sys.argv[2]) if len(sys.argv) > 2 else CODE_W_DEFAULT
    wrapped = wrap_code(src, w)
    longest = max(len(l) for l in wrapped.split(chr(10)))
    print(wrapped)
    print(f"--- max line width: {longest} (limit {w})", file=sys.stderr)
    assert longest <= w, "wrap failed"
