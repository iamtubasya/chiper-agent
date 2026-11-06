# Self-hosted / on-prem product labs (Octopus Deploy worked case)

For engagements where the in-scope "target" is a **product you must install yourself**
(Octopus Server/Tentacle, GitLab, Jira DC, SonarQube, Confluence, …) rather than a hosted domain.
Your attack surface is a lab you build; the deliverable is a finding in the shipped product.

## 0. Read the brief for the two things that decide feasibility

- **Which build is in scope.** "Currently supported versions on our website" usually means the vendor's
  latest release channel. Grab the exact installer/container tag, not a random version.
- **What the vendor already excludes.** Octopus's brief pre-excludes: descriptive error messages /
  stack traces, all non-200 pages, missing-headers, TLS/cipher issues, self-XSS, source-code disclosure,
  non-confidential info disclosure, and known-library CVEs without proven exploitability. Half the
  "findings" a scanner produces are on that list — do not spend the session there.

Many briefs also hand you a **free/trial licence** for a researcher address. Take it; you cannot test a
server-side feature without a running server.

## 1. Host capacity FIRST — before you build anything

```bash
powershell.exe -NoProfile -Command "[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024)"
powershell.exe -NoProfile -Command "(Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors"
```

A **6 GB / 4 vCPU** host running Docker Desktop + SQL Server + a large .NET app will thrash. The symptoms
impersonate product bugs and cost hours:

- `docker ps` / `docker logs` / `docker cp` stop returning (60 s timeouts) while `echo` still works;
- the product's HTTP API answers `000` / empty reply (connection accepted, no response);
- the product's own startup commands spin at 80 % CPU for minutes and look hung;
- containers land in `Exited (255)` together after the Docker VM restarts.

Mitigations that worked: cap the database (`MSSQL_MEMORYLIMIT_MB: "1024"`), stop unrelated lab
containers (`docker start <name>` restores them — stopping is reversible, say so in the report),
run long verbs under `timeout`/background instead of assuming a hang, and re-check free RAM whenever
everything goes slow.

## 2. Docker recipe — Octopus Server + SQL Server 2022

The server has **no PostgreSQL support** (verify by listing the image's `Microsoft.Data.SqlClient*` /
`EntityFrameworkCore.SqlServer` and the absence of any `Npgsql*`). SQL Server is mandatory.

- **`DISABLE_DIND=Y` on BOTH images.** The server image boots dockerd for container workers; under
  Docker Desktop the DinD daemon dies (`Docker-in-Docker Daemon exited with code 32`) and the container
  takes itself down. The tentacle image has the same flag inside `run-tentacle.sh`.
