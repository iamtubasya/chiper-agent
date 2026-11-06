## PHASES 1-3: SCOPE + RECON + ANALYZE (Detailed)

---

    deep-diving. Skipped tool = NO RESULT. The user audits this — produce a tool→result ledger
    including negatives and still-running jobs.
22. **Setiap perubahan state di akun target wajib dicatat, dipulihkan, dan di-disclose** sebelum sesi
    ditutup: nama tampilan yang dipakai sebagai payload, password yang berubah (termasuk efek samping
    permintaan reset), member uji yang dibuat/dihapus, client OAuth yang teregistrasi, file yang terunggah.
    Tulis di `ENGAGEMENT_LOG.md` + `findings.json`, dan sebutkan artefak yang tidak bisa dihapus sendiri
    (mis. DCR tanpa `registration_access_token`) supaya vendor bisa membersihkannya.
23. **Sebelum bilang "sudah deepdive", terbitkan TOOL-COVERAGE LEDGER — bukan narasi.** User menuntut ini
    berulang kali ("sudah deepdive lagi? pakai all tools dan varian attack yg blm dicoba"). Bentuk jawaban
    yang diterima: tabel eksplisit **tool → hasil**, termasuk tool yang BELUM dijalankan dan yang hasilnya
    NEGATIF. Aturan:
    - Setiap ronde "all tools" wajib menyebut tool mana yang baru dijalankan ronde itu dan mana yang
      belum (sqlmap/arjun/dalfox/naabu/gau+waybackurls/kxss/interactsh/ffuf/gobuster/smuggling/cache/
      graphql/dnsReaper/nuclei tag-rotation). Diam soal tool yang tidak dijalankan = overclaim.
    - Untuk target **web3/kontrak**, himpunan tool-nya BEDA dan wajib disebut utuh sebagai tabel
      tool→status: `forge build` per paket, slither per paket (bukan sekali), aderyn, mythril,
      echidna/medusa, halmos/hevm, `forge test`/fuzz, verifikasi source on-chain (Arbiscan/Etherscan),
      simulasi fork. Tool web2 (sqlmap/dalfox/nuclei/ffuf/dll) ditandai **N/A untuk scope kontrak** —
      jangan dihitung "belum dijalankan". Kalau ada tool yang memang tak bisa jalan, tulis alasannya
      satu baris + langkah verifikasi yang dilakukan sebelum menyerah. Triase FP static-analyzer &
      resi economics ada di `references/web3-static-analysis-triage.md`.
    - Negatif itu deliverable: "OOB 0 callback", "smuggling tidak ada desync", "ffuf 0 hit",
      "CORS reflect tapi tanpa impact (auth API-key, bukan cookie)" ditulis apa adanya dengan alasan
      singkat — bukan disembunyikan.
    - Label severity dari tool ≠ temuan: template nuclei bisa bilang `[critical] config-json-exposure`
      padahal isinya cuma site key publik / feature flag. Buka body-nya dan nilai sendiri sebelum
      melaporkan; kalau FP, tulis "FP, sudah diverifikasi" agar tidak dihitung dua kali.
    - Satu varian per kelas: bila `kxss` menandai parameter terpantul, jalankan `dalfox` untuk memutuskan
      XSS — refleksi saja bukan temuan; bila `arjun` menemukan parameter hanya dari perbedaan HTTP code,
      itu heuristik lemah dan tidak boleh diklaim.
    - **Cakupan itu per-artefak, bukan per-klaim.** Di monorepo (mis.
      `packages/{contracts,horizon,issuance,subgraph-service}`), "4 paket di-build" ≠ "4 paket
      dianalisis". Kalau `slither` baru jalan di 1 paket, tulis 3 paket lain sebagai BELUM
      dijalankan dan JANGAN bilang sweep-nya selesai — user menagih ini ("sudah semua tools
      dipanggil dan dipakai? termasuk varian attack?"). Sebelum menyatakan audit tuntas, jalankan
      analyzer yang sama ke SETIAP paket (paket hardhat-only: `--compile-force-framework hardhat`),
      atau nyatakan eksplisit apa yang tersisa. Prinsip yang sama untuk varian attack: sebut per
      kelas mana yang ditest, sebagian, N/A, dan belum — jangan pernah "semua".

24. **JANGAN akhiri turn dengan menu pilihan.** Owner sudah berkali-kali bilang *"jgn nanya2 terus (execute
    first)"*; sesi ini menutup tiga turn berturut-turut dengan "mau opsi A, B, atau C?" dan owner cuma
    membalas notifikasi sistem — artinya pilihan itu tidak pernah dijawab, cuma menunda kerja. Aturannya:
    pilih aksi sisa dengan nilai harapan tertinggi, **kerjakan**, lalu laporkan apa yang sudah dilakukan.
    Sajikan opsi hanya kalau pilihan itu benar-benar butuh keputusan owner (menyentuh akun/uang/scope
    vendor), bukan sekadar lanjut-atau-berhenti.
