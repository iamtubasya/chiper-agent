---
name: hunt-php2shell
version: 1.0.0
author: operator (QWEN)
license: internal
description: Use when target runs PHP 5.4-8.5 for pre-auth RCE.
metadata:
  hermes:
    tags: [bug-bounty, php, rce, cve, memory-disclosure, 0C, verification]
---

# hunt-php2shell — PHP runtime pre-auth RCE + memory disclosure

## When to Use

Load this skill when **any** of these is true:

- Recon/fingerprint reports the target runs **PHP** at any version from 5.4 to 8.5
- The target is WordPress, Drupal, Joomla, Magento, or Laravel and the PHP
  version is unknown or unverified (assume vulnerable until proven patched)
- `X-Powered-By: PHP` or a `PHPSESSID` cookie is observed
- A CVE-driven hunt is requested and the target has a web frontend
- Phase 0C needs a verification step that generic scanners cannot cover

Do **not** load this for non-PHP stacks (Node, ASP.NET, Java, Ruby, Go) — the
bug is PHP-runtime-specific and the exploit bodies are PHP-specific.

**CVE-2026-109618** (OOM corruption → RCE) and **CVE-2026-109619** (stale global
state → UAF → RCE *or* memory disclosure). CVSS v4.0 **9.2**. Disclosed
2026-10-20, patched 2026-10-21.

## Why generic scanners miss this

The bug is in the **PHP runtime, beneath the application**. A fully patched
WordPress/Drupal/Joomla/Laravel on a vulnerable PHP build is still exposed.
nuclei has no template for a heap UAF reached through multipart parsing, and
the attack runs *before any application code executes* on Apache mod_php.
Only a purpose-built verifier can test for it.

## Affected / fixed

| | |
|---|---|
| Affected | PHP **5.4.0 → 8.5.x** (every branch) |
| Fixed | 8.2.35 · 8.3.36 · 8.4.27 · 8.5.12 |
| EOL (no official patch) | 5.x, 7.x, 8.0, 8.1 — source-only backports exist for 7.4/8.0/8.1 |
| Config stopgap | `session.upload_progress.enabled = Off` (neutralises the UAF vector, keeps uploads working) |

## Root cause

`php_session_rfc1867_callback` (`ext/session/session.c`) stores raw `zval *`
bucket pointers (`post_bytes_processed`, `current_file_bytes_processed`)
directly in live `HashTable` structures.

1. **Trigger** — a multipart POST activates progress tracking (default config).
2. **Free** — a progress update cycle re-reads session data; `zend_hash_update()`
   destroys the previous tree via `zval_ptr_dtor`, freeing the block.
3. **Reclaim** — the freed bucket memory is reclaimed and the dangling pointer
   is redirected to crafted `zend_fcall_info` / `zend_internal_function`.
4. **Execute** — `zend_call_function()` runs → arbitrary command execution.

Separately, an OOM `longjmp()` bailout during multipart parsing leaves `PS(id)`
dangling; a later request on the same worker consumes it as a live
`zend_string` and URL-encodes the reclaimed heap into `Set-Cookie: PHPSESSID`.

## Two impacts — pick the one that pays

### 1. Memory disclosure (quieter, often higher payout)

Heartbleed-style read primitive at the PHP layer. **No auth, no code
execution.** Leaks live worker memory: TLS private keys, API keys, DB DSNs,
session tokens from other in-flight requests. Leaves almost no trace.