- **Pin `MASTER_KEY` AND mount the config dir.** `install.sh` writes the master key into `$HOME/.octopus`
  (root's home), *not* the documented config volume. Recreate the container → a fresh master key is
  generated while the DB volume still holds data encrypted with the old one →
  `Failed to decrypt the Octopus Server certificate`. Fix: set `MASTER_KEY` to the value the first boot
  printed, **and** add `- <volume>:/root/.octopus`. With the marker in that volume, later boots skip
  setup entirely and come up in ~2 min instead of ~15.
- **SQL healthcheck needs room:** `start_period: 150s`, `timeout: 25s`, `retries: 40`. With a 5 s timeout
  compose gives up with `dependency failed to start: container octo-sql is unhealthy` even though SQL is
  perfectly healthy — a healthcheck artefact, not a broken DB.
- **`restart: unless-stopped` on every service**, or one engine/VM restart leaves you with `Exited (255)`
  and no lab.
- Licence via `OCTOPUS_SERVER_BASE64_LICENSE`; admin bootstrap via `ADMIN_USERNAME` / `ADMIN_PASSWORD` /
  `ADMIN_EMAIL`.
- API key for testing: `docker exec <server> ./Octopus.Server admin --instance OctopusServer --username admin --apiKey "API-XXXX"`.
  **The key must start with `API-`** — the server rejects anything else with a specific message, and each
  such invocation is a full (slow) app start, so run it in the background.

## 3. Octopus REST API mechanics (the parts that cost iterations)

Auth: `X-Octopus-ApiKey: API-...` (no CSRF) or a login cookie **plus** `X-Octopus-Csrf-Token` (the value
is the `Octopus-Csrf-Token_<installId>` **cookie**, not a meta tag). Without the header, every cookie-authed
write returns `403 "A required anti-forgery token was not supplied or was invalid"` — which reads exactly
like an RBAC denial. Always check which of the two you are looking at before recording a negative.

Discovery: `GET /api/` returns ~180 links; the class-level collections hang off space-scoped paths
(`/api/Spaces-1/<resource>`) that are NOT listed at the root.

| Action | Path / payload note |
|---|---|
| Create deployment-process step | `PUT /api/Spaces-1/projects/<id>/deploymentprocesses` (no trailing id) |
| **Step target roles** | live in the **step-level** `Properties["Octopus.Action.TargetRoles"]`, NOT inside `action.Properties`. Wrong location → `400 "Please select one or more target tags…"` |
| Step shape | `step.Actions = [ { ActionType, Name, Properties } ]`; a step with no `Actions` → `400 "does not have any actions"` |
| Create release | `POST /api/Spaces-1/releases` (root-level, not under the project) |
| Create runbook snapshot | `POST /api/Spaces-1/runbookSnapshots` |
| Publish a runbook snapshot | `PUT` the runbook with `PublishedRunbookSnapshotId` set — otherwise the run returns `400 "Runbook has no published snapshot"` |
| Deploy | `POST /api/Spaces-1/deployments` → returns `TaskId` |
| Task log | `/api/tasks/<id>/raw`, `/api/tasks/<id>/details[?verbose=true]` |
| Scoped user role | `POST /api/Spaces-1/scopeduserroles` (space-scoped). Posting to `/api/scopeduserroles` with a space-level role → `400 "cannot use a role with Space level permissions at the System level"` |
| Create space | needs `SpaceManagersTeams` (+ `SpaceManagersTeamMembers`, `ExtensionSettings`) or `400` |
| Create team | needs `ExternalSecurityGroups: []` or `400` |

Register a tentacle by env var (no CLI): `ACCEPT_EULA=Y, DISABLE_DIND=Y, ServerUrl=http://<server>:8080,
ServerApiKey=..., TargetEnvironment=<env> + TargetRole=<role>` (deployment target) **or**
`TargetWorkerPool=<pool> + TargetRole=<role>` (worker). `ServerUrl` must be the in-network address.

## 4. Testing the "sensitive variable masking" control

The masking control is the vendor's own stated focus area on this program, and it is testable end-to-end
with no tentacle at all once a worker/target exists.

Method: create a project + sensitive variables + a Bash step that echoes them, deploy, then diff the raw
task log against the values. Vary **one** dimension per run:

- value **length** 1, 2, 3, 4, 8, 16 → finds a hard cut-off;
- full value vs `head -n 1` / `head -n 2` / `tail -n 1` / `cut -c1-20` / embedded in a larger line;
- multi-line values of 2, 3, 20, 40 lines;
- the same value through `/raw`, `/details` and `/details?verbose` (leaks were identical on all three).

Verified result against Octopus Server 2026.3.15882 / Tentacle 12.2.4509 (two findings):

1. Values **shorter than 4 characters are never masked** — boundary exactly at 4.
2. Only an **exact complete occurrence** is replaced. Any partial reproduction (a prefix, one line of a
   multi-line value, the value embedded mid-line) is written to the task log **in cleartext**, including
   via bash `command not found` errors that echo a line of the value.

Root cause, with the code in the public Tentacle source and the *same classes shipped inside the server*
(`Octopus.Core.dll` / `Octopus.Shared.dll` / `Octopus.Server.dll` all contain
`SensitiveValueMasker` / `SensitiveDataMask` / `AhoCorasick`):

- `SensitiveValueMasker.CreateTrie()` — `if (string.IsNullOrWhiteSpace(instance) || instance.Length < 4) continue;`
- `AhoCorasick.Find()` reports only complete matches; `SensitiveDataMask.ProcessDeferred()` / `Flush()`
  pass a buffered "partial match" chunk to the output action **unchanged** when no complete match spans it.

Attribution trick worth reusing: grep the shipped server DLLs for the class names you found in the open
source component. If the same class ships in both, the root cause is shared and the finding is not
"tentacle-only".

## 5. RBAC / multi-space matrix that actually proves something

Build it properly or don't claim a result:

- user + team + **space-scoped** user roles, then a real cookie+CSRF login (or that user's own API key).
- Test the **permission-bearing** writes, not just reads: user/team/role/variable/project/workerpool/feed/
  environment/config, plus `GET /api/configuration`.
- **Do not score an RBAC result off a `400`.** Octopus runs model binding/validation for some endpoints
  before the permission check, so an incomplete payload returns `400` and looks like "the check was
  bypassed". Re-send a **valid** payload; the real answer is `403 "Missing permission: ProjectCreate"`.
  Confirm against the role's `GrantedSpacePermissions` list — the union the user holds either contains the
  permission or it doesn't.
- Cross-space isolation: create a second space as admin, confirm the low-priv user gets `403` on every
  resource in it and that `GET /api/spaces` lists only their own space.
- Note the benign-by-design ones so they aren't re-investigated: a user may edit their own profile
  (`PUT /api/users/<own-id>` → 200) and mint their own API key; a `deploymentcreator` role legitimately
  gets `201` on `POST /api/deployments`.

## 6. Writing it up

The brief may mandate **plain text only** (PDF/DOCX gets bounced). Lead with the focus-area language the
vendor used, give numbered repro steps with the exact variable values and step body, then show the raw
log lines, then the root cause with file/class names, then impact, then remediation. State explicitly
that the platform mis-masks rather than framing it as the script's fault, and keep the honest negatives
in a coverage ledger — a well-run negative on the vendor's *other* stated focus area is what makes the
positive credible.
