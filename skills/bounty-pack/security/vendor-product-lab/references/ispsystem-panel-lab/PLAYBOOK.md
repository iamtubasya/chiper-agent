---
name: ispsystem-panel-lab
description: "Use when standing up a local ISPsystem panel (BILLmanager 6, DNSmanager 6, ISPmanager 6, VMmanager, DCImanager) for authorized bug-bounty testing — offline RPM install, service/DB init, identity creation, and API enumeration via func=auth session cookies."
metadata:
  hermes:
    tags: [security, bug-bounty, ispsystem, billmanager, coremanager, lab, wsl, almalinux, self-hosted]
---

# ISPsystem Panel Lab (BILLmanager 6 / COREmanager 5)

Stand up a fully functional ISPsystem billing panel locally, then enumerate and
attack its 1000+ function API. Verified end-to-end on AlmaLinux 9.8 / WSL2.

## When to use

- Target is any ISPsystem product (bug bounty: ispsystem.ru/bug-bounty or
  ispsystem.com/bug-bounty).
- Products: VMmanager, DCImanager, BILLmanager, DNSmanager, IPmanager, SSL.
- All share the COREmanager 5 framework: C++ daemon (`core`) + `ihttpd` web
  server + MySQL + EJS/JS SPA frontend. A bug in the framework hits every panel.
- BILLmanager is the richest target (multi-tenant, money movement, 200+ plugins).

## Reward tiers (drives prioritization)

| # | Bug | USD |
|---|-----|-----|
| 1 | DoS/hang via panel by non-admin | 200 |
| 2 | License limit bypass | 300 |
| 3 | Employee attacks another employee | 300 |
| 4 | User obtains another user's data | 600 |
| 5 | Non-main-admin obtains admin rights | 1200 |
| 6 | Social engineering | 200-1200 |

Rules: only self-owned installs; no third-party damage; no request-volume DoS;
no executable patching for license bypass; publicly-known bugs excluded;
confidential until fixed; report to tech support with max-debug panel logs.

## Step 1 — Get the packages (DO THIS ON THE WINDOWS SIDE)

WSL2 outbound is ~268 B/s and unusable. Download on Windows, copy via /mnt/d.

Repo layout at `https://download.ispsystem.com/repo/centos/`:

- `<ver>/9/x86_64/` — **coremanager** + coremanager-pkg-* (use `intstable`)
- `6-<ver>/9/x86_64/` — **gen6 managers** (billmanager, dnsmanager6, ispmanager)
  + 200+ `billmanager-plugin-*`
- `6-intstable/9/x86_64/` — newest gen6 (billmanager-corporate up to 6.15x)
- `base/9/x86_64/` — ISPsystem-owned deps: GeoIP, GeoIP-GeoLite-data[-extra],
  libetpan-isp, nodejs-ejs, node24-isp, node24-ejs-isp, pandoc-isp, wkhtmltox

Directory listings are browsable; `repodata/` exists but dnf metadata downloads
time out — install from local files with `dnf install ./*.rpm`.

Working set (AlmaLinux 9, versions verified 2026-10):
```
coremanager-5.449.3-1.el9.x86_64.rpm          (intstable)
coremanager-pkg-{mysql,nodejs,wkhtmltopdf,php}-5.449.3-1.el9.x86_64.rpm
GeoIP-1.6.12-7.el8.x86_64.rpm GeoIP-GeoLite-data-2018.06-5.el8.noarch.rpm
GeoIP-GeoLite-data-extra-2018.06-5.el8.noarch.rpm libetpan-isp-1.9.4-1.el9.x86_64.rpm
nodejs-ejs-1.0.0-1.el9.noarch.rpm node24-ejs-isp-3.1.10-1.noarch.rpm
node24-isp-24.22.0-1.x86_64.rpm pandoc-isp-3.6.4-2.x86_64.rpm
wkhtmltox-0.12.6.1-2.almalinux9.x86_64.rpm
billmanager-corporate-6.154.6-1.el9.x86_64.rpm  (6-intstable)
billmanager-plugin-{libs,pmauto,template-processor,gwlocalmail,gwremotemail,
  docker,ispcommon,python-libs}-6.154.6-1.el9.x86_64.rpm
billmanager-landing-dragon-ejs-1-6.154.6-1.el9.x86_64.rpm
coremanager-theme-dragon-5.449.3-1.el9.x86_64.rpm
```
Ubuntu/Debian repos exist but only publish a subset (no plugins) — use EL9.

