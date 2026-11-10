---
name: countly-local-deployment
description: "Use when standing up a Countly PoC lab for its bug bounty."
---

# Countly Local Deployment (native WSL, no Docker)

Countly adalah **white-box source bounty** (SECURITY.md): in-scope = repo publik, TAPI **PoC hidup wajib** ("findings from source reading/static analysis alone are not eligible"). Ini resep deployment di WSL native — lebih andal daripada Docker (yang wedge di host ini karena hypervisor WSL2 + C: full).

## Alasan native WSL, bukan Docker
- Docker Desktop gagal start saat C: penuh (`unexpected EOF` saat pull) atau WSL2 wedge (`CreateInstance/E_FAIL`).
- Countly punya banyak plugin yang di-`npm install` saat boot pertama — native WSL di ext4 jauh lebih cepat + disknya besar (952 GB vs C: 5 GB).

## Titik jebakan (semua sudah ketemu + dipecahkan)
1. **Mongod install via apt ngegantung.** `gpg --dearmor` dari repo.mongodb.org lambat/ke-block ISP. → Pakai **tarball binary langsung dari `fastdl.mongodb.org`** (tanpa gpg, tanpa apt):
   ```
   curl -fsSL -o mongo.tgz "https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2204-7.0.14.tgz"
   tar xzf mongo.tgz && mv mongodb-linux-x86_64-ubuntu2204-7.0.14 mongodb
   ```
2. **`cd /root` permission denied.** WSL default user = `windows10` (bukan root). Pakai `$HOME`, dan jalankan `ln -sf` ke `/usr/local/bin` lewat `-u root` (atau langsung panggil `$HOME/mongodb/bin/mongod`).
3. **`plugins/plugins.json` hilang** di clone fresh (`.gitignore`). Error: `Cannot find module './plugins.json'`. Fix: `cp plugins/plugins.default.json plugins/plugins.json` — `getFixedPluginList` auto-overwrite resolusinya.
4. **API mati kena SIGHUP** kalau di-launch `&` di dalam `bash -lc` (parent shell exit → child tewas). Fix: `setsid nohup node api/api.js > log 2>&1 < /dev/null &` atau via systemd unit (`/etc/wsl.conf` `[boot] systemd=true`).
5. **Mongod harus `--fork`** supaya survive (jangan foreground).

## Langkah (runtun)

```bash
# 1. mongod (tarball fastdl)
wsl -d Ubuntu-26.04 -e bash -lc '
 cd $HOME && curl -fsSL -O https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2204-7.0.14.tgz
 tar xzf mongodb-linux-x86_64-ubuntu2204-7.0.14.tgz && mv mongodb-linux-x86_64-ubuntu2204-7.0.14 mongodb
 mkdir -p mongodb/data mongodb/log
 mongodb/bin/mongod --dbpath mongodb/data --bind_ip 127.0.0.1 --port 27017 --fork --logpath mongodb/log/mongod.log'

# 2. node (nodesource 20)
wsl -d Ubuntu-26.04 -u root -e bash -lc 'curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs'

# 3. clone + deps
wsl -d Ubuntu-26.04 -e bash -lc 'cd $HOME && git clone --depth 1 https://github.com/Countly/countly-server.git countly
 cd countly && npm install --no-audit --no-fund'

# 4. config + plugins.json
wsl -d Ubuntu-26.04 -e bash -lc 'cd $HOME/countly && cp api/config.sample.js api/config.js
 cp frontend/express/config.sample.js frontend/express/config.js
 cp plugins/plugins.default.json plugins/plugins.json'

# 5. boot API (survive)
wsl -d Ubuntu-26.04 -e bash -lc 'cd $HOME/countly && setsid nohup node api/api.js > $HOME/countly-api.log 2>&1 < /dev/null &'
```

Health check: `curl http://127.0.0.1:3001/i` → `{"result":"Missing parameter \"app_key\"..."}` = hidup (port 3001 default).

## Seed kredensial (bikin sendiri, jangan manual)
Script `countly-seed.js` di `D:/data hermes/bug-bounty/countly/` — insert admin member (argon2 via `argon2` dep countly) + app + akun user read-only (untuk BOLA differential). Jalanin: `cd countly && node countly-seed.js`.

## Titik kontrol inti (speed-run buat audit balik)
- `common.returnOutput` → `stringifyEscaped` = **escaping global** (menutup semua sink `v-html`).
- `common.isForbiddenFieldName` = `__proto__/constructor/prototype`.
- `common.findUnsafeMongoOperator` = blok `$where/$function/$accumulator`.
- `ssrf-protection.isUrlSafe` + `safeLookup` + `followRedirect:false`.
- Upload: `sniffImageType` (magic bytes) + jimp re-encode + `logoStorageName` namespacing.

## Turn-off jelas (yang nggak usah dikejar)
- `consolidate`, `errorlogs` = OOS tegas.
- heatmap `/o/actions` + token = OOS (deprecated).
- DoS/resource exhaustion = OOS (exclusion #6).