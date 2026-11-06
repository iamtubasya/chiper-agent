---
name: vendor-product-lab
description: "Stand up a vendor product locally (installer, VM appliance, panel) to hunt IDOR/privesc."
version: 1.0.0
author: RESEARCHER_NAME
metadata:
  hermes:
    tags: [security, lab, bug-bounty, self-hosted, vendor-product, panel, billing, wsl, api-enumeration]
    platforms: [windows, linux]
---

# Vendor Product Lab

Build a **real, licensed, locally-owned installation of a vendor's production
software** and attack that. Not a deliberately-vulnerable practice app, not a
firmware appliance VM — the actual product the bounty program pays for.

## When this skill applies

| Situation | Use instead |
|---|---|
| Program says "only products in your personal possession" / "we do not review damage to third-party installs" | **this skill** |
| The vendor offers a **cloud-managed edition / trial instance** of the product | **this skill, Phase 2b** — provision your own trial; skip Phases 2-5 |
| Product is a firmware/appliance/NAS OS image | `security/vm-appliance-lab` |
| You just need to rehearse a technique on something intentionally broken | `local-vuln-lab` |
| Product is source-available on GitHub | white-box review, no lab needed |

Trigger phrases from the operator: *"cek scope nya, cek rules nya, cek core
bisnisnya, baru mulai cari bug nya"*, *"sy approved semua perizinan"*,
*"jangan berhenti sampai dapat temuan"*.

## Why this class exists

Most self-hosted product bounties (ISPsystem, cPanel, Plesk, Virtualmin,
CloudStack, ...) gate on **ownership**. Testing a provider's live install voids
the report. But the highest-paying tiers are almost always *multi-tenant logic*
bugs — one customer reading another's data, a non-admin reaching admin, a
license limit bypassed. **You cannot prove any of those without at least two
competing identities inside one installation.** The lab is not optional; it is
the only way to produce a submittable PoC.

## Phase 1 — read the program before touching anything

Extract and keep: product list, reward tiers, explicit exclusions, submission
channel, and the "known/public bugs are excluded" clause. Map each reward tier
onto a concrete test you can run later. Exclusions that bite:

- "no DoS by request volume" -> no load testing, no brute force
- "no solutions based on modifying executable files" -> license bypass must be
  logic-level, not binary patching
- "bugs already public are excluded" -> check vendor advisories/CVE/news first,
  and **resolve the build's revision id before hunting a known class**: vendor
  advisories ship patch revision ranges (e.g. "below Revision 150340"), and the
  product itself will tell you its build (`/rest/information/version/<product>`
  -> `NAC-CLOUD-R-154085-5.0.92.1022`). If the installed revision is above every
  range, that whole CVE family is already patched and any "finding" in it is a
  duplicate — record the comparison as evidence and move on.
- "employees and relatives excluded" -> confirm you are eligible

## Phase 2 — find the distribution channel

Do not guess URLs. Enumerate the vendor's package repo by directory listing —
most expose an autoindex:

```
https://<vendor-cdn>/repo/<osfamily>/                          # dists/ pool/ *.repo *.list
https://<vendor-cdn>/repo/<osfamily>/pool/main/<letter>/       # every package, by first letter
https://<vendor-cdn>/repo/<osfamily>/dists/<release>-<codename>/main/binary-<arch>/Packages.gz
```

Read the vendor's own `install.sh` — it is the authoritative map of supported
OS versions and repo names:

```bash
curl -sL http://<vendor-cdn>/install.sh -o install.sh
grep -nE 'OSVERSIONS|dists|baseurl|mirrorlist|NOTIFY_SERVER' install.sh
```

Two traps:

- A dist can exist in the index for only *some* products (framework packages in
  one repo, product + plugins in another). Enumerate `pool/` directly — the pool
  is the ground truth for what files exist.
- The newest release often lives in a **generation-prefixed** path
  (`6-5.452/`, `6-intstable/`) rather than `stable/`. Follow the `mirrorlist.txt`
  files; they name the live paths.

## Phase 2b — if a cloud-managed edition exists, provision a trial instead of installing

**Do this check before Phase 3.** Many vendors ship a cloud-managed edition of the
same product and let researchers stand up a trial instance from the account
portal. That gives you a licensed, admin-access instance of the *real* product in
~15 minutes, with none of the repo/licence work of Phases 3-5.

