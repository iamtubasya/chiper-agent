# Self-hosted appliance / node-software audits: lab standup + secret-masking methodology

Use when the program scope is a **self-hosted product** (an agent, node, server or appliance you must
install and run) rather than a website. There is no hostname to scan; the attack surface only exists
once the thing is running. Worked example: Octopus Deploy (Bugcrowd) — Octopus Server + Octopus Tentacle,
C#/.NET, licensed on-prem product. Findings from that run are a good template for what this class yields.

## 1. Scope reality check

- Self-hosted programs usually scope **the shipped binary/image**, not the vendor's website. Read the
  brief twice: "you may sign up at <vendor>/downloads with your @BC_ALIAS.com address for a free
  licence" is an *instruction*, not a target — installing and licensing locally is authorized.
- Vendor SaaS/property is usually a **separate** program (Octopus: `bugcrowd.com/octopus-og`).
- Typical focus areas to anchor on (Octopus's own list, broadly reusable): privilege escalation inside
  the product's RBAC; secrets not masked in task/job logs; broken encryption on the agent↔server wire;
  and "arbitrary code execution only via a *novel/unintended* vector" — the product is *designed* to run
  code, so the intended script path is explicitly not a finding.
- The products are mature and have been picked over. Budget for depth, and expect the honest result to
  be a small number of precisely-scoped correctness gaps rather than a headline RCE.

## 2. Lab standup — get this right before anything else

**Check the host budget FIRST.** A "SQL Server + large .NET app" stack wants ~3–4 GB. On a small host
(6 GB / 4 vCPU) an uncapped Docker stack thrashes, and containers die with `exit 255` / OOM mid-audit.
Before you start: free RAM and free *disk* on the drive Docker uses, and put all artifacts on the
roomier drive. A container crash loop that looks like a product bug is usually the host.

Concrete traps hit for real (each cost 10–30 min):

- **Docker-in-Docker images exit themselves.** Vendor images that bundle dockerd kill the whole
  container when the inner daemon fails (`Docker-in-Docker Daemon exited with code 32 / Terminating
  ...`, container `exit 143`). Set `DISABLE_DIND=Y` unless you actually need container-based workers.
  Same for the agent image (`octopusdeploy/tentacle`).
- **Pin the secrets the container generates on first boot AND mount the instance dir.** If the product
  writes a master key into `$HOME/.octopus` (not a volume) while the DB lives in a volume, recreating
  the container mints a *new* key against the *old* DB → "Failed to decrypt the ... certificate. This
  usually indicates the wrong master key". Capture the key from the first boot log, set it as an env
  var (`MASTER_KEY`), and mount the home dir.
- **Healthcheck gates.** `depends_on: {condition: service_healthy}` plus a 5 s healthcheck timeout will
  abort startup on a slow box ("dependency failed to start: container ... is unhealthy"). Raise
  `timeout` and `start_period` (SQL Server 2022 wanted 150 s start_period on 1 GB buffer pool).
- **Add `restart: unless-stopped`.** A Docker VM restart otherwise leaves every container silently
  down; you find out only when the next API call 000s.
- **Cap the database.** `MSSQL_MEMORYLIMIT_MB=1024` etc. keeps the host alive.
- **Cold start is slow and quiet.** The app's own bootstrap runs a sequence of full runtime starts
  (`create-instance` → `database` → `configure` → `admin` → `license` → `run`), ~10–15 min on a weak
  box. Watch the container log, not the HTTP port, to know where you are.
- **Reach in-network services without publishing ports:** `docker exec <container> bash -lc "getent
  hosts <peer>; curl -sk https://<peer>:PORT/"`. Publish a port only when you need host-side tooling.

## 3. Secret-masking test methodology (the reusable core)

Products that "mask secrets in logs" almost always implement it as **literal full-string replacement**
with a length cut-off. That gives exactly two reproducible bug classes. This sequence found both:

1. **Baseline.** Sensitive value, script does `echo "#{Secret}"`. Confirm the whole value becomes
   `********`.
2. **Length boundary.** Echo values of **1, 2, 3, 4, 8, 16** characters. Report the exact boundary
   ("length 4+ masked, 1–3 not"). Implementations commonly skip short values to avoid masking
   everything (`if (instance.Length < 4) continue;`) — the short ones then leak *in full*, with no
   transformation by the script at all. This is the cleanest version of the finding.
3. **Partial reproduction.** Emit only part of the value and check each:
   `head -n 1`, `head -n 2`, `tail -n 1`, `cut -c1-20`, `fold -w 10`, and embedded mid-line
   (`echo "x$(... )y"`). A masker that matches only *complete* occurrences emits the partial in
   cleartext.
4. **Multi-line values** (PEM keys, service-account JSON, `.env`, kubeconfig — the realistic shape of a
   sensitive variable): full echo vs partial echo. Full value masked + `head -n 2` cleartext is a very
   legible demonstration.
5. **Chunk boundaries.** Emit lots of output, then the value. Streaming maskers keep buffers; a value
   straddling a chunk can escape.
6. **Every surface, not just the raw log.** Compare the raw log, the structured details endpoint, the
   `?verbose` details, *platform-rendered* text (e.g. manual-intervention instructions, step notes),
   artifacts and output variables. Note in the report which ones leaked and which did not — "masking
   works on the platform-rendered surface but not on partial reproductions" reads as a precise bug, not
   a vague complaint.
7. **VERIFY THE AUDIENCE, don't assert it.** Create a deliberately low-privileged account holding only
   viewer-type roles, log in as it, and read the affected log. Only then can you write "a user who
   cannot author processes sees the raw secret". Quote the request in the report.

**Root-cause attribution.** Decompile the shipped assemblies and grep for the masking classes
(`SensitiveValueMasker`, `SensitiveDataMask`, AhoCorasick, `SafeSanitize`). The same classes often ship
in *both* the server and the agent, which lets you say which components carry the defect. Cite the
`<4` guard and the "deferred partial match flushed unmodified" path — that is what convinces a triager
it is a defect and not a script's choice.

**Watch the program's own exclusion list.** A one-byte request that raises an unhandled
`ArgumentOutOfRangeException` (`req.Substring(0, 2)` with no length guard) is a real robustness nit but
usually excluded as "descriptive error messages / stack traces". Record it in the coverage ledger as a
negative; do not spend a finding slot on it.

## 4. Reading an RBAC bug from a 403

A **CSRF failure is not an authorization result.** Cookie-authenticated writes need the product's
anti-forgery header; without it *every* write is 403 and the matrix looks uniformly "secure" (or, worse,
you read a 403 as privilege enforcement when you never actually reached the authorizer). Extract the
CSRF value from the session cookie / meta tag and re-run.

Also: some endpoints run model validation *before* the permission check, so an incomplete payload
returns `400` rather than `403`. Always re-test with a **valid payload** before calling it a bypass —
in this session the 400 became a clean `403 Missing permission: X`, i.e. no bug.

## 5. .NET white-box setup on a Windows host

- The bash installer fails under MSYS (`OS name could not be detected: UName = MINGW64_NT-...`). Use the
  PowerShell one:
  `powershell -File dotnet-install.ps1 -Channel 8.0 -InstallDir /home/agentuser/.dotnet`
  (and `-Channel 6.0 -Runtime dotnet` if a tool needs the older runtime).
- **Export `DOTNET_ROOT`** or tool shims fail with `You must install .NET to run this application`
  / `Failed to resolve hostfxr.dll`.
- `ilspycmd` install can fail with `Settings file 'DotnetToolSettings.xml' was not found in the package`
  — clear `~/.nuget/packages/<tool>` and pin a version compatible with the runtime you installed.
- ILSpy 8.2 **crashes on some assemblies**: `System.ArgumentException: Argument must be between 0 and 2
  (Parameter 'fieldCount')` from `DecompilerTypeSystem` when `AssemblyFileVersion` has a short form.
  Move to a newer ilspycmd.
- `ilspycmd -l c <asm>.dll` lists classes (fast, no full decompile) — use it to find the types worth
  decompiling, and grep the raw DLL bytes for class/member names when you only need "does this ship in
  which assembly".
