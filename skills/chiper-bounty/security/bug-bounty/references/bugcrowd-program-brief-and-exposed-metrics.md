# Bugcrowd program-brief extraction + exposed-`/metrics` recon

## Extract the brief without a login (works on live Bugcrowd engagements)
The engagement page (`/engagements/<slug>`) is a JS SPA; the brief renders client-side and is
generally login-gated in the HTML. But the changelog endpoint serves the whole brief as JSON with a
`.json` suffix on the path:

1. Find the changelog id in the page HTML:
   `curl -s https://bugcrowd.com/engagements/<slug> | grep -oE 'changelog/[0-9a-f-]{36}'`
2. Fetch the brief JSON (no auth):
   `curl -s https://bugcrowd.com/engagements/<slug>/changelog/<id>.json`
   → `data.brief` = description, general rules, `targetsOverview` (OOS list), `safeHarborStatus`
   → `data.scope` = list of groups, each with `name`, `inScope`, `rewardRangeData` ({1..5: min/max}),
     `targets[]` (uri, category, tags) — i.e. the entire in/out scope + per-tier payouts
   → `vrtVersion`
3. Public stats (no auth): `/engagements/<slug>/statistics` (rewardedVulnerabilities, averagePayout,
   validationWithin), `/engagements/<slug>/scope_ranks`.

Pitfalls:
- Under MSYS/git-bash, `curl -o relative.json` writes to the Windows cwd, not the shell's `/tmp` →
  always use absolute output paths, or pipe straight into python.
- `curl ... | python3 - <<'EOF'` is a trap: the heredoc steals stdin and python reads the script
  instead of the pipe. Write the parser to a file and use `python3 file.py < input`.

## Enforce the real scope — "allow-all" is wrong for a vendor program
A Bugcrowd engagement has defined tiers and an explicit OOS list. Read them and respect them: firing
at out-of-scope hosts = rejected findings + account ban, not "maximum coverage". Honour per-program
rules verbatim — e.g. Tripadvisor requires the string `bugcrowd` in the User-Agent, accounts and
display names containing "bugcrowd", test-properties only, and forbids DoS / social engineering /
AI-system attacks / touching live properties-customers.

## Egress triage
- WARP egress (104.28.x.x) is often WAF-flagged (DataDome/GeeTest). Check `warp-cli status` before
  concluding a target blocks you; `warp-cli disconnect` / `connect` toggles it.
- BUT a *total TCP timeout* (`curl` code `000`, every IP on :443 `CLOSED/FILTERED`) to one specific
  host = that host allow-lists source IPs (typical for partner/payment APIs) → changing egress will
  NOT help. Don't burn time rotating.
- Turning WARP OFF can make main hosts return 403 (worse). Keep it ON when it's the cleaner path.

## Hunt vector: unauthenticated Prometheus `/metrics`
API hosts frequently expose the Prometheus scrape endpoint on the public listener. Probe with a clean
session (no cookie / no auth header): `/metrics`, `/prometheus`, `/actuator/prometheus`, `/-/metrics`.
Confirm by response `content-type: text/plain; version=0.0.4;charset=UTF-8` and `# HELP` / `# TYPE`
lines. Try sibling hosts too — often only one is open.
The value is in what the labels leak: internal microservice names (`hs-partner-auth`, `meta_hac`,
HSS, device registry), `method_name=` / `endpoint=` API-method inventories, controller class names
(`RegistrationController`), internal business/revenue counters (CPC revenue, click tracking).
Classify as **Sensitive Data Exposure → Information Disclosure (exposed monitoring interface)**; per
Bugcrowd VRT this is LOW (P4, `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` = 5.3) unless labels
carry secrets/PII. Read-only, single request, no DoS.

## Report staging (Gmail draft)
The user wants report text staged as a Gmail draft in `[Gmail]/Draf` (reusable mechanism: read the app
password from `~/check_basabasi_email.py`, IMAP `imap.gmail.com`, `APPEND` with `(\Draft)`; delete any
prior draft of the same subject first so there is exactly one). Caveat: Bugcrowd submissions go
through the **platform form** (`/engagements/<slug>/submissions/new`), NOT email — the draft is a
staging container addressed to self and is never sent. A PoC/report is only staged once there is a
VERIFIED finding (working reproduction); never draft a report for an unconfirmed lead.
