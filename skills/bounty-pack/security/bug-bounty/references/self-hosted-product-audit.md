# Self-hosted / on-prem product audits (the target is SOFTWARE, not a URL)

A distinct program shape: the scope is a product you must **install and run yourself**
— Octopus Server/Tentacle, GitLab, Jira/Confluence Data Center, Grafana, TeamCity,
Jenkins, Vault, Zabbix. The engagement page has no hostname to scan; it points at a
download page. Everything below is the workflow that replaced the usual
recon → scan → exploit chain.

Worked case: Octopus Deploy on Bugcrowd (2026-10). Scope = "Octopus Server & Octopus
Tentacle, supported versions from the download page", P1 $6000 … P4 $200, 46 findings
already paid, avg $2,220.

## 0. Read the brief for the two clauses that define the whole engagement

1. **What is in scope** — usually only the product and only *supported versions*
   (they fall out of support ~6 months after release, so test `latest`).
   The vendor's own SaaS (octopus.com, trust.*) is normally a *separate* program or
   explicitly out of scope; testing it is the fastest way to burn the engagement.
2. **The intended-execution carve-out** — agent/orchestrator products are *designed* to
   run privileged arbitrary code. The brief says outright: reward for arbitrary code
   execution only via a **novel or unintended** vector, not the intended script
   execution. Everything you write must live inside that line.

Also expect an unusually specific focus-area list (this program's was: novel
privileged execution, privilege escalation via RBAC, broken encryption between
server and agent leading to a *demonstrated reproducible* secret leak, and sensitive
variables not correctly masked in task logs). That list IS your test plan — it tells
you what they will pay for.

## 1. Get the product legally and cheaply

- Free/trial licence through the researcher alias (Bugcrowd: `@BC_ALIAS.com`,
  forwards to your real inbox). The brief usually states this explicitly.
- Read the licence email for the machine/feature limits — a trial may cap targets,
  projects, or users, which changes what you can build.
- Trial keys expire; note the date in the engagement log so a resumed session knows
  whether the lab still boots.

## 2. Stand up the lab — prefer the official container over the native installer

Native installers want admin and a supported server OS; the vendor's own image is
disposable, needs no admin, and resets in seconds. Pitfalls that cost real time:

| Symptom | Cause | Fix |
|---|---|---|
| Container exits `143` right after `Docker-in-Docker Daemon exited with code 32` (log shows `Terminating …`) | the image bundles DinD and the entrypoint kills the app when DinD dies — `mount: /sys/kernel/security: permission denied` on a Docker Desktop host | set `DISABLE_DIND=Y`. Both the Octopus server and tentacle images honour it and then `exec` the app directly |
| Recreate works, then startup errors `Failed to decrypt the … certificate. This usually indicates the wrong master key is being used` | the DB volume persisted (data encrypted with the **old** key) while the container's config/home dir did **not** — a recreate generated a new key | pin the key (`MASTER_KEY=<base64>` for Octopus) **and** mount the config dir (`- /root/.octopus`) so both survive recreation |
| `docker compose` aborts: `dependency failed to start: container <db> is unhealthy` although the DB later reports healthy | healthcheck `start_period`/`timeout` too tight for a DB on a slow disk (SQL Server 2022 needed ~150 s before its first successful probe) | raise `start_period` to 120–180 s and `timeout` to ~25 s |
| Everything crawls / containers die with `exit 255` mid-engagement | host memory and/or disk exhausted — a mid-size .NET app + SQL Server does **not** fit in 6 GB, and a full system disk breaks installers silently | cap the DB (`MSSQL_MEMORYLIMIT_MB: "1024"`), stop unrelated containers, and put `restart: unless-stopped` on every service so an engine restart doesn't end the engagement |

Small-host reality check: read free RAM (`Get-CimInstance Win32_OperatingSystem`) and
`(Get-PSDrive C).Free` before blaming the product for being slow. Note in the log which
unrelated containers you stopped, so they can be restarted afterwards.

## 3. Get authenticated early

- The product's own CLI can mint an API key without the UI:
  `docker exec <ctr> ./Octopus.Server admin --instance … --username admin --apiKey <key>`.
- **Respect the vendor's key format.** Octopus rejects a key without the literal
  `API-` prefix (`"doesn't start with \"API-\" as expected"`), and a second call
  rewrites the key rather than adding one. Cheap and easy to lose 20 minutes to.
- The API root (`GET /api/`) is worth reading: it self-describes every collection and
  the space-scoped paths. `Version`, `ApiVersion`, and the `Links` map are the recon.

## 4. Then test it like a web app

It serves its own REST API on `localhost`, so the normal discipline applies: enumerate
endpoints, check what is reachable unauthenticated, and check whether a
sensitive-looking value round-trips. Two cheap, high-signal probes:

- **Unauth sweep** of every collection (`/api/projects`, `/api/users`, `/api/tasks`,
  `/api/configuration`, …) — record which answer 200/401/403/404.
- **Read back what you wrote**: create a variable/secret flagged sensitive, then
  `GET` its container and confirm the API returns `Value: null`. If it returns the
  value, that is a finding and you found it in one request.

## 5. White-box a closed-source product too

- The shipped assemblies are on disk in the container (`docker cp <ctr>:/<appdir> .`).
- You often do **not** need a full decompile to attribute behaviour to a class: count
  class-name strings inside the DLLs.
  `python -c "b=open('Octopus.Core.dll','rb').read(); print(b.count(b'SensitiveValueMasker'))"`
  proved the *server* shipped the same masking classes as the open-source Tentacle —
  which is what let one root cause explain both products.
- Some components are public source (Octopus Tentacle, Halibut, the CLI). Reading them
  to find bugs **in the in-scope binary** is legitimate; the repository itself is
  normally out of scope, so keep the finding anchored to the shipped product.
- Decompiler setup on Windows is in `tool-installation-windows.md` §".NET product audits".

## 6. What these programs actually pay for

- **Security controls that silently fail.** Secret masking / redaction / log scrubbing
  are the highest-yield area: they are core, they are testable in one deploy, and a
  failure is an in-scope "sensitive data in logs" finding. Technique:
  `secret-in-error-strings-and-log-leak.md` §"Control-gap testing".
- **RBAC.** Create a deliberately low-privilege account, read its granted permissions
  straight from the role objects (`GrantedSpacePermissions`), then probe writes and
  cross-tenant/cross-space reads. Report the negative when it holds — an honest
  coverage ledger makes the real findings credible.
- **Transport security between components** (agent ↔ server, node ↔ controller,
  listener ports). Check whether a client with an untrusted or absent certificate can
  reach anything beyond the preamble, and fuzz that preamble.
- **"Novel or unintended" code execution only** — not the product's intended script
  execution, which is the whole point of an agent.

## 7. Evidence, framing and hygiene

- You own the lab, so reproduce end-to-end and paste the **raw** artifact into the
  report: the task-log lines, the API response, the request. No customer data is
  involved, so frame it as a *correctness failure of a documented control*, not an
  active compromise.
- Prove the **audience**, don't assert it. Log in as your low-privilege account and
  show it reading the leaked value; that converts "impact statement" into evidence.
- Controls commonly ship as a shared library used by several components. One root cause
  → one report; say explicitly whether you consider two gaps one report or two.
- Many briefs demand **plain text** reports (PDF/DOCX get bounced). Write the report as
  a `.txt` from the start.
- Note in the engagement log what you created on the vendor's systems (the licence
  account) and that the lab is disposable — and remember the clean-up step.
