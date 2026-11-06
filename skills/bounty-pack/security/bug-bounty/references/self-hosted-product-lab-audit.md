# Self-Hosted / On-Prem Product Lab Audit

> Use when a program's in-scope target is an **installable product** (on-prem server,
> agent/daemon, CLI, appliance, library) rather than a hosted web app. The work becomes:
> stand the vendor's product up locally, then attack your own instance.
> Worked end-to-end on Octopus Deploy (Octopus Server + Tentacle, .NET, Bugcrowd, 2026-10).

## 0. Read the scope for the SHAPE of the target before touching anything

On-prem programs phrase scope as a *product*, not a URL (`octopus.com/downloads`, "Octopus
Server & Tentacle"). Consequences that change the whole plan:
- The vendor's marketing site is usually a **separate program / out of scope**; testing it
  breaks scope. Only the shipped product counts.
- The brief often ships its own lab instructions (a getting-started link, and a **free
  licence via your `@BC_ALIAS.com` alias**). Use them — it is authorised and it is the
  documented path.
- "Supported versions only" is common; install the version the downloads page serves.
- **Open-source sub-components are fair game as white-box material** even when the repo is
  listed out-of-scope: the finding is in the shipped binary, and the repo tells you where to
  aim. (Octopus Tentacle is public; Octopus Server is not.)

## 1. Lab strategy: container first, native install last

Native installs of enterprise products want SQL Server / a licensed OS / admin rights. A
container is faster and disposable. For a `server + database` product:

```yaml
services:
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    container_name: <p>-sql
    restart: unless-stopped            # else the lab dies with the Docker VM and stays dead
    environment:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: "<pw>"
      MSSQL_PID: "Developer"
      MSSQL_MEMORYLIMIT_MB: "1024"     # see pitfalls — required on a small host
    healthcheck:
      test: ["CMD-SHELL", "/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P \"$$MSSQL_SA_PASSWORD\" -Q 'SELECT 1'"]
      interval: 15s
      timeout: 25s
      retries: 40
      start_period: 150s               # a 5s timeout makes the DB look permanently unhealthy
  app:
    image: <vendor>/<product>:latest
    container_name: <p>-server
    restart: unless-stopped
    depends_on:
      sqlserver:
        condition: service_healthy
    environment:
      ACCEPT_EULA: "Y"
      DISABLE_DIND: "Y"                # see pitfalls — DinD wedges many vendor images
      MASTER_KEY: "<pin a fixed key>"  # see pitfalls — a regenerated key bricks the DB
      DB_CONNECTION_STRING: "Server=sqlserver,1433;Database=<db>;User Id=sa;Password=<pw>;TrustServerCertificate=True;"
      ADMIN_USERNAME: "admin"
      ADMIN_PASSWORD: "<pw>"
    ports: ["1322:8080"]
    volumes: ["<p>-home:/root/.octopus"]   # mount the CONFIG dir, not just the data dirs
```

Read the image entrypoint before guessing env names — vendor images are shell scripts and
`docker run --rm --entrypoint cat <image> /install.sh` reveals every supported variable
(`DISABLE_DIND`, `MASTER_KEY`, `ADMIN_*`, `TARGET_*`, `SERVER_URL`, `SPACE`, …).

## 2. Pitfalls that cost real time (all hit on the Octopus run)

- **Docker-in-Docker wedges the container.** Vendor server/agent images start `dockerd` and
  kill themselves when it dies (`Docker-in-Docker Daemon exited with code 32` →
  `Terminating …` → exit 143). Set `DISABLE_DIND=Y` unless you actually need container-based
  workers. Symptom on a `server` image: a setup command spins at ~80% CPU for 10+ minutes
  and the entrypoint never advances.
- **Recreating the container regenerates the product's master key while the DB volume
  persists.** Result: `Failed to decrypt the <product> certificate. This usually indicates the
  wrong master key is being read.` Fix = pin the key with `MASTER_KEY=<value from the first
  boot log>` **and** mount the instance config dir (`/root/.octopus`, `$HOME/.octopus`, …).
  The config dir is often NOT the same as the data dirs you mounted first.
- **`depends_on: condition: service_healthy` + a too-short healthcheck timeout** = "dependency
  failed to start: container <db> is unhealthy" while the DB is actually fine. SQL Server 2022
  needs ~2 minutes to become queryable on a slow host; give `start_period: 150s`,
  `timeout: 25s`.
- **No `restart:` policy means a Docker Desktop VM bounce leaves the lab dead** and the port
  silently refuses. Containers exit 255 with no useful log.
- **Small host = thrash, not failure.** On a 6 GB / 4 vCPU box, DB + app + browser + the
  agent's own containers swap hard: `docker ps` and `docker logs` themselves time out, and the
  API answers `000`/`curl (52)`. Cap the DB (`MSSQL_MEMORYLIMIT_MB`), stop unrelated lab
  containers (`docker stop` is reversible — say so in the write-up and give the restore
  command), and **check free disk before assuming a product bug.**
- **A full host disk masquerades as everything else.** A 100%-full `C:` produced
  `ExtractToFile ... not enough space on the disk`, a truncated SDK install that later threw
  `Could not load file or assembly`, and containers exiting 255. Docker Desktop's WSL vhdx
  lives on `C:` (`%LOCALAPPDATA%\Docker\wsl\disk\docker_data.vhdx`) and grows to several GB.
  Free space first, then diagnose. Recursive `du`/`Get-ChildItem` over a full 188 GB drive
  will itself time out — use a GUI sizer (WinDirStat/TreeSize) rather than scripting it.

## 3. Reach the code through the product's own API, not the UI

A self-hosted product exposes a REST API that the UI is just a client of — script against it
and you can build any state in a few calls. Practical rules learned the hard way:

- **Discover the model by GETting an existing object** and mirroring its field names. POSTing
  a hand-guessed payload mostly returns `The <Field> field is required.`; that error text *is*
  the schema.
- **Nested step properties live on the STEP, not the ACTION.** (A deployment step rejected
  `Octopus.Action.TargetRoles` placed inside `Actions[0].Properties`; it had to go in the
  step's own `Properties`.) When a validator complains about a field you *did* set, try the
  sibling level before rewriting the payload.
- **Create collections at the space/root scope**, not under the apparent parent
  (`POST /api/Spaces-1/releases`, `/api/Spaces-1/runbookSnapshots`) — the parent-path variant
  returns 405/404 even though GET works there.
- **Read the raw log artifact directly** (`GET /api/tasks/<id>/raw`, `/details`,
  `/details?verbose`) rather than scraping rendered HTML — it is the same bytes the UI shows,
  and it is what the report should quote.

## 4. Build impact evidence with a second, weaker account

Do not assert "a lower-privileged user could see X" — create the account and show it.
Give the second user **only** plausible non-admin roles, log in for real, and fetch the same
artifact. One command turns an assumption into a quoted response in the report.

## 5. White-box for a closed-source product

`docker cp <container>:/<appdir> ./server-bin` pulls the shipped assemblies. See
`tool-installation-windows.md` → ".NET product audits" for the decompiler recipe and for the
cheap trick that attributed the Octopus finding: **grep the DLLs for class names** to prove
which shipped assembly implements the behaviour (`b.count(b'SensitiveValueMasker')`).

## 6. Close out the lab honestly

State what you changed on the host and how to undo it (stopped containers + the
`docker start <names>` to restore them), keep the disposable instance available until triage,
and note that nothing was touched on vendor-operated infrastructure.
