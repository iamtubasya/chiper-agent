# Submitting findings to a GitHub-hosted target (Private Vulnerability Reporting)

Many source-only targets ship a `SECURITY.md` pointing at `security@<domain>`. **Verify that address
before you build drafts around it** — then prefer the repo's own reporting channel.

## Step 1 — is the advertised contact real?

| Check | Command / signal | Verdict |
|---|---|---|
| MX | `dig +short MX <domain>` → `(root)` | **null MX** — the domain accepts no mail |
| A + parking | A-record hits a parking IP; `/.well-known/security.txt` 302 → `/lander` | parked |
| TLD siblings | `.app` / `.finance` / `.org` → NXDOMAIN | only one parked domain |
| Real fallback | `git log -1 --format=%ae` on the repo, plus the maintainer's personal site `mailto:` | two independent sources = trustworthy |

Two independent sources agreeing (commit author **and** personal site) is the bar before you
re-address a disclosure. Record the dead-address evidence in the report/PHASE_LOG so the recipient
sees why the channel changed.

## Step 2 — is Private Vulnerability Reporting enabled?

```bash
curl -s https://api.github.com/repos/<owner>/<repo>/private-vulnerability-reporting   # {"enabled":true}
```

Web form for a human: `https://github.com/<owner>/<repo>/security/advisories/new`
(redirects to login unauthenticated). Generate paste-ready text per finding if the user prefers manual.

## Step 3 — the API (external reporter path)

```
POST /repos/{owner}/{repo}/security-advisories/reports
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2026-03-10
{"summary": "...", "description": "<full markdown report>", "severity": "critical|high|medium|low",
 "vulnerabilities": [{"package": {"ecosystem": "other", "name": "<repo>"},
                      "vulnerable_version_range": "all versions (rev <sha>)"}]}
```

⚠️ Do **not** confuse it with `POST /repos/{owner}/{repo}/security-advisories` — that **creates an
advisory** and requires security-manager/admin on the repo. An external researcher gets 401/403 there.
Probe both unauthenticated: `401` = endpoint exists, needs auth.

Retry the POST **without** the optional `vulnerabilities[]` block on `422`.

## Step 4 — token type (the usual wall)

| Token | Requirement | Note |
|---|---|---|
| fine-grained PAT | repo permission **Repository security advisories: Read and write** | need Repository access = All repositories to make `write` selectable |
| classic PAT | scope **`public_repo`** | worked here; `X-OAuth-Scopes: public_repo` |

Diagnose a rejection from the response headers, not the message:

```
403  x-accepted-github-permissions: repository_advisories=write   -> the token is missing that permission
```
A `401 Bad credentials` almost always means the token value never reached the process (see below).

## Step 5 — two blockers you WILL hit

1. **Content-creation secondary limit.**
   `403 {"message":"You have exceeded a secondary rate limit and have been temporarily blocked from content creation."}`
   Typical of a **young / low-history account**. It fires on the *first* POST, so pacing does not help.
   Nothing is created (403 = rejected, no side effect). Options: retry later, submit through the web
   form, or use a more established account. Report `0/N submitted` honestly — do not imply partial success.

2. **The secret-scrubber eats the token out of your own command.**
   Typing a token into a terminal command can get it replaced with `***` before execution, leaving a
   broken command (`unexpected EOF while looking for matching "`) or a literal `***` in the env var
   (`echo ${#VAR}` → `3`, not 40). Writing the literal `SECRET = "value"` shape into a **file** can be
   mangled too.
   **Fix: never put the secret in a command or a file you author — have the script read it from a path
   the user populates**, e.g. `token = os.environ.get("GITHUB_TOKEN") or open(HERE/".gh_token").read().strip()`,
   then ask the user to drop it in once. Verify with a length/prefix print before spending a request.

## Step 6 — gate the send (do this every time)

Default the script to **dry-run**; require BOTH a token AND an explicit confirmation env var
(`I_CONFIRM_USER_FINISHED_READING=yes`) to POST. Keep a resumable state file
(`evidence/pvr-submitted.json`) keyed by finding id so a re-run only sends what is missing and never
duplicates a report. Print `OK <id> -> <url>` / `FAIL <id> <code> <msg>` per finding.

Prove the gate actually refuses (run it once with no token, once with a token but no confirmation)
before telling the user it is ready — "it can't fire early" is a claim you should have demonstrated.