25. **Sebelum ngaku "deployed ≠ published", verifikasi dulu sampai bytecode.** Sesi ini sempat over-claim
    "source live nggak ada di repo" cuma dari beda **panjang** bytecode — padahal metadata Solidity ikut
    memuat path source, dan ternyata delta aslinya cuma 10 baris yang hidup di branch `deploy/hotfix`.
    Urutan yang benar: bandingkan **code section** (bukan panjang) → cek SEMUA remote branch
    (`git ls-remote --heads origin`) → kuantifikasi dengan `git diff --stat <audited>..<branch> -- contracts/`
    → baru simpulkan. Prosedur lengkap + jebakan metadata + cara pulihkan source live dari
    verifier-alliance ada di skill `live-vs-source-bytecode-forensics`. Output tool yang error sebelum
    diperbaiki BUKAN hasil analisis — jangan pernah dibaca sebagai temuan (mis. log slither/mythril yang
    hasil analisis — jangan pernah dibaca sebagai temuan (mis. log slither/mythril yang gagal compile).

26. **Registrasi yang di-gate identitas (HP+SMS, KYC) = batas COVERAGE, bukan "target bersih".**
    Kalau seluruh surface ber-token terkunci di belakang akun yang cuma bisa dibuat dengan nomor HP asli
    (contoh: Blink — `userLogin {phone, code}`, captcha-gated, tanpa signup email, tanpa testnet, DCR mati),
    jangan (a) turun ke curl-only, (b) bilang "0 temuan", atau (c) mengarang identitas/KYC. Yang benar:
    serahkan **ledger coverage unauth** (tool yang jalan + hasil negatifnya, per kelas), lalu sebut
    eksplisit apa yang akan terbuka dengan satu akun — biasanya justru kelas vuln targetnya (validasi
    consent `grant_scope`, BOLA/IDOR antar-akun, api-keys, alur bayar). Lalu minta SATU hal konkret ke
    operator (nomor HP / akun tes / API key). Ini satu-satunya pertanyaan blocking yang sah di tengah
    engagement — dan jgn tutup turn dengan menu opsi. Contoh lengkap:
    `references/blink-galoy-vdp-engagement.md` §6.

27. **JANGAN diem berjam-jam lalu baru lapor sekali di akhir.** Owner menegaskan ini langsung
   (*"ttp kasih info progressnya, jgn diam aja"*, 2026-10-17). Pada engagement panjang (recon → scan → deep-dive → report), setiap selesai satu langkah nyata (recon mapped, scan kelar, satu kandidat ter-triase, satu blocker ditemukan) → kirim update singkat: apa yang baru dikerjakan, artefak di mana, langkah berikutnya. Update bukan ringkasan akhir: jangan menumpuk 10 tool call lalu bicara sekali. Korelatnya: notifikasi "background process completed" juga layak di-ack singkat, bukan diabaikan total.

30. **Ronde kosong BUKAN alasan berhenti — generate kelas angle BARU.** Owner berulang kali bilang
   *"jangan berhenti sampai dapat temuan"* dan *"deepdive lagi dr angle yg berbeda"* (2026-10-20,
   Byte Federal: 6 ronde). Saat satu putaran sweep habis tanpa temuan, JANGAN laporkan blocker yang
   sama lalu menunggu — inventariskan kelas uji yang BELUM pernah jalan dan kerjakan. Daftar
   pemantik yang terbukti (Byte Federal 6-6 negatif, tapi tiap kelas benar-benar diuji): DNS
   categorization + origin hunt (Host-header ke IP telanjang), subdomain takeover (subzy + verifikasi
   manual), MCP server driving, source review repo GitHub vendor, CVE version-check plugin/stack
   persis, mass-assignment di registrasi, request smuggling, CORS reflection, entry-credential IDOR
   (journey-id/token variants), storage-path enumeration, IVR/TwiML param tampering, AI-chat param
   tampering, LNURL/extension endpoint probe, WP namespace + admin-ajax nopriv sweep. Satu putaran
   = satu tabel ledger tool→hasil (termasuk negatif). Menu pilihan di akhir = pelanggaran rule 24;
   kalau benar-benar butuh satu input operator (nomor SMS tes), sebut sebagai SATU hal konkret, bukan sebagai menu.
   31. **Tiap temuan WAJIB dibawa ke "impact + attacker bisa apa", dan JANGAN keluar dari target yang user
       sebut.** Owner menegaskan berulang kali (2026-10-24, Zenya): *"tiap temuan ad impact dan as attacker
       bisa apa"* dan *"temuan spt 400/500 itu harus kamu kembembangkan"* — oracle / differential / status-code
       mentah adalah LEAD, bukan finding; rangkai jadi attack chain nyata (siapa penyerang, bisa apa, dampak
       ke data/akun) sebelum presentasi. Dan saat owner bilang *"fokus di <target> aja, jgn kemana-mana"*,
       jangan drift ke domain/tenant/trial-search di luar target yang disebut — kalau eskalasi ke impact
       sungguhan butuh aset di luar scope (akun tes, api_key, kredensial), sebut sebagai SATU blocker konkret
       + minta satu unlock; JANGAN bikin akun di sistem produksi pihak ketiga (tenant customer/regulated).
       Kesimpulan "belum terbukti / verified-negative + kontrol yang bekerja" jujur SELALU diterima; over-claim
       tidak. Detail teknik + tabel re-klasifikasi scope: `references/zenya-multitenant-saas-api-enumeration.md`.
   bukan sebagai menu.

28. **Cek STATUS PROGRAM (paused/retired/expired) SEBELUM investasi dalam audit.**
   *"kl program dipause, ganti target"* (2026-10-20, Zora — program paused Aug 2026, reports not
   reward-eligible). Ambil brief dari halaman program LEBIH DULU; kalau status paused/retired/
   expired → jangan bakar waktu di recon/scan/deep-dive, langsung ganti target dari pool
   (kecuali operator eksplisit minta lanjut untuk riset). Aturan yang sama saat baca pool:
   `status` = state program (active/retired/expired), BUKAN audit progress — program `retired`
   di pool = jangan diaudit untuk reward.
29. **CF Bot Management = uniform-403 wall — bedakan respons CF dari respons aplikasi.** Kalau
   ffuf/nuclei mengembalikan 403 dengan UKURAN IDENTIK di semua path (contoh nyata: 5863 bytes /
   668 words di wallet+mobileapi Byte Federal), itu bot-block pada UA default tool — BUKAN temuan

---

   dan BUKAN hasil negatif aplikasi. Fix: ulangi ffuf dengan browser UA
   (`-H "User-Agent: Mozilla/5.0 ... Chrome/131..."`); nuclei yang stall >10 menit di host
   CF-challenged → kill dan catat "stalled on CF-challenged host", jangan tunggu. Turnstile
   (widget CF) juga mengalahkan Chromium headless DAN headed — pola lengkap + cara ekstrak
   kontrak API dari bundle JS meski challenge tak terpecahkan:
   `references/bytefederal-2026-10-engagement.md` §"CF walls".

   **The stall is not CF-specific** (2026-10-26, Hivenet — plain nginx + a React SPA): a broad
   `-severity critical,high,medium -etags dos,fuzz` sweep at `-rl 8` against three hosts sat at ~2% of
   43k template-host pairs after 41 minutes with **zero** output and zero matches. Signal to act on:
   the stats line shows requests crawling and `Matched: 0` — not a slow host, a bad sweep shape. Kill it,
   then rerun per host with a narrow tag set and a hard request timeout
   (`-tags exposure,misconfig,cve,default-login -timeout 8 -retries 1`), and report the rerun as
   **PARTIAL coverage**, never as "clean". Pair this with the same discipline on ffuf: **filter by
   STATUS, not by size, on JSON backends.** `-mc all -fs 38` against a host whose 404 body is 57 bytes
   returned 89 "hits" that were all 404s; a size filter tuned to one host's error page does not
   generalise across a multi-host sweep. Use `-mc 200,201,204,301,302,401,403,500` and read the bodies.

32. **CHAIN every lead to its terminating sink before discarding it — a lead scored in isolation is scored
   wrong.** Operator pushed exactly this after a MONETA run closed with a clean-looking "no findings"
   ("km udh cb lead ny dcek via chain attack?"). Each lead had been judged alone and each looked dead; the
   honest deliverable is a **chain table that names the step where it dies**, not a list of dismissed leads.
   Format that satisfied the challenge (`references/moneta-cz-engagement.md` §Chain analysis):
   ```
   CHAIN n — <entry primitive> -> <hop> -> <sink>
     Step 1 <entry reachable?>              HOLDS
     Step 2 <untrusted value propagated?>   HOLDS
     Step 3 <guard condition>               HOLDS as a condition
     Step 4 <can attacker control the enabling arg?>
              <the grep that proves it>     => DIES AT STEP 4 / UNPROVEN (blocked on X)
   ```
   Worked example: deep link -> WebView with JS enabled -> JS bridge. It looked like ATO. It died only at
   step 4, because `arg_script_file` (the flag that attaches the bridge) had exactly one writer, hardcoded
   `null`, and the fragment-link enum had zero entries pointing at that fragment. Three greps turn a scary
   lead into a defensible negative — and the chain table proves you actually looked.
   Corollary: a chain that terminates at "the server validates it" is **UNPROVEN**, never a finding and never
   a verified negative; name it as the single unproven hop and say which credential would settle it.

33. **Volume honesty: read the telemetry out of the log file before writing the coverage ledger, and never
   write the flattering number.** In the MONETA run I wrote "full nuclei sweep — KILLED at 1% (34k requests
   inappropriate for a bank)". The process log said otherwise: `Requests: 26648/34410 (77%)`, 43m55s,
   0 matches. I had also labelled a run "curated" that loaded **1396 templates** (`cves/2021/*` +
   `cves/2024/*` + exposures/configs), 4221 HTTP connections, 25 minutes. Both were corrected in ADDENDUM
   entries and in `findings.json.request_volume_disclosure` — but the lesson is to not write the number in
   the first place:
   - Before the ledger line, `tail` the run's stderr and quote real counters (`Requests: a/b`, `Matched:`,
     `HTTP connections:`). Never reconstruct from memory or from when you sent the kill.
   - "Curated" has a definition: **~10 templates chosen from the fingerprinted stack**. Loading two whole
     CVE-year directories is a bulk sweep wearing a curated label.
   - For bank / fintech / any target whose policy mentions service availability, do NOT launch a 34k-request
     full-template sweep "to be thorough". Pick templates from the fingerprint (Liferay 7.4, Spring Boot
     openapi, F5 ASM), cap with `-max-host-error` + a hard timeout, and accept that template spraying finds
     nothing on a well-patched stack (0 matches in ~31k requests across this engagement).
   - Disclose total request volume to in-scope hosts in the report artefact even when no clause was broken
     literally. "<100 requests" style clauses usually scope to rate-limit testing; that is not a licence to
     spend 30k requests elsewhere.

