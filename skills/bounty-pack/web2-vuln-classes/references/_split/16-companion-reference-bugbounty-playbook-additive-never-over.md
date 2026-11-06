## Companion Reference — `bugbounty-playbook` (additive, never overrides)

Per-class root cause / bypass tables live here. The companion shelf
`bugbounty-playbook` (mirror of bugbounty.info, 186 pages) adds **chain context and
workflow depth** per class — it never overrides this file's rules:

- End-to-end chain context per class → `references/chains/` (e.g. IDOR→ATO, XSS→ATO, SSRF→cloud RCE, SSTI→RCE, race→financial, GraphQL BFLA→extraction).
- Hunting workflow (target selection, time-boxing, chain thinking) → `references/methodology/`.
- Per-surface TTPs (web/api/cloud/cicd/AI-LLM/mobile/web3) → `references/attack-surface/`.

Read: `skill_view(name='bugbounty-playbook', file_path='references/chains/IDOR-to-ATO.md')`

```


---