Detection signature (for the operator's blue team): **Snort rule `1:67375`** —
two consecutive URL-encoded null bytes (`%00%00`) in the PHPSESSID cookie
value.

### 2. Pre-auth RCE

Confirmed against Apache mod_php with default input and memory limits. On
mod_php the attack runs during request startup, before application code.

## Pipeline position — phase 0C-C2e

Wired into `audit-pipeline-orchestrator.py` **after C2d (impact-verify), before
C3 (business-logic)**. It is a *verification* step: it consumes the candidate
URLs recon already produced and proves or disproves the primitive.

```
scripts/php2shell-verify.py <target_dir> <target_url> \
    --limit 8 --rounds 40 --sleep 1 --timeout 20
```

Runs automatically on every pipeline run. SKIPs itself when
`php2shell-verification.json` already exists for the target (same
fresh-run discipline as C2–C6b).

## Artifacts it writes

| File | Purpose |
|---|---|
| `php2shell-verification.json` | ledger — always written, even all-negative |
| `php2shell-confirmed.json` | only on CONFIRMED |
| `php2shell-findings.md` | `## <title>` sections for `aggregate-findings.py` |
| `tool-evidence/php2shell/<host>_<port>.txt` | raw heap + response samples |
| `tools-usage.json` | appended via `usage_ledger` (phase `0C-C2e`) |

## Verdict vocabulary

| Verdict | Meaning |
|---|---|
| `CONFIRMED` | heap recovered **and** a high-value secret carved (TLS key / cert / token / DSN) |
| `PARTIAL_HEAP` | heap recovered but no recognizable secret format |
| `PARTIAL_OOM` | memory-limit fatal reproduced, no dangling-pointer read |
| `NEGATIVE` (rounds fired) | PHP runtime confirmed, primitive not observed |
| `NEGATIVE` (short-circuited) | non-PHP stack detected, rounds **not** fired |
| `ERROR` | transport/parse failure — recorded, never silently dropped |

### Stack short-circuit (added 2026-10-22, measured on quarterwise.co.uk)

`detect_stack()` fingerprints the runtime before any round is fired. A
**positive non-PHP signature** (Next.js, Vercel, ASP.NET, Django, Rails,
Tomcat, Node/Express) short-circuits to `NEGATIVE` with `rounds=0` and the
detected stack named in the ledger and in `php2shell-findings.md`.

Why this matters: firing 40 rounds of 25MB multipart bodies at a Next.js app
wastes time **and** produces a negative that reads as "we tested and it's
safe" when the truth is "the technique cannot apply". The markdown now has a
dedicated `## php2shell not applicable on <url> (non-PHP stack)` section so
the two cases can never be confused.

**Conservative by design:**
- A **positive PHP signal always wins** — `X-Powered-By: PHP`, a `PHPSESSID`
  cookie, or `PHPSESSID` in the body means the target is treated as PHP even
  if a non-PHP marker is also present (a PHP app behind Cloudflare is still PHP).
- **Cloudflare alone never short-circuits.** It fronts PHP too. Only used as
  corroboration.
- **An unknown stack does NOT short-circuit.** Stripped headers are not proof
  of a non-PHP runtime — those targets still get their rounds, so the negative
  is earned rather than assumed.

Unit-tested 12/12 (`_test_detect_stack.py`), including the two trap cases:
"headers stripped" and "Cloudflare only" must both fall through to
`unknown` / `short_circuit=False`.

## OOM trigger strategies (all confirmed in public advisory)

| Strategy | Mechanism |
|---|---|
| `NO_LEN` | omit Content-Length → bypasses `post_max_size`, unlimited body |
| `HDR_AMP` | unlimited part headers, ~4× PHP memory per wire byte |
| `NESTED` | empty file controls + nested array names (don't count toward `max_file_uploads`) |
| `CHUNKED` | chunked transfer slips past the `post_max_size` check |

The tool cycles all four. `--memory-limit 32` is enough to reproduce the fatal
on a default mod_php config.

## Detection / hunting guidance

Behavioural indicators (post-exploitation, for the client's blue team):

- PHP worker (`php-fpm`, `php-cgi`, `httpd`, `apache2`) spawning `/bin/sh`,
  `/bin/bash`, `cmd.exe`, `powershell.exe`, `python`, `perl`
- PHP worker spawning `curl`, `wget`, `nc`, `certutil.exe`
- Reverse-shell patterns: `/dev/tcp/`, `fsockopen`, `mkfifo`
- Immediate recon: `whoami`, `id`, `uname -a`, `ipconfig`
- Unexpectedly large or malformed PHPSESSID response cookies
- Large multipart submissions followed by memory-limit errors or repeated 500s
- Unexplained PHP worker crashes/restarts

Exposure figure for scoping conversations: ~884,000 internet-facing hosts
advertised PHP 8.1 or older in Shodan banners on 2026-10-20 (~59% of hosts
reporting a version), plus ~740,000 reporting PHP without a version.

## Reporting notes

- **Rotate-first framing.** Memory disclosure leaves little trace, so tell the
  operator to rotate every credential a PHP worker held *before* confirmed
  compromise, not after.
- **Patch is the only complete fix.** PHP states no configuration change fully
  closes it; every interim mitigation closes one path and leaves others open.
- **EOL branches stay exposed.** If the target runs 8.1 or older, the finding
  is "unpatchable without a vendor backport" — that raises severity, not lowers it.
- **By-design check.** `session.upload_progress` being enabled is the *default*,
  not a misconfiguration. Do not report "upload_progress enabled" as a finding
  on its own — report the demonstrated leak.

## Local lab (for validating your own PoC before touching a target)

Build a vulnerable PHP from source (distro repos only ship the patched version):

```bash
# WSL Ubuntu — toolchain
apt-get install -y build-essential autoconf bison re2c pkg-config \
    libxml2-dev libsqlite3-dev libssl-dev zlib1g-dev libcurl4-openssl-dev libonig-dev

# vulnerable source: 8.4.26 is the LAST pre-patch release (fix landed in 8.4.27)
curl -sSL -o php-8.4.26.tar.gz https://www.php.net/distributions/php-8.4.26.tar.gz
tar xzf php-8.4.26.tar.gz && cd php-8.4.26

# confirm the vulnerable code is in the tarball BEFORE building
grep -n 'post_bytes_processed' ext/session/session.c   # raw zval storage = the bug

./buildconf --force
./configure --prefix=/opt/php8426 --with-openssl --with-zlib --enable-mbstring \
    --enable-fpm --with-fpm-user=www-data --with-fpm-group=www-data
make -j$(nproc) && make install
/opt/php8426/bin/php --version   # 8.4.26 = pre-patch = vulnerable
```

### Measured lab results (2026-10-22, real PHP 8.4.26 build)

Full stack tested: **nginx 1.28 → php-fpm (8 workers, dynamic pool) → PHP 8.4.26**
with `memory_limit=32M`, `session.upload_progress.enabled=1`.

| Test | Result |
|---|---|
| OOM fatal via chunked multipart (25.6MB wire, `NO_LEN` strategy) | **reproduced 17/17** — `child NNNN exited with code 70` in the fpm log every ~10s |
| `session.upload_progress.enabled` default | **On** (confirmed via `php -i` and live probe) |
| Fingerprint (PHP + upload_progress detection) | **works** — `X-Powered-By: PHP/8.4.26` + PHPSESSID cookie |
| Leaked heap in PHPSESSID | **not observed in this lab** — see "What did NOT reproduce" below |
| PHP 8.4 `max_multipart_body_parts` / `max_input_vars` | **new hardening**, caps NESTED/HDR_AMP at ~1000 parts |
| nginx `client_max_body_size` | default 1M → **413**, must raise to 128m |
| nginx `client_body_buffer_size` | default 16k → "invalid chunked body", must raise |

**Four hard lessons from the lab — all now fixed in the shipped tool:**

1. **Do NOT send a PHPSESSID cookie on the read request.** If a cookie is
   present PHP reuses that session and emits **no Set-Cookie at all**, so the
   leaked heap never surfaces. A cookie-less request forces PHP to mint a new
   session id — that is the path that URL-encodes the reclaimed heap into the
   response header. (First version of the harvester sent a cookie and got
   `cookies=0` on every single round.)

2. **`NO_LEN` must actually chunk-frame its body.** The first version declared
   `Transfer-Encoding: chunked` but sent a raw multipart body. nginx rejected
   it with `client sent invalid chunked body` and the request never reached
   PHP at all — zero OOM hits, and it looked like a negative result. Always
   verify the wire bytes match the declared encoding.

3. **The built-in dev server (`php -S`) is single-process.** CVE-2026-109619
   needs a *persistent worker* for the dangling `PS(id)` pointer to survive
   into the next request. Use **php-fpm with a pool** (or Apache mod_php).
   Testing `php -S` and reporting "negative" would be a false negative.

4. **Raise the proxy limits or you test the proxy, not PHP.** nginx's
   `client_max_body_size` (1M) and `client_body_buffer_size` (16k) both
   silently truncate/reject the payload before php-fpm ever sees it.

### What did NOT reproduce (honest negative)

The OOM primitive is solid (17/17 worker crashes), but the **memory-disclosure
read via PHPSESSID did not surface** in this lab. Every follow-up request got a
clean 32-char hex session id. Plausible causes, in order of likelihood:

- The freed bucket is reclaimed by the allocator *before* the next request
  reaches the upload-progress cleanup path (heap layout / timing dependent)
- `zend_string` length metadata on the dangling pointer does not happen to
  point at attacker-recognizable bytes
- The 8-worker pool spreads requests across processes, so the "same worker"
  requirement is met only by chance

**This is why the verifier distinguishes `PARTIAL_OOM` from `CONFIRMED`.** An
OOM-only result is a real, reportable primitive (it proves the runtime is
unpatched and the attack surface is reachable), but it is NOT proof of secret
disclosure. Do not report a leak you did not observe.

### php-fpm lab config (multi-worker — what the CVE actually needs)

```ini
; /opt/phpvuln/php8426/etc/php-fpm.d/lab.conf
[lab]
user = www-data
group = www-data
listen = 127.0.0.1:9000
pm = dynamic
pm.max_children = 8
pm.start_servers = 4
pm.min_spare_servers = 2
pm.max_spare_servers = 6
php_admin_value[memory_limit] = 32M
php_admin_value[post_max_size] = 64M
php_admin_value[upload_max_filesize] = 64M
php_admin_value[max_input_vars] = 5000
php_admin_value[max_multipart_body_parts] = 5000
php_admin_value[session.upload_progress.enabled] = 1
```

```bash
/opt/phpvuln/php8426/sbin/php-fpm --fpm-config /opt/phpvuln/php8426/etc/php-fpm.conf
```

**WSL networking note:** the PHP server inside WSL2 is not reachable from
Windows `curl` on `127.0.0.1` (separate network namespace). Either run the
harvester *inside* WSL, or use the WSL adapter IP (`hostname -I`).

## Related skills

- `audit-runbook` — phase 0A–0F SOP; C2e slots into 0C
- `hunt-rce` — RCE class hunting (the CVE-2026-109618 half)
- `hunt-data-exposure` — secret-leak routing (the CVE-2026-109619 half)
- `exploit-depth` — L0→L5 escalation once a signal appears
- `chain-to-impact` — if the hunt only yields Low, chain it
- `security-lab-range-practice` — drill the technique on a local lab first
