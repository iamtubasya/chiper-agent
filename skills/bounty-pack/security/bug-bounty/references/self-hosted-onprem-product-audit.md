# Self-hosted / on-premise product audits (Octopus Deploy worked case)

Reach for this whenever the program scope is a **product** (installer, Linux package, container
image) rather than a website: "test our on-prem/self-hosted Server + Agent". Bugs' impact lives in
the shipped binary, so there is **no hostname to enumerate**. Web scanners (nuclei / ffuf / gobuster
/ sqlmap / dalfox / smuggling / cache) are **N/A** — mark them N/A in the coverage ledger, do not
count them as "not run".

The work is three phases: **(1) build a lab from the vendor's own download, (2) drive the product's
own API as the test harness, (3) white-box the shipped assemblies/source for the control you are
probing.**

---

## 1. Scope reality check (do this before anything else)

- Jot the brief's exclusions verbatim into `SCOPE.md`. Self-hosted briefs almost always exclude:
  descriptive error messages/stack traces, non-confidential info disclosure, source-code disclosure,
  SSL/TLS issues, clickjacking, self-XSS, secrets from public aggregation sources. Those are the
  reflex findings — they are **$0 here**.
- Note the **focus areas**. Vendors list what they will actually pay for. Octopus's four:
  (a) privileged code execution via a *novel/unintended* vector (their intended script execution is
  explicitly NOT a finding), (b) privilege escalation inside the product's RBAC, (c) broken
  encryption on agent↔server messaging → reproducible secret leak, (d) **sensitive variables not
  masked in task logs**. (a) and (b) are heavily picked over; (c) and (d) are control-correctness
  bugs and are the tractable ones.
- Version matters: self-hosted briefs usually scope "**supported versions**" (Octopus: latest
  download, falling out of support 6 months after release). Test the current download.
- The vendor's marketing site is normally a **separate, out-of-scope program**. Do not test it, even
  while signing up.

## 2. Build the lab (Docker compose is the fastest path)

Vendor ships a supported container → prefer it over the MSI. Native MSI usually needs a DB server
plus admin rights; the container path bundles the app and only needs a DB.

```yaml
services:
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    environment:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: "<pw>"
      MSSQL_MEMORYLIMIT_MB: "1024"        # cap it, see memory notes
    healthcheck:                          # generous: cold SQL is slow on a small host
      test: ["CMD-SHELL", "/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P \"$$MSSQL_SA_PASSWORD\" -Q 'SELECT 1'"]
      interval: 15s
      timeout: 25s
      retries: 40
      start_period: 150s
  app:
    image: <vendor>/<product>:latest
    privileged: true                      # only if the image wants DinD
    depends_on: { sqlserver: { condition: service_healthy } }
    environment:
      ACCEPT_EULA: "Y"
      DISABLE_DIND: "Y"                   # see gotcha 1
      MASTER_KEY: "<pinned base64>"       # see gotcha 2
      DB_CONNECTION_STRING: "Server=sqlserver,1433;Database=<db>;User Id=sa;Password=<pw>;TrustServerCertificate=True;"
      ADMIN_USERNAME: "admin"
      ADMIN_PASSWORD: "<pw>"
      ADMIN_EMAIL: "<ninja alias>"
    volumes: [ "app-home:/root/.<product>" ]   # see gotcha 2
    ports: [ "1322:8080" ]
```

**Free licence**: the brief usually tells you to sign up on the vendor site with your
`@BC_ALIAS.com` alias to get a trial key. That signup is *sanctioned* — do it, and record the
key in `creds.json`. Signup is a multi-step flow (email → 6-digit code mailed to the alias → set
password → pick hosting → org name → licence page). Read the code out of the forwarded mail
(parse the IMAP app password out of the existing mail-check script rather than re-typing the secret)
and drive the flow in a stealth browser.

### Lab gotchas that cost real time

