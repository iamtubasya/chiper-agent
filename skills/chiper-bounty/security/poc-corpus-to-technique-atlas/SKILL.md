---
name: poc-corpus-to-technique-atlas
author: RESEARCHER_NAME
description: >-
  Turn a local PoC corpus (thousands of GitHub PoC repos, nuclei templates) or an oversized
  reference shelf into a lean, deduped METHOD-level technique atlas. Pipeline: classify by
  vuln class -> pull the technique (never the code) -> filter malware/scam -> dedupe ->
  write per-class reference files + 00-INDEX -> cross-link owner skills. Use when the user
  says "extract the techniques from this corpus", "80k PoCs but not all extracted", "turn
  the PoC dump into a skill", "distill the reference skills", "extract blog/disclosure
  techniques", or when a reference directory has grown too large to be read. Produces
  poc-technique-atlas output; never copies payload bodies.
metadata:
  hermes:
    tags: [security, poc, corpus, techniques, distillery, skills]
---

# PoC Corpus → Technique Atlas

Grow a knowledge base instead of a storage bin. From a big PoC dump you extract **methods**
(what the bug does, the transferable trick) and drop the raw code, malware, and duplicates.
The result is a shelf the agent can actually read during an audit.

> Real run this encodes: `D:/data hermes/poc-compact` (2,223 GitHub PoC repos) +
> `nuclei-templates` (13,777) + PortSwigger WSA + YesWeHack blog → skill
> `security/poc-technique-atlas` (28 classes / ~1,950 techniques + detection index +
> distilled shelf). Also distilled the pre-existing 18 MB shelves (-24x).
> Scripts: `D:/data hermes/_poc_techniques/` and `~/extract_*.py`.

---

## When to use

- "Ekstrak tekniknya dari korpus/situs/repo ini jadi skill."
- A corpus (PoC repos / nuclei) or reference shelf that is too big to read.
- You want techniques, **not** a mirror: the user explicitly says the raw dump "just grows
  storage and won't be used".

## Hard rules

1. **Extract the METHOD, never copy the code/payload body.** One line per technique +
   an exemplar repo id. No exploit bodies (also AV-safe).
2. **Filter malware/scam BEFORE it enters.** Drop repos that ARE malware tooling, keep PoCs
   that target a vuln (even in C2 frameworks). See the filter below.
3. **Dedupe.** Signature on class + normalized technique words; skip repeats.
4. **Additive integration only.** New skill + append-only cross-links; never reorder an
   owner skill's workflow. Owner rules win on conflict.
5. **Never delete an oversized shelf without confirmation** — archive (move) with a pointer.
6. **Verify** — read every output file (AV), YAML-parse every touched SKILL.md, count.

---

## Pipeline

### 1. Inventory (know what's already covered)
```python
# per skill: SKILL.md size, #references, ref bytes -> pick the big ones
for root,_,fs in os.walk(SKILLS):
    if "SKILL.md" in fs: ...
```
Record the largest shelves so you can dedupe against them.

### 2. Fingerprint the source
| Source | Bulk content | Fallback |
|---|---|---|
| Quartz site | `/static/contentIndex.json` | sitemap crawl |
| MkDocs | `/search/search_index.json` | sitemap crawl |
| Next.js blog | site `rss.xml` / `feed` | render via CDP |
| GitHub PoC dump | walk repo dirs; `README.md` first | shallow code header comment |
| nuclei | walk `*.yaml`; `info.name`/`tags` | — |

### 3. Classify + extract the technique
- Classify by **name + first README line** against class regexes (rce, sqli, xss, ssrf, …).
- Technique = first meaningful line of `README.md` (strip badges), else a header comment
  in a shallow code file that mentions exploit/poc/bypass/inject/…
- Output row: `technique (method) | exemplar repo`.

### 4. Filter malware / scam (subject test, not keyword test)
```python
MAL_TOOL = r"(stealer|keylogger|ransomware|botnet|rootkit|spyware|clipper|wiper)|" \
           r"\b(rat)\b.*(builder|panel|server)|\bc2\b.*(framework|panel)|(xmrig|cryptominer)|" \
           r"(dropper|loader)\b.*(builder|fud)|phish.?kit|carding|skim(mer|ming)|credential.dump"
LEGIT = r"\bcve-\d{4}-\d+\b|\bpoc\b|detect|vulnerab|patch|disclos|research|writeup|analysis"
drop = MAL_TOOL.search(name+desc) and not LEGIT.search(name+desc)
```
Pitfall hit in real run: a naive keyword filter drops legit CVE PoCs ("XZ backdoor",
"ransomware chain", "Empire C2 RCE PoC"). Always require the **LEGIT** escape hatch, then
re-scan the output for residual indicators and audit each hit by hand.