34. **Don't kill a crawler before harvesting its tail — and gate it so it can't leave scope.** A `katana`
   run on `www.moneta.cz` wandered onto an out-of-scope sibling (`esg.moneta.cz`) and was killed; the partial
   output file still contained the **only new attack surface found after the initial report** —
   `/unsecured/portal/exchangerate/list` and `.../history/list`, a module family the hand-kept wordlists had
   missed entirely. Fixes: cap with `-d 2` instead of aborting, filter to in-scope hosts, and always `grep`
   the partial output for `/unsecured/`, `/api/`, `.json` before declaring surface exhausted.

35. **When a request parameter name is unknown, capture the real request from the UI — stop guessing.**
   Seven hand-guessed payload shapes for `exchangerate/history/list` all returned the same generic CBL error.
   A 40-line Playwright script (`page.on("request", ...)`, filter on the endpoint substring, dismiss the
   OneTrust overlay first) captured the actual body in one shot:
   `{"exchangeRatesDate":"2026-10-26T01:00:00"}`. The injection verdict then came free: every quote/OR/
   stacked/`${}`/epoch payload was rejected by Jackson with
   `Cannot deserialize value of type java.time.LocalDateTime` — a strictly typed sink, no injection.
   Playwright is not only for SPA reverse; it is the cheapest oracle for API contracts.