Shape of the route (full worked recipe, contract replay, JSF console login chain,
edition-gate test: `references/cloud-trial-to-admin-console.md`):

1. Register on the **bug-bounty-specific** account-portal URL if the policy names
   one — registering through the normal form can forfeit the reward.
2. Provision through the portal's own AJAX action (single-use CSRF token, mint one
   per request). Submit the `<option value="…">` string, not the numeric
   `value2` used by the plan-lookup action — the numeric id returns a generic
   "invalid access" that masquerades as an authz rejection.
3. The admin credential for the product console is **the email + password you
   typed into the provisioning form**, not an emailed invite.
4. Budget the trial: quota is usually **1 per account and global across
   products** — every later attempt (including a different product) is refused.
   Do not spend it on a smoke test.

## Phase 3 — pick the host OS

Match the vendor's supported matrix. On a Windows box, install the matching WSL
distro rather than forcing packages onto whatever you already have:

```bash
wsl -l -o                       # what is available
wsl --install -d <Distro>       # e.g. AlmaLinux-9
wsl -d <Distro> -u root -- ...  # root without a password prompt
```

Forcing `--osfamily/--osversion` onto an unsupported distro usually fails on
glibc/soname mismatches. Installing the right distro is faster than debugging it.

## Phase 4 — install in dependency order

Install **base deps -> framework -> product -> plugins**, never all at once.
Each layer's failure names the next missing package.

```bash
dnf -y install epel-release                      # most vendor deps live in EPEL
dnf -y install --nogpgcheck --setopt=install_weak_deps=False ./base-*.rpm
dnf -y install --nogpgcheck --setopt=install_weak_deps=False ./framework-*.rpm
dnf -y install --nogpgcheck --setopt=install_weak_deps=False ./product-*.rpm ./plugin-*.rpm
```

Download the RPMs/debs **on the Windows host with curl** and copy them into the
distro over `/mnt/<drive>` — see the pitfall on WSL network throughput. Keep a
single flat directory of every RPM you fetched; re-installing is then one
command and you can also extract them for white-box review
(`rpm2cpio x.rpm | cpio -idm`, or `dpkg-deb -R x.deb out/`).

**Extract the product package even after a successful install.** The payload is
the cheapest white-box source you will ever get: UI metadata, message catalogs,
templates, SQL schema. For ISPsystem this meant 23k lines of `billmgr.xml`
listing every callable function with its intended access level.

## Phase 5 — license

Trial licenses are usually IP-bound and one-shot per server, and the vendor
client area may demand a phone-verified signup. Check whether the panel is
functional *without* a supported license before spending time on registration —
many panels run fully with an unsupported/expired trial and only gate a few
features. Verify with the vendor's own license tool and by calling a function.

## Phase 6 — seed competing identities (the point of the whole exercise)

Create, at minimum:

| Identity | Purpose |
|---|---|
| main administrator | owns everything, the "victim" of privesc |
| staff/employee with limited rights | the type #3 attacker *and* victim |
| client A and client B in the same account | the IDOR pair |
| a second account/tenant | cross-tenant checks |

Order matters — most panels require project/provider -> account -> user ->
employee. Discover the required fields by calling the edit function with no
arguments: the panel returns its full parameter list as the error body. Then
feed them one at a time; each error names the next missing mandatory field.

Record every credential and the resulting DB ids in the reference file.

## Phase 7 — reverse the API, then enumerate it

Find the auth call by watching what the login form actually sends (browser
devtools, or grep the JS bundle). Typical shape:

```
POST https://<host>:<port>/<manager>
Content-Type: application/x-www-form-urlencoded
X-Requested-With: XMLHttpRequest        <- often REQUIRED, without it you get the HTML shell
func=auth&username=<u>&password=<p>&lang=en&sok=ok
  -> 200 + Set-Cookie: <mgr>ses5=<session id>
```

Then `func=<anything>&out=json` with that cookie returns structured JSON instead
of the SPA HTML. Confirm the session works before enumerating.

**Enumeration method (the highest-value step):**

0. **Unauthenticated-reach probe first.** Run the same enumeration with *no*
   session cookie (`panel_func_enum.py --no-auth`). Anything that does not
   return access-denied here is reachable with **no credentials at all** — an
   immediate finding class, and it costs nothing because you already have the
   function list. Never skip this because "the panel requires login"; the whole
   point is to find out whether it actually does.
