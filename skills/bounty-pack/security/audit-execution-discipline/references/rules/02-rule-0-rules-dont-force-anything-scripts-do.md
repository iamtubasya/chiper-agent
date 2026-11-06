## ⛔ RULE 0: RULES DON'T FORCE ANYTHING — SCRIPTS DO

**User correction (2026-09-22): "Enforce, rule, checkpoint, skr hard gate, tapi semua apa efeknya? Tetap kamu langkahi juga, sy mau solusi permanen"**

ALL the rules below are advisory — the agent CAN read them and still skip.
The PERMANENT fix is: **USE THE SCRIPT, NOT THE RULES.**

```
PRIMARY METHOD (permanently forces execution):
python C:/Users/WINDOWS10/AppData/Local/hermes/scripts/audit-run-all.py <TARGET> --tech "<tech>"

This ONE SCRIPT forces all phases (0A→0F) with real tools.
Every step is disk-verified. Phase-model drift + blocker/operator discipline:
`references/phase-model-alignment-and-blocker-discipline.md`.

SECONDARY: Manual steps below are FALLBACK only when audit-run-all.py fails.
```

**Why:** Rules are text the agent can ignore. Scripts are code that forces execution. ALWAYS prefer the script.

**⛔ RULE 0-A: REFERENCE SHELF IS CONSULTED EVERY AUDIT — `bugbounty-playbook`.** The
`bugbounty-playbook` skill (mirror of bugbounty.info, 186 pages) MUST be read from during every run —
it is an on-demand shelf, not a load-and-evict skill, and does not count against phase budgets.
Loading the skill once and never opening a page = SKIPPING it. Mandatory consult points, one page each:
`references/00-INDEX.md` (catalogue) · 0B → `references/recon/<page>.md` · 0C → `references/attack-surface/<track>/<class>.md`
· 0C-escalate → `references/chains/<chain>.md` · 0F → `references/reporting/<page>.md`.
Read via `skill_view(name='bugbounty-playbook', file_path='references/...')`. Record which page was read at
each point in PHASE_LOG.md (proof, not narrative). Owner rules (triage-validation always-rejected list,
PART 0 gate) override its content.