## Overclaiming Patterns (10 BANNED)

1. **Critical RCE** padahal command injection ter-block
2. **Account Takeover** padahal hanya bisa akses data
3. **Full data exfiltration** padahal hanya 1 field
4. **Privilege escalation** padahal hanya lihat role
5. **SQL injection** padahal hanya boolean blind
6. **SSRF** padahal hanya internal scan
7. **Business logic flaw** padahal hanya manipulasi quantity 1-2
8. **Mass assignment** padahal hanya tambah field kosong
9. **Authentication bypass** padahal hanya bypass rate limit
10. **Session fixation** padahal hanya fix session sendiri

## Severity Calibration

| Finding Type | Max Severity |
|-------------|-------------|
| CORS misconfiguration | P3 MAX |
| CSRF (no impact demonstrated) | P3 MAX |
| Clickjacking | P3 MAX |
| Open redirect (no chaining) | LOW MAX |
| SSL/TLS weak cipher | INFO MAX |
| Missing security headers | INFO MAX |
| Information disclosure (non-sensitive) | INFO MAX |
| Business logic (quantity 1-2) | P4 MAX |
| Mass assignment (empty field) | P4 MAX |
| Rate limit bypass | P4 MAX |
| Session fixation (own session) | P4 MAX |

## Finding Priority Order