1. **DinD kills the container.** These vendor images often run Docker-in-Docker for
   container-based workers. Under a nested/virtualised host DinD dies ("Docker-in-Docker Daemon
   exited with code 32") and the image's own watchdog then **kills the app** — the *agent* image does
   the same (`exit 143`, "Terminating Tentacle"). Both server **and** agent images honour
   `DISABLE_DIND=Y`; set it on every container in the stack unless you specifically need
   container-based workers.
2. **Pin the master key and mount the config dir.** The app stores its DB-encrypted server
   certificate under a key held in its config dir. If that dir is not a volume, recreating the
   container mints a *new* key while the DB volume persists → `Failed to decrypt the <product>
   certificate. This usually indicates the wrong master key`. Fix: keep the printed `MASTER_KEY`
   (the install script echoes it) in an env var and mount the config dir
   (`/root/.<product>` for root-run containers). Symptom→cause: recreate → cert-decrypt error.
3. **Small hosts thrash.** A 6 GB / 4 vCPU box cannot hold Windows + Docker Desktop +
   SQL Server + a large .NET server + a browser comfortably. Cap the DB buffer pool
   (`MSSQL_MEMORYLIMIT_MB`), and if the host is already loaded, stop unrelated lab containers for the
   duration (`docker start <name>` restores them — say so in the report rather than silently
   deleting anything). Watch free RAM with a cheap poll:
   `powershell -NoProfile -c "[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024)"`.
4. **Every in-container CLI call is a full app start.** The install script invokes the product CLI
   ~10× (create-instance → database → path → node → ssl → admin → license → run). On a slow host
   first boot is **10–20 minutes and looks hung**. Don't restart it. Watch progress with a
   `docker logs --tail 1` poller writing to a file — it gets past "Configuring Paths" etc.
5. Do not run `docker ps` in a tight loop on a thrashing daemon; it hangs the CLI. Background the
   diagnostic and read a file.

## 3. Authenticate into the API

- Probe the **unauthenticated surface first** with a cheap loop over ~25 endpoints. Typical result:
  only `/api/authentication` and a health endpoint are public, everything else 401. That is a
  negative, not a finding — record it.
- **API-key prefix gotcha.** Products often enforce a literal key format. Creating a key via the CLI
  with a malformed value *succeeds*, but the API then rejects it with
  `...doesn't start with "API-" as expected` or a bare `not valid`. Pass a correctly-prefixed value
  the first time (e.g. `API-BC_USERNAMERESEARCH1234567890ABCDEF`).
- Create it in-container:
  `docker exec <app> ./<Product>.Server admin --instance <inst> --username admin --apiKey "API-..."`
  (each such call costs minutes on a slow host — background it).
- Confirm identity with `GET /api/users/me` before building anything on top.

## 4. Turn the product API into the test harness

REST APIs of this shape are fiddly in *structural* ways, not semantic ones. The winning loop is:
GET a resource, mutate its JSON, PUT it straight back — never hand-build the body. Then:

- **Collections POST at the root**, not under the parent path. Item-create URLs that 405 on
  `POST /api/Spaces-1/projects/Projects-1/releases` work as `POST /api/Spaces-1/releases`.
  Same for runbook snapshots. Read the `Links` bag on the parent resource for the real path.
- **Required-field errors are the schema docs.** The server answers
  `{"Errors":["The <Field> field is required."],"Details":{"<Field>":"..."}}` — feed it back and you
  converge in 2–3 iterations. Fields discovered this way: `ProjectGroupId`, `RunRetentionPolicy`,
  `ExternalSecurityGroups`, `Username`.
- **Nesting traps.** A "step" is `{Properties:{...}, Actions:[{ActionType, Properties:{...}}]}` — a
  step with an empty `Actions` array is rejected as "does not have any actions". Some validators read
  a key from the **step-level** `Properties`, not the action's; when a validator insists a field is
  missing while you can see it set, try the same key one level up (`Octopus.Action.TargetRoles`
  had to sit on the step).
- Wiring a run end-to-end (Octopus): create environment + project → runbook (needs
  `RunRetentionPolicy`) → PUT the runbook process → publish a snapshot
  (`POST /api/Spaces-1/runbookSnapshots`) → **set the runbook's `PublishedRunbookSnapshotId`** (else
  "Runbook has no published snapshot") → `POST .../runbooks/<id>/run` → poll
  `GET /api/tasks/<taskId>` until `Success|Failed|Canceled`.
