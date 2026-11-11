# ISP DNS sinkhole — the tool installs fine but every call dies with "Connect Timeout"

**Class:** a CLI installs, prints its version, answers `--help` — and then fails on *every* call
that touches its backend. The cause is not the tool, not the target, and not a geo-block: the
**local resolver** is returning a sinkhole address for the host.

**Measured case (2026-10-31):** `@binance/agentic-wallet` (`baw`) v1.12.0 installed cleanly via
npm, `baw --version` → `1.12.0`, `baw --help` listed every subcommand. Every real call died:

```
{"success":false,"error":{"code":50001002,"name":"REQUEST_TIMEOUT",
 "message":"Connect Timeout Error (attempted address: www.binance.com:443, timeout: 10000ms)"}}
```

---

## The ladder — four probes, each kills one hypothesis

Run them in order. **Do not skip to "buy a residential proxy"** — that is the answer to a
different question, and reaching for it here wastes a whole session.

| # | Probe | Command | What a hit means |
|---|---|---|---|
| 1 | What does the **local** resolver say? | `nslookup www.binance.com` | a CNAME to something that is not the vendor's CDN = **sinkhole**. Here: `block.myrepublic.co.id` → `158.140.186.3` |
| 2 | What does the **internet** say? | `curl -s "https://dns.google/resolve?name=www.binance.com&type=A"` | the real answer. Here: CNAME `dobbmei4jnjlh.cloudfront.net` → 8 CloudFront IPs. Cross-check against `cloudflare-dns.com` |
| 3 | Is the real IP reachable at all? | `curl -s -o /dev/null -w "%{http_code} %{time_total}\n" --max-time 15 --resolve www.binance.com:443:<realIP> https://www.binance.com/` | `202` in 0.26 s = the host is fine, **only resolution is broken** |
| 4 | Can you write the fix to disk? | `cp /c/Windows/System32/drivers/etc/hosts ~/hosts.bak && printf '\n1.2.3.4 www.binance.com\n' >> /c/Windows/System32/drivers/etc/hosts` | `Permission denied` + `net session` → *not admin* ⇒ use the shim below, not the hosts file |

**Rule:** a version flag proves the *binary* runs. It proves nothing about reaching the backend.
Probe with a call that actually leaves the machine before declaring a tool working — the same
doctrine as "installed ≠ working", one layer up. On this host `baw --version` answered correctly
while every network call was dead.

**Never pin an IP you did not just resolve through DoH.** Two independent DoH providers agreeing
is the bar; a memorised or guessed edge IP is not. CDN IPs rotate, so re-resolve rather than
treating a pinned list as permanent.

---

## The fix — `dns.lookup` shim via `NODE_OPTIONS` (no admin, no hosts file)

The hosts file is read-only without elevation, and a UAC prompt is not available to an
autonomous run. Node honours a preload module, so patch resolution in-process instead:

```javascript
// ~/.baw/baw-dns-fix.js  — pin the sinkholed host to its real CDN IPs
const dns = require('node:dns');

// host -> pool of real IPs. Refresh with DoH when they rotate:
//   curl -s "https://dns.google/resolve?name=<host>&type=A"
const PINNED = {
  'www.binance.com': ['13.33.88.105','13.33.88.24','13.33.88.123','13.33.88.84',
                      '18.244.51.107','18.244.51.95','18.244.51.24','18.244.51.63'],
  'app.binance.com': ['13.230.56.252','52.193.67.40','35.77.180.16'],
  'web3.binance.com': ['13.35.1.20'],
  'binance.com': ['13.33.88.105','13.33.88.24','13.33.88.123','13.33.88.84'],
};

// Pin ONE ip per host (see the round-robin trap below) — never a per-request counter.
const PIN_INDEX = 0;
function pick(host) {
  const pool = PINNED[host];
  if (!pool) return null;
  return pool[Math.min(PIN_INDEX, pool.length - 1)];
}
function isPinned(h) {
  return typeof h === 'string'
    && Object.prototype.hasOwnProperty.call(PINNED, h.toLowerCase().replace(/\.$/, ''));
}

const origLookup = dns.lookup;
dns.lookup = function (hostname, options, callback) {
  if (isPinned(hostname)) {
    const host = hostname.toLowerCase().replace(/\.$/, '');
    const pool = PINNED[host];
    if (typeof options === 'function') { callback = options;
      return process.nextTick(() => callback(null, pick(host), 4)); }
    if (options && options.all)
      return process.nextTick(() => callback(null, pool.map(a => ({address:a,family:4}))));
    return process.nextTick(() => callback(null, pick(host), 4));
  }
  return origLookup.apply(dns, arguments);
};

// promise form (undici / Node >=18 fetch)
if (dns.promises && dns.promises.lookup) {
  const origP = dns.promises.lookup.bind(dns.promises);
  dns.promises.lookup = async function (hostname, options) {
    if (isPinned(hostname)) {
      const host = hostname.toLowerCase().replace(/\.$/, '');
      if (options && options.all) return PINNED[host].map(a => ({address:a,family:4}));
      return { address: pick(host), family: 4 };
    }
    return origP(hostname, options);
  };
}

// code that bypasses lookup entirely
for (const fn of ['resolve4','resolve6','resolveCname','resolve']) {
  if (typeof dns[fn] === 'function') {
    const orig = dns[fn].bind(dns);
    dns[fn] = (hostname, ...rest) => {
      if (isPinned(hostname)) {
        const host = hostname.toLowerCase().replace(/\.$/, '');
        if (fn === 'resolveCname') return Promise.resolve(['cloudfront.net']);
        if (fn === 'resolve4')    return Promise.resolve(PINNED[host]);
        if (fn === 'resolve6')    return Promise.resolve([]);
        return Promise.resolve([PINNED[host][0]]);
      }
      return orig(hostname, ...rest);
    };
  }
}
```

Patch **all four surfaces**, because different HTTP stacks reach resolution differently:
callback `lookup`, promise `lookup`, and `resolve4`/`resolveCname` for code that bypasses
`lookup`.

### ⛔ Pin ONE IP per host — round-robin is a trap for any tool with server-side session state

The first version of this shim round-robined the whole edge pool
(`REAL_IPS[rr++ % REAL_IPS.length]`). That is wrong for a CLI that does a **multi-step
handshake**, and it cost 8 failed login attempts before the cause was found (2026-10-31):

```
baw auth signin  -> QR created, qrCodeId returned      (landed on edge node A)
baw auth verify  -> AUTH_REJECTED "QR code does not exist or expired"   (landed on node B)
```

The QR/session state is bound to the backend node behind the edge IP. Round-robinning
means `signin` and `verify` land on **different nodes**, so the second call cannot see the
first call's state — and the error text ("does not exist or expired") reads exactly like a
genuine expiry, sending you down a time-based investigation that cannot succeed. The
rejection latency was also inconsistent (58 s – 519 s), which is the tell that it is not a
5-minute TTL.

```javascript
// per-host single-IP pin — use this, NOT a round-robin counter
const PIN_INDEX = 0;
function pick(host) {
  const pool = PINNED[host];
  if (!pool) return null;
  return pool[Math.min(PIN_INDEX, pool.length - 1)];
}
```

**Rule:** round-robin is fine for a stateless request (a fetch, a scanner probe). For
**anything with a session, handshake, or multi-call flow** (auth, QR pairing, OAuth device
flow, cart, upload-then-confirm), pin one IP per host for the whole flow. If throughput
matters, pin per *process*, never per *request*.

### ⛔ Cloudflare WARP can be the thing that breaks it — test it OFF before blaming the target

Once the shim was single-IP pinned, one more variable had to be removed. With **WARP
connected**, `baw auth verify` returned a *different* error — `50001001 NETWORK_ERROR`
`"Connection reset by server"` — and the same shim with **WARP disconnected** returned
`SUCCESS` on the first try.

So the two fixes interact, and the failure modes are distinguishable by their error text:

| state | error | meaning |
|---|---|---|
| shim round-robin | `AUTH_REJECTED` "QR does not exist or expired" | **your own shim** split the session across nodes |
| WARP connected, shim pinned | `NETWORK_ERROR` "Connection reset by server" | **WARP** is resetting the flow mid-handshake |
| WARP off, shim pinned | — | works |

`NETWORK_ERROR` / "Connection reset by server" is a *transport* failure and is **not** the
same finding as `AUTH_REJECTED` / "does not exist or expired" (a *state* failure). Do not
collapse them into "the target rejects us from this region" — that conclusion is what
produced a wrong geo-block diagnosis here before WARP was switched off.

