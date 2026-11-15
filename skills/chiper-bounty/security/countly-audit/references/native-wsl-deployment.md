# Countly native WSL deployment (live PoC)

White-box bounty REQUIRES a working PoC on a deployment you control. Countly cannot run without
MongoDB + Node. On this Windows host, Docker Desktop is an unreliable path (its VHD lives on C:,
which is usually 95%+ full, and Docker Desktop's WSL2 backend wedges "unable to start"). Native
WSL is the robust route: the WSL ext4 filesystem has ~950 GB free.

Verified 2026-11-04. All commands run from git-bash, driving `wsl -d Ubuntu-26.04`.

## 0. Prereq check

```bash
wsl -l -v                          # distro alive? (Stopped is fine)
wsl -d Ubuntu-26.04 -e sh -c 'df -h / | tail -1; free -h | head -2; which node npm'
```

If `CreateInstance/E_FAIL` or "Catastrophic failure" → WSL2 backend is wedged, reboot Windows.

## 1. Install mongod (TARBALL from fastdl — NOT apt)

The apt path hangs on `gpg --dearmor` (network to `mongodb.org` is slow/blocked). The tarball from
`fastdl.mongodb.org` skips the keyring entirely and is faster:

```bash
wsl -d Ubuntu-26.04 -e bash -lc '
  cd $HOME
  curl -fsSL -o mongo.tgz "https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2204-7.0.14.tgz"
  tar xzf mongo.tgz && mv mongodb-linux-x86_64-ubuntu2204-7.0.14 mongodb && rm -f mongo.tgz'
# symlink (needs root):
wsl -d Ubuntu-26.04 -u root -e bash -lc '
  ln -sf $HOME/mongodb/bin/mongod /usr/local/bin/mongod'
```

Note: the tarball ships `mongod` but NOT `mongosh` (mongosh is a separate package) — Countly only
needs the server (it talks via the node driver), so `mongosh` is not required.

## 2. Install Node (nodesource) — WSL has no node by default

```bash
wsl -d Ubuntu-26.04 -u root -e bash -lc '
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs'
# → node v20.20.x, npm 10.x
```

## 3. Clone + npm install (on ext4, NOT /mnt/d)

```bash
wsl -d Ubuntu-26.04 -e bash -lc '
  cd $HOME && git clone --depth 1 https://github.com/Countly/countly-server.git countly
  cd countly && npm install --no-audit --no-fund'   # ~650 packages, ~2 min
```

## 4. Start mongod (forked, survives)

```bash
wsl -d Ubuntu-26.04 -e bash -lc '
  mkdir -p $HOME/mongodb/data $HOME/mongodb/log
  $HOME/mongodb/bin/mongod --dbpath $HOME/mongodb/data \
    --bind_ip 127.0.0.1 --port 27017 --fork --logpath $HOME/mongodb/log/mongod.log'
```

## 5. Config + the `plugins.json` quirk (CRITICAL)

```bash
wsl -d Ubuntu-26.04 -e bash -lc '
  cd $HOME/countly
  cp api/config.sample.js api/config.js
  cp frontend/express/config.sample.js frontend/express/config.js
  cp plugins/plugins.default.json plugins/plugins.json'   # ← without this, `Cannot find module ./plugins.json`
```

`plugins/plugins.json` is `.gitignore`-d (generated at install time) so a bare clone lacks it. It is
just a JSON array of enabled plugin ids; `pluginDependencies.getFixedPluginList` re-writes it on boot
if needed. Copying `plugins.default.json` is the exact right seed.

## 6. Start the API (survive SIGHUP)

The trap: `node api/api.js &` run inside a `wsl -e bash -lc` that then exits gets **SIGHUP** as the
WSL instance tears down its session — the node master dies ("Got signal: SIGHUP / Exiting due to
master exited"). Launch with `setsid nohup ... < /dev/null &` to fully detach:

```bash
wsl -d Ubuntu-26.04 -e bash -lc '
  cd $HOME/countly
  setsid nohup /usr/bin/node api/api.js > $HOME/countly-api.log 2>&1 < /dev/null &'
```

Health check (port 3001 is the API default):

```bash
wsl -d Ubuntu-26.04 -e bash -lc 'curl -s -w "%{http_code}" http://127.0.0.1:3001/i'
# 400 + {"result":"Missing parameter \"app_key\" or \"device_id\""} = HEALTHY (server up, that 400 is correct)
# first boot spends a few minutes auto-installing plugins ("Installing plugin ...")
```

Confirm processes are detached: `ps -eo pid,comm,args | grep -E "node|mongod"` should show
`countly: api master` + 2× `countly: api worker`, NOT a child of a short-lived bash.

## 7. Seed identity (admin + apps + non-admin members)

`scripts/seed.js` (in this skill) writes directly to MongoDB via the `mongodb` + `argon2` deps that
already exist in Countly's own node_modules — no API round-trip, no fake PII. Copy it into the countly
dir on WSL and run `node seed.js` from there (so `require('mongodb')`/`require('argon2')` resolve).

Key schema facts learned from source:
- member `permission` shape: `{c:{},r:{},u:{},d:{},_:{a:[], u:[[]]}}` (empty = no access). `admin_of`
  is legacy. `user_of` = legacy read-only app list. `global_admin:true` = full.
- app must carry `key` (the SDK app_key), `id_key` (same, immutable), and `keys:[{key,added_at,last_data}]`
  (accepted-keys array). The API resolves incoming `app_key` against `keys.key` then `key`.
- passwords are argon2 (`argon2.hash('pw'+secret)`; secret is `config.passwordSecret`, default "").

## 8. Differential probe pattern (verifies authz/hardening, not just reads)

The whole point of a live deployment is the **differential**: valid-vs-invalid, owner-vs-neighbor,
admin-vs-scoped. `seed.js` creates app A + app B + `userb` (read-only on A only) + `userc` (no access)
+ a scoped token, so you can fire:

- BOLA: `userb` api_key on app B → expect `{"result":"User does not have right"}` (schema-confirm a
  with-tenant-context request first, per audit-runbook RULE 24e).
- scoped-token escalation: `auth_token=<scoped>` on `/i/token/create?can_login=true` → refused.
- redaction: admin `/o/export/db?collection=members` → api_key/password absent.

Output of these probes is captured verbatim in the log; that is your PoC/negative-control artifact.