## ⛔ RULE 23: Unified Pipeline Hard-Won Fixes + Findings Quality Bar

**Session findings (2026-09-26):** full end-to-end run (0A→0F) exposed real bugs and a user-mandated quality bar. Read the full transcript + code recipes in `references/unified-pipeline-fixes-2026-09-26.md`:

- **Infinite recursion**: `force-full-execution.py` must be a LEAF — never re-spawn `audit-run-all.py`/orchestrator (that's what made "STEP 1 never finish").
- **URL→filename sanitization** on Windows for output dirs AND tracker names (no `://`, `/`, `:`, `?`, `=` in paths).
- **C4**: execute ALL matched PoC repos with entry point (required types first, cap 25) — not just REQUIRED_TYPES (else C5 starves).
- **C5**: payload-file patterns must include `CVE-*.py`/`exploit*.py`/`main.py` + code-file fallback (old patterns matched 0/51 repos).
- **aggregate-findings**: recursive rglob (was root-only), schema-complete findings (severity/poc/impact/chain), severity mapped from evidence keywords.
- **chain_builder**: cap 40 signal-findings + `--max-len 3` (permutations of 120 findings = hang).
- **validate-findings**: accept `poc` OR `evidence` OR `text`; auto-reject by-design + phishing/social BEFORE PoC check.
- **`.py` file association on Windows = VS Code opens instead of executing** — always prefix `python.exe "tool.py"`.
- **Findings Quality Bar (finding_gate.py + validate-findings.py)**: DROP = by-design / phishing-social / info-class / dead-chain / speculative. DOWNGRADE = overclaim language / 4xx-as-success / no evidence marker / no impact signal. REPORT = evidence marker + real impact signal. **Low still allowed.**
- **Proof technique**: known-vulnerable express app (13 validated High in ~10 min) vs clean httpbin (0) — proves tools+knowledge sufficient; missing findings = shallow recon (add depth-1 link crawl) or aggregator schema gap, NOT missing tools.

