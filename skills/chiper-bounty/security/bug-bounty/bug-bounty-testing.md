## PHASE 4-4.5: VERIFY, EXPLOIT & DEEPDIVE (Detailed + References)

---

- `references/edoverflow-cheatsheets/` -- 20 cheatsheets (XSS, SQLi, SSRF, OAuth, etc)
- `references/src-hunter/` -- 267 files: 20 playbooks, 50 payloader dirs, 6 methodology, 141 H1 reports, 3 dicts, 3 templates
- `references/nuclei-templates/` -- 21 Nuclei scan templates (IDOR, LFI, RCE, SQLi, SSRF, SSTI, XSS, XXE)
- `references/spyhunt-payloads/` -- 7 payload files (API, bypasses, proxies, SQLi, SSRF, traversal, XSS)
- `references/awesome-osint/` -- OSINT tools list (250KB)
- `references/awesome-android/` -- Android security resources (29KB)
- `references/awesome-web3/` -- Web3 security resources
- `references/burpsuite-pentester/` -- BurpSuite cheatsheet (5KB)
- `references/cbh-hunt-skills/` -- 58 specialized hunt skills (IDOR, OAuth, GraphQL, SAML, etc)
- `references/cbh-skills/` -- 25 other skills
- `references/cbh-commands/` -- 15 command references

### Integrated Tools (from repos)
- `tools/abh/` -- 64 files: hunt.py, intel_engine.py, llm_redteam.py, sast_scan.py, oob_listener.py, lead_board.py, visual_triage.py, waf_encoder.py, spray_orchestrator.sh, etc
- `tools/cbh-engine/` -- 11 files: engine, llm_client, token_manager
- `tools/cbh-scripts/` -- 16 files: validation, test harness
- `tools/dnsReaper/` -- 155 files: full subdomain takeover detection tool (50+ service signatures)
- `tools/ezXSS/` -- 111 files: full blind XSS server (PHP)
- `tools/spyhunt/` -- 177 modules + 150 WAF plugins + 5 smuggler files + 7 payloads
- `tools/bxss/` -- 39 files: blind XSS server (Node.js)
- `tools/jshunter/` -- 34 files: JS endpoint extractor (Go)
- `tools/allforone/` -- Nuclei template updater
- `tools/src-hunter/` -- src-hunter CLI


---


