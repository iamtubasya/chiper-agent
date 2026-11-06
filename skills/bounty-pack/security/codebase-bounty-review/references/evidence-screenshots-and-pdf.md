# Evidence screenshots + per-finding PDF (the "make it triager-grade" pass)

When the user says a PoC is *"kurang lengkap"* / *"jgn hanya keterangan singkat"*, they want three
things added to every finding, not prose: **real printed values**, a **screenshot of the run**, and a
**PDF that carries both**. Pipeline below is the one that was accepted.

Order (each step depends on the previous — do not reorder):

```
PoC prints values  ->  run + capture transcript  ->  render PNG  ->  build PDF  ->  QA  ->  rebuild drafts
```

## 1. Make the PoC print values

Rust/Soroban: `extern crate std;` after `#![cfg(test)]`, then `std::println!` (see SKILL.md pitfalls).
Use `{:?}` for `Address`. Print: input state, the attacker action, the resulting values, and a final
boolean line:

```rust
std::println!("[1] Alice deposits 1000 XLM -> vault balance = {}", token.balance(&vault_id));
std::println!("[3] Attacker balance after call = {} (1,000 XLM stolen)", attacker_bal);
std::println!("RESULT: vault fully drained = {}", attacker_bal == X && vault_bal == 0);
```

Vitest: plain `console.log("PoC TL-XX | response status =", res.status, "| called =", mock.mock.calls.length > 0);`
Prefix every line with `PoC <ID> |` — that prefix is what the screenshot extractor keys on.

## 2. Capture one transcript per finding

```bash
cargo test -p <pkg> <poc_name> -- --nocapture > ../_audit/evidence/raw/TL-01.txt 2>&1
npx vitest run __tests__/poc/poc-x.test.ts > _audit/evidence/raw/TL-04.txt 2>&1
```

⚠️ Re-check a transcript for `error[` before treating it as evidence — a crate that failed to compile
still writes a file, and a `lines=0` screenshot is the tell.

## 3. Render a terminal-style PNG (Pillow)

Values that produced a readable, accepted image (1500px wide, Consolas via `C:\Windows\Fonts\consola.ttf`):

| setting | value |
|---|---|
| canvas width | 1500 |
| body font / line pitch | 17px monospace / 31px |
| wrap | 118 chars |
| bg / bar | `#0d1117` / `#161e29` |
| body / RESULT | `#d6e2e8` / green `#7ee787` |
| title bar | 3 traffic-light dots + `Terminal — <ID> PoC evidence` + the `$` command in blue |

Extractor rules (the part that breaks silently):
- **Strip ANSI first**: `re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line)`. Vitest colourises `console.log`,
  so an unstripped `startswith("PoC TL-")` matches nothing and you get a blank image.
- Keep lines starting `PoC TL-`, `[`, `RESULT`, `-----`, and `test test::… ok`; dedupe.
- Script lives beside the audit dir; compute paths from the **audit root**, not `__file__`'s own
  folder if the script sits in a `tools/` subdir.

## 4. Embed images in the PDF

The `md_to_report_pdf.py` converter only handles headings/bullets/code/paragraphs. Patch it to accept
an image line — insert the branch right after the code-fence block, before the `# ` heading check:

```python
m_img = re.match(r"^!\[(.*?)\]\((.+?)\)\s*$", ln.strip())
if m_img:
    from reportlab.platypus import Image as _RLImage
    _cap, _path = m_img.group(1), m_img.group(2)
    if os.path.exists(_path):
        _im = _RLImage(_path)
        if _im.imageWidth > 170 * mm:            # reportlab accepts the absolute path with a space
            _r = (170 * mm) / _im.imageWidth
            _im.drawWidth, _im.drawHeight = 170 * mm, _im.imageHeight * _r
        story.append(_im); story.append(Paragraph(inline(_cap), CAP))
```

Also add a caption style (`CAP`) — 9pt, `#555`. Markdown becomes:

```markdown
![Figure 1 — TL-01 PoC run: the vault is fully drained by an arbitrary caller.](D:/.../evidence/img/TL-01.png)
```

Report structure that satisfied the reviewer (3 pages, per finding):
Summary · Impact · Affected asset **+ vulnerable-code excerpt** · Root cause · Environment ·
**Steps to reproduce (numbered)** · Expected/observed output · **Evidence screenshot** ·
Impact boundary (honest limits) · Remediation · References (CWE).

## 5. QA before shipping

- `pdf_layout_check.py <pdf> --tokens "Page 1 of" <ID>` → `problems=0` on every file.
- Text-layer scan: raw entities, literal markup, non-English leftovers, "watermark"/"draft".
- **Normalise whitespace before substring checks** (`re.sub(r"\s+", " ", txt)`) — a reporter name or
  page token can be split across a line break in the extracted text and produce a phantom FAIL.
- Assert the image actually landed: `sum(len(pg.get_images()) for pg in doc) > 0`.
- Attachment check: `sha256(attached) == sha256(local)` **and** `%PDF-` magic, per draft.

## 6. Rebuild the drafts idempotently

Delete every prior draft matching the subject prefix, then append all N again. Verify by re-fetching
the folder and counting — a delete loop that reports `REMOVED_OLD 0` while the count is still correct
means the previous round's copies were already `\Deleted` (IMAP `fetch` hides them); the net state is
what matters, not the counter.