## Step 2 — Install

```bash
wsl --install -d AlmaLinux-9          # ~10 min; may need wsl --shutdown + retry
wsl -d AlmaLinux-9 -u root -- bash -c '
  dnf -y install epel-release
  cd /root/rpms
  dnf -y install --nogpgcheck --setopt=install_weak_deps=False \
    ./GeoIP-*.rpm ./libetpan-isp-*.rpm ./nodejs-ejs-*.rpm ./node24-*.rpm \
    ./pandoc-isp-*.rpm ./wkhtmltox-*.rpm
  dnf -y install --nogpgcheck --setopt=install_weak_deps=False \
    ./coremanager-5.449.3-1.el9.x86_64.rpm ./coremanager-pkg-*.rpm
  dnf -y install --nogpgcheck --setopt=install_weak_deps=False \
    ./billmanager-corporate-*.rpm ./billmanager-plugin-*.rpm \
    ./billmanager-landing-dragon-ejs-1-*.rpm ./coremanager-theme-dragon-*.rpm
'
```

Pitfall: do NOT add an ispsystem yum repo — its repodata download times out and
poisons every later `dnf` call. Install from local RPM files only.

## Step 3 — Services, DB, first project

```bash
systemctl start mysqld ihttpd
PW=$(grep DBPassword /usr/local/mgr5/etc/billmgr.conf.d/db.conf | awk '{print $2}')
mysql -u root -e "CREATE DATABASE billmgr CHARACTER SET utf8mb4;
  CREATE USER billmgr@localhost IDENTIFIED BY '$PW';
  CREATE USER billmgr@127.0.0.1 IDENTIFIED BY '$PW';
  GRANT ALL PRIVILEGES ON billmgr.* TO billmgr@localhost;
  GRANT ALL PRIVILEGES ON billmgr.* TO billmgr@127.0.0.1; FLUSH PRIVILEGES;"
```
The billmgr schema (400+ tables) is created automatically on first daemon start.
There is no `billmgr.service` — the daemon is `bin/core billmgr`, spawned by ihttpd.

Bootstrap order (each step depends on the previous):
```bash
M=/usr/local/mgr5/sbin/mgrctl
$M -m billmgr project.edit name=lab notifyemail=a@b.c supportemail=a@b.c \
      site=https://lab.local billurl=https://lab.local sok=ok      # -> id=1
$M -m billmgr account.edit username=LabClient project=1 email=c@lab.local \
      passwd=PW confirm=PW country=1 sok=ok                        # -> id=2
$M -m billmgr user.edit name=user1 passwd=PW confirm=PW email=u1@lab.local \
      realname=U1 account=2 default_access_allow=on sok=ok         # level 16
$M -m billmgr employee.edit name=emp1 realname_ru=E1 realname=E1 \
      passwd=PW confirm=PW email=e1@lab.local sok=ok               # level 29
```
`country=1` is mandatory or account.edit fails. Employee requires `realname_ru`.

Identity model: `user.level` 16 = client user, 29 = employee/staff.
`core_users.super=on` = account owner. `user2role`/`user_role` = RBAC.

## Step 4 — API access (the important part)

Panel: `https://<wsl-ip>:1500/billmgr` — **ihttpd binds the WSL VM IP, not
127.0.0.1**. Get it with `hostname -I`.

Login (sets the session cookie):
```
POST /billmgr   func=auth&username=U&password=P&lang=en&sok=ok
  Header: X-Requested-With: XMLHttpRequest
  -> Set-Cookie: billmgrses5=<hex>; path=/; HttpOnly; Secure
```
Then every function is callable:
```
POST /billmgr   func=<name>&out=json     Cookie: billmgrses5=...
```
Response is JSON with a `doc` key, or `{"doc":{"error":{"$type":"access",...}}}`
when the access gate rejects it.

CLI equivalent (no HTTP, runs as root — great for tracing):
```
/usr/local/mgr5/sbin/mgrctl -m billmgr <func> [params]
```
`/usr/local/mgr5/var/billmgr.log` logs **every SQL statement** at EXTINFO — use
it to reverse the backend authz logic for any function.