```
IDOR/BOLA > Auth bypass > Priv esc > RCE/SSRF > SQLi > Business logic > Mass assignment > Info disclosure > CORS/CSRF/Clickjacking
```

## Tool Map (by phase)

| Phase | Tools |
|-------|-------|
| 1-2 | subfinder, httpx, naabu, katana, gau, waybackurls |
| 3 | ffuf, dalfox, kxss, nuclei, sqlmap |
| 4 | gobuster, ffuf, dalfox, manual testing |
| 4.5+ | slither, mythril, echidna, medusa, aderyn (web3) |
| 5-8 | finding_gate.py, chain_builder.py, bug-report-delivery |

## Cloudflare-fronted targets (detail: `references/cf-fronted-target-techniques.md`)
- **UA blocker nyata:** ffuf/nuclei UA default -> 403 seragam (size identik) dari CF Bot Management.
  Itu bluff, BUKAN hasil. Ulangi dengan browser UA. nuclei STALL di host CF-challenged -> jalankan
  per-host, batasi waktu, jangan gabung banyak host dalam satu background job.
- **Origin hunt:** klasifikasi IP per kelas (proxy CF vs Tailscale 100.x vs telanjang). CF-fronted
  tak bisa di-bypass lewat IP telanjang + Host-header kalau origin cuma sajikan default-vhost.
- **subzy FP di CF:** "takeover" pada host yang resolve ke IP proxy CF hampir selalu FALSE POSITIVE.
  Cek A-record dulu; takeover asli butuh CNAME ke servis yang bisa di-klaim.
- **Soft rate-limit:** probing berat bisa memicu CF error 1006 per-IP — rampas, bukan temuan.
- MCP host (`/sse`) -> `references/mcp-server-testing.md` · SPA/KYC gate (Turnstile/OTP) ->
  `references/spa-api-discovery-and-gated-flows.md` · Mobile RN/Hermes ->
  `references/mobile-rn-hermes-recon.md`.

## References

- `references/spring-gateway-and-spa-api-mapping.md` — **turn a minified SPA bundle + a Spring-Boot
  gateway into a classified map of the unauthenticated API surface.** The key trick: Spring with the
  static-resource fallback **never 404s** — `"No static resource <path>."` in a 400 JSON envelope is a
  *definitive* "route not deployed" oracle, while `NotNull must not be null`, `missing.userid`,
  `POWER_AUTH_SIGNATURE_INVALID` and `"This endpoint is for testing purposes only."` classify
  OPEN / AUTH / GUARDED respectively. Also: gateway base from the SPA's synchronous
  `./config.json` load, extracting only the ~360 real API calls out of ~1,800 quoted paths by the
  project's request-builder shape (`hD)("/path")`), free DTO walk via successive `NotNull` field
  errors, and the ffuf `-fr "No static resource"` + WAF-block-size pitfalls. Read before probing any
  `/openapi`-style gateway.
- `references/qr-device-pairing-login-audit.md` — **QR / "scan to log in" / device-pairing audit**:
  token entropy split (`<hex>-<counter>`), derivation tests against session cookie / decoded uuid /
  counter / timestamp, the **cross-session polling oracle** (session B polls A's `authenticationId` —
  highest-yield check), `scopeType` tampering that is not a finding unless the authorization outcome
  changes, confirm-without-bind and post-auth session-fixation/replay tests, and how to write the
  "all controls hold" verdict as a deliverable.
- `references/moneta-2026-10-engagement.md` — **MONETA (email-only bank programme)**: scope
  (www + ib only, no subdomains, mobile Smart Banka), the ineligible-list + Hall-of-Fame reading that
  says *the whole unauth periphery is already paid* (host-header, text injection, rate limit, info
  disclosure, Liferay portlet misconfig…), Liferay 7.4 + F5 ASM + Spring `openapi` + Wultra PowerAuth
  stack map, the full OPEN/AUTH/GUARDED endpoint classification, verified negatives not worth

---


---

