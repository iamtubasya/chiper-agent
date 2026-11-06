# Verifying a vendor's own security advisory (instead of quoting it)

When a vendor publishes a `SECURITY.md` / advisory about a compromise in their own repo, the advisory is a **claim**,
and claims about code are testable. Quoting it as fact is a sourcing failure that will be caught the moment someone
asks "did you verify this?".

**Rule: split the advisory into individually testable assertions, test the ones that are testable offline, and state
plainly which one you could not test and why.** Verdict vocabulary:
`VERIFIED` · `NOT VERIFIED` · `INDETERMINATE — <reason>`.

---

## Worked case: Superstate `request-with-api-key` (2026-10-01)

Advisory claimed, in summary:
1. the GitHub repo's `src/example.ts` contained malicious code from 2026-01-16 to 2026-05-28, hidden behind
   whitespace padding in commit `e180dd8`;
2. the published npm package `@superstateinc/api-key-request` versions 0.1.0–0.1.4 is **NOT affected**, because the
   last publish (2025-08-01) predates the malicious commit;
3. the loader "attempted to read credentials from common local file locations and exfiltrate them".

### Test 1 — the date reasoning (cheap, decisive)

```bash
curl -s "https://registry.npmjs.org/@superstateinc/<pkg>" | python -c "
import json,sys; d=json.load(sys.stdin)
print(sorted(d['versions']))
for v,t in d['time'].items():
    if v not in ('created','modified'): print(v, t)"
```
Result: 0.1.0 (2025-07-21) … 0.1.4 (2025-08-01). Compare against `git log -1 --format=%ci <malicious-sha>`
(2026-01-16). Last publish **predates** the malicious commit ⇒ the exclusion argument holds on its face.

### Test 2 — actually open the artifacts, do not trust the date argument alone

```bash
for v in 0.1.0 0.1.1 0.1.2 0.1.3 0.1.4; do
  curl -s -o pkg-$v.tgz "https://registry.npmjs.org/@superstateinc/<pkg>/-/<pkg>-$v.tgz"
  mkdir -p x-$v && tar -xzf pkg-$v.tgz -C x-$v
done
grep -rl "atob(\|eval(\|<malicious-host>\|<c2-host>" x-*/ ; echo "(empty = clean)"
find x-*/ -name ".env" -o -name ".env.*"       # check the shipped dotenv for REAL values
```
Result: 0 of 5 tarballs contained the loader signature or any C2 reference; the one shipped `.env.example` held
empty values only. **Verdict for assertion 2: VERIFIED.**

### Test 3 — read the injected code yourself (static only)

The payload hides behind ~3,000 spaces of padding so the diff reads as one line. Extract and decode **in memory**:

```python
import re, base64
raw = open("example.ts", encoding="utf-8", errors="replace").read()
m = re.search(r"atob\('([A-Za-z0-9+/=]+)'\)", raw)
js = base64.b64decode(m.group(1)).decode("utf-8", errors="replace")
print(js)          # print it; do NOT write it to disk and NEVER execute it
```
What it actually was: a **three-chain dead-drop downloader**, not a self-contained credential stealer —
TRON `api.trongrid.io/v1/accounts/<addr>/transactions` (fallback Aptos `fullnode.mainnet.aptoslabs.com`) →
`raw_data.data` hex→utf8 → **string reversed** → used as a tx hash via `eth_getTransactionByHash` on
`bsc-dataseed.binance.org` (fallback `bsc-rpc.publicnode.com`) → `result.input` hex→utf8 → `.split("?.?")[1]` →
XOR with a static key → `eval()`; stage 2 re-spawned via
`child_process.spawn("node", ["-e", ...], {detached:true, stdio:"ignore", windowsHide:true})`.

⇒ **Assertion 3 is INDETERMINATE.** The credential theft lives in the stage-2 blob that is stored on BSC, so it
cannot be retrieved or disproved offline. Do **not** contact the chain or the attacker infrastructure to complete
the picture. Report it exactly that way: "consistent with the design, not statically provable from the loader".

### AV caveat — the reason to decode in memory

Writing the decoded payload to disk gets it quarantined by Defender on Windows. The symptom is confusing:
`open()` on a file that `os.path.getsize()` happily reports (1973 bytes) then fails with
`OSError: [Errno 22] Invalid argument`, and a later `os.remove()` fails with `WinError 2`. Decode, print, move on —
and never keep a decoded payload as an artifact.

---

## Full-history secret sweep (do this on any repo you are asked to trust)

```bash
git clone <repo>                       # FULL history, not --depth 1
trufflehog git file://$PWD --no-update --json > trufflehog.json 2>&1   # if it needs the network: --no-verification
git log --all -p > full-history-patch.txt                              # big on purpose
grep -nE "AKIA|ASIA|api[_-]?key|secret|password=|PRIVATE KEY|sk_live|sk_test|ghp_|xox[baprs]-|eyJ|Bearer |0x[0-9a-fA-F]{64}|mnemonic" full-history-patch.txt
```

Triage each hit into **placeholder** (`your-api-key-here`, empty value) vs **real**. For anything that looks real:
record the credential **type**, the file+commit, and its **length + sha256** — never the raw value in the report —
and do **not** test it against any service. Probing a found credential is a policy violation, not diligence.

Note: a zero-result trufflehog run is a weak negative on its own (it may have failed to verify/scan). Pair it with
the `git log --all -p` grep above, and diff HEAD-tree hits against history hits so a placeholder in the current tree
does not mask a real value in an older commit.