- **Register the vendor's own agent as the execution target.** Don't fight the built-in worker: run
  the agent container with the vendor's documented env (`ServerUrl`, `ServerApiKey`,
  `TargetEnvironment`+`TargetRole`, or `TargetWorkerPool`, `Space`). It self-registers. A
  worker-targeted step still demands `TargetRoles` and gets *skipped* ("has a role that overlaps: X")
  when no target matches — registering as a **deployment target** with a matching role is the path
  that actually runs.
- **Read the task log three ways**: `GET /api/tasks/<id>/raw` (plain text),
  `GET /api/tasks/<id>/details` (structured), `?verbose=true`. Always diff the surfaces — a leak that
  shows in one and not another changes the finding.

## 5. Testing a log-redaction / secret-masking control

This is the highest-yield angle on a mature product, because masking is a *control* with a
correctness boundary, and vendors state it as a paid focus area. Method:

1. **Length boundary sweep.** Create sensitive variables with values of length 1, 2, 3, 4, 8, 16 and
   `echo` each one. Print them as `Ln=[#{Var}]` so you can read the boundary straight off the log.
   Octopus refused to mask **anything under 4 characters** (`SensitiveValueMasker.CreateTrie()`
   does `if (... || instance.Length < 4) continue;`). A 4-char value where one char is a newline
   normalises down to 3 and is dropped too.
2. **Partial reproduction.** A masker that matches *complete literal values* only rewrites whole
   occurrences. Anything that emits **part** of the value leaks it, un-masked:
   `head -n 1` / `head -n 2` of a multi-line secret, `tail -n 1`, `cut -c1-20`,
   `fold -w 10`, and any output where the value ends up **embedded inside a longer line**
   (e.g. a shell `command not found` error echoing each line of a 40-line value).
   Full-value echo in the same task was masked while the partial was not — that contrast *is* the PoC.
3. **Multi-line values.** These are the realistic shape of the secrets people mark sensitive (PEM
   keys, GCP service-account JSON, kubeconfigs, `.env`). Sweep 2 → 3 → 40 lines.
4. **Don't overclaim transformed forms.** `base64` / `rev` / `xxd` obviously produce a different
   string and are not matched — that is the script's doing, expected, and will be rejected. The
   reportable part is partial/complete-match semantics and length cut-offs, not "the masker doesn't
   invert base64".
5. **Check every surface**, not just the log you read first: `/raw`, `/details`, `?verbose`, the
   rendered UI, artifacts, and the deployment's output-variable manifest.
6. Read the control's implementation when you can. Preserve the raw evidence per task
   (`tasklog-<n>.txt`) and cite task ids in the report — a triager will re-run them.

### Attributing the control (which target owns the bug)

Both sides of a client/server product usually ship the *same* masking classes. Attribute by grepping
the shipped binaries, not by guessing the layer:

```python
needles = [b"SensitiveValueMasker", b"SensitiveDataMask", b"AhoCorasick", b"SafeSanitize"]
for f in glob.glob("extracted/*.dll"):          # or .so / .jar / Mach-O
    b = open(f, "rb").read()
    print(os.path.basename(f), {n.decode(): b.count(n) for n in needles})
```

Reading *every* DLL is slow — pass an explicit short list of likely assemblies
(`Octopus.Core.dll`, `Octopus.Shared.dll`, `Octopus.Server.dll`, `Octopus.Tentacle.Core.dll`).
Empty result on one assembly means nothing; the same class appearing in both the server and the agent
assemblies is what lets you name both in-scope targets.

## 6. Severity honesty for control-correctness findings

A masking gap that requires a step to *output* part of the value, and discloses only a fragment,
is **P4/P5**, not P1. Say so in the report — claim the correctness failure, name the audience
(anyone with task-log/ProjectView rights, plus retention and export), and name the realistic secret
shapes (multi-line keys/JSON), rather than inflating it. Vendors who list masking as a focus area will
engage with an honest P4; an inflated one gets closed.