1. Extract every callable function name from the product's UI metadata
   (`func="..."` attributes) — this is the complete attack surface, not a
   wordlist guess.
2. Log in as the **lowest-privilege** identity and call every function with no
   parameters. Classify each response:
   - `access denied` -> control working, deprioritise
   - `missing parameter <x>` -> **the access gate passed**; the ownership check
     may live *after* parameter validation. These are your candidates.
   - real data returned -> investigate immediately
3. Repeat as a higher-privilege identity and **diff the two scans**. Anything
   reachable by the low-priv user that the metadata marks admin-only is a
   privilege-escalation candidate; anything that returns another tenant's rows
   is a data-disclosure candidate.
4. Only then start passing real object IDs and competing identities.

`scripts/panel_func_enum.py` implements steps 0-3 generically, including the
`--diff` mode.

**Generalise the classification before trusting it — three traps that fake findings.**
The three-bucket classify above is necessary but not sufficient. On any vendor panel:

1. **One error type can mean two things.** COREmanager's `missed` covers both "parameter absent"
   and "function not found — module not loaded"; reading only `$type` turned 12 unloaded functions
   into phantom authz bypasses. Always read `msg`/`detail`.
2. **The success envelope is present in error responses too** (`{"doc":{"error":{…}}}`), so
   `"doc" in body` is not an "executed" signal. Test for the access-denied marker *first*.
3. **A clean 200 on a `.add`/`.create`/`.setup` endpoint is usually a rendered wizard step, not a
   write.** Confirm side effects in the database before claiming the action succeeded.

Worked ISPsystem-specific versions of all three, plus the referer/CSRF-gate oracle technique and a
verified-negative matrix, are in `security/ispsystem-panel-lab` §"Four false-positive traps". The
general authz-testing discipline (capability-gain test, verified negatives, cross-tenant seeding)
is in `security/authed-webapp-audit`.

**Verify the diff tool itself before trusting its output.** A one-character
logic error in the set-difference (`f not in b` while iterating `b`) silently
reports *zero* functions unique to one scan — which reads exactly like "no
difference" and kills the privesc lead without a warning. Sanity-check any diff
by hand on two or three known-different functions first.

## Pitfalls (all hit for real)

- **WSL2 outbound throughput can collapse to hundreds of bytes/sec** while the
  Windows host pulls the same URL at full speed. Symptom: `dnf`/`apt` metadata
  downloads time out at "less than 1000 bytes/sec". Fix: fetch every package on
  the Windows side with curl, then `cp /mnt/<drive>/... /root/rpms/` and install
  locally. Do not fight the repo through WSL networking.
- **`wsl --install -d <Distro>` can hang past any sane timeout** and leave the
  distro in a "Running" limbo. Recovery: `wsl --shutdown`, then
  `taskkill /F /IM wsl.exe`, then retry. A first command against a fresh distro
  may also need a terminate-then-run cycle before it answers.
- **MSYS mangles absolute Linux paths** passed to `wsl ... -- bash /mnt/...`:
  `/mnt/d/x.sh` becomes `C:/.../git/mnt/d/x.sh`. Prefix every such command with
  `MSYS_NO_PATHCONV=1`.
- **Write scripts to a file, never as an inline `wsl -- bash -c '...'` string.**
  Nested quoting breaks `awk "{print $1}"` and friends silently. Generate the
  file from Python with `newline='\n'` — default text mode on Windows emits
  CRLF, which makes `bash` fail with `syntax error near unexpected token $'do\r'`.
- **The panel's web server usually binds the distro's own IP, not `127.0.0.1`.**
  Resolve it at runtime (`hostname -I | awk '{print $1}'`) and build the base URL
  from that. Hardcoding localhost gives you connection-refused and sends you
  debugging the wrong layer.
- **Python `urllib` cookie capture:** `urllib.request.urlopen()` does **not**
  use your opener, so an `HTTPCookieProcessor` never fires and you silently scan
  as anonymous. Always call `opener.open(req)`. Symptom: an "authenticated" scan
  whose cookie header prints empty.
- **`dnf` with a half-broken vendor repo poisons every later transaction.** If
  you added a repo file to test something and it fails metadata download, remove
  it (`rm /etc/yum.repos.d/<file>.repo && dnf clean all`) before installing
  anything else.
