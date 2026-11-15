# Porting a working PoC into scanner templates (nuclei / ffuf)

Measured 2026-10-27 on Juice Shop 20.3.0 + DVWA 1.10 local Docker. Every entry below
produced a **false negative or false positive** until fixed. Read this before blaming a
target for "0 findings".

---

## 1. The reach test (run this FIRST when 0 hits)

A scanner that never landed is indistinguishable from a hardened target. Before touching
matchers, prove the request arrives:

```yaml
id: probe-reach
info:
  name: reach
  author: q
  severity: info
  tags: dbg
http:
  - raw:
      - |
        POST /vulnerabilities/exec/ HTTP/1.1
        Host: {{Hostname}}
        Content-Type: application/x-www-form-urlencoded

        ip=127.0.0.1;id&Submit=Submit
    matchers:
      - type: word
        part: body
        words: ["DVWA"]        # a word that exists on ANY page of the app
```

- 0 hits → the request is not arriving (host, cookie, port, TLS, proxy).
- hit → the request arrives; the real matcher is wrong.

**Worked case.** `nuclei -u http://localhost:4280 -t <real template>` → `No results found`.
Same template against `http://127.0.0.1:4280` → immediate hit. `localhost` resolved to
`::1`; DVWA binds IPv4 only. Two hours of matcher debugging avoided by one reach test.

---

## 2. Transport traps, in the order they usually bite

### `%3B` is re-encoded
In a raw template body, writing `ip=127.0.0.1%3Bid` does **not** produce `;` at the target.
Write the literal character:

```
ip=127.0.0.1;id&Submit=Submit
```

Symptom: reach test passes, injection never fires, response looks like the benign request.

### YAML single-quoted regex: `\\d` is not `\d`
Inside a YAML single-quoted string, backslashes are literal. So `'uid=\\d+'` reaches the
engine as a pattern matching a **literal backslash**, never a digit.

Prefer character classes, which need no escaping:

```yaml
regex:
  - 'uid=[0-9]+.gid=[0-9]+'     # '.' because '(...) ' is 12 chars, not 1
```

Better still, for exact strings use `type: word` and skip regex entirely:

```yaml
matchers-condition: and
matchers:
  - type: word
    part: body
    words: ['uid=33(www-data)']
  - type: word
    part: body
    words: ['gid=33(www-data)']
```

The `.`-vs-`[0-9]+` mistake cost a whole round: `uid=\d+\([a-z_]+\)\s+gid=\d+` never
matched because `.` matched exactly one character where `(www-data) ` is twelve.

### Cookie names are case-sensitive
`Cookie: phpsessid=<sid>` silently drops the session; every authenticated template then
reads a login page, which looks like "authz enforced". Use `PHPSESSID`, exactly as issued.

Diagnostic: `-debug` and read the dumped request/response. The response carries
`Set-Cookie: PHPSESSID=<a DIFFERENT sid>`, i.e. the server rejected yours and minted a new
one. That asymmetric `Set-Cookie` is the tell that your cookie was not accepted.

### Undefined `{{var}}` fails silently
A `Cookie: {{sec}}` line with no `-V sec=...` makes the template produce no match, not an
error. Either remove the line (pass the cookie via `-H`) or supply `-V sid=... -V sec=...`.

Note: `-V` values are substituted into the **raw request**, so the same template can be
reused across security levels — that is what makes the paired test below cheap.

### Session expiry between rounds
DVWA sessions expire. If a run that worked 10 minutes ago now returns login pages, re-login
and capture a fresh sid rather than assuming authz was tightened.

---

## 3. `-mc 200` is invalid on any proxying sink

A proxy-style endpoint returns HTTP 200 **even when the upstream 404s**, because the
envelope succeeded. So `-mc 200` matches every word in the list.

Measured, ffuf against an SSRF proxy whose upstream path is fuzzed:

```
-mc 200                     -> secret logs nope-xyz latest/... admin/users   (1 FP)
-mc 200 -fr 'Not Found'     -> secret logs latest/... admin/users            (clean)
-mc 200 -fs 285             -> admin/users secret latest/... logs            (clean)
```

`nope-xyz` is the control: a word that cannot exist. If it matches, the filter is wrong.

Also measured: `-mr 'A|B|C'` **with** `-mmode and` still let `logs` through, so prefer the
body-size filter (`-fs <404 size>`) — read the 404 once, note its exact length, filter it.

---

## 4. Paired falsifiability test (the real proof a probe transfers)

DVWA ships both the vulnerable and the fixed implementation of the same feature, selectable
per session via the `security` cookie. That makes it a free patched oracle.

One template set, one target, only the code path changes (inject via `-V`):

```bash
for lvl in low medium high impossible; do
  nuclei -u http://127.0.0.1:4280 \
    -t tools/dvwa-cmdi.yaml -t tools/dvwa-sqli.yaml \
    -t tools/dvwa-lfi.yaml  -t tools/dvwa-xss.yaml \
    -V sid=$SID -V sec=$lvl -silent -no-color -rl 5 -c 1
done
```

Result that means the probe is real:

```
security=low          4 hits  command-injection, lfi, sqli, reflected-xss
security=medium       0 hits
security=high         0 hits
security=impossible   0 hits   <- the actual fix
```

Result that means the probe is a false positive: any hit at `impossible`.

### Where to find a patched oracle on other targets
- Vulnerable-by-design apps with security levels (DVWA `low`/`impossible`).
- Library version pairs (old release vs release containing the fix).
- Pre-rewrite legacy endpoint vs the rewritten one that added the ACL.
- The project's own fix commit / branch, run locally.
- A `deprecation`/`successor` field in the response naming the hardened replacement.

### Honest limit
When the paired control lives inside a lab **you** authored, it proves internal consistency,
not transfer. Only classes tested against third-party code earn the word "transfer".
Say which is which in the report.

---

## 5. Blind sinks: silence is correct

For SSRF/webhook/email, a content matcher that stays silent is behaving **correctly**. The
only valid proof is OOB:

```
POST /ssrf/blind?url=http://<id>.oast.fun/probe
-> {"queued":true}                       no body to match
-> interactsh logs: dns A + dns AAAA + http GET /probe
   with User-Agent: python-requests/2.32.3   <- server-side, not the researcher's browser
```

Controls that must be run alongside:
1. Same OOB host against an allowlisted endpoint → 403 (filter works).
2. Benign external URL against the vulnerable sink → must still succeed (see §1 of SKILL.md:
   if benign is blocked identically, the block is NAT/egress, not target validation).

---

## 6. Internal-only target = un-fakeable SSRF proof

Design the SSRF target so a hit cannot be fabricated: publish no host port.

```
docker ps
lab-internal   8080/tcp                    <- NO host binding, only the docker network
lab-app        0.0.0.0:8090->8080/tcp
```

If a response from `lab-internal` shows up in `lab-app`'s output, the only path was a
server-side fetch. Docker NAT cannot produce that content. This turns "SSRF suspected" into
a structural proof instead of an argument.

Corollary pitfall: **inside a container, `127.0.0.1:<host-port>` is the container itself**,
not the host. The app must reach a sibling by service name (`http://lab-receiver:8080`).
Two probes failed on exactly this before the service name was used.
