# ISPsystem BILLmanager 6 — worked lab recipe

Session: 2026-10-27. Target `https://www.ispsystem.ru/bug-bounty` (mirror:
`ispsystem.com/bug-bounty`). Everything below is reproducible.

## 1. Program facts

Products: VMmanager, DCImanager, BILLmanager, DNSmanager, IPmanager, SSL certs.
All share the **COREmanager 5** framework (C++ daemon + `ihttpd` + MySQL +
EJS/JS SPA frontend).

Reward tiers (RU page in ₽, EN page in USD):

| # | Bug | ₽ | $ |
|---|---|---|---|
| 1 | DoS/hang via panel by non-admin | 15 000 | 200 |
| 2 | Use more resources than licensed | 25 000 | 300 |
| 3 | Employee attacks another employee | 25 000 | 300 |
| 4 | User obtains another user's data | 50 000 | 600 |
| 5 | Non-main-admin obtains admin rights | 100 000 | 1200 |
| 6 | Social engineering | 15 000–100 000 | 200–1200 |

Submission: tech-support form (name, vuln type #1–#6, email, step-by-step
repro, current vs expected result, screencast link, CAPTCHA) + accept the
offer. Review 3 business days. Payout only after the fix ships, max 1 week.

Exclusions that shaped the plan: no third-party installs; no DoS by volume; no
executable-file patching for license bypass; publicly-known bugs excluded;
employees/relatives excluded; confidential until fixed.

Chosen product: **BILLmanager 6** — richest business logic (money path,
promotions, pricelists, 200+ plugins) and tiers #3/#4/#5 all map onto it.

## 2. Repo layout (the part that costs time)

Base: `https://download.ispsystem.com/repo/`

```
centos/
  intstable/9/x86_64/     <- coremanager + coremanager-pkg-* (framework)
  6-intstable/9/x86_64/   <- billmanager-corporate + ALL 200+ plugins (gen 6)
  6-5.452/9/x86_64/       <- stable snapshot of the above
  base/9/x86_64/          <- GeoIP, libetpan-isp, node24-isp, nodejs-ejs,
                             pandoc-isp, wkhtmltox  (vendor-built base deps)
ubuntu/pool/main/<letter>/ <- debs; billmanager + dnsmanager6 + ispmanager only
```

`install.sh` at `http://dl.ispsystem.com/install.sh` is the authoritative
supported-OS list:

```
centos_OSVERSIONS="6 7 8 9"
debian_OSVERSIONS="wheezy jessie stretch buster bullseye"
ubuntu_OSVERSIONS="trusty xenial bionic focal jammy noble"
```

Traps confirmed:
- `dists/stable-<codename>` only exists for ancient releases; current packages
  live in `intstable-<codename>` and in the generation-prefixed trees.
- `ubuntu/pool` has **no plugin packages** — the full plugin set is EL9-only.
- The `6-intstable` Packages index does **not** contain coremanager; framework
  comes from `intstable`. Two repos are mandatory.
- Directory autoindex is enabled on `mirrors.download.ispsystem.com` and
  `download.ispsystem.com` but 403s on some `dists/` paths — probe the pool.

## 3. Host

`wsl --install -d AlmaLinux-9` (AlmaLinux 9.8, systemd available, root via
`-u root`). Ubuntu 26.04 was already present but unsupported by the vendor.

## 4. Exact package set and install order

Download on the **Windows host** (WSL egress was ~268 B/s; host curl did 15 MB
in seconds), copy to `/root/rpms`, install in three layers.

Layer 1 — base (`centos/base/9/x86_64/`):

```
GeoIP-1.6.12-7.el8.x86_64.rpm
GeoIP-GeoLite-data-2018.06-5.el8.noarch.rpm
GeoIP-GeoLite-data-extra-2018.06-5.el8.noarch.rpm
libetpan-isp-1.9.4-1.el9.x86_64.rpm
nodejs-ejs-1.0.0-1.el9.noarch.rpm
node24-ejs-isp-3.1.10-1.noarch.rpm
node24-isp-24.22.0-1.x86_64.rpm
pandoc-isp-3.6.4-2.x86_64.rpm
wkhtmltox-0.12.6.1-2.almalinux9.x86_64.rpm
```

Layer 2 — framework (`centos/intstable/9/x86_64/`):

```
coremanager-5.449.3-1.el9.x86_64.rpm
coremanager-pkg-mysql-5.449.3-1.el9.x86_64.rpm
coremanager-pkg-nodejs-5.449.3-1.el9.x86_64.rpm
coremanager-pkg-wkhtmltopdf-5.449.3-1.el9.x86_64.rpm
coremanager-pkg-php-5.449.3-1.el9.x86_64.rpm
```

Layer 3 — product + plugins (`centos/6-intstable/9/x86_64/`, all `6.154.6-1`):

```
billmanager-corporate  billmanager-plugin-libs
billmanager-plugin-template-processor  billmanager-plugin-docker
billmanager-plugin-pmauto  billmanager-plugin-gwlocalmail
billmanager-plugin-gwremotemail  billmanager-landing-dragon-ejs-1
coremanager-theme-dragon-5.449.3-1  billmanager-plugin-ispcommon
billmanager-plugin-python-libs
```

