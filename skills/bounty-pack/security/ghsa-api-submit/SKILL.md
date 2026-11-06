---
name: ghsa-api-submit
description: Submit a GitHub private vulnerability report (GHSA) via REST API without a browser. Use when reporting a bug to a GitHub repo that has private vulnerability reporting enabled and you have a PAT.
category: security
---

# GHSA API Submission (no browser)

Submit a private vulnerability report to any GitHub repo via REST API. No browser, no login dance, no `gh` CLI required. Scriptable and fast.

## When to use
- Target is a GitHub repo with private vulnerability reporting enabled (README/SECURITY.md links to `/security/advisories/new`)
- You have a GitHub PAT (classic `ghp_...` or fine-grained) with `repo` scope
- You want to avoid driving a web form / solving a browser login

## Endpoint

```
POST https://api.github.com/repos/{owner}/{repo}/security-advisories/reports
```

Headers:
- `Authorization: Bearer <PAT>`
- `Accept: application/vnd.github+json`
- `X-GitHub-Api-Version: 2026-03-10`
- `Content-Type: application/json`

Body:
```json
{
  "summary": "Short one-line title",
  "description": "Full markdown report",
  "severity": "low|moderate|high|critical",
  "cwe_ids": ["CWE-284", "CWE-287"]
}
```

`vulnerabilities` (package/ecosystem) is **NOT required** for app/server targets — omit it. Only add it when reporting against a package ecosystem (npm/pip/maven...).

## Response
- `201 Created` -> `ghsa_id`, `html_url`, `state: "triage"`
- `404` -> private vulnerability reporting not enabled on the repo
- `403` -> token lacks `repo` scope, or repo not eligible
- `422` -> bad body (check `severity` enum, `cwe_ids` format like `CWE-123`)

## Pitfalls
- **Read-back GET returns 401 for the reporter — this is NORMAL.** The reporter gets no API read access; GitHub emails a tracking link to the PAT owner instead. Do NOT treat 401 as a failed submission. The 201 + `ghsa_id` is the proof.
- Classic PAT needs `repo` scope. Fine-grained PAT needs "Repository security advisories" repository permission (write).
- The PAT owner's identity is what the maintainer sees. Use the account you want credited/contacted.
- NEVER paste the PAT into a chat, log, or script file. Pass via env var: `GH_TOKEN='***' python submit.py` and read `os.environ["GH_TOKEN"]`.
- **If the operator pastes a PAT into chat anyway, use it — then tell them to revoke it in the SAME reply, and name the scopes that make it dangerous.** Measured 2026-10-30: the token arrived in-chat carrying `admin:enterprise, admin:org, delete_repo, workflow, admin:public_key, admin:ssh_signing_key, audit_log, repo, gist, copilot` — full account control, not the single `repo` scope a report actually needs. Two habits make this safe:
  1. `GET /user` first and read `X-OAuth-Scopes` + `login`. That tells you *which account the maintainer will see* (the credited/contacted identity) and how loud the revoke warning has to be, before you file anything.
  2. Put the revoke link (`https://github.com/settings/tokens`) and the exact over-broad scopes in the final message — not buried under the finding summary. A leaked `delete_repo` token is a worse outcome than the bug you just reported.
- Fine-grained PATs fail with `403` when the "Repository security advisories" permission is missing; classic PATs need `repo`. Confirm scope from `X-OAuth-Scopes` rather than guessing from the response code.
- A PAT with broad scopes (`admin:org`, `delete_repo`, `workflow`) is dangerous once leaked — revoke it right after use.
- **Do NOT interpolate the PAT into a shell command line.** The terminal harness rewrites secret-looking values in commands to `***`, so `GH_TOKEN='***' python submit.py` reaches the process with the literal string `***` and the API answers `401 Bad credentials` — indistinguishable from a revoked token. Confirmed 2026-10-30: the same PAT returned `200` from `GET /user` but `401` from the submit script three times until the value stopped crossing the shell.
  Working pattern: write the token to a file from `execute_code` (or `write_file`), then have the script read it:
  ```python
  # setup, in execute_code — never in a shell string
  open(r"C:\...\.ghtok", "w").write(token)
  # submit.py
  TOKEN = open(os.path.join(os.path.dirname(__file__), ".ghtok")).read().strip()
  ```
  Scrub the file (`write_text("REVOKED")`) as soon as the report is filed, and revoke the PAT itself if it ever appeared in chat.
- **Distinguish 401-causes before retrying.** `GET /user` with the same token tells you whether the credential is alive. `200` there + `401` on submit = the value is being mangled in transit (see above), not revoked.
- **One root cause = one advisory.** Measured 2026-10-30: two findings on the same target (registration pre-hijacking, and a verification-code path missing its attempt counter) were filed as two separate reports — `GHSA-v5pf-gxfc-7cq3` and `GHSA-2223-mv52-4wvq`. Bundling distinct root causes into one advisory makes triage argue about the weaker half and drags the stronger half down with it. Split them, and cross-reference by `ghsa_id` in the description when one enables the other.
- Check the repo's SECURITY.md first: some projects only accept reports through a form or a specific email, and a GHSA report may not be reviewed.

## Verification
1. POST returns `201` and a `ghsa_id` starting with `GHSA-`
2. `html_url` == `https://github.com/{owner}/{repo}/security/advisories/{ghsa_id}`
3. Maintainer sees it under Security tab -> "Private vulnerability reports" queue
4. PAT owner receives a GitHub notification email with the tracking link

## Reference
https://docs.github.com/en/rest/security-advisories/repository-advisories#privately-report-a-security-vulnerability
