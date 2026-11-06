# Owned-infra proof for resource/quota bugs (worked recipe)

Companion to `probe-validation` §2g. Built 2026-10-28 proving a `cpu: 0 → unlimited CPU`
validator bypass in RunOnFlux/flux v8.21.1, entirely on a local Windows + Docker Desktop box.
Reusable for any "client supplies the limit, value 0 means no limit" class.

## When to use

- A vulnerability exists in software that other people run (decentralised fleet, self-hosted
  product, SaaS you cannot touch). The vulnerable *population* is third parties; the *software*
  is the target.
- The proof is a resource/limit/quota decision (`cpus`, `memory`, `replicas`, `tier`, `expires`).
- You need something a vendor can verify without trusting a stranger's host.

## Phase 1 — source, pinned

```bash
git clone --depth 1 --single-branch --branch v8.21.1 https://github.com/RunOnFlux/flux.git v8.21.1
git -C v8.21.1 log -1 --format=%H     # record the commit: 9bb1419
```

Annotated tags sometimes resolve to a tag object, not a commit — `git log -1` gives the real
SHA to quote in the report.

Map the call-sites before writing any harness; grep is the whole map:

```bash
grep -rn "checkComposeHWParameters\|checkHWParameters" --include=*.js .
```

## Phase 2 — module harness: run the REAL validator

Do not reimplement validation. Monkeypatch `Module._load` once, then `require()` upstream.

Key corrections learned the hard way:

1. A hand-written `config` stub is not enough — an unrelated module deep in the graph read
   `config.database.daemon.collections.scannedHeight.collectionName` and crashed at import
   time. **Load the real `ZelBack/config/default.js`.**
2. `config/default.js` requires `../../config/userconfig` → the file must exist:
   `cp sampleUserConfig.js config/userconfig.js`.
3. For bare packages that are not installed (`axios`, `bson`, …), do not `throw` — return a
   permissive Proxy stub, or the whole graph refuses to load.

```js
const Module = require('module');
const RS = String.fromCharCode(92);          // backslash, avoids escaping hell
const ROOT = 'D:/data/flux-src/v8.21.1';
const realConfig = require(ROOT + '/ZelBack/config/default.js');

const noop = () => {};
const stubOf = (n) => new Proxy(function () {}, {
  get: (t, p) => (p === 'then' ? undefined : stubOf(n + '.' + String(p))),
  apply: () => Promise.resolve({}),
});
const STUB = ['dbHelper','dockerService','geolocationService','benchmarkService',
              'fluxNetworkHelper','generalService','ipLocationStore','geolocationRule',
              'cacheManager','chainUtilities','nodePinning','fluxCommunication'];

const orig = Module._load;
Module._load = function (req, parent, isMain) {
  if (req === 'config') return realConfig;
  const norm = String(req).split(RS).join('/');
  if (norm.endsWith('/lib/log')) return { info: noop, warn: noop, error: noop, debug: noop };
  const base = norm.split('/').pop();
  if (STUB.indexOf(base) !== -1) return stubOf(base);
  try {
    return orig.apply(this, arguments);
  } catch (e) {
    const isBare = !norm.startsWith('.') && !norm.startsWith('/') && norm.indexOf(':') === -1;
    if (isBare && (e.code === 'MODULE_NOT_FOUND' || e.code === 'ERR_MODULE_NOT_FOUND')) {
      return stubOf(base);                   // package not installed -> stub, keep going
    }
    throw e;
  }
};

const hw = require(ROOT + '/ZelBack/src/services/appRequirements/hwRequirements.js');
const appUtils = require(ROOT + '/ZelBack/src/services/utils/appUtilities.js');
```

Feed it the **exact spec the exploit sends** — copy it from the exploit, do not retype from
memory — and print four things:

```
PART 1  checkComposeHWParameters(spec)            -> ACCEPTED  (the branch v8 actually takes)
PART 2  checkHWParameters(component)              -> REJECTED "CPU badly assigned"  (v<=3 only)
PART 3  specificationFormatter(spec).compose[0]   -> cpu=0 ram=100 hdd=1   (0 survives formatting)
PART 4  HostConfig                                 -> {"NanoCPUs":0,"Memory":104857600,...}
```

Parts 1+2 together are the paired test: same spec, two code paths, opposite verdicts.
Part 3 kills "some later normaliser fixes it". Part 4 is the exact object handed to Docker —
copy its numbers straight into the runtime phase so the two phases provably connect.

Quote call-sites with line numbers in the report:

```
appValidator.js:1389   if (version <= 3) checkHWParameters(...) else checkComposeHWParameters(...)
appValidator.js:144    typeof cpu !== 'number'   -> 0 is a number, passes
hwRequirements.js:376  checkComposeHWParameters  -> only "too much", never "too little"
hwRequirements.js:328  checkHWParameters         -> has cpu < 0.1, unreachable for v8
appUtilities.js:716    appComponentCorrect.cpu = ensureNumber(0)   -> stays 0
dockerService.js:1202  NanoCPUs: Math.round(appSpecifications.cpu * 1e9)  -> 0
```

## Phase 3 — runtime differential (two containers, one variable)