Plus optional audit-surface plugins, same version: `ai`, `analytics-storage`,
`ispmanager`, `keycloak`, `ldap`, `marketplace`, `pmcustom`, `pmmanual`,
`telegram`, `addon-templates`, `addonquota`, `autoinvoice`, `baas`,
`bonusprogram`, `businessintelligence`, `businessprocesses`,
`dedic-reservation`, `denovo`, `dl`, `fz406`, `granularity`, `ie`, `libchat`,
`novnc`, `otel`, `paymentreceipt`, `promisepayment`, `sorm`, `vdcbackup`,
`vkid`, `vkontakte`, `yandexmetrika`.

```bash
dnf -y install epel-release
dnf -y install --nogpgcheck --setopt=install_weak_deps=False ./<layer>.rpm
```

`epel-release` is mandatory — `fcgi`, `geoip`, `jsoncpp`, `libunwind`,
`qrencode`, `trousers`, `libidn`, `libssh2` all come from EPEL.

## 5. Service + DB bootstrap

```bash
systemctl start mysqld
PW=$(awk '/^DBPassword/{print $2}' /usr/local/mgr5/etc/billmgr.conf.d/db.conf)
mysql -u root -e "CREATE DATABASE IF NOT EXISTS billmgr CHARACTER SET utf8mb4;
  CREATE USER IF NOT EXISTS billmgr@localhost IDENTIFIED BY '$PW';
  CREATE USER IF NOT EXISTS billmgr@127.0.0.1 IDENTIFIED BY '$PW';
  GRANT ALL PRIVILEGES ON billmgr.* TO billmgr@localhost;
  GRANT ALL PRIVILEGES ON billmgr.* TO billmgr@127.0.0.1; FLUSH PRIVILEGES;"
systemctl start ihttpd        # spawns bin/core billmgr on first request
```

Notes:
- There is **no `billmgr.service`**. The daemon is `bin/core billmgr`, spawned by
  `ihttpd`. `systemctl start billmgr` fails with "Unit not found" — that is
  normal, not a fault.
- `db.conf` is generated at install time with a random password; read it, do not
  invent one.
- The package ships `/usr/local/mgr5/etc/billmgr.lic` already containing a
  **Trial License** (`licctl info` shows `Supported: no`, expired). The panel is
  nonetheless fully functional — no client-area signup was needed.
- `ihttpd` listens on the **distro IP**, not `127.0.0.1`. Resolve with
  `hostname -I`.

## 6. Identity seeding (order is mandatory)

```bash
M=/usr/local/mgr5/sbin/mgrctl

# 1. project/provider — notifyemail + supportemail are mandatory
$M -m billmgr project.edit name=lab notifyemail=lab@lab.local \
   supportemail=lab@lab.local site=https://lab.local billurl=https://lab.local sok=ok

# 2. account — project=<id>, country=<id>, passwd all mandatory
$M -m billmgr account.edit username=LabClient project=1 email=client@lab.local \
   passwd=ClientPass123 confirm=ClientPass123 country=1 sok=ok

# 3. users (level 16 = client)
$M -m billmgr user.edit name=user1 passwd=Pass1234 confirm=Pass1234 \
   email=user1@lab.local realname=UserOne account=2 default_access_allow=on sok=ok

# 4. employee (level 29 = staff) — realname_ru mandatory
$M -m billmgr employee.edit name=emp1 realname_ru=EmpOne realname=EmpOne \
   passwd=Pass1234 confirm=Pass1234 email=emp1@lab.local sok=ok
```

Field discovery trick: call any `*.edit` with **no arguments** — the error body
is the complete parameter list. Then add them one at a time; each error names the
next missing mandatory field.

Resulting identity matrix:

| login | level | account | role |
|---|---|---|---|
| user1 / Pass1234 | 16 | 2 | client A (IDOR attacker) |
| user2 / Pass1234 | 16 | 2 | client B (IDOR victim) |
| labclient | 16 | 2 | account owner, `core_users.super=on` |
| emp1 / Pass1234 | 29 | 1 | employee/staff |

`level 16` = client user, `level 29` = employee. `core_users.super=on` marks the
account's own primary user.

## 7. API model (COREmanager 5)

```
POST https://<distro-ip>:1500/billmgr
Content-Type: application/x-www-form-urlencoded
X-Requested-With: XMLHttpRequest          # REQUIRED — without it you get the SPA HTML
func=auth&username=user1&password=Pass1234&lang=en&sok=ok
  -> 200, Set-Cookie: billmgrses5=<32 hex>, billmgrlang5=dragon:en

POST ... func=<any>&out=json   (Cookie: billmgrses5=...)
  -> JSON {"doc":{...}} on success, {"doc":{"error":{"$type":"access",...}}} on denial
```

Session cookie name is `<manager>ses5` (`billmgrses5`, `ispmgrses5`, ...).
`out=json` is what turns the SPA shell into machine-readable output.