## Step 5 — Enumerate the attack surface

Extract the full function list from the installed metadata:
```bash
grep -oh 'func="[^"]*"' /usr/local/mgr5/etc/xml/*.xml | sed 's/func="//;s/"//' | sort -u
# 1554 total across core + plugins; billmgr.xml alone has ~1021
```
Plugin functions live in `billmgr_mod_*.xml`, so scanning only `billmgr.xml` misses ~1/3 of the
surface. `level="admin"` in the XML is a UI hint only — the real check is server-side, so treat it
as a priority list, never as proof.

Then replay each as a low-privileged user and classify:
- `access` error  -> gate held
- `missed` param  -> **gate passed**, needs an argument (prime lead)
- `OK`            -> returned real data
- other error     -> gate passed, failed later

Differential scan (level 16 vs level 29, and vs **no cookie at all**) separates
"user-reachable by design" from "admin-only but reachable" and from "unauthenticated". Then replay
every gate-passer with two competing identities and cross-tenant object IDs to prove IDOR / privesc.

**Ready-to-run harness** (login with correct cookie capture, correct classifier order, tenant
seeding SQL, wizard-vs-action check, and the MSYS/CRLF/f-string pitfalls):
`references/attack-harness.md` in this skill.

### Four false-positive traps — each one produced a fake finding before being disproven

These are the reason a verified negative is worth writing down. All hit on BILLmanager 6.154.6.

**1. `missed` is AMBIGUOUS — it means two different things.** COREmanager returns
`{"doc":{"error":{"$type":"missed"}}}` both for *"required parameter absent"* **and** for
*"function not found — the associated module is missing"*. Read the message body before classifying:

```
"Failed to find the '__value__' function. The associated module is missing"  -> NOT a finding
"Field 'X' has invalid value / cannot be empty"                             -> real param gate
```
Classifying the second as "authz gate open" invented a dozen fake findings. Count the NOFUNC set
explicitly: on BILLmanager 6.154.6, **182 of 1554 functions were simply not loaded** (~12% of the
surface untestable until the owning plugin is installed). Install the plugin before concluding
anything about those functions.

**2. `"doc"` is present in error responses too.** The envelope is `{"doc":{"error":{…}}}`, so
`'"doc"' in body` is true for *every* error. A classifier that treats "has doc" as "executed"
reports every denied call as a success. Check `"$type":"access"` / `Insufficient privileges`
**first**, then for any `$type`, and only then fall back to the doc check.

**3. A 200 with no error is usually a rendered WIZARD step, not a completed write.**
`account.discount.add`, `gateway.create`, `fraud_gateway.create`, `billmgr.backup.setup`,
`backup.storages.add`, `bundle.pricelist.add`, `company.add`, `docflow_connection.add` all returned
a clean doc for a level-16 user. The daemon log gave it away:

```
wizard EXTINFO Wizard 'account.discount.add' done
```

…and **zero rows** existed in `discount` / `gateway` / `pricelist` / `bundle` / `companycontract` /
`docflow_connection`. Multi-step `.add`/`.create` endpoints render step 1 to anyone who can reach
the form. **Confirm side effects in the DB (or via a read endpoint) before claiming an action
succeeded.** A ~2.6 KB response is a form; a real write returns the created object.

**4. A CSRF/referer gate sits IN FRONT of the authz check — use it as an oracle.**
~30 delete/action functions answer `referer_confirm` before any privilege check. It is satisfiable
by sending a `Referer` header whose **host** matches the panel, which makes it a useful
discriminator: with a valid referer the same call returns `access` (denied) or proceeds, so you can
separate "CSRF gate" from "authz gate". Measured: exact host passes; `http://` is accepted for an
`https://` page (scheme-agnostic, **not** CSRF-exploitable); superdomain (`host.evil.com`),
host-in-path, query-inject, fragment and userinfo variants are all **blocked** — it is a real host
check, so do not report it as a bypass.

**Error responses leak the caller's own identity.** Every error embeds
`"stack":{"action":{"$level":"16","$user":"5","$":"<func>"}}` — reproducible on ~30 functions, but
it discloses the attacker's *own* level and id, so run the capability-gain test
(`security/authed-webapp-audit`) before treating it as reportable.

### Verified-negative matrix (BILLmanager 6.154.6, level-16 client user)

