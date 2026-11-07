# Re-Zipping the Audit-Pipeline Bundle for Other Agents (2026-09-29)

Use when the user asks: "rebuild the zip so it's updated, give me the path to send to another agent".
The bundle is the portable packaging of the audit pipeline; its source of truth is on disk, and
the ZIP is a derived artifact. Any patch to the live pipeline must end with a re-zip, or the
handoff ships the old code.

## Layout / paths

- Bundle source tree: `~/.chiper/bundle-src/audit-pipeline-bundle-v1`
  (toolkit/scripts, toolkit/tools, skills/, data/, MANIFEST.md, LOAD.md, INDEX.md, _gen_index.py, verify.sh)
- Ship ZIP: `D:\data hermes\audit-pipeline-bundle-v1.zip` — top-level folder inside = `audit-pipeline-bundle-v1/`
- Measured (2026-09-29): 1,720 files, 29.2 MB, compresslevel 6, `testzip()` OK.

## Full update flow (do all six, in order)

1. **Patch the LIVE scripts first** (`~/.chiper/skills/bounty-pack/*.py`).
   Live is primary; the bundle copy is a mirror (user rule: fixes live on the live system).
2. **Sync live → bundle** (automated): `python <hermes>/scripts/bundle-sync.py sync` — syncs every
   bundle target from the live toolkit and verifies md5; `bundle-sync.py check` reports drift
   without writing (exit 1 on drift). Manual equivalent: `cp <live>.py bundle-src/audit-pipeline-bundle-v1/toolkit/scripts/`
   (new helpers like `tool_router.py` get added the same way; confirm with md5sum both sides).
3. **Regenerate the index**: `python bundle-src/audit-pipeline-bundle-v1/_gen_index.py`
   → rewrites INDEX.md from a real walk (prints "N shipped files").
4. **Update MANIFEST.md + LOAD.md** by hand: dependency table (new tools/paths) and a dated
   Changelog line describing exactly what changed.
5. **Rebuild the ZIP** (Python zipfile, NOT the shell `zip` — the dir name contains a space):

   ```python
   import zipfile
   from pathlib import Path
   src_root = Path(r"~/.chiper/bundle-src/audit-pipeline-bundle-v1")
   out = Path(r"D:\data hermes\audit-pipeline-bundle-v1.zip")
   if out.exists(): out.rename(out.with_suffix(".zip.bak-<date>"))   # backup old zip first
   with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
       for p in sorted(src_root.rglob("*")):
           rel = p.relative_to(src_root.parent)   # keeps top-level "audit-pipeline-bundle-v1/"
           if "__pycache__" in rel.parts or ".git" in rel.parts: continue
           if p.is_dir(): z.writestr(rel.as_posix() + "/", "")
           else: z.write(p, rel.as_posix())
   ```

   - compresslevel 9 timed out the terminal on this tree (~62 MB unpacked); 6 is fast enough.
   - Run it as a `background=true` job + `process wait` — the terminal's 60 s cap kills long zips.
6. **Verify from the archive, not the source dir**:
   - `zipfile.testzip()` → must be None.
   - Spot-check that the patched files are in: `any("toolkit/scripts/force-full-execution.py" in n ...)`.
   - **Diff old vs new file lists** (set diff of non-directory, non-`__pycache__` names):
     - `added` = expected (new helpers) —
     - `removed` = files that vanished from disk since the previous build. This happens silently
       (observed: 2 files present in the 2026-09-26 zip were already deleted on disk by 2026-09-29
       and silently dropped from the new zip). Report it honestly instead of assuming the new zip
       is a strict superset.

## Pitfalls

- **Quote native paths everywhere.** `D:\data hermes\...` breaks in bash/MSYS when unquoted;
  prefer Python with `Path(r"...")` for anything touching this zip.
- **Never report the path from memory** — after the build, print the exact ZIP path + size +
  backup path in the reply; the user hands that path to another agent.
- **Don't ship `__pycache__`** — the 2026-09-26 zip accidentally carried 21 .pyc entries;
  exclude them (also keeps the zip smaller).
- The bundle's `MANIFEST.md` says the bundle excludes `D:/data hermes/poc-compact` (654 MB)
  on purpose — only its extracted index (`data/poc-techniques-index.json`) ships. Don't "fix"
  that by adding the raw repo.
- General packaging doctrine (secret scrub, clean-extract verification, stale-bundle hazard,
  skip-if-present loader) lives in the `portable-bundle-packaging` skill — this reference only
  covers THIS specific bundle's rebuild mechanics.

## 2026-09-29 instance (what changed in that re-zip)

- `toolkit/scripts/force-full-execution.py` — per-tool correct CLI syntax, honest status
  vocabulary, `_param_url()`/`_nuclei_template_dir()`, arjun+kxss in MANDATORY_TOOLS.
- `toolkit/scripts/tool_router.py` — NEW in bundle (sqlmap param guard → arjun fallback,
  kxss as xss fallback, graphqlmap `.bat` invoked directly).
- `MANIFEST.md` changelog + `LOAD.md` dependency row (arjun/kxss added).
- `INDEX.md` regenerated (1,720 shipped files).
- Old zip preserved as `audit-pipeline-bundle-v1.zip.bak-20260926`.
