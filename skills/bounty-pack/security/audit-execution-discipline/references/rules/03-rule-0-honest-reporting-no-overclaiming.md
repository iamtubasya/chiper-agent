## ⛔ RULE 0: Honest Reporting — NO Overclaiming

**User correction: "kamu harus stop overclaim, stop juga laporan bohong yg mana bilang udh dilakukan ternyata tidak, stop halu, biasakan pekerjaan kamu sesuai fakta, laporan yg detail apa yg sudah dan apa yg belum dilakukan tiap phase, harus ada check point yg memeriksa ulang"**

**MANDATORY:** Before claiming ANY phase complete, run verification checkpoint:
```bash
python ~/.chiper/skills/bounty-pack/audit-checkpoint.py <target_dir> --phase <phase>
```
Only claim COMPLETE if checkpoint returns ALL ✅. If any ❌, that phase was NOT done.
The checkpoint reads ACTUAL FILES FROM DISK — not self-reported claims.

> **Phase-set parity (0A–0F) + the glob/`is_file()` trap + the doc sweep:**
> `references/phase-set-parity.md`

**⛔ HARD BLOCK: NEVER generate report with "zero findings" unless:**
1. ALL 30 vectors executed with REAL TOOLS (sqlmap/dalfox/SSRFmap, bukan curl)
2. ALL 10 exploit chain layers completed
3. ALL checkpoint checks PASS (audit-checkpoint.py)
4. findings.json exists
5. Every "negative" finding has PROOF (terminal output showing tool ran)
If checkpoint shows incomplete → DO NOT GENERATE REPORT. Go back and finish.

**⛔ Auto-save state after every step:**
```bash
python ~/.chiper/skills/bounty-pack/audit-state.py save <target> --phase <X> --step "<what>"
```

**Prohibited claims:**
- ❌ "All vectors tested" without checkpoint showing 30/30 with evidence
- ❌ "All refs loaded" without tracker confirmation
- ❌ "Phase complete" without checkpoint passing
- ❌ "Tool executed" without terminal output as proof
- ❌ "Finding proven" without tool output for every step
- ❌ "File exists" without terminal ls/verify showing it
- ❌ "Skill updated" without skill_view confirming content changed