- **Long enumeration sweeps need a logfile, not a pipe.** Piping a multi-thousand-name
  sweep through `tail` buffers the whole run — you see nothing for minutes and cannot
  tell a slow sweep from a dead one. Write to a log file and `flush()` after every
  hit/progress line, then `tail` the file from a different call. Also run it as a
  background process: the code sandbox kills anything past ~300 s, and a sweep of
  n×prefix combinations over 5k names takes longer than that.
- **A zero-hit sweep is only meaningful if the sweep itself was validated.** Include a
  name you already know answers (the one you found by hand) as a positive control in
  the candidate list; if it does not show up in the output, the harness or the log path
  is broken, not the target hardened.
- **Read the daemon log, not just the HTTP response.** Vendor panels typically
  log every SQL statement at debug level
  (`/usr/local/mgr5/var/<mgr>.log`). That is a free map of the schema and of the
  exact query behind any function — the fastest way to find the missing
  `WHERE account_id = <session account>` that constitutes an IDOR.
- **"Requires <Edition> edition" + a fully rendered page is NOT a licence bypass.**
  Gated fields are usually `disabled` in the DOM only. You must force-enable,
  submit, **reload and re-read**; only a persisted change is a finding. On Genian
  NAC the write did not persist — client-side gate, server-side enforcement
  working, verified negative (2026-10-27).
- **Values inside `disabled` inputs are still readable from the DOM.** That is
  minimal-value information exposure and most programs exclude it; record it as a
  negative rather than filing it.
- **JSF/PrimeFaces consoles break ordinary Playwright flows** — `networkidle`
  never settles (polling), ids containing `:` need `\\:` in the selector, OTP
  stages hide the field in a dialog **iframe** (`otpAuthDlg.xhtml`), and dialogs
  throw `subtree intercepts pointer events` on click. Details + the full login
  chain: `references/cloud-trial-to-admin-console.md`.
- **A REST path returning `200` on a JSF app may be an HTML error shell, not an
  endpoint.** Check `content-type` / body before counting a route as live; a
  404-shaped HTML page with status 200 will otherwise inflate your surface map.
- **Single-use credentials invalidate a variant matrix unless you measure the
  control first.** Replaying a consumed token/assertion fails for the *second*
  submit regardless of tampering — re-capture a fresh credential per variant
  (intercept and `route.fulfill` so the browser never uses it) and fire the
  control before every variant.
- **A rejected trial/provisioning request is not an authz finding until the
  legitimate baseline succeeds.** Generic "invalid access" appears for bad enum
  values, quota exhaustion, and genuine authorization alike; establish a working
  baseline first or the differential is uninterpretable.

## Rules

- The lab is yours; full offense is appropriate there. Still keep evidence
  separated from live-target evidence.
- Never report a finding from the lab against a third party's install.
- Stop services when idle on a 6 GB host.
- A "gate passed" result is **not** a finding. It is a lead until you have
  executed the action with competing identities and reproduced it 3x.

## Support files

- `references/ispsystem-billmanager-lab.md` — full worked recipe: repo layout,
  exact RPM set and install order, DB bootstrap, identity seeding commands,
  COREmanager 5 API model, and the enumeration results shape.
- `references/cloud-trial-to-admin-console.md` — the **no-install** acquisition
  route: cloud-trial provisioning contract + replay, what the trial actually
  grants, JSF/PrimeFaces admin-console login chain (incl. OTP-in-iframe),
  edition/licence-gate proof procedure, and single-use-token control discipline.
  Verified on Genian NAC 5.0 Cloud (2026-10-27).
- `scripts/panel_func_enum.py` — generic login + function-enumeration harness
  with response classification and per-user JSON output for diffing.

## Absorbed playbooks (complete sub-packages under `references/`)
Three routes to owning a real multi-tenant surface, all under this umbrella:

- `references/ispsystem-panel-lab/PLAYBOOK.md` — ISPsystem panels (BILLmanager 6 / DNSmanager /
  ISPmanager / VMmanager): offline RPM install, service+DB init, `func=auth` session cookies,
  1554-function enumeration, four false-positive traps and the verified-negative matrix.
  `references/attack-harness.md` holds the harness.
- `references/vm-appliance-lab/PLAYBOOK.md` — when the product ships as an appliance image: find the
  hypervisor, run QEMU headless with no window on the user's screen, read the framebuffer without a
  vision model, appliance recipes (`references/synology-xpenology-dsm.md`,
  `scripts/qemu_monitor.py`). Also the correct way to redirect "more attack variants" pressure on a
  live target into a lab.
