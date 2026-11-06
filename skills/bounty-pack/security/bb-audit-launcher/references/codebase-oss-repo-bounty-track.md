# Codebase / OSS-Repo Bounty Track (white-box, no live host)

Use when the program's in-scope assets are **source repositories** rather than live hosts —
Immunefi "Blockchain/DLT codebase" programs (Hedera, and similar) are the canonical case. There is
no URL to probe and the program almost always **forbids testing deployed mainnet/testnet code**
(local forks only). Consequence: the entire web2/web3 scanner layer is **N/A by program rule**, and
the work is source review + dependency/SAST analysis.

Verified on the Hedera (Immunefi) engagement, 2026-10.

## Phase mapping (vs the standard 0A–0F)

| Phase | What it becomes here |
|---|---|
| 0A SCOPE | Record the asset repos (exact `github.com/<org>/<repo>`), reward tiers, and the **prohibited-activities** text verbatim. |
| 0B RECON | Clone every in-scope repo; map module layout; pull recent history. No subdomain/port/URL recon. |
| 0C HUNT | Dependency CVE scan + SAST + cross-repo pattern sweeps + **line-level review** (see below). |
| 0D GATE | **N/A-BLOCKED** — no HTTP surface, program forbids live testing. Say so; never "passed". |
| 0E FINDINGS | `findings.json` with `validated_findings[]` + `observations[]` + `residual_gaps[]`. |
| 0E-REVIEW | Verified **negatives are first-class** — list each file/function you read and why it's sound. |
| 0F REPORT | Immunefi format; PoC may be code-level (grep + line references) when the defect *is* a stub. |

## Step 1 — Clone (Windows pitfalls)

```bash
export MSYS_NO_PATHCONV=1
cd <workspace>/repos
for r in <repos...>; do git clone --depth 1 --single-branch "https://github.com/<org>/$r.git" "$r"; done
```
- `cd <dir>` must SUCCEED before cloning, or clones land in `$HOME`. Check `[ -d "$d/.git" ]`.
- Big Java repos can fail checkout on Windows: `fatal: unable to checkout working tree`. Fix in-place:
  `git config core.longpaths true && git config core.protectNTFS false && git restore --source=HEAD :/`.
  A repo with rc=128 but a usable working tree is fine to review.
- Cross-drive `mv` (C:→D:) is slow under Defender — clone **directly** into the target drive.

## Step 2 — Map + prioritise by freshness

```bash
git -C <repo> log --oneline -60        # native git needs `cd`, not `-C <msyspath>`; or cd first
git fetch --depth 300 origin           # shallow clone -> get history before reading log
```
"NEW == UNREVIEWED": the newest merged features have the lowest maturity. Read their diffs first
(`git show --stat HEAD`). Also read `docs/`, `**/AGENTS.md`, `CLAUDE.md` in-repo for design intent.

## Step 3 — Automated layer (only these actually leave evidence)

| Tool | Command | Notes |
|---|---|---|
| npm audit | `npm audit --json > evidence/x.json` | works from `package-lock.json`, no install |
| Go vuln | `govulncheck ./...` | needs Go toolchain |
| Go SAST | `gosec -fmt=json -out=D:/path/out.json -exclude-dir=examples,tck ./sdk/...` | scoping to a package avoids 50-min runs; `-out` needs a **Windows-style path** |
| Java deps | gradlew dependency-check / `mvn` | repo ships `gradlew`; mvn/gradle may be absent |
| pattern sweep | `rg -n --no-heading -e '<pat>' <repo>` | far faster than a Python `os.walk` regex sweep |

Cross-repo sweep patterns that have signal: `BEGIN .*PRIVATE KEY`, `mnemonic\s*[:=]`,
`implements <CriticalInterface>`, `unsafe {`, `Math.random`, `child_process|Runtime.exec`,
`TODO|FIXME|HACK.*(sec|auth|sign|bypass)`, and the stub markers below.

```bash
# find security-critical code wired to a no-op
rg -n -i -e 'fake|stub|accepts every|accepts any|temporary|insecure|placeholder|not implemented|return true' <repo>/src/main
```
Ignore hits in `/test/`, `/test-clients/`, `*Test.java`, and public test keys (e.g. Hedera's
well-known local operator key `302e020100300506032b657004220420a60...` = NOT a secret).

## Step 4 — Line-level review of security-critical paths

For a DLT codebase the money is in **verification / authorization**, not web inputs. Read:
- signature verification (BLS / Ed25519 / ECDSA / threshold): is the *real* impl wired, or a fake?
- proof verification primitives (SSZ Merkle branch, Merkle-Patricia Trie, IAVL, Merkle proofs):
  leaf↔root binding, exclusion semantics, depth/index constants, traversal guards.
- quorum math: `(2n)/3+1` (QBFT) or `signedPower*3 > totalPower*2` (CometBFT) — check overflow
  (`addExact`/`multiplyExact`) and that the totals come from the **trusted** set, not the payload.
- the trust-anchor / config bootstrap path: does it verify anything, or is approval the only gate?
- feature-flag gate: walk `isDisabled()`/`enabled()` to state real reachability honestly.

**Worked example (the finding that landed):** `FakeBlsSignatureVerifier.fastAggregateVerify(...)`
returns `true` unconditionally, lives in `src/main`, is the *only* implementation of the interface,
and is hard-wired in two system-contract call handlers (`new EthereumSyncCommitteeProofVerifier(
FakeBlsSignatureVerifier.INSTANCE)`). The sibling peer-ledger verifiers were real → an isolated
defect, not a weak model. Feature-flag `clpr.enabled` default `false` → severity downranked one
level per the program's own "not active in production" clause. Grep for the sibling stubs first —
"is this the only implementation, and is it wired?" is the whole finding.

## Tool-invocation traps (Windows/MSYS)

- With `MSYS_NO_PATHCONV=1`, **native** tools (rg, gosec, go) get the raw `/d/...` string and can't
  resolve it → use Windows-style `D:/path` for their arguments; bash redirection `> /d/...` is fine.
- `gosec -out=/d/...` fails with "cannot find the path specified" — pass `-out=D:/...`.
- `go install` needs absolute Windows `GOPATH`/`GOMODCACHE` (`C:/Users/<u>/go`) or it errors
  "GOMODCACHE entry is relative". Flaky proxy downloads (TLS timeout) → simply retry the install.

## Coverage-answer discipline (the user WILL ask "all tools? all variants?")

Never answer "yes". Answer mechanically from disk:
1. list the artifact set (`find <ws> -name '*.json' -o -name '*.txt'`) — a phase with no artifact
   never ran;
2. `command -v` the whole tool universe, then diff INSTALLED vs **fired-with-evidence**;
   name the **INSTALLED-but-never-fired** tools explicitly (that's the real gap);
3. for this track, mark the scanner layer **N/A by program rule** (no live host), not "passed";
4. state verified NEGATIVES per file/function, and list what was NOT touched.

## Artifact layout

```
<ws>/SCOPE.md            # assets, rewards, prohibited activities (verbatim)
<ws>/PHASE_LOG.md        # phase status + coverage ledger (verified negatives) + tools-fired table
<ws>/findings.json       # validated_findings[] + observations[] + residual_gaps[]
<ws>/report/<TITLE>.md   # Immunefi-format report
<ws>/evidence/           # npm audit json, govulncheck txt, sweep-*.txt, gosec json
<ws>/repos/              # the clones
```