Recorded so a future session does not repeat it. **All blocked:**

| Vector | Result |
|---|---|
| `payment.edit/print/su`, `expense.edit`, `user.edit`, `account.edit/su`, `subaccount.edit` on another tenant's `elid` | `access` denied |
| `payment?account=3`, `payment?subaccount=2` filter widening | no cross-tenant rows |
| `session.filter`, `session.su`, `userrights.edit`, `project.edit`, `reseller.edit`, `ihttpd.edit`, `sysinfo` | `access` denied |
| `/mancgi/upload` (`type=data` write, `type=link` SSRF to `127.0.0.1` / `169.254.169.254` / `file:///etc/passwd`) | `"Access denied"` |
| CSRF `Referer` spoofing (11 variants) | all `referer_confirm` |
| `su` to a user in the caller's own account | succeeds (by design); foreign account / employee → `user_not_found` |
| `expense.edit amount=-9999` / `-0.0001` / `abc` | rejected, server-side range `[0,92233720368.00]` |
| `subaccount.edit elid=<own> balance=999999` | `access` denied (`$object":"action"`) |
| `payment.add` any amount | `no_paymethod` — **untested**, paymethod could not be made client-visible |
| Installing 27 more plugins to revive NOFUNC | 182 NOFUNC unchanged; needs a live processing module |

The owner-vs-foreign `elid` pair is the proof shape: the same call returns full data for the
owner's id and `access` for the foreign id. That pair is what makes an eventual positive credible.

### Plugin-activation experiment — installing plugins does NOT revive NOFUNC functions

Tried and measured, so a future session does not repeat a ~30-minute install + rescan cycle.

Installed 27 more plugins on top of the base set (`pmmanual`, `pmcustom`, `pmdcimgr`,
`pmdcimgr6`, `pmdnsmgr`, `pmenomssl`, `pmgogetssl`, `pmipmgr`, `pmispmgrssl`,
`pmnamecheapssl`, `pmpaasvepp`, `pmresellerclub`, `pmthesslstore`, `pmvmmgr`, `pmvmmgr6`,
`pmvmmgr6-iaas`, `pmvmware`, `pmvmwarevds`, `pmvsphere`, `pmopenstack`, `pmopenstackvds`,
`pmcpanel`, `pmplesk`, `pmispmgr4/5/6`, `pmvdsmgr`). Loaded `.so` modules went **63 → 92** and
the XML function count went 1554 → 1555.

**Result: the 182 NOFUNC functions were unchanged.** Re-scanned and diffed — identical.

Confirmed it is *not* a privilege issue: `test.request`, `osmgr.install`, `file.edit`,
`affiliate.edit`, `uniservice.edit`, `app.edit`, `selecttickets.edit`, `ipmgr2.net.ip`,
`ipdb.addr`, `recipemgr.update` all return NOFUNC for **both** level-16 and level-29.

**Why:** those modules are only registered when a real *processing module* is connected — an
actual VMmanager / IPmanager / DCImanager server. A local panel with no processing node cannot
load them. Budget for this: ~12% of the surface is untestable in a standalone lab.

**What plugins DID unlock:** the `pm*` processing-module plugins activated `vdc.*`
(`vdc.vm.edit`, `vdc.router.firewall.edit`, …) and `paas.edit` — those moved from NOFUNC to
live. So the rule is: `pm<product>` plugins register their service functions; the
file-manager / osmgr / recipemgr / ipmgr2 / test / affiliate / uniservice / app /
selecttickets modules need a live backend, not a package.

### `su` is reachable by a client but correctly scoped (not privesc)

`su` is callable by a **level-16** client yet **denied for a level-29 employee** — an inversion
that looks like a bug and is not. Measured scoping:

| target `elid` | who | result |
|---|---|---|
| 4, 5, 6 | users inside the **caller's own account** | succeeds, issues a new `auth` session |
| 7 | employee (account 1) | `user_not_found` |
| 8, 9 | users of another account | `user_not_found` |

Out-of-scope targets answer `user_not_found`, **not** `access denied` — good design, no user
enumeration. Every other `.su` variant (`session.su`, `account.su`, `user.su`, `employee.su`,
`reseller.su`, `vdc.su`, `paas.su`, `colocation.su`, `dedic.su`, `ticket_favorite.su`) is
`access` denied for level 16.

