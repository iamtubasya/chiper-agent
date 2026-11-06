# Monitor for New Surface — "new code is buggy code"

> Load at **0B** when the program is recurring / long-running, or when the estate is already
> heavily hunted. Being first to test a change beats being the most skilled tester of code that
> a thousand hunters already hammered. This is a surface-acquisition strategy, not a scanner.

Principle: the edge is not smarter — it is **faster to the new surface**. Value of a diff
decays within hours once other hunters' tooling catches the same change.

---

## 1. What to watch, per asset type

| Asset | Signal | What it means |
|---|---|---|
| SPA / web app | JS bundle filename or content hash change | new deploy → re-run JS deep-analysis on the **diff**, not the whole bundle |
| DNS | new subdomain in continuous enum | new service, usually stood up without the main app's hardening |
| Certificates | new cert issuance (CT logs) | often precedes a subdomain going live — catch it before it is linked anywhere |
| Repos | new repo, new commit, force-push, deleted-then-recreated branch | force-push usually means a secret was scrubbed; it still lives in reflog/cache for a window |
| Contracts | proxy `Upgraded` event, new deployment from the same deployer | test the new implementation the moment it is verified, before TVL ramps |
| Mobile | store version bump | pull the new APK/IPA immediately, diff against the previous decompile |
| Comms | changelog, status page, release notes, job postings | each announces next quarter's attack surface before it is public |

## 2. Baseline first

You cannot diff without a baseline. On first contact with a target, snapshot into the
workspace `monitor/`:

```
monitor/<target>/subdomains.txt        sorted, deduped
monitor/<target>/bundle-hashes.json    {url: sha256}
monitor/<target>/contracts.json        {chain:address: bytecode_sha256, impl, admin}
monitor/<target>/app-versions.json     {platform: version, artifact_sha256}
monitor/<target>/repo-heads.json       {repo: default_branch_head_sha}
```

Re-run the snapshot on each return visit; the diff is the work queue.

## 3. Operationalization (cheap and boring wins)

- cron + `subfinder`/`dnsx` for subdomains; append new only
- small script hashing `<script src>` bundles per app; report changed hashes only
- CT-log watcher (certstream or crt.sh polling) filtered to the target's registrable domain
- GitHub API polling for the target org (new repos, new commits on watched branches)
- RSS/webhook watch on changelog, status page, release notes
- on-chain: subscribe to `Upgraded(address)` on in-scope proxies; alert on new verified source

Keep the watchers **passive**. Monitoring must never look like scanning — a diff check that
fetches one JS file is recon, not a scan.

## 4. SLA and triage of a change

```
change detected → initial pass within hours, not days
```

Initial pass on a diff means:
1. What is new (endpoint, parameter, role check, dependency, contract function)?
2. Does the new surface inherit the guards the old surface has? (This is where the bugs are —
   new code copies the shape of old code but forgets one guard.)
3. Does the new surface touch value, privilege, or tenant boundary?
4. Does the change *remove* something — a check, a scope restriction, a rate limit, a
   validation branch? Deletions in security-relevant files are the highest-yield diff.

## 5. Diff-hunting rules

- Security-relevant diffs first: auth middleware, permission decorators, token handling,
  serializers that decide what fields leave the server, payment/entitlement logic, migrations.
- `git log -S "<guard>"` / `git log -p -- <auth file>` — a function repeatedly patched is a
  function with a history of getting it wrong.
- Never assume the new deploy is a hardened version of the old one. Deploys ship regressions.
- A changed response shape (extra field) is a finding seed: over-fetch is how internal data
  leaves through public APIs.

## 6. Report of coverage

Monitoring output is coverage evidence, not a finding. Log it as:

```
WATCHED:     <asset types + mechanisms actually running>
SNAPSHOTS:   <n baselines, dates>
DELTAS:      <n changes, each -> tested / queued / not-testable-and-why>
```
