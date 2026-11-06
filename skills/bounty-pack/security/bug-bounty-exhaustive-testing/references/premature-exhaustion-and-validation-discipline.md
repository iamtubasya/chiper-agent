# Premature Exhaustion + Validation Discipline (Zenya & ChainPort, 2026-10-24)

Two engagements back-to-back. Both burned the same lesson: **manual curl/requests probing is NOT an
exhaustive audit**, and a scary-looking signal is NOT a finding until exploitability is proven.

---

## 1. THE FAILURE: "exhausted" after manual probing only (Zenya)

On Zenya I ran ~40 rounds of hand-rolled `requests` probing (endpoint sweeps, injection, XXE, verb
tampering, CORS, JWT, OAuth, SAML, IDOR-by-GUID…), found one solid bug (username enumeration) + one
Low (WP user enum), then twice told the user the surface was "well-hardened / exhausted."

User correction (escalating, frustrated):
> "amu cepat sekali nyerah. itu web2 web3 sebanyak itu skill dan toolsnya, masa kamu bilang udh habis attack surface"
> "deepdive lebih luas dan dalam"

**What I had NOT done:** the mandatory automated tool suite and the deep passive sources. The moment I
actually ran them the picture changed:
- `nuclei` / `ffuf` / `katana` on all subdomains (katana surfaced the `/pools/[id]` dynamic route).
- **Deep JS-bundle analysis** (all `/_next/static/chunks/*.js`): ABIs, keychain/session-key functions,
  hardcoded hosts, S3 buckets, RPC providers.
- **Crawling the docs site sitemap** → this is where ChainPort's entire documented API surface
  (`/api/meta`, `/api/port`, `/api/token`, `/function_caller`, `/token/list`, `/cardano/build_tx`,
  `/cardano/sign_tx`) and 108 contract addresses came from.
- **Comparing staging vs prod** subdomains (different contracts/config; staging-api behaved differently).

**RULE (embed):** "I probed a lot with curl" ≠ exhaustive. Before the word "exhausted / well-hardened"
leaves your mouth, confirm you ran the automated ladder (nuclei/ffuf/katana/gau) AND mined the passive
gold (JS bundles, docs sitemap, staging vs prod diff). On ChainPort the payable finding
(broken API auth) existed only in the docs + the staging/prod auth diff — invisible to manual curl on
the obvious endpoints.

---

## 2. VALIDATION DISCIPLINE — prove it's a finding AND not by-design

Recurring user corrections this session: "kamu harus buktikan, jgn teori", "pastikan ini bukan data
public atau by design", "tiap temuan ad impact dan as attacker bisa apa", "jgn brute force tp cari celah".

### 2a. Check the API's DECLARED auth before claiming anonymous access is a bug
Zenya `/api/cases/fields` returned 612 sensitive field definitions to the anonymous account — looked
like a strong data-model disclosure. But the Swagger (`/api/swagger/v1/swagger.json`) marked the
operation `security: [{}, {basic}, {bearer}]` — the leading `{}` = **anonymous access is explicitly
allowed** (needed for the FLOW public report form). Sibling endpoints (`/objects/data_types`,
`/cases/case_types`) returned `[]` for anon, confirming the schema endpoint is intentionally open.
→ **`{}` in Swagger/OpenAPI security = by-design anonymous. DROP.** Always pull the spec and read the
per-operation `security` before reporting "anonymous can read X."

### 2b. Validate CORS exploitability, don't stop at reflect+creds
Zenya developer WP `/wp-json/*` reflected ANY `Origin` + `Access-Control-Allow-Credentials: true` —
textbook CWE-346. But it was **non-exploitable**:
- WP REST cookie-auth requires the `X-WP-Nonce`; the nonce is NOT in any `/wp-json/` response and
  `/wp-admin/` + `/wp-login.php` send NO CORS headers → attacker can't obtain it cross-origin.
- WP auth cookie had no `SameSite` attr → browser default **Lax** → not sent on cross-site `fetch()`.
→ authenticated routes return 401 for the cross-origin attack; only already-public endpoints are
readable. **Reflect+ACAC is necessary, not sufficient.** Check (1) nonce/token requirement, (2) cookie
SameSite, (3) whether the nonce is leakable, before assigning severity.

### 2c. Impact + attacker-capability + proof, every time
User rejected "username enumeration" as insufficient until framed with the attack chain
(enumerate → credential-stuff → ATO) and honest severity (Low–Medium, not "critical ATO"). And rejected
brute-forcing real passwords outright. Frame each finding as: what the attacker CAN do, with a
reproducible PoC, at honest severity.

---

## 3. TECHNIQUE — Broken/inconsistent API auth across route families (ChainPort, the payable one)

The app had TWO API families on the same host with DIFFERENT auth enforcement:
- **App routes** (`/api/port/tokens`, `/api/bridge/quotes`, `/api/port/balances`) → `403 Missing
  Authentication token` (key enforced).
- **Documented API** (`/api/meta`, `/api/port`, `/api/token`, `/function_caller`, `/token/list`,
  `/cardano/*`) → processed WITHOUT any key (200 / 400-missing-param / 503).

The tell was an **intra-family inconsistency**: `/cardano/build_tx` POST → `403` (auth present) but
`/cardano/sign_tx` POST → `503` (auth check MISSING) — and `sign_tx` is the ChainPort Node's Cardano
co-signing endpoint. Method: enumerate every route family (app routes, documented/developer API,
staging-api, webhooks), then diff the no-key response per route AND per HTTP method. A route that
returns 400/503 (processed) where its sibling returns 403 = missing auth.

Bonus from the same host: `/api/meta` (no key) dumped 2.7MB incl. **full contract ABIs**; `/token/list`
dumped 159 tokens; invalid params on 5 endpoints returned **Python tracebacks** (CWE-209) leaking
`/var/task/...`, `psycopg2` (PostgreSQL), SQLAlchemy, AWS Lambda.

---

## 4. TECHNIQUE — Access-control test for UNVERIFIED contracts (no source)

When Etherscan shows the contract unverified and `heimdall decompile --include-yul/--include-sol`
(beta) produces no source, you can still test access control dynamically:
1. `heimdall decompile <bytecode>` → `abi.json` gives every function signature + `stateMutability`
   (works even when source gen fails).
2. Compute 4-byte selectors (`keccak256("name(types)")[:4]`; pycryptodome `keccak`).
3. `eth_call` every **nonpayable/payable** (state-changing) function from an arbitrary `from` address
   via a public RPC (publicnode / llamarpc). `REVERT` = protected; `OK` (no revert) = candidate
   unprotected function.
ChainPort Vault: 16/16 state-changing fns reverted from an arbitrary address → access control solid
(no finding). This is a fast, source-free AC screen — run it before declaring a contract "can't audit."

## 5. Misc captured this session
- **Etherscan V1 is deprecated** → use V2: `https://api.etherscan.io/v2/api?chainid=1&module=contract&action=getsourcecode...`.
- **Proxy contracts**: `getsourcecode` on the proxy returns `Proxy=1` + `Implementation=0x..`; fetch the impl.
- **Docs sitemap is a recon goldmine** (`/sitemap.xml`, `/sitemap-pages.xml`) — API endpoints, contract
  addresses, ABIs, auth hints (HMAC/nonce/signature). Crawl it before declaring the API surface known.
- **Traceback leak (CWE-209)**: send a wrong-typed/missing param; a 503 with `Traceback ... /var/task/`
  leaks stack + libs + cloud. Capture full body for PoC.