```bash
# vulnerable: HostConfig from PART 4
docker run -d --name f5live --network f5net --cpus 0 \
  --memory 104857600 --memory-swap 2202009600 alpine:latest \
  sh -c 'for i in 1 2 3 4; do yes > /dev/null & done; wait'

# control: same image, same memory, only the cap differs
docker run -d --name f5cap --network f5net --cpus 0.1 \
  --memory 104857600 --memory-swap 2202009600 alpine:latest \
  sh -c 'for i in 1 2 3 4; do yes > /dev/null & done; wait'
```

Measure with cgroup counters, never `docker stats` CPU%:

```bash
export MSYS_NO_PATHCONV=1                 # git-bash rewrites /sys/... without this
docker exec f5live cat /sys/fs/cgroup/cpu.max      # max 100000      => no quota
docker exec f5cap  cat /sys/fs/cgroup/cpu.max      # 10000 100000    => 10% of one core
docker exec f5live cat /sys/fs/cgroup/cpu.stat     # nr_periods 0, nr_throttled 0
docker exec f5cap  cat /sys/fs/cgroup/cpu.stat     # nr_periods N, nr_throttled N
```

Derive cores from `usage_usec` delta over wall time (`/proc/uptime`), one shell block:

```sh
u1=$(grep usage_usec /sys/fs/cgroup/cpu.stat | cut -d' ' -f2); t1=$(cut -d' ' -f1 /proc/uptime)
for i in 1 2 3 4 5 6 7 8; do yes > /dev/null & done
sleep 4; pkill yes
u2=$(grep usage_usec /sys/fs/cgroup/cpu.stat | cut -d' ' -f2); t2=$(cut -d' ' -f1 /proc/uptime)
awk -v a=$u1 -v b=$u2 -v x=$t1 -v y=$t2 'BEGIN{du=(b-a)/1000000;dt=y-x;printf "cores=%.3f\n",du/dt}'
```

The control must land on its declared value (0.099 for a 0.1-core cap). If the control does not
hit its cap, your measurement is broken and the "unlimited" reading is meaningless.

## Phase 4 — live public endpoint reading kernel state per request

```bash
# CGI proof page: reads /sys/fs/cgroup on every hit -> cannot be hand-written
mkdir -p www/cgi-bin      # script prints Content-Type: text/plain then the cgroup values
docker run -d --name f5live  --network f5net --cpus 0   -v "$PWD/www:/www:ro" alpine:latest \
  sh -c 'apk add --no-cache busybox-extras >/dev/null 2>&1; httpd -f -p 8080 -h /www'
# nginx sidecar fans out: /unlimited -> f5live:8080 , /capped -> f5cap:8080
docker run -d --name f5proxy --network f5net -p 49140:80 \
  -v "$PWD/proxy/default.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$PWD/www:/www:ro" nginx:alpine
# public URL, no account
cloudflared tunnel --url http://localhost:49140 --no-autoupdate --protocol http2
```

Put both panels side by side on one page and label them VULNERABLE / CONTROL. Verify the public
URL three times and quote the code:

```bash
for i in 1 2 3; do curl -s -o /dev/null -w "%{http_code}\n" "$URL/"; sleep 4; done
```

## Pitfalls (all hit for real)

- **`pkill -f "while :"` inside the container kills PID 1**, because PID 1 *is* that command
  line. Container dies, you lose the workload, and it looks like the exploit does not hold.
  Match the leaf binary (`pkill yes`) or use `docker exec -d` to add workers instead.
- **`docker stats` CPU% on a starved VM is an instrument artifact** — 32% for an unlimited
  container on a 2-core Docker Desktop VM. Never present it as evidence of a cap or its absence.
- **git-bash rewrites `/sys/fs/cgroup/...`** into `C:/Users/.../git/sys/...`. Prefix
  `MSYS_NO_PATHCONV=1` on every `docker exec` that names an absolute Linux path.
- **The terminal tool refuses foreground commands containing `&`** ("uses '&' backgrounding").
  Use `docker exec -d sh -c '...'` or a script file instead of inlining `cmd &`.
- **`busybox` httpd is not in `alpine` by default** → `apk add --no-cache busybox-extras`, and
  CGI only runs from a `cgi-bin` directory under `-h <root>`.
- **Cloudflare quick tunnel may report QUIC FAIL and still work over TCP/HTTP2.** Re-run with
  `--protocol http2` before concluding egress is blocked.
- **nginx `proxy_pass` needs every container on one user-defined network**, and the static root
  must be mounted into the *proxy*, not only into the backends, when the proxy serves `/`.
- **Measure after a settle period** (≥20 s) so container start-up does not pollute the counters.

## What goes in the report

1. Commit SHA + the five `file:line` call-sites.
2. The harness output (four PARTs) — labelled as the *real* modules executing.
3. The two-column table (`cpu:0` vs `cpu:0.1`) with `cpu.max`, cores, `nr_periods`,
   `nr_throttled`.
4. The live URL, with the note that values are read from `/sys/fs/cgroup` at request time.
5. One sentence stating that no third-party host was contacted, registered against, or installed
   to — and why that matters (vendor verifiability).
