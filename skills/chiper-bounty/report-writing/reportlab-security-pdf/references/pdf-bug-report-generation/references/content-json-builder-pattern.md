# Content-JSON + generic builder

Every nested-quote trap in SKILL.md shares one root cause: **report content lives inside the
generator source.** `C('''…''')`, line-append with `TQ`, the `execute_code` writer collision, the
"code block ending in a quote" bug — all are content-vs-wrapper collisions.

The cheaper fix is not to dodge them better. It is to keep content out of the generator.

## Shape

Two artefacts per engagement, not one generator per finding:

1. **`content_<FID>.json`** — the report as a list of typed blocks.
2. **`build_pdf.py`** — ONE generic builder, written once, reused per finding.

Block vocabulary: `h1`, `h2`, `p`, `code`, `meta` (list of `[field,value]`), `table` (rows),
`spacer` (points), `pagebreak`.

## Why it works

The JSON is written from `execute_code` with `json.dump`. Content strings are ordinary Python
strings in that cell, so `"`, `'`, backticks, `$function$`, SQL bodies and curl payloads survive
with **zero escaping care**. No `TQ` constant, no line-append bookkeeping, no `ast.parse` ritual
per section, no shell heredoc.

The builder has no content literals, so nothing collides with a quote. It is ~40 lines.

```python
for blk in cfg['sections']:
    t, x = blk.get('t'), blk.get('x')
    if   t == 'h1':        s.append(P(x, H1))
    elif t == 'h2':        s.append(P(x, H2))
    elif t == 'p':         s.append(P(x, BODYS))
    elif t == 'code':      s.append(C(x))
    elif t == 'meta':      s.append(meta_table(x))
    elif t == 'table':     s.append(tbl(x))
    elif t == 'spacer':    s.append(Spacer(1, x))
    elif t == 'pagebreak': s.append(PageBreak())
```

Run `python build_pdf.py content_<FID>.json` once per finding. Both reports come out with
identical furniture, so the style module stays the single source of truth for margins/type.

## Evidence (2026-10, two reports)

The first attempt wrote the generator through a **quoted shell heredoc**:

```bash
cat > gen.py <<'PYEOF'
```

and died with `unexpected EOF while looking for matching `''` — the body contained apostrophes,
so bash never found the terminator. The JSON route replaced it: 7-page and 6-page PDFs built
**first try**, both `layout: clean`, zero `&[a-zA-Z]+;` artifacts.

## Caveats

- **Do not pre-escape the JSON.** `report_style.py` already runs `esc()` inside `C()`/`tbl()`;
  double-escaping prints `&amp;` literally. JSON holds raw text.
- **BUT `P()` does NOT escape — only `C()`/`tbl()` do.** A bare `&` in a `p`/`h1`/`h2` block
  (e.g. a URL fragment `selector=X&sk=Y`, or `a=1&b=2`) renders as an entity artifact
  (`&sk;`) in the PDF. Either keep prose `&`-free (rephrase: "selector=X plus sk=Y"), or run
  `esc()` on `p`/`h` blocks in the builder. `code`/`table` blocks are safe as-is. The pypdf
  assertion (`&[a-zA-Z]+;` must be empty) catches this — run it on every build, it found a
  live `&sk;` that the layout gate passed.
- **Sweep named entities before building**, as on any path:
  `s.replace("&mdash;","\u2014")`, then assert `not re.findall(r'&[a-zA-Z]+;', s)`.
- **Re-staging is cheap**: edit JSON, re-run builder, re-run `qa_pdf_layout.py --margin-mm 14.8`.
  A rebuilt PDF is still a changed PDF, so the staged draft is stale — delete then append.
- **One finding = one JSON = one PDF.** A generic builder does not license merging findings.
