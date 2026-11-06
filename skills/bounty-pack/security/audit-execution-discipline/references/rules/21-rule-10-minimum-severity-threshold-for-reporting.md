## ⛔ RULE 10: Minimum Severity Threshold for Reporting

**User correction (2026-09-22): "minimal medium baru kt fu temuannya"**

When the user asks for findings or report, do NOT present Low/Info findings as reportable findings. Only present findings that reach **Medium severity or higher**.

**Workflow:**
- During audit: document ALL findings (including Low/Info) in `findings.json` for completeness
- When reporting to user: FILTER — only show Medium+ findings
- If ALL findings are Low/Info: state clearly "Tidak ada Medium+ findings. Target ini well-hardened."
- Do NOT pad the report with Low/Info findings to make it look substantial
- Do NOT inflate severity to meet the threshold

**Exception:** If the user explicitly asks for ALL findings regardless of severity, then show everything. But default assumption is Medium+ threshold.