### Money-flow validation is server-side (verified)

- `expense.edit amount=-9999` / `-0.0001` → rejected with
  `"The 'Amount' field has invalid value. This value is too short. It must be a number from
  [0,92233720368.00]"`. The range is enforced **server-side**, not client-side.
- `expense.edit amount=abc` → rejected. `0`, `999999999`, `1e10` pass the amount check and fail
  later on a missing `realdate` — so **param validation runs BEFORE the authz check**. That
  ordering is a free oracle: supply a valid value and a denied call flips from `value` to
  `access`.
- `subaccount.edit elid=<own> balance=999999` → `access` denied, `$object":"action"`
  ("Insufficient privileges to access Function"). Balance is not client-writable.
- Cross-tenant `expense.edit elid=2` → `access` denied, and the error names the foreign
  subaccount id.

### Pitfall — making `payment.add` testable

`payment.add` answers `no_paymethod` until a paymethod exists that the *client* flow will pick
up. Creating one is fiddlier than it looks:

- `paymethod.edit` requires `name_ru` **and** `profiletype`; `profiletype` is a
  `type="multiple"` select whose values are **not** in the `enumeration` /
  `enumerationitem` tables (those hold network/CPU/RAM lists), so guessing `person` /
  `company` / `legal` / `individual` all fail with `value(profiletype)`.
- Inserting the row directly via SQL (`paymethod` + `paymethod2project`) makes it visible to
  `mgrctl` and the DB, but `payment.add` **still** returned `no_paymethod` for every amount —
  negative, zero, and valid alike. So the amount-validation path of the payment flow remains
  **untested**; do not claim it as a verified negative.
- Next time: create the paymethod through the employee UI (or find the real `profiletype`
  domain) rather than SQL, then re-test `payment.add` with `-1000`, `0`, `-0.01`,
  `999999999999`.

### Untested high-value surface (next session)

- **`errorjournal.edit` returns error type `xml` for a level-16 user** — not `access`, not
  `missed`. Possible XML-injection / XXE surface in the error journal. Highest-value new lead.
- **Level inversions to explain**: `journal.edit`, `scheduler.edit`, `paas.edit` pass the gate
  for level-16 while emp1 (29) is denied. Confirm by-design vs bug.
- **`vdc.*` is now live** (after `pmvmmgr6-iaas`) but the lab has zero VDC objects — seed some
  and run the owner-vs-foreign `elid` pair across `vdc.vm.*`, `vdc.network.*`,
  `vdc.router.firewall.*`, `vdc.snapshot.*`, `vdc.volume.*`.
- **Real money-flow business logic with live objects** — `payment.add` → balance → `expense` →
  refund: negative amounts, currency rounding, duplicate-submit races, promocode/coupon
  stacking. (Tier #2 licence-limit bypass and #4 data access both live here.)
- **Employee-vs-employee (tier #3)** — needs two employees with *different roles* to exercise
  `department.rights`, `user_role.rights`, `rights2.user.*`.
- **`template-processor` + `doctmpl`** — user-editable document templates rendered through EJS
  are a classic SSTI → RCE path.

## Pitfalls

- **urllib cookie capture**: `urllib.request.urlopen()` ignores your opener, so
  `HTTPCookieProcessor` never fires and you silently scan as anonymous. Always
  call `opener.open(req)`, and assert the cookie string is non-empty before
  trusting any result.
- `wsl -- heredoc` mangles awk/quotes. Write scripts with Python
  (`open(path,"w",newline='\n')`) and run with `MSYS_NO_PATHCONV=1`.
- Trial license ships pre-installed and reads `Supported: no` / expired — the
  panel still works fine for testing. Ignore it.
- WSL drops the distro VM when idle; re-check `systemctl is-active mysqld ihttpd`
  after any gap, and retry connections with backoff.
- `wsl -l -v` can hang if the LxssManager service died — recover with
  `wsl --shutdown`, `taskkill /F /IM wsl.exe`, then retry.

## Related

- `security/bug-bounty` — unified bounty router
- `hunt-business-logic`, `hunt-idor`, `hunt-auth-bypass` — per-class technique
- `bb-methodology`, `audit-runbook` — phase discipline
- `bug-report-delivery`, `pdf-bug-report-generation` — report output