CLI equivalent (root, no session): `/usr/local/mgr5/sbin/mgrctl -m billmgr <func> [params]`.
Useful for seeding and for reading state without a browser.

## 8. White-box from the package

`dpkg-deb -R` / `rpm2cpio | cpio -idm` the product package. For BILLmanager:

```
usr/local/mgr5/etc/xml/billmgr.xml                 23 477 lines — every function + toolbar
usr/local/mgr5/etc/xml/billmgr_userrights_{0,16,29}.xml   per-level function whitelists
usr/local/mgr5/etc/xml/billmgr_msg_*.xml           message catalogs (error text)
usr/local/mgr5/skins/**, *.ejs                      UI templates
usr/local/mgr5/etc/sql/*.sql                        seed data
```

`billmgr.xml` yielded **1021 distinct `func="..."` names** — the complete
callable surface, far better than any wordlist. `level="admin"` / `level="user"`
attributes are *UI hints only*; real enforcement is in the C++ daemon, so the XML
tells you what the vendor *intended*, which is exactly what you diff against.

## 9. Enumeration result shape (level-16 user, 1021 functions)

| class | count | meaning |
|---|---|---|
| `access denied` | 878 | control working |
| `missing parameter <x>` | 65 | **gate passed**, needs params — prime leads |
| real data returned | 37 | investigate immediately |
| `referer_confirm` | 30 | CSRF-ish gate, understand before dismissing |
| `no_available_pricelist` / `no_currency` / `no_companycontract` | 9 | config gaps, not security |
| `value` / `assert` | 2 | possible input-validation bugs |

Accessible-to-level-16 functions worth driving with competing IDs:
`expense.edit/delete/filter`, `globaldiscount.edit/delete`,
`invoice.edit/delete/item.edit/item.correction`, `contract.edit/delete`,
`fraud_gateway.create`, `gateway.create`, `billmgr.backup.setup`,
`document.filter/pdf/print`, `money_all.filter`, `item_all.filter`,
`affiliate.*`, `gdpr_user_journal.filter`, `s3storage.service_export`,
`soft.licvalue`, `uniservice.su`, `domain.doc.upload/download`.

## 10. Known-issue intel (exclusion check)

ISPsystem had a live **VMmanager 6** security incident in Oct 2026 (FirstVDS
breach — attackers mounted VM disks read-only and exfiltrated credentials).
Vendor published only mitigation advice, **no technical details**. That is a
different product from BILLmanager, but it confirms the vendor is actively
burning through vulns and that VMmanager 6 is worth a separate lab.

No public BILLmanager writeups were found — low duplicate risk.

## 11. Unauthenticated-reach probe (accidental, then deliberate)

The third enumeration run had the urllib cookie bug (see Pitfalls) and went out
with an **empty cookie header** — i.e. fully anonymous. Do not discard such a
run: it is a free unauthenticated-reach probe, and it produced a real lead.

Observed with **no session at all** (1021 functions):

- **51 functions did not return access-denied.**
- `money_all.filter` returned ~15.9 KB and `item_all.filter` ~14 KB of real
  data — both are aggregate/report surfaces that a level-16 user can also reach.
- Also non-denied anonymously: `logon`, `recovery`, `period`, `platformpacket`,
  `notify.template`, `soft.licvalue`, `showroom.mini`, `s3storage.service_export`,
  `service_profile.doc`, `processing.customparam.filter`,
  `referralprogram.rule.history`, `ticket_open.edit/delete`,
  `uniservice.*` (13 functions), `affiliate.*` (14), `app.*` (9),
  `accountoption`, `globaldiscount.edit/delete`.

Interpretation is still open: the panel may set a pre-session cookie on the auth
POST even when credentials fail, so "no cookie" may not mean "no session". That
is exactly why this must be re-run deliberately with `--no-auth` and the
response inspected for whether a session id was issued. If `money_all.filter`
returns real data with genuinely no session, that is an unauthenticated
data-disclosure bug and pays immediately.

Technique lesson: when an auth harness silently fails, the resulting
unauthenticated sweep is a *distinct and valuable* scan, not wasted work. Keep
it, label it, and re-run it deliberately.

## 12. Next actions queued

1. Confirm or deny the unauthenticated reach above with a deliberate `--no-auth`
   run, checking whether a session id is issued on a failed auth.
2. Run the identical scan as `emp1` (level 29) and diff against the `user1`
   scan (`panel_func_enum.py --diff`), hand-verifying the diff on a few
   known-different functions first.
3. For every Tier-A function, replay with `user1`'s session against `user2`'s
   object IDs and against admin-only objects; capture exact request/response.
4. Anything that succeeds: reproduce 3x, then PDF PoC + Gmail draft (not sent).

## 13. Artifact locations

```
D:\isplab\rpms\        all fetched RPMs
D:\isplab\bm\          extracted billmanager deb (white-box)
D:\isplab\funcs.json   1021 function names
D:\isplab\fuzz.py      enumeration harness (superseded by the skill script)
D:\isplab\scan_*.json  per-identity scan results
/usr/local/mgr5/var/billmgr.log   every SQL statement, debug level
```