### 5. Dedupe + lay out
```
<poc-technique-atlas>/references/
  00-INDEX.md            # class table: what it covers | technique count | file
  <class>.md             # | # | Technique (method) | Exemplar repo |
  nuclei-detection.md    # per-class matcher kinds (word/status/dsl/regex) + severity mix
  portswigger/           # WSA topics
  distilled/             # distilled index of the pre-existing shelves
  web-blogs/             # blog/disclosure technique posts
```

### 6. nuclei detection index (what to look for)
matchers are **nested under protocol sections** (`http:`, `dns:`, `tcp:`), NOT top-level.
Walk `d[proto]` lists and collect each matcher's `type` (word/status/regex/dsl/binary/size).

### 7. Distill existing oversized shelves
For each reference file: title + section headings + technique-like bullets → one card.
Real numbers: 730+89+69+187 files / ~20 MB → 827 KB (~24x).

### 8. Archive the raw bloat (needs confirmation)
Move (never delete) vendored sub-dirs to `D:/data hermes/_archive/refs-<date>/<skill>__<sub>`
and leave `skills/security/bug-bounty/references/ARCHIVED-SHELVES.md` pointing at the archive + the distilled index.
Real run: moved 16.15 MB (src-hunter 12.7 MB alone) → shelf 18.3 MB → 2.7 MB.

### 9. Cross-link owners (additive) + making it MANDATORY
Append a "Companion Reference — `poc-technique-atlas`" block listing the index + classes to
the END of each owner SKILL.md (`exploit-cookbook`, `bb-audit-launcher`, `bug-bounty`,
`vuln-hunter`, `audit-execution-discipline`, `web2-vuln-classes`, `security-arsenal`,
`hunt-dispatch`, `bb-methodology`, `bugbounty-playbook`).

For per-phase use, add it to the launcher's phase loading matrix and the router
(`bb-audit-launcher`, `bug-bounty`, `audit-execution-discipline`, `vuln-hunter`,
`autonomous-vuln-researcher`), phrased as: *"on-demand shelf — read ONE class file per phase,
does NOT count against the phase context budget"* (a shelf that counts against context gets
dropped). Where to read it:
- Phase 0B recon / 0C attack-surface mapping → `00-INDEX.md`, pick 1 class file.
- Phase 0C per-class testing → that class file + `nuclei-detection.md` for the observable.
- 0E review → `distilled/` before opening any heavy original shelf.

### 10. Verify
Read every output file (catches AV blocks), YAML-parse every touched SKILL.md, count
classes/rows, confirm 0 malware lines remain.

---

## Pitfalls (all hit in real runs)

- **Malware filter too aggressive** → drops legit CVE PoCs. Use the LEGIT escape hatch + audit.
- **nuclei matchers**: nested under protocol keys, not top-level. A top-level scan yields 0.
- **Next.js blogs**: body is client-side; `__NEXT_DATA__` often has only menu/footer. Use the
  site RSS for the article list; render only key articles via CDP for structure.
- **CDP page selectors** in a rendered article hit the nav `<h3>`s, not the body — scope to
  `main`/`article` or drop nav labels.
- **skill_manage patch rejects SKILL.md > 100 KB** — append via the generic `patch` tool.
- **Never bulk-load the shelf into context** — it exists to be read one file at a time.
- **Keep reference filenames distinct from skill names** (a vendored `rce/` dir shadowing a
  skill name breaks `skill_view('<name>')`).
- Confirm before deleting anything; archive (move) + pointer is the safe default.

## Files

- `D:/data hermes/_poc_techniques/` — extracted technique data + distill outputs.
- `~/extract_poc_techniques.py`, `~/build_atlas.py`, `~/extract_nuclei_index.py`,
  `~/distill_refs.py`, `~/link_atlas.py`, `~/archive_shelves.py` — the pipeline scripts.