WARP also does not change your country: `warp-cli --accept-tos connect` from Indonesia
still egresses as `country: "ID"` (`curl -s https://api.country.is/`). Turning it on is not
a geo-block bypass, so if the real problem is geo, WARP will not fix it and you will have
added a variable for nothing. Verify egress *and* re-run the flow with it off.

**Order of operations when a multi-step CLI flow fails:** (1) confirm the resolver is not
sinkholed, (2) pin ONE IP, (3) make sure no VPN/WARP is in the path, (4) only then consider
the target's own region policy. Each step removes one hypothesis; skipping to (4) wastes the
session.

Invoke it two ways, and **ship both**, because bash and `cmd` resolve different files:

```bash
# bash / git-bash caller  ->  /usr/local/bin/baw   (chmod +x)
export NODE_OPTIONS="--require $HOME/.baw/baw-dns-fix.js ${NODE_OPTIONS}"
exec "/usr/local/bin/baw-original" "$@"
```

```bat
:: cmd / PowerShell caller  ->  %APPDATA%\npm\baw.cmd
@echo off
setlocal EnableExtensions
set "NODE_OPTIONS=--require $HOME/.baw/baw-dns-fix.js %NODE_OPTIONS%"
node "/usr/local/bin\node_modules\@binance\agentic-wallet\dist\index.js" %*
```

Note the `.cmd` calls `node <pkg>/dist/index.js` **directly**. Do not have it re-invoke
`baw.cmd` — see the trap below.

---

## ⛔ Trap — a wrapper that calls itself recurses until Windows gives up

First attempt had `%APPDATA%\npm\baw.cmd` set `NODE_OPTIONS` and then exec
`"...\npm\baw.cmd" %*` — the same file. Every call printed
`Maximum setlocal recursion level reached.` and nothing ran. The original npm launcher must be
renamed (`baw-original.cmd` / `baw-original`) **before** the wrapper takes its name, and the
wrapper must target the real entrypoint (`node <package>/dist/index.js`), never its own path.

Generalises: any shim you install **over** an existing launcher needs the original moved aside
first, and must not resolve back to itself through PATH. Same family as the `.bat`/`.cmd`
shim rules in RULE 1b — a shim that resolves is not a shim that runs.

---

## Third-party skill packs — the installer's symlink is not Hermes's skills dir

`npx skills add <owner>/<repo> --skill <name>` cloned to `~/.agents/skills/<name>` and created a
symlink under `~/.claude/skills/`. Hermes reads `~/.chiper/skills/bounty-pack/skills/` and saw
**nothing** — `skills_list` did not contain the new skill, and a filesystem `find` for the name
under the hermes tree returned only unrelated icon packages.

Fix — a junction (works without admin, and survives the installer's own layout):

```bash
cd ~/.chiper/skills/bounty-pack/skills && \
  cmd /c "mklink /J binance-agentic-wallet $HOME/.agents/skills/binance-agentic-wallet"
```

Verify with `skill_view(name='<skill>')` — a directory that exists is not a skill that loads.
Check the skill's own declared requirements too: this one declares `requires.bins: [baw]` plus an
npm install step, so the CLI had to be installed separately (`npm install -g
@binance/agentic-wallet`) before the skill was usable. Run the skill's own gates
(`baw cli-check --required-version <v>`, `baw skill-check --skill-name <n> --current-version <v>`)
as the final proof — they exercise the network path, which `--version` does not.

---

## Reporting

State the measured chain, not the conclusion: local resolver → sinkhole IP; DoH → real IPs;
`--resolve` → reachable in 0.26 s; hosts file → permission denied; shim → first successful call.
Anything less and the next session cannot tell a sinkhole from a geo-block from a dead service.

**And when a multi-step flow still fails after the shim works, do not stop at the first
plausible story.** The resolution here took three distinct causes stacked on top of each other,
and each one *looked* like the previous one:

1. ISP sinkhole → fixed by the shim (single-call commands started working).
2. Round-robin shim → broke the two-step auth flow, masquerading as QR expiry.
3. WARP in the path → reset the handshake, masquerading as a region block.

The end state was `SUCCESS` with **no** proxy, **no** VPN, and a single pinned IP. The wrong
conclusion reached along the way — "Binance geo-blocks Indonesian IPs" — was supported by two
real failures and was still false. Report the *sequence of removed variables*, not the final
guess, so the next session inherits the diagnosis and not the superstition.