---

  re-running, and the one real lead (deep-link→WebView phishing, HoF-bucket) plus the wall
  (≈360 authenticated endpoints, needs one KYC'd test login). Also carries **banking-programme tooling
  discipline**: curated nuclei only (default sweep = ~34k requests), katana domain confinement,
  `-rate 10 -t 2`, and skipping the rate-limit test entirely when the policy caps it.

- `references/moneta-cz-engagement.md` — **MONETA bank VDP (moneta.cz), email-only, no test accounts.**
  Liferay 7.4 + Spring Boot `openapi` + F5 ASM stack map; the **tri-state auth classification** for Spring
  gateways (`"No static resource"` = unmapped / `cbl.missing.userid` = session /
  `POWER_AUTH_SIGNATURE_INVALID` = PowerAuth) plus the correct ffuf `-fr "No static resource"` filter;
  complete unauthenticated surface and the 5 live `/unsecured/portal/*` modules; **5 chain tables naming the
  exact step each lead dies at**; 14 verified controls so they are not re-burned; the single unproven hop
  (`contextId` server validation); and the two methodology corrections (volume-ledger fabrication, leads
  scored in isolation). Read before any bank/fintech re-run.
- `references/secrets-surface-audit.md` — **di mana rahasia sebuah produk bisa bocor**: enam surface
  (task log, endpoint preview/interpolate, payload interruption, artifact, storage layer, log
  container produk itu sendiri), cara menguji masking dengan set marker (panjang 1/2/3/4, nilai
  multi-baris yang dipotong, nilai embedded), membuktikan enkripsi at-rest dengan menanam marker
  lalu mencarinya di storage, dan aturan kejujuran (tabel kosong = "tidak bisa dinilai", bukan "bersih").

| File | Purpose |
|------|---------|
| `references/operator-workflow.md` | 14-point checklist |
| `references/rls-policy-migration-audit.md` | **Multi-tenant authz white-box from SQL migrations.** Reconstruct live RLS policy state (last-op-wins) with the two regex traps that produce false counts — the quoted-schema `ON "public"."tbl"` miss and the DROP-without-ON match; bin API-key helpers by reading their BODY (scope-aware / scope-blind-but-key-aware / key-unaware), never by name; why PERMISSIVE policies OR together so ONE scope-blind `FOR ALL` defeats every scope-aware sibling on that table; the docs-promise-vs-code-comment contradiction as a ready-made finding; and why an app-layer `module: null` gate skip is NOT a finding until you check RLS compensation. Read before auditing any Supabase/Postgres-RLS target or any open-source multi-tenant app. |
| `references/god-eye-validation.md` | Validation framework |
| `references/severity-rules.md` | Severity calibration |
| `references/checklist-219-boxes.md` | 219-box report gate |
| `references/reporting.md` | Report writing |
| `references/humanize-screenshots.md` | Screenshot standards |
| `references/advanced-vuln-vectors-2026.md` | Advanced vectors |
| `references/host-header-injection-methodology.md` | **Host Header Injection class** — probe shape, all-host sweep, impact taxonomy (reset-poisoning ATO), negative controls (XFH/session-fixation/cache), worked mail.com case + Adafruit 403 counter-example |
| `references/pre-submission-verification.md` | Pre-submission checks |
| `references/pre-submission-self-review-gate.md` | **Run AFTER the PDF is built, BEFORE staging any draft.** Five questions that killed two otherwise-clean reports (2026-10): (1) does the vendor's own docstring describe the behavior as intended — if yes it is a documented decision, reclassify or reframe as a docs-vs-code contradiction; (2) does severity rest on a doubt-phrased question ("whether X adds a scope check") — resolve it or downgrade; (3) is the proved/argued table actually filled from the proved column; (4) against the target or only a clone — say which; (5) would the honesty block embarrass you when the vendor replies "that's by design". Staging is the LAST step, never a way to pressure-test findings. |
| `references/pdf-generation-pitfalls.md` | Bug-report PDF generation (fpdf2 core-font/unicode traps, reportlab screenshot embed) + **§7: stage the PoC PDF as a Gmail DRAFT attachment before moving on (owner rule)** + §8: verify a screenshot is non-blank when the vision model is unavailable |
| `references/bb-methodology.md` | BB methodology |
| `references/recon-methodology.md` | Recon methodology |
| `references/vuln-methodology.md` | Vuln methodology |
| `references/bugcrowd-vrt.md` | VRT reference |
| `references/vrt-lookup.md` | **Fetch and query the Bugcrowd VRT instead of guessing the category** — the taxonomy JSON URL, the leaf-walk query, and the rule that `Disclosure of Secrets` splits P3 (`For Internal Asset`) vs P1 (`For Publicly Accessible Asset`). Read before writing the severity line of any Bugcrowd report. |
| `references/bugcrowd-ninja-alias-signup.md` | Self-signup with `@BC_ALIAS.com` alias + reading the forwarded verification mail (Mandrill decode) |
| `references/email-template-injection.md` | HTML/link injection in transactional mail (invite, resend, notifications): sink table, payload ladder, escape-differential evidence trick, DKIM/SPF capture, CRLF header-injection negative test, escape-map across templates, honest P4→P3 scoping |
| `references/info-disclosure-complete.md` | Info-disclosure playbook (web2 + self-hosted services): classic sources, plus **§17 sink-fidelity** — "redaction at the log is NOT redaction at the sink" (find the redactor, follow the value, the sink without it is the bug; error-object fidelity: `format!("{:#}", e)` / `traceback` re-inject secrets into stored+served strings) and **§18 self-hosted daemon surface** (bind address, auth *coverage* vs mere presence, default-port/start-condition, official docker-compose/Helm exposure, severity framing vs the program's impact table) |
| `references/postmessage-iframe-channel-testing.md` | Embedded/payment pages: find the `message` handler in the bundle, framing check (incl. the 429-page `X-Frame-Options` trap), local attacker-origin harness, CDP OOPIF attach to read the cross-origin iframe DOM, demo/preview-token hunting, "proved vs not proved" P4 scoping, re-test leads before submitting |
| `references/vendor-granted-account-constraints.md` | Vendor-granted accounts with a written "don't touch X" rule: enforce via rules file + env-var route guard + capability flags, prove compliance in the report, and avoid the generic-clicker near-miss that fired the forbidden action and killed the session |
| `references/wordpress-admin-attack-surface.md` | WordPress/CMS marketing sites: `/wp-json/` route table as the plugin map, the **400-before-permission trap** when classifying REST auth (400 ≠ unprotected), the **500-not-401 differential**, **download-the-exact-plugin-build** white-box greps (`register_rest_route` / `permission_callback` / **`wp_ajax_nopriv`**), the **nopriv unauthenticated-handler** finding class (static-`token`-only gate → `media_sideload_image` SSRF), the one-route-missing-`permission_callback` differential (e.g. iThemes `/bans` 200 vs siblings 401), readme.txt + nuclei detected_version fingerprinting with the "a version is not a CVE" rule, author/Yoast enum, cardoma.shop case study, and the OOB/smuggling/ffuf negatives so the next pass skips them |
| `references/sherlock-program-rules.md` | **Sherlock** programs (any of them): submission is a login-gated form not e-mail; the excluded-class list that gets reports rejected; the verbatim "user transferred tokens directly" clause + its two escape prongs (pre-empt it in the report); duplication is by ROOT CAUSE so several routes = ONE report; impact must name the missing control; mandatory prior-audit duty + what to do when the reports are unreachable (disclose + offer withdrawal) |
| `references/smart-contract-methodology.md` | Smart contract |

---

| `references/web3-static-analysis-triage.md` | Contract-audit tool set (forge build / slither per package / aderyn / mythril / echidna / forge test), the **slither-FP triage table with verified reasons** (incl. the inherited-custom-modifier `unprotected-upgrade` FP and how to prove it), the solc-pin slither stall fix, and the **economics-verification rule** (prove the pool round-trip before claiming a slippage/inflation theft). Read before finalising any contract-audit coverage ledger. |
| → `web3-audit/references/cross-chain-settlement-and-attestor-audit.md` | **Bridge / intent-settlement protocols: the bug lives in the DIFF between the off-chain attestor service and the on-chain program (credit amount, currency, id packing). Load when the target has an oracle/attestor API + a settlement vault.** |
| `references/solana-blackbox-program-analysis.md` | **Solana black-box program analysis without source** — IDL-driven borsh account decoding (worked Loan layout), programdata upgrade-authority extraction, single-key vs Squads-multisig detection, instruction co-sign mapping from IDL signer flags, multi-asset oracle-account decoding, tx tracing via getSignaturesForAddress, RPC endpoint discovery, API authz mapping by error-message differential, docs-vs-on-chain contradiction as a finding class |
| `references/recon-triage-and-vendor-claim-verification.md` | Recon FP killers (wildcard-DNS test, NXDOMAIN sweep, S3 `AccessDenied` vs `NoSuchBucket`, "resolves ≠ live ≠ takeover", env-codename enumeration, auth-parity check), independently verifying a vendor's published advisory (npm publish dates + tarball grep + placeholder-vs-real secrets), in-memory handling of malicious payloads (AV Errno 22), and scanner-label-vs-finding triage (aderyn H×3 all FP). **§10 = three more FP classes: a wildcard at the REGISTRABLE-DOMAIN level means the whole domain family is a third party (random-label test + apex title + RDAP, before spending one request); a generic-name bucket hit is not ownership evidence (read the `<Key>` list — the public listings found belonged to other companies); and gau/waybackurls output is historical (3 of 4 juiciest archived endpoints were already dead — resolve first, then probe)**. **§11 (2026-10): subzy takeover flags on CF-proxied hosts are FALSE POSITIVES — influx/ldbapi/ldbapiglobal flagged "Cargo Collective" but all resolve to CF proxy IPs and the generic CF 404 matched the fingerprint; classify every subdomain's IP class (CF / Tailscale-100.x / bare cloud) before believing any takeover output, and check dangling-IP candidates for a live SSH banner before claiming recyclable. Tailscale IPs (100.64/10) in public DNS for internal hostnames (secmon/netbox/im/status) = recon-only info candidate, not a finding without reachability** |
| `references/target-reachability-and-egress-triage.md` | Host resolves but TCP/HTTPS times out: tell an **egress/WAF block** apart from an **IP-allowlisted partner API** (raw TCP `:443` probe + toggle the egress, e.g. `warp-cli`; still FILTERED on every egress ⇒ allowlist, record unreachable and stop). Plus: DataDome answers 200 for one egress IP and 403 for another, so try >1 egress before declaring "WAF blocks all"; and the MSYS `curl -o` relative-path + `curl \\| python3 - <<PY` pitfalls. |
| `references/passive-recon-during-target-lockout.md` | **You got the target to ban your IP mid-engagement** (429 → TCP drop, survives WARP rotation): the ban-cooldown ladder with detection one-liners, what fuels the ban even at "gentle" rates (error storms count as traffic), and the passive value stream that keeps the run productive without touching the target (wayback CDX endpoint discovery, archived openapi/postman recovery, the **by-design check** via the vendor's marketing site, offline JS white-box, pre-built next-batch scripts). Read the moment a target starts 429-ing or a scan run shows mass timeouts. |
| `references/agent-kb-bounty-exploit-master.md` | Master KB |
| `references/cross-chain-bridge-audit.md` | Cross-chain / intent-settlement bridge protocols (Relay, message bridges): recon (clone protocol+vaults+off-chain-oracle repos; verify deployed source via Blockscout/Sourcify; enumerate chain slugs from the public API; find the settlement chain's RPC/explorer; read the oracle service's unauthenticated Swagger at `/documentation/json`), the money-path authorization table (deposit→MINT bounded by the emitting token contract, fill→TRANSFER, withdraw→BURN, recovery), the `abi.encodePacked` id/alias collision brute-force (with per-VM encoding lengths), off-chain `force`/skip-verification flags, commitment-scheme checks, the honest protocol-track reporting shape (0D = N/A, findings.json observations[], coverage ledger), and the Relay case study + residual gaps |
| `references/wordpress-unauth-handler-hunting.md` | WordPress/WooCommerce unauth-handler hunt: plugin-stack fingerprinting, full REST-namespace enumeration, the **400-fires-before-permission_callback** auth-classification trap, `wp_ajax_nopriv` / `permission_callback=__return_true` white-box grep (read the body before believing the flag), token/shared-secret handler conclusions (no `===` bypass, no safe write-oracle, disambiguating the empty read), xmlrpc / CVE-2023-5561 / media-enum checklist, and the CDN rate-limit-block signature (uniform tiny 403 + tools throwing TLS errors) with egress-rotation recovery |

| `references/desktop-app-binary-analysis.md` | Desktop app binary + auth-surface analysis: MSI/DMG extraction, MSI table dump, Authenticode, Ed25519 key recovery, public env config, Zitadel/Auth0 batteries, mailbox-search pitfall, object-id-as-capability. |
| `references/engagement-techniques-2026-10.md` | Byte Federal + Fastmail technique bank (anti-bot, Livewire, JMAP, OAuth DCR, CF tools, subzy, quarantine). |
| `references/graph-node-indexer-audit.md` | **Graph Node / indexer software (off-chain, Rust/TS):** the scope-reality check (The Graph's reward table has 4 impacts; indexer-software risks appear only in the prose), where secrets actually live (no indexer key on-node; provider URLs / DSNs / log-store passwords are), the unauthenticated-surface inventory with code anchors (admin JSON-RPC `0.0.0.0:8020` no auth; index-node `:8030` auth gates only `proofOfIndexing`), the **live PoC harness** (docker compose stack + local JSON-RPC reverse proxy that forwards via `curl`) with every boot/deploy pitfall hit for real, and the important negative: a dead RPC does **not** promote the URL into a served `fatalError.message` (block-stream errors are retried, never become a `SubgraphError`) |
| `references/zenya-multitenant-saas-api-enumeration.md` | **Multi-tenant SaaS API testing** — product API lives on per-tenant subdomains, NOT the apex; public `/api/` landing + `/api/swagger/v1/swagger.json` = full route map; **N-state enumeration oracle** via token/registration endpoints (invalid→"not found" / valid-restricted→"not allowed" / valid-wrong-secret→"invalid X"), unthrottled; **anonymous access-boundary classification** (403=enforced / 200-[]=by-design-scope / 404=no-IDOR / 200+data=check the by-design carve-out BEFORE calling broken-AC); api_key bypass battery (empty/null/default/timing — a proper secret fails all); scope re-classification table (version-listing / public-files / non-200 / rate-limit-no-impact / third-party = OOS); honest pre-auth-ATO-enabler framing. Worked case: Zenya. |
| `references/audit-process-discipline.md` | **PROCESS rules the operator enforced** (moneta.cz, 2026-10-26): chain every lead to its sink before judging it; verify ≥3× with *different* methods; a tool marked N/A without being RUN is a violation ("BELUM dijalankan" ≠ N/A); read the real telemetry before writing the ledger. |
| `references/unauth-enumeration-and-reflection.md` | **Finding + testing the unauth surface**: error-oracle parameter discovery (harvest 400 field names, don't guess), character-by-character reflection escaping map + why HTML entities are safe inside `<script>`, WAF differential fingerprinting, response-size fingerprinting so a block page is never mistaken for an endpoint, browser-capture over guesswork, why a bare 500 is operational not a finding. |
| `references/mobile-static-analysis-pitfalls.md` | **APK white-box traps**: `jadx -d` "finished with errors, count: N" = per-method failure, not missing classes; dex string-pool false positives (name in pool ≠ call site); "hidden debug menu" leads need layout `visibility` checked; Kotlin `defpackage/`; the four gates of a deep-link→WebView chain; scheme hijack only matters if the link carries a secret. |
| `references/chainport-2026-10-engagement.md` | **ChainPort** cross-chain bridge (closed-source, no payable finding): surface map (23 subdomains incl. live dev/staging/preprod, Next.js app proxying a key-gated AWS API-GW backend, secured S3), the **closed-source barrier** (Vault+Deployer unverified + heimdall source-gen fails → fund-loss logic unauditable), the **access-control-solid negative** (all 16 state-changing fns REVERT from arbitrary via the heimdall-ABI + eth_call sweep in `smart-contract-audit/references/unverified-contract-abi-ethcall-recon.md`), verified negatives (no XSS/injection/takeover/CORS), and the ONE re-hunt unblock (contract source). |
| `references/secret-in-error-strings-and-log-leak.md` | **Secret leak via error strings / logs / status APIs** (the concrete shape of the "private information being stolen" impact): credentials embedded in URLs, the 6-step method (grep the format sites → find the redaction helper → check whether redaction is applied to the *value* or only the *log line* → look for the adjacent redacted/unredacted asymmetry that is the smoking gun → trace promotion to a client-visible endpoint → check the default deployment), what evidence convinces a triager, and the pitfalls (verify the promotion path before claiming a served leak; log-only ≠ remotely-readable; unauth admin API is a *different* finding) |

| `references/self-hosted-product-lab-and-octopus.md` | **Self-hosted / on-prem products** (Octopus Server+Tentacle, GitLab, Jira DC, …): the check-free-RAM-first rule (a 6 GB host running Docker Desktop + SQL Server + a big .NET app produces symptoms that impersonate product bugs), the Docker recipe that actually boots (`DISABLE_DIND=Y` on both images, pin `MASTER_KEY` + mount `/root/.octopus` or the container regenerates the key and the DB stops decrypting, long SQL healthcheck `start_period`, `restart: unless-stopped`), the Octopus REST API mechanics that cost iterations (**step target roles live in step-level `Properties`, not `action.Properties`**; space-scoped `scopeduserroles`; `API-` prefix required on keys; the CSRF cookie is the header value), how to test a **sensitive-variable masking** control (length sweep + partial/`head`/`cut`/embedded/multi-line variants) with the verified `<4 chars` and exact-complete-match-only gaps, and the RBAC/multi-space matrix rule: **never score a permission result off a `400`** — re-send a valid payload and confirm against `GrantedSpacePermissions` |

| `references/self-hosted-product-audit.md` | **Self-hosted / on-prem product audits** — the target is software you install yourself, not a URL (Octopus, GitLab, Jira DC, Grafana…): reading the brief's scope + intended-execution carve-out, trial licence via the researcher alias, standing up the vendor's container (**DinD exit-143**, **master-key-changes-on-recreate**, DB healthcheck `start_period`, small-host memory/disk), minting an API key (vendor key-format trap), white-box attribution to a shipped class without a decompiler, what these programs actually pay for (silently-failing security controls, RBAC, component transport), audience-proving and plain-text reporting |
| `references/spa-api-envelope-reverse-engineering.md` | Extracting a modern SPA's private API from its bundles (VeSync): runtime `config.js` → API hosts; bundle grep for paths; the axios `{context:{...}, data:{...}}` envelope; appID map; lazy chunks for field names; error-code enumeration; Playwright hydration wait (~20 s, `domcontentloaded`). |
| `references/spa-client-crypto-and-shared-account-tokens.md` | After the endpoint map: client-crypto replication + shared service-account tokens (`*_ACCOUNT_SUB`, unauthenticated `download-token`); PBKDF2-SHA512(1e6)+AES-GCM `hex(nonce)||hex(ct)` replication to read/forge objects; the 8-step create flow; IMAP `AND(from_=...)` fix; `<name>_NOTE.txt` for misleading logs. |

## Lifecycle-enforcement & API-version-parity hunting (2026-10-26, Hivenet)

Two bug classes that both paid on one target, and generalise to any SaaS with a share/transfer feature and
more than one API generation. Worked case (scope, submission format, Send crypto recipe, both findings,
24-item negative ledger): `references/hivenet-2026-10-engagement.md`.

- **Version parity.** When a product still routes both `/x` (legacy) and `/x/v2`, test the SAME write on
  both before anything else. The legacy route is where the ACL check was never back-ported. The decisive
  pair is *fabricated id -> 400* (existence check only) against *a real object owned by another tenant ->
  2xx* (no authorization check). If v2 answers `403 ... does not have access to this V2 document`, you
  already have the differential the report needs; the sibling endpoints (`/v2/bulk`, `/expire`,
  `/users`) then tell you how wide it is. Confirm whether the gap is create-only: v1 `GET`/`PUT` of the
  same foreign record answering 403 sharpens the finding instead of weakening it.
- **Claimed lifecycle vs enforced lifecycle.** Take every promise the interface makes — delete, expiry /
  TTL, revoke, "the recipient cannot forward it" — and test it at the STORAGE layer, not the metadata
  layer. Delete the object, then re-read the blob/asset path with a FRESH anonymous token: `DELETE
  /share/{id} -> 204` while `GET /blob/{cid} -> 200` and still decrypts is a finding on its own. Also
  (a) let a short TTL expire naturally and re-read, and (b) probe for the *absence* of any delete route on
  the blob path (405/404 = nothing can ever purge it, including support). For share-link products, prove
  it the strong way: derive the key from what a link holder legitimately receives, decrypt a file you
  uploaded, delete the transfer, then decrypt again with a brand-new token. Byte-identical plaintext after
  deletion is the evidence shape; "the endpoint still returns 200" is not.
- **Scope discipline for these:** both classes were proved entirely between two self-owned free accounts,
  with no third party's object touched. Keep it that way — it is what lets the report state "no real user
  data accessed" without qualification, which is the single line a triager checks first.

## Wall-triage quick rules (2026-10-20, Byte Federal — full bank: `references/target-defense-patterns-and-wall-triage.md`)
- **Spring "openapi" gateway + React SPA (bank/fintech) → read
  `references/spring-gateway-route-oracle-and-spa-api-map.md` FIRST.** It carries the three-way
  route-existence oracle (`No static resource X` = unmapped / `cbl.missing.userid` = exists+auth /
  validation error or 200 = **unauth, attack here**), the bundle-regex that separates 364 real API
  calls from 1840 quoted strings, the F5 ASM uniform-block-size ffuf fix (`-fs <blocksize>` and
  `-fr "No static resource"` — without it ffuf invents dozens of fake hits), the
  capture-the-contract-with-Playwright rule after param guessing fails, and the katana gating rule
  (gate with `-d 2`; grep a killed crawl's tail before discarding it — moneta's tail was the only new
  surface found post-report).
- **Uniform 403 sweep = CF edge block, not an app map.** If every probed path returns the identical
  status+byte-size, rerun with a browser UA before concluding anything. Laravel reached = JSON
  `{"message":"The route X could not be found."}`.
- **A block page can be `HTTP 200`.** F5 ASM (moneta.cz 2026-10) answers `200` with an **identical
  46650-byte HTML body on every path name**; 75/75 "hits" in one ffuf run were that page. Establish
  the baseline size once, then `-fs <size>`. Real directories came back `403` at a *different* size
  (48397 B) and absent paths `404` with the app's own 490053 B page — that three-way size split is
  the WAF/app tell. When the path *is* an app route the block comes as
  `{"supportID":"…","response_type":"General"}`, which is also what you get for XML/`<!DOCTYPE`
  payloads ⇒ **XXE is unreachable by design; log it as "WAF blocks before the parser", not as a
  failed test and never as a finding.**
- **Never `-ac` on a WAF-fronted host.** ffuf auto-calibrate discarded a genuine route hit here
  because the block-page baseline dominated. Filter on an app string (`-fr "No static resource"`)
  or an explicit `-fs`, not on auto-calibration.
- **Spring gateway route-map fingerprint (1 request/path, no tooling needed).** Body fragment decides
  the verdict: `No static resource <p>` = route absent → drop it; `cbl.missing.userid.exception` =
  mapped + session enforced; `POWER_AUTH_SIGNATURE_INVALID` = mapped + step-up enforced;
  `{"code":"NotNull","message":"<field>"}` = **mapped and open, and it hands you the schema one
  field at a time** (send `{}`, read the missing field, add it, repeat — mapped a loan calculator in
  3 requests). Full worked map: `references/moneta-cz-2026-10-engagement.md` §4.
- **NEVER score a security control off truncated stdout.** In this run a first read of
  `ssl-pinning.json` showed only the 4 expired rotation entries and produced the conclusion
  "pinning is dead"; the file actually had 8 entries — 4 expired + 4 valid, overlapping correctly.
  Dump to a file, count entries, print `len()`, and re-read in full *before* writing "control X is
  broken". A partial view is exactly the shape that manufactures a false critical
  (`references/moneta-cz-2026-10-engagement.md` §8).
- **A guard message that names the feature is still a guard.** `/openapi/testing/skip-login` shipped
  to prod answers `"This endpoint is for testing purposes only."` — deployed but disabled. Run the
  12-variant path battery (`/`, `/.`, `;`, `;a=b`, `//`, `%00`, `%20`, case, `?x=1`, `./`, `..;/`),
  then move on. The variants that fall through to a Spring `400`/SPA `404` reveal nothing.
- **Programme limits that reshape the arsenal instead of cancelling it.** Bank briefs often cap
  traffic ("not more than 100 requests to test rate limit") and make scan output alone ineligible.
  Do not respond by going manual and do not respond by running the full 7137-template sweep either
  (34k requests — inappropriate, and here it was killed at 1%). Narrow the **template set**:
  9 Liferay/CVE templates = 24 requests, `-rl 4 -c 2`, real result. Curated-and-measured is still
  automated; "gentle automated" is the standing rule.
- **Bundle grep inflates the API map ~99%.** 364 paths grepped out of a production SPA bundle
  yielded 360 dead ones — client routes and API routes are intermixed. Do not read that ratio as
  "the surface is small"; run each through the route fingerprint above instead of guessing.
- **Program-status gate at Phase 0A:** read the LIVE policy page for a paused/retired banner before
  recon (pool `status` field is stale-able). Paused = no rewards = switch target, don't invest.
- **Turnstile/SMS/mobile-sig walls are coverage limits, never "0 findings":** name the wall and the
  endpoints it protects in the ledger, and state the ONE concrete unlock (test phone / solved token).
- **Historical gau hits, vendor GitHub source, and `/openapi.json` are free white-box** — use all
  three before live probing; test key *enforcement* (dummy key → 401), not just presence.
- **A Spring gateway's "No static resource X" is a route oracle, not a 404.** Use it to separate
  *not deployed* from *deployed+open* (`NotNull`) / *deployed+auth* (`missing.userid`,
  `POWER_AUTH_SIGNATURE_INVALID`) / *deployed+test-guarded* (`"for testing purposes only"`).
  Full recipe: `references/spring-gateway-and-spa-api-mapping.md`. Test-protected endpoints deserve
  a bounded bypass sweep (trailing slash, `/.`, `;`, `;a=b`, `//`, `%00`, `%20`, case, `?x=1`, `..;/`)
  and then an honest "guard holds" line — not a claim of access.
- **Financial targets: the default nuclei sweep is a scope violation waiting to happen.** Full-default
  ran ~34k requests across 2 hosts on a bank that caps rate-limit testing at 100 requests. Use curated
  `-t <dir>` per stack + named CVE ids, `-rl 4 -c 2`, and count your total requests as a deliverable
  (380 for a whole bank engagement is defensible; 34,000 is not). Same for `katana -kf all`, which
  escaped scope into a sibling domain on a Liferay site — confine with `-fs`/`-cs` or kill it.

## Regulated targets (banks / fintech) — read this FIRST
`references/regulated-target-engagement-discipline.md` — volume discipline (never a 7k-template sweep on a
bank; ~10 templates matched to the fingerprinted stack), read the nuclei telemetry before claiming how far a
killed run got, F5-ASM/Cloudflare block-page byte-size fingerprinting (46650 = ASM block, 48397 = app 403,
490053 = app 404), extract API contracts with a browser capture instead of guessing, don't kill crawlers
before they print, and chain-before-discard + 3x independent re-verification of every lead.

## External Repos (19 integrated)

All 19 repos merged into `references/` and `tools/`. 739 reference files + 593 tool files.

## Session / Next.js notes

- `references/nextjs-reflection-and-env-leak-verification.md` — Next.js `__NEXT_DATA__` `env` leak
  (internal host + plaintext scheme, CWE-200) + the **reflection-vs-XSS encode-differential test**:
  dalfox `[I] Reflected ...` is NOT a finding (`[V]` is); verify `"`→`%22` / `</script>`→`%253C...`
  by hand before scoring. Includes the RSC flight payload gotcha and `_buildManifest.js` route dump.
- `references/hosted-platform-and-appliance-fingerprints.md` — tell a third-party hosted platform
  from the client's app in one request (Teamtailor ATS => OOS even on `*.brand.com`), fingerprint
  Palo Alto GlobalProtect / Entra App Proxy / Azure EasyAuth / Jamf / GCS custom-domain buckets, map
  the backend estate from the CSP, and triage custom WordPress plugin `admin-ajax.php` handlers.
- `references/nextjs-server-actions-and-session-identity.md` — verify WHAT ACCOUNT your stored
  session cookie belongs to before testing (a stale jar may be an old free account while your key
  is paid); enumerate/replay/drive Next.js App Router **server actions** (42-hex ids, `Next-Action`
  header, per-render `$ACTION_KEY`, React native value setter, TOTP two-step gates); git-bash path
  mangling and Hermes secret-redaction gotchas.
- `references/nextjs-action-replay-and-authz.md` — replay actions HEADLESSLY: the static form format
  that works (bare field names; Chromium's `_1_` prefix always 500s from requests), why JS-invoked
  wire ids must be harvested live (they are not in the bundle or the RSC payload), the
  `page.route` body-rewrite authz test with mandatory positive controls, MFA-gated destructive
  actions, and the free-tier-cap replay recipe.
- `references/burna-ai-platform-2026-10.md` — target that PUBLISHES a VDP (security.txt + safe-harbour
  policy = the authorization): CT-log surface expansion (staging/v2/internal hosts, publicly-reachable
  staging 200-ing the full app), the **split-plane** API (control-plane REST on `api.*` with the
  better-auth cookie vs data plane on `agent.*` with a 5-min Bearer JWT minted by a `getAuthToken`
  Server Action; `POST` on a read path = 404 -> creation lives in actions), the **PRO enrollment token**
  test (`pro_`+32 hex, sha256-at-rest, raw-shown-once -> guess/forge not feasible; report the negative as
  a control), and the two entity-setup automation pitfalls (a required base-ui combobox blocks the submit
  with NO POST; Python slicing `[:N]` inside `page.evaluate` throws `Unexpected token ':'`).
- `skills/security/audit-execution-discipline/references/audit-pipeline-phases-and-fresh-run.md` (in `audit-execution-discipline`) — the
  orchestrator's real 0A→0F model, the mandatory full-URL + `--scope` gate, and where the resume
  state actually lives when you need a genuine fresh run.

## Engagement credentials & session hand-over

- `references/engagement-credentials-and-totp.md` — user asks "kasih email/password/2FA akun
  <target>" (or you are wiring a SECOND agent to log in): where creds actually live
  (`_progress/<target>_vN/creds_*.json`, `totp_pro.json`, `api_key.txt`, `totp_helper.py`), the
  api-key-vs-accountId-vs-TOTP-secret mix-up, stdlib TOTP generation (no pyotp), the copy-paste
  hand-over block (secret + fresh code + otpauth URI), the secret-tripwire *display* masking trap
  (masked print ≠ corrupt file), and "never verify creds by attempting a live login".

## Indexer / node software (The Graph graph-node)
`references/graph-node-indexer-audit.md` — auditing indexer/node software when the only reachable
reward impact is High "private information being stolen" (The Graph = worked case). Surface map with
file:line: unauth admin JSON-RPC on `0.0.0.0:8020` (unconditional, default port); index-node `:8030`
serving `fatalError.message` unauthenticated (auth gates only `proofOfIndexing`); the
`redact_log_urls` **asymmetry** — redaction applies to log lines only, the error VALUE keeps the
provider URL + API key; deterministic-vs-non-deterministic error classification deciding whether a
URL-bearing error is ever persisted/served. Includes a reusable local PoC harness (compose override +
curl JSON-RPC reverse proxy + minimal subgraph + graph-cli deploy gotchas) and the honest limit: a
log-level leak is NOT a High API disclosure — prove persistence first.

## Bugcrowd program scope extraction (no login)

- `references/bugcrowd-scope-extraction.md` — pull a Bugcrowd engagement's full brief
  + scope + rules WITHOUT a researcher login: the changelog `.json`-suffix trick (the
  page is a SPA, the plain path 404s), the `data.brief` / `data.scope` JSON shape,
  what to always extract (reward tiers, the OOS host list AND excluded vuln classes,
  the mandatory "bugcrowd" User-Agent / test-property rules), and the MSYS shell
  pitfalls (relative `curl -o` lands in the wrong dir; `curl | python3 - <<'PY'` eats
  the pipe). Use at Phase 0A/0B of any Bugcrowd audit, before firing tools. Runnable:
  `scripts/bugcrowd_scope_extract.py <slug>` — fetches the HTML, finds the changelog id, prints the
  scope tiers + reward table + rules.

## Vendor-specific scope + surface notes

- `references/hivenet-2026-10-engagement.md` — **Hivenet** (Store/Send/Compute; email-only
  programme, CVSS vector mandatory). Architecture (chunk + share record + metadata, the
  public download token, the v1/v2 record split), the three submitted findings, the chains
  that died with the verbatim server error that killed them, and the full negative list.
  Load before any Hivenet re-hunt.
- `references/desktop-app-supply-chain-analysis.md` — **desktop apps (MSI/DMG)**: map the
  download/update channel, extract an MSI without 7-Zip (`msiexec /a` elevated, or read
  tables via the WindowsInstaller COM object), hunt constants in a 180 MB .NET binary,
  and write the updater verdict a triager accepts. Companion to `mobile-app-bundle-recon.md`.
- `references/runonflux-2026-10-engagement.md` — **RunOnFlux**
  $50–$500 bands, "no aggressive scans"): the whole backend map recovered from the SPA `VITE_*` inlined env
  (gateway / mutable-platform / p2p agent / user-profile / payment-v2 / Zitadel), the passwordless auth contract
  (code bound to the email + single-use = a working control), the anonymous `machine token` from `/auth/download-token`
  that reads any transfer's share record, and **F1 High — `POST /mutablerecords` (v1) skips the per-document ACL that
  `/v2` enforces**, so any free account writes permanent records into another tenant's volume. Includes the full
  zero-knowledge derivation recipe (`readKey = PBKDF2-SHA512(pw=share.name, salt=share.rootMid, 1e6)`, AES-GCM
  `nonce(12)||ct`, hex-string key decode trap) used to prove decryptable injection into someone else's transfer,
  plus the verified-negative list (KEK ownership, Stripe confirm, counter endpoint, Swift bucket read-only).

- `references/runonflux-2026-10-engagement.md` — **RunOnFlux** (`runonflux.com` Web3 cloud, email-only bounty, PGP-required): full live-host map, verified-negative ledger (node-API "401-inside-200-body" trap, storage universal-403 auth gate vs IDOR, console CORS locked, ownllm AI gate solid), **F1 MEDIUM passkey `postMessage("*")` WebAuthn-assertion leak** (staged as draft+PDF), storage/marketplace route quirks + the authenticated-IDOR blocker (needs a test wallet), and the Gmail-draft routing fact (OAuth token is Calendar-scoped → use IMAP App-Password).
- `references/mailcom-2026-10-engagement.md` — **mail.com** (United Internet; discretionary rewards, authenticated-area scope): **Host Header Injection finding (validated 3x, shipped)** — auth services build absolute redirects from the untrusted `Host` header and leak `srttkn`/`jsessionid`; 5 affected hosts found by sweeping the whole live-host list (not just the first hit); reset-link poisoning = ATO framing; negatives documented (session fixation, cache poisoning, XFH, TRACE); signup geo-gated for ID egress. Includes the reusable host-header sweep recipe.
- `references/adafruit-io-authenticated-testing.md` — **Adafruit IO** authenticated testing techniques (open registration, $25–$150 CVSS bands, no findings — hardened target): Bearer-JWT capture from Playwright network events, AIO key location (`aio-key-modal`), Gmail `+alias` canonicalization trap (use mail.tm for account 2), the full 15-endpoint IO API map via navigate-and-capture, the IDOR matrix pattern, MQTT ACL test with the victim-side close-the-loop rule (QoS-0 publish success ≠ write landed), bytecode `dynamic_actions` injection probe via validation-status differential, trigger schema (`lt`/`gt`, no webhook action), volcano Zen Cart admin notes, cleanup discipline.
- `references/loopscale-2026-10-engagement.md`
  bytefederal.com bounty $50–$20K): brief + full surface map; ByteAuth QR-login ecosystem
  white-box (byteauth-laravel + byteauth-nextjs public on GitHub — webhook handlers, the
  `isset($data['email'])` binding-check shape); FastAPI "Global Id" (apikey enforced &
  validated, openapi.json + /test exposed); KYC Astro SPA (Turnstile + FaceTec + Persona +
  Plaid, journeyId-as-token IDOR hypothesis, api-register contract); mobileapi DRF money API
  (/v2/locations open, /v2/users/* SMS-OTP gated); portal Next.js (login solid); **live
  unauthenticated MCP server driven over SSE**; split-APK nested extraction + Hermes bundle
  pitfall; Tailscale-IP DNS leak; 6 info-level candidates + honest coverage limits.
- `references/mcp-server-http-audit.md` — **driving an unauthenticated MCP server over
  HTTP/SSE**: GET /sse → `data: /sse?sessionId=...` → POST JSON-RPC ke URI itu
  (initialize → notifications/initialized → tools/list → tools/call); tool-IDOR shape
  (sequential numeric IDs), injection shapes pada free-text tool args, cross-session posting,
  dan kapan server tool stateless-publik = verified negative (bukan temuan).
- `references/bytefederal-2026-10-engagement.md` — **Byte Federal** (Bitcoin ATM operator; 11 rounds,
  no payable finding). Full gate map (wallet = mobile-app-only registration; KYC = SMS+Turnstile+FaceTec;
  fastbyte = app ECDSA), verified-negative list (subzy FP on CF IPs, origin hunt, smuggling, CORS, WP, MCP),
  and the single blocker for re-engagement (one SMS-receivable test number).
- `references/loopscale-2026-10-engagement.md` — **LoopScale** (Solana lending; `tars.loopscale.com` API + `case.loopscale.com` services): Mintlify recon playbook (`llms.txt` → `.md` page twins → `api-reference/openapi.source.json` = full 126-endpoint spec), the empty-body auth-map probe (`scripts/api_auth_map.py`) + error-message differential for auth-header discovery, the `User-Wallet` **presence-only BOLA class** on Solana dApp backends, codama IDL signer scan, live market-config anomaly analysis; 4 findings (1M/3L) + verified negatives. Rounds 2–3 appended: open-RPC discovery (`rpc.loopscale.com`), **LS-05 single-key upgrade authority vs documented 3/5 multisig** (programdata bytes 4–36 / 12–44), BEAM NAV-oracle account decode (152-B entries, 18-dp prices, single pusher key), 40/42 instruction co-sign map, loan health scan (clean), Squads-created test loans, web/marketing/injection negatives.
- `references/altcha-antifraud-and-token-rotation-testing.md` — **reusable technique bank**: ALTCHA PoW reverse-engineering + offline solver (nonce-bytes + big-endian uint32 counter as PBKDF2 password; the two payload formats; the error ladder), fingerprint-vs-IP anti-fraud triage ("Detected as spam" on every egress = browser-fingerprint check → escalate to real Chromium; 429+Retry-After = per-IP throttle), rotating-token API testing from inside the browser page context (`Authorization: Token` + `credentials:'include'`, ~10-request token life, batch/re-login pattern), and the Windows Playwright host fixes (executable_path, backtick-in-evaluate, MSYS paths).
- `references/djangoeurope-2026-10-engagement.md` — **djangoeurope** (Django hosting panel, DRF API + Angular SPA, no published program): DRF root endpoint enumeration, lazy-chunk harvesting (17 chunks = the real feature surface), ALTCHA + anti-fraud registration bypass, **DE-08 email-change-without-verification ATO** (PATCH /email/{id}/ applies unverified address as login identity), SMTP VRFY/RCPT enumeration, PayPal IPN verification control, full IDOR/RCE negative ledger, and the Gmail-token int-expiry fix.
- `references/hivenet-2026-10-engagement.md` — **Hivenet** (send.hivenet.com / app.hivenet.com / console.hivecompute.ai; privately managed, e-mail-only, low reward ceiling): full backend map, the `PBKDF2(name, rootMid)` folder-key model that makes every Send link a capability, three findings (legacy v1 record create missing authz → cross-tenant write; chunks never deleted and no delete route → delete/expiry is UI-only; `POST /metadata` accepts a foreign shareRecordId → vendor e-mail relay + sender spoofing + third-party decrypt), the chains that died, and the IMAP-window / Playwright-Auth0 pitfalls that produced false negatives.
- `references/bytefederal-2026-10-engagement.md` — **Byte Federal** (Bitcoin-ATM operator; 10 rounds, no payable finding — technique bank): Livewire auth-component driving (magic-link/QR; `fill()` doesn't sync `wire:model`, scripted `/livewire/update` needs live snapshot + plain `_token`), KYC API contract mapping via 400/401/422 differentials and pydantic field leaks, presence-only header checks vs encrypted vendor payloads (FaceTec), origin hunting behind CDN (DNS categorization, Host-header probing, bare-IP DB port scans), RN split-APK + Hermes secret mining, and the honest-negative ledger discipline.
- `references/moneta-2026-10-engagement.md` — **MONETA Money Bank** (email-only, no platform, no test
  accounts): the "(no subdomains)" scope wrinkle, the ≤100-requests rate-limit cap, the HoF dedupe list,
  Liferay DXP + Spring "openapi" + F5 ASM stack, the 16-endpoint unauth surface that is the whole
  reachable attack surface, the QR-login entropy/oracle analysis, the `/testing/*` soft-guard sweep, the
  valid rotating pin set, and the APK FPs (debug menu is `visibility="gone"`; deep-link WebView is
  phishing-only because the JS bridge needs `arg_script_file`). Read before any moneta re-hunt — it
  records 6 hours of verified negatives.
- `references/spring-gateway-route-oracle-and-spa-api-map.md` — **Spring "openapi" gateway + React SPA
  banks/fintechs**: `config.json` (`API_URL`, `FEATURE_FLAGS`) before the bundle; the bundle regex that
  yields 364 real API calls out of 1840 quoted strings; the three-way **route-existence oracle**;
  Jackson error messages as a free request schema; the F5 ASM uniform-block-size ffuf fix
  (`-fs` + `-fr "No static resource"`, else ffuf invents fake hits); capture-the-contract-with-Playwright
  after param guessing fails; katana gating and the "grep a killed crawl's tail" rule.
- `references/proton-2026-10-engagement.md` — **Proton** (proton.me product family, report to security@proton.me): explicit in-scope host list (unlisted subdomains = OUT), the **API auth triple** (`Accept: application/vnd.protonmail.v1+json` + CURRENT `x-pm-appversion` + `Bearer` AND `x-pm-uid` — a stale appversion returns 422 "web page out of date", which is an APPVERSION error not a session error; capture the app's real headers via a Playwright request listener), the **session-fork flow** and FINDING F1 (unauthenticated `GET /api/auth/v4/sessions/forks/{selector}` issues full-scope AccessToken+RefreshToken; the URL-fragment `sk` is never required; validated 4x, SUBMITTED 2026-10-21 + auto-acknowledged, triage queue slow/prioritizes critical), the signup wizard path (real username input inside the anti-fraud iframe, ProtonCAPTCHA jigsaw blocks automation → headed-browser manual-solve handoff, login has no captcha, disposable domains blocked, repeat attempts escalate to a SILENT form block), the round-2 wallet API map (path-variant transactions endpoint, PGP-encrypted tx metadata, client-side signing; the `XxxID`-vs-`XxxId` wire-casing lesson), and verified negatives (Lumo guest AI limits enforced, Pass public_link API tight, SN version-gate, headers/CORS clean, nuclei all info-level). **Round 4 (2026-10-25) adds FINDING P-01 — unauthenticated SSRF in Lumo via `tools[].function.parameters.$ref` (submitted; schema-validity oracle, redirect-following, RFC1918 timing classifier, cloud-metadata all filtered), the signup off-screen `#username` decoy that blocks self-provisioning, SimpleLogin now ACTIVATED (`Authentication: <api_key>`; activation is `{email,code}`), and the SRP public-link contract + the "parameter-validation rejection is not a brute-force test" trap.** Read before any Proton re-hunt.

- `references/program-header-and-rate-instrumentation.md` — when the policy makes a request header
  (e.g. `X-BugBounty-Researcher`) a CONDITION of authorization: the additive in-process injector
  (`subprocess.run`/`Popen`/`urllib.Request` monkeypatch wired into orchestrator/force-full-execution/
  tool_router/scope_checker), the shell-string injection rules (quoted-path, pipe-segment skip list,
  fail-open direction), the VERIFIED per-tool flag table (`-H` vs `--headers=`; passive tools = N/A),
  the "excessive traffic" one-line scope-risk-log + GENTLE-mode rule, and the report-side effects of
  the policy read (mandatory AI/tool disclosure sentence, excluded classes to drop with reasons).
- `references/program-scope-traps.md` — **read this BEFORE recon on any new program.** Scope follows the FEATURE, not the URL (an OOS path reached through an in-scope API is still parked); sibling BRANDS that "operate independently" are OUT even though they share the group's branding + footprint (Tripadvisor→Viator/TheFork/CruiseCritic/Jetsetter/SeatGuru/HelloReco, plus minority-investment domains like traxo.com — check ownership %, not the name); a parked bug CLASS ("IDOR in property owner features is temporarily out of scope") kills a whole workstream and un-parks later; a "use TEST properties only / never touch live customers" rule is a constraint on your ENTIRE method (place-scoped features like photo-upload cannot be lawfully exercised without the program's test-entity ids — stop and ask, never fall back to a live object); and why a text→markdown extraction of the brief silently drops the hrefs/ids you will need later (keep the raw HTML, re-fetch the brief each session).
- `references/tripadvisor-2026-10-engagement.md` — **Tripadvisor (Bugcrowd)**. The OOS clauses that
  silently eat a session: TAMG brands that "operate independently" (Viator, TheFork, CruiseCritic,
  Jetsetter, SeatGuru, HelloReco) are **OUT**, and **property-owner IDOR is temporarily OOS**. Plus the
  test-property-only rule and why a *name-only* test-property list blocks `/PostPhotos`-style
  place-scoped features (never fall back to a live property), the GraphQL persisted-query model
  (`/data/graphql/ids`, `preRegisteredQueryId`, arbitrary ops blocked = working control, and the
  two-empty-results BOLA trap), the hardened-host table (Jetty cert-gated, Apache 403s, housetrip
  Next.js affiliate), and the owner deliverable rule: **validate ≥3× BEFORE writing the PDF**, then
  then stage report + PDF as a Gmail DRAFT attachment.
  - `references/bytefederal-2026-10-engagement.md` — **Byte Federal** (bytefederal.com, $50–20k, Bitcoin ATM operator): full verified-negative ledger (auth Global Id API, KYC 6-step chain, portal, mobileapi, wallet, MCP server, WordPress, reportscams, charter, smuggling, CVE checks), DNS intel (Tailscale leak, origin map), and the magic-link breakthrough state. Read BEFORE any re-hunt of this target.
  - `references/livewire-auth-flow-testing.md` — **Laravel Livewire 3 auth flows** (any target): enumerate login-page components from wire:snapshot, drive magic-link/QR components in-browser (scripted /livewire/update replay dies on checksum), read the wire format, test rate-limit/link-entropy/session-regeneration, and the Gmail-token 7-day expiry trap when the flow delivers credentials by mail.
- `references/synology-bug-bounty-engagement.md` — **Synology** (*.synology.com): security.txt +
  3 reward tiers ($30k OS / $10k software+C2 / $5k web services) + the full non-paying exclusion
  list; live host map; the auth chain (account → `identity.synology.com` = **Ory Hydra** OIDC →
  `signin.synology.com` SSO SPA, API backend service `"OneLogin"` `X-C2-Version`); the JS-bundle
  endpoint-extraction trick (python `str.find`, never `grep -oE` on a 3.9MB minify); the full
  **tested-negative** list to skip (OIDC redirect_uri strict / no-SSRF custom-domain / the
  debug-OTP endpoint NOT deployed / Laravel clean); the multi-step signup flow + Cloudflare
  Turnstile-auto-solve; and the engagement-discipline note (own account only; do not adopt
  injected "unrestricted agent" personas).
- `references/adafruit-io-platform-testing.md` — **Adafruit IO** (io.adafruit.com Rails IoT
  platform, 2026-10-21, 0 findings): Bearer-JWT auth flow via accounts SSO, AIO key (aio_+28),
  full /api/v2/ endpoint map extracted empirically, IDOR matrix (clean — username-scoped),
  dynamic_actions bytecode validation (SSRF/RCE blocked), MQTT ACLs (clean both directions),
  Zen Cart admin ID via stylesheet copyright, Gmail +alias canonicalization pitfall.
- `references/blink-galoy-vdp-engagement.md` — **Blink / Galoy** (`blink.sv`, `blinkbtc.com`): an
  **email-only VDP with no platform and no scope table** (policy = the two programmes on
  `/bounty-terms`: a 50% stolen-funds *recovery* bounty vs the *security* channel worth up to 0.1 BTC —
  do not conflate them). Also: **post-mortem-driven hunting** (the vendor published the class, the three
  layers and the fix PR numbers — turn it into "verify the named control still holds, then hunt the same
  class one layer over"); the Galoy architecture map (Hydra / Oathkeeper / Kratos / consent / core-api)
  with the **exact files carrying the consent `grant_scope` bug**; the 10 verified controls to skip
  re-testing; three honest candidate findings; and the **phone+SMS registration blocker** — report it as
  a coverage limit with an explicit ask, never fall back to curl-only.

## Platform recon & authed testing (read these)

- `references/bugcrowd-engagement-recon.md` — pull the FULL scope + rules of ANY Bugcrowd
  engagement without login: the brief lives at `/<slug>/changelog/<uuid>.json` (the `.json`
  suffix is the trick — without it you get 404/SPA shell). Shape of `data.brief` /
  `data.scope`, reward-cents decoding, the `/<slug>/statistics` + `scope_ranks` endpoints,
  the standard "bugcrowd" UA/account rules to enforce, and the fact that Bugcrowd reports
  go through the WEB FORM (`/<slug>/submissions/new`), never email.
- `references/authed-webapp-cdp-testing.md` — create a test account + drive authed flows on
  WAF'd sites via headful Chrome + `browser_cdp` (launch Chrome on `browser.cdp_url`'s port;
  Hermes `browser_*` may point at another backend). Includes the duplicate-id / MooTools form
  trap (`getElementById` returns the container DIV — use `querySelector('input[id=".."]')` +
  `Input.insertText`), reCAPTCHA-Enterprise-may-not-block-submit, IMAP verification-mail read,
  state-change/revert hygiene, and the `grep … | head && echo FOUND` false-positive trap
  (exit status is `head`'s — always count matches explicitly before believing a hit).
- `references/multi-account-auth-testing.md` — testing auth/IDOR/JWT across **2+ live accounts
  in one session**. The failure mode that FABRICATES a cross-account ATO: a session helper whose
  account is a module-global `CREDS` dict + auto-relogin-on-401 — after a 300s JWT expires
  mid-analysis the refresh silently re-logs-in as a DIFFERENT account inside the old jar, so
  `/api/me` shows the other user's data. Hard rules: pin creds per Session instance at
  construction, rebuild sessions after any `importlib.reload`, re-login before trusting any
  sudden 401/identity shift, and **clean-room reproduce every identity/authorization finding**
  (fresh process + fresh login + one variable changed). Also: the JWT forgery battery shape
  (alg:none, HS256 key-confusion SPKI/PKCS1 × PEM/DER, kid injection, tampered-sig, expired
  replay — swap in-place in the live jar, restore after each), the cookie-vs-Bearer baseline
  trap, emailed step-up code extraction (newest `internalDate` + decoy-number filter), and the
  IDOR test shape (uniform-error = no oracle; differential = existence oracle; a "not found"
  from BOTH sides with no positive control is UNPROVEN-BENIGN, not a verified negative).
- `references/fintual-2026-10-engagement.md` — **Fintual** (`fintual.cl/.mx/.com/.in`,
  `fintu.al`, `fnt.al`): email-only self-run bounty (`security@fintual.com`), dedup baseline =
  `hall-of-fame.txt`. Architecture: Rails monolith (JSONAPI `/api/*` + GraphQL **`/gql/`**, NOT
  `/graphql`), emailed-code login → 300s RS256 `monolith_token` cookie, MX signup = single-shot
  `/onboarding-mx/api/signup/web` (no verify_email, unlike CL). `/auth/jwt {aud}` allowlist =
  `stocks-broker-mx` only, consumer not in served build. Sequential IDs (users/banks/reserves)
  but correctly scoped; entitlement gate pre-KYC verified; nickname non-unique but zero identity
  function. Honest candidates: MX ToS-consent client-only (Low/compliance), aud-minting
  (unproven). Coverage wall = needs ONE funded+KYC'd+PIN'd account; tooling notes (WAF 403 ≠
  clean, nuclei focused-list beats apex-wildcard, subzy needs `--output` not `--hidepassed`).

- `references/mailcom-2026-10-engagement.md` — **mail.com** (United Internet; discretionary
  reward, scope = authenticated web apps incl. auth systems): **VALIDATED Host-Header Injection
  finding** (`password.mail.com/passwordrecovery/` leaks `srttkn`, `account.mail.com/` leaks
  `jsessionid` to the poisoned host in a 302; reset-link poisoning → ATO path; XFH not trusted;
  3x reproduced) + the reusable **unauth auth-surface hunting pattern** (recovery flow, login
  state machine, OAuth DCR/authorize, Host-header as first probe) for geo-walled targets, the
  DNS-wildcard-vs-real-infrastructure classification, origin-bypass geo-gate test (server-side,
  not CDN header), subzy CF false-positive verification, and pool hygiene (skiff.com dead).

- `references/fastmail-2026-10-engagement.md` — **Fastmail** (email/calendar SaaS, self-hosted
  $100–$5k): signup API contract (`x-trustedclient: Yes`, JMAP 3-element methodCalls, geo-gate
  ID→SMS verified server-side), OAuth DCR (localhost-only + normalization) + authorize passthrough,
  login state machine (410/400 semantics, phl/ams regional), SPA module-map white-box, full JMAP
  data model from proxyWorker. Wall: account needs SMS.
- `references/unauth-surface-techniques.md` — **cross-session playbook**: wildcard-DNS artifact
  classification (group bare IPs before probing), origin geo-gate provenance test (CF-header vs
  server-side), CORS reflection triage (needs ACAC + cookie auth), JMAP/DRF discovery patterns,
  SPA bootstrap module-map white-box, Livewire action driving, SvelteKit `__data.json`, Turnstile
  wall framing, target-switch `_QUARANTINE`+manifest pattern, anti-abuse gate taxonomy.

## Self-hosted / on-premise products (installer or container, not a website)

- `references/self-hosted-onprem-product-audit.md` — **the target is a product, not a hostname**
  (Octopus Server/Tentacle is the worked case). Scope reality check (their exclusions + the paid
  focus areas), the Docker-compose lab recipe with the gotchas that cost hours (DinD kills the
  container → `DISABLE_DIND=Y` on server **and** agent; unpinned master key → cert-decrypt failure on
  recreate; boot looks hung for 10–20 min), the free-licence signup, the **API-as-harness** pattern
  (root-level collection POSTs, required-field errors as the schema, step/Action nesting traps,
  registering the vendor's own agent as a deployment target), and the reusable **log-redaction /
  secret-masking control test matrix** (length boundary sweep → partial reproductions → multi-line
  values → per-surface diff) plus how to attribute the control to a specific in-scope binary.
  Web scanners are **N/A** for this class — say so in the coverage ledger, don't file them as
  "not run".

## Self-hosted / on-prem product targets (SOFTWARE, not a URL)

When the scope table names a downloadable product ("Octopus Server", "Octopus Tentacle") instead of
hostnames, the target is the SOFTWARE and the lab is yours to build. Start here — these load together:

- `references/self-hosted-product-audit.md` — the whole track: scope reality check (the vendor's own
  website is usually OUT), building the lab in Docker, the container pitfalls that eat hours
  (`DISABLE_DIND=Y` or DinD wedges the entrypoint; **pin `MASTER_KEY` + mount `/root/.octopus` or a
  container recreate silently generates a new key and the DB stops decrypting**; `restart:
  unless-stopped`; API keys must start with `API-`), the auth model (API key vs cookie+CSRF), API recon
  from the root `Links` map, the **RBAC + cross-space matrix** (including the 400-vs-403

---

