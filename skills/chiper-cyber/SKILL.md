---
name: chiper-cyber
description: 'Chiper-cyber router: SQL injection, XSS, IDOR, recon, OSINT, red team, sigma rule, deteksi
  ancaman, forensik, cloud, AD — katalog 143 skill cyber + protokol baca SKILL.md'
origin: chiper-cyber
version: 0.3.5
compatibility:
- chiper
- claude-code
- cursor
- windsurf
references:
- path: ~/.chiper/skills/chiper-cyber/README.md
- path: ~/.chiper/skills/chiper-cyber/SOUL.md
- path: ~/.chiper/skills/chiper-cyber/TOOLS.md
- path: ~/.chiper/skills/chiper-cyber/HEARTBEAT.md
- path: ~/.chiper/skills/chiper-cyber/AGENTS.md
- path: ~/.chiper/skills/chiper-cyber/IDENTITY.md
- path: ~/.chiper/skills/chiper-cyber/CHIPER_TOOLS_BASELINE_2026_07.md
- path: ~/.chiper/skills/chiper-cyber/CHIPER_TOOLS_BASELINE_2026_08.md
- path: ~/.chiper/skills/chiper-cyber/CHIPER_TOOLS_BASELINE_2026_09.md
- path: ~/.chiper/skills/chiper-cyber/docs/tools/full-inventory.md
- path: ~/.chiper/skills/chiper-cyber/references/upstream-sync-protocol.md
---


# CHIPER CYBER — MASTER SKILL DIRECTORY

## 1. Purpose and authority

This file is the master directory and routing layer for the CHIPER Cybersecurity skill collection. It gives the agent a map of the available specialist skills, their intended functions, categories, and filesystem locations.

**This file is not a replacement for any specialist skill.** Every specialist directory has its own `SKILL.md`. The specialist file is the authoritative source for that skill's detailed procedures, prerequisites, tools, workflow, safety constraints, references, and verification steps.

Use this master file to decide **which files to read**. Use the selected subfolder `SKILL.md` files to decide **how to perform the work**.

## 2. Repository layout and path rules

Expected root:

```text
$HOME/.chiper/skills/chiper-cyber/
├── SKILL.md                 # this master directory (file ini)
├── AGENTS.md                # workspace instructions
├── SOUL.md                  # persona & hacker laws
├── README.md                # overview + quick start
├── TOOLS.md                 # tool notes
├── USER.md MEMORY.md IDENTITY.md HEARTBEAT.md TEMPLATE.md CLAUDE.md
├── CHANGELOG.md UPDATELOG.md  # riwayat rilis (gabungan release notes)
├── SKILL_REMEDIATION_LIST.json
├── CHIPER_TOOLS_BASELINE_2026_0{7,8,9}.md
├── references/              # shared references
├── docs/                    # shared documentation
├── validation/              # validation scripts & test resources
├── engagement/              # engagement scope & planning records
├── memory/                  # daily notes (memory/YYYY-MM-DD.md)
├── chronicle/               # monthly/weekly historical records
└── chiper-***/              # 143 specialist skills
    ├── SKILL.md             # authoritative specialist instructions
    ├── payloads.md          # attack payloads
    ├── test-cases.md        # structured test cases
    └── guides/              # deep-dive guides
```

Each skill path in this catalog is relative to `$HOME/.chiper/skills/chiper-cyber/` and has this form:

```text
<skill-directory>/SKILL.md
```

For example:

```text
$HOME/.chiper/skills/chiper-cyber/chiper-web-sqli/SKILL.md
```

If the repository is mounted at a different location, resolve the same relative path from the actual CHIPER Cyber root. Do not assume the current working directory.

## 3. Mandatory discovery and loading protocol

Follow this protocol whenever a request needs one or more CHIPER specialist skills.

### 3.1 Understand the request

Extract the objective, target or technology, requested outcome, scope, authorization, constraints, and expected deliverable. Identify whether the task is research, assessment, implementation, testing, incident investigation, reverse engineering, documentation, or agent engineering.

Do not select a skill from a keyword alone. Interpret the complete request and identify the underlying technical domains.

### 3.2 Find the actual skill directories

Inspect the live filesystem. Enumerate directories matching `chiper-*` beneath this root and check whether each has a `SKILL.md`. The catalog below is a routing index, not proof that a path still exists.

Useful discovery commands (adapt paths and shell syntax to the environment):

```bash
find $HOME/.chiper/skills/chiper-cyber -mindepth 2 -maxdepth 2 -type f -name SKILL.md -print | sort
find $HOME/.chiper/skills/chiper-cyber -mindepth 1 -maxdepth 1 -type d -name 'chiper-*' -print | sort
```

Use the filesystem or file-reading tool available in the current runtime. If shell access is unavailable, use the platform's file search/read capability.

### 3.3 Select a skill set

Classify each candidate as one or more of:

- **Primary** — directly handles the main technical objective.
- **Supporting** — supplies a related specialization needed by the task.
- **Prerequisite** — must be completed or understood before another skill.
- **Verification** — independently checks findings, fixes, or outputs.
- **Reporting** — structures the final evidence and deliverable.

Select the smallest complete set that covers the task. Do not load all skills for an ordinary task. Load multiple skills when the objective crosses domains or when a selected skill requires another skill.

### 3.4 Read the selected specialist files completely

For every selected skill:

1. Open the actual `<skill-directory>/SKILL.md`.
2. Read from the beginning through the end. If the reader returns partial content, continue until the full file has been read.
3. Read YAML/frontmatter, description, triggers, prerequisites, instructions, workflow, constraints, tool guidance, output format, and verification sections.
4. Follow references to required local files, scripts, templates, examples, and shared resources. Read those resources before relying on them.
5. Follow cross-references to other CHIPER skills. Add required skills to the selected set and read their full `SKILL.md` files too.
6. Keep a record of which files were actually opened and read.

**Never execute a specialist workflow based only on its folder name, this catalog entry, a short description, cached memory, or a search snippet.**

If a selected `SKILL.md` is missing, unreadable, truncated, or inaccessible, state that explicitly. Do not claim it was read. Continue only with unaffected work.

### 3.5 Plan, execute, verify, report

Before complex work, create a compact plan containing the objective, scope, selected skills and roles, prerequisites, execution order, tools, expected outputs, and verification method.

Execute the specialist procedures in their stated order. Preserve relevant evidence between stages. Verify important results using the methods required by the specialist skills. Report only operations actually performed and results supported by evidence.

## 4. Skill registry

The entries below describe the intended role inferred from each skill directory name and its specialization. They are discovery hints, not substitutes for reading the actual skill file. The specialist `SKILL.md` may narrow, expand, or correct the summary.

## Reconnaissance, OSINT & Intelligence

### `chiper-recon-osint`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-recon-osint/SKILL.md`
- **Function:** Reconnaissance teknis dan OSINT untuk memetakan target, aset, domain, subdomain, teknologi, serta permukaan serangan.
- **Use when:** Gunakan saat memulai assessment dan mengumpulkan informasi target yang berada dalam scope.

### `chiper-osint`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-osint/SKILL.md`
- **Function:** Open-source intelligence: mengumpulkan, menghubungkan, dan menganalisis informasi dari sumber terbuka.
- **Use when:** Gunakan untuk riset entitas, organisasi, infrastruktur, dan jejak digital.

### `chiper-social-intelligence`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-social-intelligence/SKILL.md`
- **Function:** Analisis jejak dan hubungan sosial dari sumber yang sah dan terbuka.
- **Use when:** Gunakan untuk pemetaan eksposur sosial dan konteks organisasi.

### `chiper-username-profiling`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-username-profiling/SKILL.md`
- **Function:** Pemetaan username dan korelasi identitas digital lintas layanan.
- **Use when:** Gunakan saat username menjadi indikator atau artefak investigasi.

### `chiper-darkweb-intel`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-darkweb-intel/SKILL.md`
- **Function:** Threat intelligence dari sumber dark-web yang dapat diakses secara sah.
- **Use when:** Gunakan untuk memeriksa indikasi kebocoran, ancaman, dan paparan organisasi.

### `chiper-exa-search`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-exa-search/SKILL.md`
- **Function:** Pencarian dan riset berbasis Exa atau sistem pencarian semantik.
- **Use when:** Gunakan saat tugas membutuhkan pencarian web/semantik dan pengumpulan sumber.

### `chiper-deep-research`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-deep-research/SKILL.md`
- **Function:** Riset mendalam, multi-sumber, dan sintesis bukti teknis.
- **Use when:** Gunakan untuk pertanyaan kompleks yang membutuhkan verifikasi silang dan laporan riset.

### `chiper-data-scraper-agent`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-data-scraper-agent/SKILL.md`
- **Function:** Pengambilan dan ekstraksi data terstruktur dari sumber yang diizinkan.
- **Use when:** Gunakan untuk mengotomatisasi pengumpulan data publik atau data yang memang boleh diakses.

### `chiper-red-team-infrastructure`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-red-team-infrastructure/SKILL.md`
- **Function:** Desain dan pengelolaan infrastruktur red-team untuk engagement yang diotorisasi.
- **Use when:** Gunakan saat menyiapkan infrastruktur operasi red-team, redirector, domain, atau komponen pendukung.

## Bug Bounty, Pentest & Vulnerability Research

### `chiper-security-bounty-hunter`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-security-bounty-hunter/SKILL.md`
- **Function:** Alur kerja bug bounty: memahami program, scope, triage, validasi, bukti, dan pelaporan temuan.
- **Use when:** Gunakan saat mengerjakan program bug bounty yang memiliki aturan dan scope eksplisit.

### `chiper-agentic-pentest`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-agentic-pentest/SKILL.md`
- **Function:** Orkestrasi penetration testing dengan agent dan workflow bertahap.
- **Use when:** Gunakan untuk assessment multi-tahap yang membutuhkan koordinasi beberapa spesialisasi.

### `chiper-vulnerability-assessment`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-vulnerability-assessment/SKILL.md`
- **Function:** Identifikasi, analisis, prioritisasi, dan validasi kerentanan.
- **Use when:** Gunakan untuk penilaian kerentanan pada aplikasi, host, jaringan, atau infrastruktur.

### `chiper-security-review`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-security-review/SKILL.md`
- **Function:** Review keamanan terhadap desain, kode, konfigurasi, dan implementasi.
- **Use when:** Gunakan untuk audit keamanan sebelum rilis atau saat meninjau perubahan.

### `chiper-insecure-design`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-insecure-design/SKILL.md`
- **Function:** Analisis kelemahan desain keamanan dan business logic.
- **Use when:** Gunakan saat risiko berasal dari arsitektur, alur bisnis, trust boundary, atau asumsi desain.

### `chiper-exploit-development`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-exploit-development/SKILL.md`
- **Function:** Riset dan pengembangan proof-of-concept eksploitasi dalam lingkungan yang diotorisasi.
- **Use when:** Gunakan untuk memahami atau memvalidasi dampak kerentanan secara terkendali.

### `chiper-patch-to-poc-pipeline`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-patch-to-poc-pipeline/SKILL.md`
- **Function:** Menghubungkan analisis patch dengan reproduksi dan proof-of-concept untuk validasi perbaikan.
- **Use when:** Gunakan untuk memeriksa apakah patch benar-benar menutup kerentanan.

### `chiper-command-injection-advanced`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-command-injection-advanced/SKILL.md`
- **Function:** Analisis dan pengujian command injection pada batas input dan eksekusi proses.
- **Use when:** Gunakan saat input dapat memengaruhi pemanggilan command atau proses sistem.

### `chiper-file-inclusion`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-file-inclusion/SKILL.md`
- **Function:** Analisis local/remote file inclusion dan kelemahan pemuatan file.
- **Use when:** Gunakan saat aplikasi memasukkan file berdasarkan input atau parameter.

### `chiper-concurrency-exploitation`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-concurrency-exploitation/SKILL.md`
- **Function:** Analisis race condition, TOCTOU, dan kelemahan konkurensi.
- **Use when:** Gunakan saat operasi paralel dapat menyebabkan state atau otorisasi tidak konsisten.

### `chiper-protocol-state-exploitation`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-protocol-state-exploitation/SKILL.md`
- **Function:** Analisis kelemahan state machine dan transisi protokol.
- **Use when:** Gunakan saat urutan pesan atau state protokol memengaruhi keamanan.

### `chiper-payload-generation`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-payload-generation/SKILL.md`
- **Function:** Pembuatan payload pengujian yang relevan dengan konteks dan batas scope.
- **Use when:** Gunakan saat workflow spesialis membutuhkan payload uji terkontrol.

### `chiper-verification-loop`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-verification-loop/SKILL.md`
- **Function:** Siklus validasi hasil, reproduksi, pemeriksaan bukti, dan konfirmasi perbaikan.
- **Use when:** Gunakan sebagai lapisan verifikasi untuk temuan atau perubahan teknis.

### `chiper-engagement-manager`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-engagement-manager/SKILL.md`
- **Function:** Manajemen engagement, scope, tujuan, tahapan, risiko, dan koordinasi pekerjaan.
- **Use when:** Gunakan untuk mengatur assessment atau engagement yang terdiri dari banyak pekerjaan.

### `chiper-pentest-reporting`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-pentest-reporting/SKILL.md`
- **Function:** Penyusunan laporan penetration test dengan bukti, dampak, prioritas, dan rekomendasi.
- **Use when:** Gunakan setelah temuan diverifikasi dan perlu disampaikan secara profesional.

### `chiper-post-exploitation`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-post-exploitation/SKILL.md`
- **Function:** Analisis pasca-eksploitasi untuk memahami dampak, akses, dan bukti dalam lingkungan uji yang diotorisasi.
- **Use when:** Gunakan setelah validasi eksploitasi ketika perlu mengukur dampak secara terkendali.

### `chiper-security-misconfiguration`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-security-misconfiguration/SKILL.md`
- **Function:** Identifikasi konfigurasi keamanan yang lemah atau tidak sesuai baseline.
- **Use when:** Gunakan saat menilai konfigurasi host, aplikasi, layanan, atau infrastruktur.

## Web Application & API Security

### `chiper-api-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-api-security/SKILL.md`
- **Function:** Penilaian keamanan API, endpoint, autentikasi, otorisasi, input, dan paparan data.
- **Use when:** Gunakan saat menguji REST, GraphQL, atau API lain.

### `chiper-web-access-control`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-web-access-control/SKILL.md`
- **Function:** Pengujian access control, IDOR/BOLA, privilege boundary, dan isolasi data.
- **Use when:** Gunakan saat memeriksa apakah pengguna dapat mengakses objek atau fungsi yang bukan haknya.

### `chiper-web-auth-bypass`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-web-auth-bypass/SKILL.md`
- **Function:** Analisis kelemahan autentikasi, sesi, token, dan mekanisme login.
- **Use when:** Gunakan saat memeriksa bypass login atau kelemahan pengelolaan sesi.

### `chiper-web-deserialization`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-web-deserialization/SKILL.md`
- **Function:** Analisis insecure deserialization dan risiko pemrosesan objek terserialisasi.
- **Use when:** Gunakan saat aplikasi menerima atau memproses data serialisasi.

### `chiper-web-sqli`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-web-sqli/SKILL.md`
- **Function:** Pengujian dan analisis SQL injection pada aplikasi web dan API.
- **Use when:** Gunakan saat input berpengaruh pada query database.

### `chiper-web-ssrf`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-web-ssrf/SKILL.md`
- **Function:** Analisis server-side request forgery dan kontrol akses jaringan dari server.
- **Use when:** Gunakan saat server mengambil URL atau mengakses resource berdasarkan input.

### `chiper-web-xss`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-web-xss/SKILL.md`
- **Function:** Analisis reflected, stored, dan DOM-based cross-site scripting.
- **Use when:** Gunakan saat input atau data ditampilkan pada konteks browser.

### `chiper-web-xxe`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-web-xxe/SKILL.md`
- **Function:** Analisis XML external entity dan konfigurasi parser XML.
- **Use when:** Gunakan saat aplikasi menerima atau memproses XML.

### `chiper-cms-framework-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-cms-framework-attack/SKILL.md`
- **Function:** Penilaian keamanan CMS dan framework web beserta plugin, tema, modul, dan konfigurasinya.
- **Use when:** Gunakan saat target memakai CMS atau framework yang perlu diuji secara khusus.

### `chiper-browser-qa`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-browser-qa/SKILL.md`
- **Function:** Pengujian perilaku aplikasi melalui browser, alur UI, dan reproduksi masalah.
- **Use when:** Gunakan untuk validasi sisi browser, alur pengguna, dan pengujian QA terkait keamanan.

### `chiper-mobile-app-instrumentation`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-mobile-app-instrumentation/SKILL.md`
- **Function:** Instrumentasi aplikasi mobile untuk observasi runtime dan pengujian perilaku.
- **Use when:** Gunakan saat assessment mobile memerlukan inspeksi proses aplikasi saat berjalan.


### `chiper-aifaceswap-api`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-aifaceswap-api/SKILL.md`
- **Function:** Reverse-engineering API internal sebuah SaaS face-swap berbasis Vue/Element-Plus — memetakan endpoint guest/no-login dan menjalankannya end-to-end dari sisi frontend.
- **Use when:** Gunakan saat menargetkan SaaS yang API-nya tidak terdokumentasi (mis. `aifaceswap.io`).


### `chiper-frontend-api-reverse`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-frontend-api-reverse/SKILL.md`
- **Function:** Merekonstruksi API internal/tak resmi sebuah web app dari bundle JavaScript frontend, termasuk skema signing request (AES/RSA/hash) yang ter-obfuscate.
- **Use when:** Gunakan saat perlu memahami atau menguji API rahasia sebuah aplikasi web dari sisi klien.

## Identity, Directory & Access Management

### `chiper-ad-cs-abuse`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-ad-cs-abuse/SKILL.md`
- **Function:** Analisis risiko penyalahgunaan Active Directory Certificate Services (AD CS).
- **Use when:** Gunakan saat lingkungan Windows menggunakan AD CS dan perlu dinilai konfigurasi sertifikatnya.

### `chiper-ad-ldap-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-ad-ldap-attack/SKILL.md`
- **Function:** Analisis keamanan Active Directory dan LDAP, termasuk konfigurasi serta jalur penyalahgunaan yang relevan.
- **Use when:** Gunakan saat assessment domain Windows atau layanan direktori LDAP.

### `chiper-cloud-identity-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-cloud-identity-attack/SKILL.md`
- **Function:** Penilaian risiko identitas pada platform cloud dan hubungan trust antar akun/tenant.
- **Use when:** Gunakan saat mengaudit identitas, role, token, dan akses cloud.

### `chiper-identity-provider-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-identity-provider-attack/SKILL.md`
- **Function:** Analisis keamanan identity provider, federasi, SSO, dan protokol identitas.
- **Use when:** Gunakan saat menguji integrasi IdP, SAML, OIDC, atau alur federasi.

### `chiper-pam-privilege-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-pam-privilege-attack/SKILL.md`
- **Function:** Analisis keamanan privileged access management dan akun berhak tinggi.
- **Use when:** Gunakan saat memeriksa kontrol akun administrator, vault, dan privileged session.

### `chiper-privilege-escalation`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-privilege-escalation/SKILL.md`
- **Function:** Analisis jalur eskalasi hak akses pada sistem dan aplikasi.
- **Use when:** Gunakan saat pengguna atau proses berpotensi memperoleh hak lebih tinggi.

### `chiper-password-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-password-attack/SKILL.md`
- **Function:** Audit ketahanan password dan mekanisme autentikasi berbasis password.
- **Use when:** Gunakan untuk pengujian password yang diizinkan, kebijakan password, dan penyimpanan kredensial.

### `chiper-secret-management-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-secret-management-attack/SKILL.md`
- **Function:** Audit pengelolaan secrets, token, key, dan kredensial.
- **Use when:** Gunakan saat mencari paparan secrets atau kelemahan lifecycle dan kontrol aksesnya.

## Network, Wireless & Communications

### `chiper-network-pentest`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-network-pentest/SKILL.md`
- **Function:** Penetration testing jaringan, pemetaan layanan, segmentasi, dan validasi kontrol jaringan.
- **Use when:** Gunakan untuk assessment jaringan internal atau eksternal dalam scope.

### `chiper-network-sniffing-mitm`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-network-sniffing-mitm/SKILL.md`
- **Function:** Analisis trafik jaringan, packet capture, dan risiko man-in-the-middle.
- **Use when:** Gunakan untuk inspeksi komunikasi dan validasi perlindungan transport.

### `chiper-network-tunneling-proxy`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-network-tunneling-proxy/SKILL.md`
- **Function:** Analisis tunnel, proxy, routing, dan jalur komunikasi jaringan.
- **Use when:** Gunakan saat memeriksa konfigurasi proxy, tunnel, atau jalur akses.

### `chiper-dns-attacks`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-dns-attacks/SKILL.md`
- **Function:** Penilaian keamanan DNS, resolusi nama, konfigurasi, dan potensi penyalahgunaan.
- **Use when:** Gunakan untuk audit DNS dan investigasi masalah atau risiko DNS.

### `chiper-wifi-pentest`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-wifi-pentest/SKILL.md`
- **Function:** Penilaian keamanan jaringan Wi-Fi dan konfigurasi wireless.
- **Use when:** Gunakan saat melakukan assessment WLAN yang diotorisasi.

### `chiper-bluetooth-rfid-nfc`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-bluetooth-rfid-nfc/SKILL.md`
- **Function:** Analisis keamanan Bluetooth, RFID, dan NFC.
- **Use when:** Gunakan saat menilai perangkat, pairing, komunikasi jarak dekat, atau sistem kartu.

### `chiper-voip-sip-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-voip-sip-attack/SKILL.md`
- **Function:** Penilaian keamanan VoIP dan protokol SIP.
- **Use when:** Gunakan saat mengaudit sistem telepon IP, SIP trunk, dan signaling.

### `chiper-vpn-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-vpn-attack/SKILL.md`
- **Function:** Analisis keamanan VPN, konfigurasi, autentikasi, dan jalur akses remote.
- **Use when:** Gunakan saat menilai gateway VPN atau implementasi akses jarak jauh.

### `chiper-email-protocol-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-email-protocol-attack/SKILL.md`
- **Function:** Analisis keamanan protokol email seperti SMTP, IMAP, dan POP3.
- **Use when:** Gunakan saat memeriksa konfigurasi dan perilaku protokol email.

### `chiper-email-security-deep`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-email-security-deep/SKILL.md`
- **Function:** Audit keamanan email secara mendalam, termasuk autentikasi domain dan proteksi pesan.
- **Use when:** Gunakan untuk penilaian konfigurasi email dan mitigasi spoofing/phishing.

## Cloud, Containers, DevSecOps & Infrastructure

### `chiper-cloud-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-cloud-security/SKILL.md`
- **Function:** Penilaian keamanan layanan cloud, konfigurasi, identitas, jaringan, dan data.
- **Use when:** Gunakan untuk assessment keamanan cloud secara umum.

### `chiper-cloud-native-vuln-research`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-cloud-native-vuln-research/SKILL.md`
- **Function:** Riset kerentanan pada komponen cloud-native dan ekosistem terkait.
- **Use when:** Gunakan untuk menganalisis kerentanan teknologi cloud-native.

### `chiper-container-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-container-security/SKILL.md`
- **Function:** Audit keamanan container, image, runtime, isolasi, dan konfigurasi.
- **Use when:** Gunakan saat workload berjalan dalam container.

### `chiper-kubernetes-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-kubernetes-attack/SKILL.md`
- **Function:** Penilaian keamanan Kubernetes, control plane, workload, RBAC, dan konfigurasi cluster.
- **Use when:** Gunakan saat mengaudit cluster Kubernetes.

### `chiper-docker-patterns`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-docker-patterns/SKILL.md`
- **Function:** Pola implementasi, konfigurasi, dan operasi Docker yang relevan dengan keamanan.
- **Use when:** Gunakan saat membangun, memeriksa, atau memperbaiki workflow Docker.

### `chiper-ci-cd-supply-chain-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-ci-cd-supply-chain-attack/SKILL.md`
- **Function:** Analisis risiko keamanan pipeline CI/CD dan rantai pasok build.
- **Use when:** Gunakan saat mengaudit pipeline, runner, artefak, dan proses deployment.

### `chiper-gitops-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-gitops-security/SKILL.md`
- **Function:** Audit keamanan workflow GitOps, repositori konfigurasi, dan deployment deklaratif.
- **Use when:** Gunakan saat deployment dikelola melalui GitOps.

### `chiper-cspm-casb-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-cspm-casb-attack/SKILL.md`
- **Function:** Penilaian kontrol Cloud Security Posture Management dan Cloud Access Security Broker.
- **Use when:** Gunakan saat mengaudit posture cloud dan kontrol akses layanan cloud.

### `chiper-sase-sse-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-sase-sse-attack/SKILL.md`
- **Function:** Analisis keamanan arsitektur Secure Access Service Edge dan Security Service Edge.
- **Use when:** Gunakan saat menilai kontrol akses jaringan berbasis cloud/SASE/SSE.

### `chiper-storage-san-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-storage-san-attack/SKILL.md`
- **Function:** Penilaian keamanan storage, SAN, dan infrastruktur penyimpanan.
- **Use when:** Gunakan saat mengaudit akses, konfigurasi, dan proteksi sistem storage.

### `chiper-data-platform-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-data-platform-attack/SKILL.md`
- **Function:** Analisis keamanan platform data dan layanan pemrosesan data.
- **Use when:** Gunakan saat menilai data lake, warehouse, pipeline, dan platform data.

### `chiper-edge-computing-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-edge-computing-security/SKILL.md`
- **Function:** Audit keamanan arsitektur dan perangkat edge computing.
- **Use when:** Gunakan saat menilai deployment edge dan proteksi node edge.

### `chiper-edge-computing-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-edge-computing-attack/SKILL.md`
- **Function:** Riset ancaman dan jalur serangan pada lingkungan edge computing.
- **Use when:** Gunakan untuk analisis risiko ofensif terkontrol pada sistem edge.

### `chiper-confidential-computing-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-confidential-computing-attack/SKILL.md`
- **Function:** Analisis keamanan confidential computing dan trusted execution environment.
- **Use when:** Gunakan saat menilai isolasi workload dan perlindungan data saat diproses.

### `chiper-hypervisor-introspection`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-hypervisor-introspection/SKILL.md`
- **Function:** Inspeksi keamanan hypervisor dan observasi virtual machine dari lapisan virtualisasi.
- **Use when:** Gunakan untuk riset virtualisasi dan investigasi runtime VM.

### `chiper-macos-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-macos-security/SKILL.md`
- **Function:** Audit keamanan macOS, konfigurasi sistem, aplikasi, dan kontrol endpoint.
- **Use when:** Gunakan saat target atau workstation menggunakan macOS.

### `chiper-supply-chain-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-supply-chain-security/SKILL.md`
- **Function:** Penilaian keamanan supply chain perangkat lunak, dependency, artefak, dan pemasok.
- **Use when:** Gunakan saat menilai risiko dependency, build, distribusi, dan provenance software.

### `chiper-database-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-database-attack/SKILL.md`
- **Function:** Audit keamanan database, konfigurasi, autentikasi, akses, dan paparan layanan.
- **Use when:** Gunakan saat menilai database dan kontrol data pada sistem yang diotorisasi.

## AI, LLM, Agents & Automation Security

### `chiper-ai-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-ai-security/SKILL.md`
- **Function:** Penilaian keamanan sistem AI secara umum, termasuk data, model, integrasi, dan deployment.
- **Use when:** Gunakan saat sistem AI menjadi objek atau komponen assessment.

### `chiper-ai-agent-framework-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-ai-agent-framework-attack/SKILL.md`
- **Function:** Analisis keamanan framework agent AI, tool invocation, memori, dan orkestrasi.
- **Use when:** Gunakan saat mengaudit framework agent atau aplikasi agentic.

### `chiper-ai-agent-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-ai-agent-security/SKILL.md`
- **Function:** Audit keamanan agent AI, izin, tool access, data boundary, dan perilaku runtime.
- **Use when:** Gunakan saat menilai agent yang dapat mengambil tindakan atau mengakses sistem.

### `chiper-ai-agent-supply-chain-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-ai-agent-supply-chain-attack/SKILL.md`
- **Function:** Analisis risiko supply chain pada agent, skill, plugin, tools, dan dependency AI.
- **Use when:** Gunakan saat memeriksa asal, integritas, dan keamanan komponen agent.

### `chiper-ai-fuzzing`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-ai-fuzzing/SKILL.md`
- **Function:** Fuzz testing untuk komponen AI, model interface, parser, dan integrasi.
- **Use when:** Gunakan saat menguji ketahanan komponen AI terhadap input tak terduga.

### `chiper-ai-safety-redteam-advanced`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-ai-safety-redteam-advanced/SKILL.md`
- **Function:** Red teaming lanjutan untuk safety, policy boundary, dan perilaku sistem AI.
- **Use when:** Gunakan untuk evaluasi ketahanan safety AI dalam lingkungan yang diizinkan.

### `chiper-llm-red-team`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-llm-red-team/SKILL.md`
- **Function:** Pengujian keamanan LLM, prompt handling, data exposure, dan integrasi model.
- **Use when:** Gunakan saat menguji aplikasi berbasis large language model.

### `chiper-mcp-server-patterns`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-mcp-server-patterns/SKILL.md`
- **Function:** Pola implementasi dan keamanan Model Context Protocol server.
- **Use when:** Gunakan saat membangun, mengaudit, atau mengintegrasikan MCP server.

### `chiper-multi-agent-collaboration`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-multi-agent-collaboration/SKILL.md`
- **Function:** Koordinasi kerja antar-agent, pembagian tugas, komunikasi, dan sinkronisasi hasil.
- **Use when:** Gunakan saat beberapa agent perlu bekerja sebagai tim.

### `chiper-multi-agent-runtime-engineering`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-multi-agent-runtime-engineering/SKILL.md`
- **Function:** Desain dan engineering runtime multi-agent, lifecycle, routing, dan eksekusi.
- **Use when:** Gunakan saat membangun atau memperbaiki infrastruktur runtime multi-agent.

### `chiper-autonomous-loops`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-autonomous-loops/SKILL.md`
- **Function:** Perancangan loop agent otonom, kontrol iterasi, stop condition, dan evaluasi.
- **Use when:** Gunakan saat agent menjalankan siklus observe-plan-act-verify.

### `chiper-council`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-council/SKILL.md`
- **Function:** Pola deliberasi atau pengambilan keputusan melalui beberapa agent/role.
- **Use when:** Gunakan saat tugas membutuhkan review multi-perspektif atau konsensus.

### `chiper-continuous-learning`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-continuous-learning/SKILL.md`
- **Function:** Pola pembelajaran berkelanjutan, evaluasi, dan pembaruan pengetahuan agent.
- **Use when:** Gunakan saat sistem agent perlu memperbaiki kualitas berdasarkan hasil terdahulu.

## Reverse Engineering, Malware, Firmware & Binary

### `chiper-binary-reverse`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-binary-reverse/SKILL.md`
- **Function:** Reverse engineering binary dan analisis perilaku program.
- **Use when:** Gunakan saat menganalisis executable atau binary tanpa source code.

### `chiper-reverse-engineering-advanced`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-reverse-engineering-advanced/SKILL.md`
- **Function:** Reverse engineering lanjutan: symbolic execution (angr, KLEE, manticore), decompiler confusion (Hex-Rays, Ghidra), binary diffing (BinDiff, Diaphora), analisis firmware & kode ter-obfuscate (OLLVM, Tigress).
- **Use when:** Gunakan saat menganalisis binary packed/ter-obfuscate, mengotomasi pipeline RE, atau menelusuri teknik APT-grade (Equation Group, Pegasus). Berbeda dari `chiper-binary-reverse` yang bersifat fundamental.

### `chiper-firmware-reverse`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-firmware-reverse/SKILL.md`
- **Function:** Analisis firmware, filesystem image, komponen, dan mekanisme boot perangkat.
- **Use when:** Gunakan saat memeriksa firmware perangkat atau embedded system.

### `chiper-malware-analysis-advanced`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-malware-analysis-advanced/SKILL.md`
- **Function:** Analisis malware lanjutan, perilaku, artefak, dan teknik analisis.
- **Use when:** Gunakan untuk investigasi sampel malware dalam lingkungan terisolasi.

### `chiper-anti-forensics`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-anti-forensics/SKILL.md`
- **Function:** Analisis teknik anti-forensics dan dampaknya terhadap akuisisi serta investigasi bukti.
- **Use when:** Gunakan untuk memahami upaya penghilangan atau pengaburan jejak digital.

### `chiper-digital-forensics`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-digital-forensics/SKILL.md`
- **Function:** Akuisisi, preservasi, pemeriksaan, dan analisis bukti digital.
- **Use when:** Gunakan saat melakukan investigasi forensik digital.

### `chiper-steganography`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-steganography/SKILL.md`
- **Function:** Analisis steganografi dan penyembunyian data dalam media atau format lain.
- **Use when:** Gunakan saat memeriksa kemungkinan data tersembunyi.

### `chiper-hardware-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-hardware-security/SKILL.md`
- **Function:** Penilaian keamanan perangkat keras, antarmuka, komponen, dan trust boundary fisik.
- **Use when:** Gunakan saat assessment melibatkan hardware.

### `chiper-hardware-side-channel-advanced`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-hardware-side-channel-advanced/SKILL.md`
- **Function:** Analisis side-channel tingkat lanjut pada perangkat keras dan implementasi kriptografi.
- **Use when:** Gunakan untuk riset kebocoran informasi melalui karakteristik fisik.

### `chiper-hsm-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-hsm-attack/SKILL.md`
- **Function:** Analisis keamanan Hardware Security Module dan implementasi key protection.
- **Use when:** Gunakan saat mengaudit HSM, konfigurasi, dan integrasinya.

### `chiper-embedded-rtos-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-embedded-rtos-security/SKILL.md`
- **Function:** Audit keamanan embedded system dan real-time operating system.
- **Use when:** Gunakan saat menilai firmware dan perangkat berbasis RTOS.

### `chiper-mainframe-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-mainframe-security/SKILL.md`
- **Function:** Penilaian keamanan mainframe dan lingkungan komputasi enterprise terkait.
- **Use when:** Gunakan saat target menggunakan platform mainframe.

### `chiper-av-edr-evasion`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-av-edr-evasion/SKILL.md`
- **Function:** Analisis perilaku antivirus/EDR dan evaluasi ketahanan deteksi dalam pengujian terotorisasi.
- **Use when:** Gunakan untuk riset validasi deteksi dan pengujian kontrol endpoint; ikuti batasan keselamatan dan scope.

## Mobile, IoT, Automotive, Radio & Physical Systems

### `chiper-mobile-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-mobile-security/SKILL.md`
- **Function:** Audit keamanan aplikasi dan platform mobile.
- **Use when:** Gunakan untuk assessment Android/iOS secara umum.

### `chiper-iot-pentest`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-iot-pentest/SKILL.md`
- **Function:** Penetration testing perangkat dan ekosistem Internet of Things.
- **Use when:** Gunakan saat menilai perangkat IoT, API, jaringan, dan cloud pendukungnya.

### `chiper-automotive-vehicle-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-automotive-vehicle-security/SKILL.md`
- **Function:** Analisis keamanan kendaraan, ECU, jaringan otomotif, dan komponen connected vehicle.
- **Use when:** Gunakan untuk riset keamanan otomotif dalam lingkungan dan perangkat yang diizinkan.

### `chiper-uav-drone-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-uav-drone-security/SKILL.md`
- **Function:** Penilaian keamanan UAV/drone, kontrol, komunikasi, dan komponen pendukung.
- **Use when:** Gunakan saat mengaudit sistem drone secara legal dan terkendali.

### `chiper-sdr-rf-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-sdr-rf-attack/SKILL.md`
- **Function:** Analisis keamanan Software Defined Radio dan komunikasi radio frequency.
- **Use when:** Gunakan saat menguji sinyal dan protokol RF dalam batas izin.

### `chiper-hf-vhf-radio-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-hf-vhf-radio-attack/SKILL.md`
- **Function:** Analisis keamanan komunikasi radio HF/VHF.
- **Use when:** Gunakan saat menilai protokol, perangkat, dan konfigurasi radio yang diotorisasi.

### `chiper-satellite-leo-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-satellite-leo-security/SKILL.md`
- **Function:** Analisis keamanan sistem satelit low-Earth orbit dan komponen komunikasinya.
- **Use when:** Gunakan untuk riset keamanan satelit/LEO.

### `chiper-physical-security-testing`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-physical-security-testing/SKILL.md`
- **Function:** Pengujian kontrol keamanan fisik dan prosedur akses lokasi.
- **Use when:** Gunakan hanya pada lokasi dan aset yang secara eksplisit diizinkan.

### `chiper-game-anticheat-bypass`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-game-anticheat-bypass/SKILL.md`
- **Function:** Analisis keamanan game dan mekanisme anti-cheat dalam lingkungan pengujian yang diizinkan.
- **Use when:** Gunakan untuk riset anti-cheat, integritas klien, dan validasi pertahanan game.

## Telecom, 5G/6G & Critical Infrastructure

### `chiper-5g-telecom-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-5g-telecom-attack/SKILL.md`
- **Function:** Analisis keamanan jaringan telekomunikasi 5G dan komponen inti/aksesnya.
- **Use when:** Gunakan saat menilai arsitektur dan kontrol keamanan 5G.

### `chiper-5g-6g-telecom-attack-advanced`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-5g-6g-telecom-attack-advanced/SKILL.md`
- **Function:** Riset lanjutan keamanan 5G/6G, arsitektur, protokol, dan permukaan serangan.
- **Use when:** Gunakan untuk analisis teknis mendalam pada ekosistem 5G/6G.

### `chiper-ics-fieldbus-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-ics-fieldbus-attack/SKILL.md`
- **Function:** Analisis keamanan protokol fieldbus dan komunikasi industrial.
- **Use when:** Gunakan saat menilai komunikasi perangkat otomasi industri.

### `chiper-scada-ics-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-scada-ics-security/SKILL.md`
- **Function:** Audit keamanan SCADA dan Industrial Control Systems.
- **Use when:** Gunakan untuk assessment defensif pada lingkungan OT/ICS.

### `chiper-cps-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-cps-attack/SKILL.md`
- **Function:** Analisis keamanan cyber-physical systems dan interaksi dunia digital-fisik.
- **Use when:** Gunakan saat sistem digital mengendalikan proses fisik.

## Blockchain, Web3, Cryptography & Payments

### `chiper-blockchain-web3`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-blockchain-web3/SKILL.md`
- **Function:** Penilaian keamanan blockchain, smart contract, wallet, dan aplikasi Web3.
- **Use when:** Gunakan saat mengaudit aplikasi atau infrastruktur Web3.

### `chiper-blockchain-l2-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-blockchain-l2-attack/SKILL.md`
- **Function:** Analisis keamanan blockchain layer-2, bridge, rollup, dan komponen terkait.
- **Use when:** Gunakan saat menilai protokol atau implementasi L2.

### `chiper-crypto-attacks`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-crypto-attacks/SKILL.md`
- **Function:** Analisis serangan dan kelemahan implementasi kriptografi.
- **Use when:** Gunakan saat menilai algoritma, protokol, parameter, atau implementasi crypto.

### `chiper-quantum-crypto-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-quantum-crypto-attack/SKILL.md`
- **Function:** Analisis risiko komputasi kuantum terhadap skema kriptografi.
- **Use when:** Gunakan untuk mengevaluasi dampak komputasi kuantum pada sistem crypto.

### `chiper-pqc-implementation-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-pqc-implementation-attack/SKILL.md`
- **Function:** Audit implementasi post-quantum cryptography dan integrasi algoritmanya.
- **Use when:** Gunakan saat menilai implementasi atau migrasi PQC.

### `chiper-post-quantum-migration-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-post-quantum-migration-attack/SKILL.md`
- **Function:** Analisis risiko dan kelemahan dalam migrasi menuju kriptografi post-quantum.
- **Use when:** Gunakan saat merencanakan atau menilai migrasi PQC.

### `chiper-open-banking-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-open-banking-attack/SKILL.md`
- **Function:** Penilaian keamanan open banking, integrasi finansial, consent, dan API.
- **Use when:** Gunakan saat mengaudit ekosistem open banking.

### `chiper-payment-security`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-payment-security/SKILL.md`
- **Function:** Audit keamanan sistem pembayaran, transaksi, gateway, dan alur finansial.
- **Use when:** Gunakan saat menilai aplikasi atau infrastruktur pembayaran.

## Data Protection, Exfiltration & Detection

### `chiper-data-exfiltration-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-data-exfiltration-attack/SKILL.md`
- **Function:** Analisis jalur dan indikator eksfiltrasi data serta kontrol pencegahannya.
- **Use when:** Gunakan untuk threat modeling, investigasi, atau validasi kontrol data loss.

### `chiper-data-loss-prevention-bypass`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-data-loss-prevention-bypass/SKILL.md`
- **Function:** Analisis kelemahan dan celah kontrol Data Loss Prevention.
- **Use when:** Gunakan untuk menguji efektivitas DLP secara terotorisasi.

### `chiper-detection-engineering`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-detection-engineering/SKILL.md`
- **Function:** Perancangan dan validasi deteksi keamanan, telemetry, serta detection logic.
- **Use when:** Gunakan saat membangun atau meningkatkan deteksi ancaman.

### `chiper-threat-hunting`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-threat-hunting/SKILL.md`
- **Function:** Threat hunting berbasis hipotesis dan analisis telemetry.
- **Use when:** Gunakan untuk mencari aktivitas mencurigakan yang belum terdeteksi.

### `chiper-threat-intel-platform-attack`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-threat-intel-platform-attack/SKILL.md`
- **Function:** Analisis keamanan platform threat intelligence dan alur pemrosesan intelijen.
- **Use when:** Gunakan saat mengaudit TIP, integrasi feed, dan pipeline intelijen.

### `chiper-logging-monitoring`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-logging-monitoring/SKILL.md`
- **Function:** Audit logging, monitoring, observability, dan integritas telemetry.
- **Use when:** Gunakan saat memeriksa kemampuan pencatatan dan pemantauan.

### `chiper-deception-honeypot`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-deception-honeypot/SKILL.md`
- **Function:** Desain dan evaluasi deception technology serta honeypot.
- **Use when:** Gunakan untuk membangun atau menilai sistem umpan dan deteksi.

### `chiper-repo-scan`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-repo-scan/SKILL.md`
- **Function:** Pemeriksaan repository untuk menemukan pola risiko, konfigurasi lemah, dan paparan rahasia.
- **Use when:** Gunakan saat melakukan triage awal terhadap source repository.

## Governance, Safety, Documentation & Operations

### `chiper-eu-ai-act-compliance-redteam`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-eu-ai-act-compliance-redteam/SKILL.md`
- **Function:** Evaluasi risiko dan pengujian red-team terkait kewajiban serta kontrol EU AI Act.
- **Use when:** Gunakan saat menilai sistem AI dalam konteks kepatuhan EU AI Act.

### `chiper-safety-guard`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-safety-guard/SKILL.md`
- **Function:** Penerapan guardrail operasional, pemeriksaan keselamatan, dan batas tindakan agent.
- **Use when:** Gunakan untuk menambahkan kontrol keselamatan pada workflow agent.

### `chiper-article-writing`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-article-writing/SKILL.md`
- **Function:** Penulisan artikel teknis dan dokumentasi berbasis riset.
- **Use when:** Gunakan saat menyusun artikel atau publikasi teknis.

### `chiper-codebase-onboarding`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-codebase-onboarding/SKILL.md`
- **Function:** Memahami struktur codebase, arsitektur, entrypoint, dependency, dan alur kerja proyek.
- **Use when:** Gunakan saat pertama kali masuk ke repository atau proyek baru.

### `chiper-bootstrap`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-bootstrap/SKILL.md`
- **Function:** Inisialisasi lingkungan kerja, konfigurasi awal, dan persiapan proyek.
- **Use when:** Gunakan saat menyiapkan workspace atau sistem baru.

### `chiper-knowledge-ops`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-knowledge-ops/SKILL.md`
- **Function:** Pengelolaan pengetahuan, dokumentasi, indeks, dan alur informasi.
- **Use when:** Gunakan saat merapikan atau mengoperasikan knowledge base.

### `chiper-chronicle`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-chronicle/SKILL.md`
- **Function:** Pencatatan kronologi, perubahan, keputusan, dan aktivitas proyek.
- **Use when:** Gunakan saat menjaga jejak historis dan audit trail.

### `chiper-terminal-ops`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-terminal-ops/SKILL.md`
- **Function:** Operasi terminal, shell, command execution, dan pengelolaan lingkungan CLI.
- **Use when:** Gunakan saat pekerjaan membutuhkan prosedur terminal yang konsisten.

### `chiper-tool-mastery`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-tool-mastery/SKILL.md`
- **Function:** Pemahaman dan penggunaan tool secara efektif, termasuk parameter, batas, dan output.
- **Use when:** Gunakan saat agent perlu memilih atau mengoperasikan tool.

### `chiper-search-first`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-search-first/SKILL.md`
- **Function:** Pendekatan pencarian dan verifikasi informasi sebelum menyimpulkan atau bertindak.
- **Use when:** Gunakan saat informasi teknis perlu diverifikasi melalui sumber yang relevan.

### `chiper-social-engineering`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-social-engineering/SKILL.md`
- **Function:** Analisis dan pengujian kesadaran serta risiko social engineering dalam konteks yang diizinkan.
- **Use when:** Gunakan untuk evaluasi proses manusia dan kontrol anti-social-engineering.


### `chiper-skill-usage-forensics`
- **Location:** `$HOME/.chiper/skills/chiper-cyber/chiper-skill-usage-forensics/SKILL.md`
- **Function:** Mengukur dan mengaudit skill agent mana yang benar-benar dipakai, berapa konteks yang dikonsumsi, dan mana yang dead weight — dari tiga sumber telemetry.
- **Use when:** Gunakan saat merapikan pack skill, menekan biaya konteks, atau memutuskan skill mana yang layak dihapus.

## 5. Cross-domain routing guide

Use these routing patterns as starting points. They are examples, not fixed recipes. Confirm the actual scope and read each selected skill before acting.

| User task / objective | Candidate skills to inspect |
|---|---|
| Web application bug bounty | `chiper-recon-osint`, `chiper-api-security`, `chiper-web-access-control`, `chiper-web-auth-bypass`, `chiper-web-sqli`, `chiper-web-xss`, `chiper-web-ssrf`, `chiper-web-xxe`, `chiper-web-deserialization`, `chiper-vulnerability-assessment`, `chiper-pentest-reporting` |
| API security assessment | `chiper-api-security`, `chiper-web-access-control`, `chiper-web-auth-bypass`, `chiper-web-sqli`, `chiper-web-ssrf`, `chiper-vulnerability-assessment` |
| Active Directory assessment | `chiper-ad-ldap-attack`, `chiper-ad-cs-abuse`, `chiper-identity-provider-attack`, `chiper-privilege-escalation`, `chiper-pam-privilege-attack`, `chiper-pentest-reporting` |
| Cloud security assessment | `chiper-cloud-security`, `chiper-cloud-identity-attack`, `chiper-cloud-native-vuln-research`, `chiper-container-security`, `chiper-kubernetes-attack`, `chiper-cspm-casb-attack`, `chiper-security-misconfiguration` |
| CI/CD and software supply chain | `chiper-ci-cd-supply-chain-attack`, `chiper-gitops-security`, `chiper-supply-chain-security`, `chiper-secret-management-attack`, `chiper-repo-scan` |
| LLM or AI agent security | `chiper-ai-security`, `chiper-llm-red-team`, `chiper-ai-agent-security`, `chiper-ai-agent-framework-attack`, `chiper-ai-agent-supply-chain-attack`, `chiper-mcp-server-patterns`, `chiper-ai-safety-redteam-advanced` |
| Multi-agent system engineering | `chiper-multi-agent-collaboration`, `chiper-multi-agent-runtime-engineering`, `chiper-autonomous-loops`, `chiper-council`, `chiper-safety-guard`, `chiper-continuous-learning` |
| Malware or suspicious binary analysis | `chiper-malware-analysis-advanced`, `chiper-binary-reverse`, `chiper-digital-forensics`, `chiper-anti-forensics`, `chiper-detection-engineering` |
| Firmware or embedded device analysis | `chiper-firmware-reverse`, `chiper-embedded-rtos-security`, `chiper-hardware-security`, `chiper-iot-pentest`, `chiper-binary-reverse` |
| Wireless or radio assessment | `chiper-wifi-pentest`, `chiper-bluetooth-rfid-nfc`, `chiper-sdr-rf-attack`, `chiper-hf-vhf-radio-attack`, `chiper-network-sniffing-mitm` |
| 5G/6G or telecom security | `chiper-5g-telecom-attack`, `chiper-5g-6g-telecom-attack-advanced`, `chiper-network-pentest`, `chiper-protocol-state-exploitation` |
| OT/ICS assessment | `chiper-scada-ics-security`, `chiper-ics-fieldbus-attack`, `chiper-cps-attack`, `chiper-network-pentest`, `chiper-detection-engineering` |
| Blockchain or smart contract review | `chiper-blockchain-web3`, `chiper-blockchain-l2-attack`, `chiper-crypto-attacks`, `chiper-vulnerability-assessment`, `chiper-pentest-reporting` |
| PQC readiness or crypto migration | `chiper-pqc-implementation-attack`, `chiper-post-quantum-migration-attack`, `chiper-quantum-crypto-attack`, `chiper-crypto-attacks` |
| Security incident investigation | `chiper-threat-hunting`, `chiper-digital-forensics`, `chiper-malware-analysis-advanced`, `chiper-logging-monitoring`, `chiper-threat-intel-platform-attack` |
| Security report or technical article | `chiper-pentest-reporting`, `chiper-article-writing`, `chiper-deep-research`, `chiper-verification-loop` |

## 6. Dependency and reference traversal

A selected skill may refer to another skill or supporting file. Treat explicit dependencies as part of the workflow:

1. Resolve the referenced path relative to the referring skill directory unless the skill says otherwise.
2. Confirm that the path exists in the current checkout.
3. Read the referenced material when required by the skill.
4. If it names another `chiper-*` skill, locate and read that skill's complete `SKILL.md`.
5. Continue until all mandatory dependencies are resolved.
6. Distinguish mandatory dependencies from optional related reading.

Do not assume a resource was loaded merely because a path is mentioned. Do not run scripts or commands just because they exist; inspect their purpose and follow the skill's prerequisites and operational constraints.

## 7. Safety, authorization, and operational boundaries

All testing, scanning, exploitation, reverse engineering, and system modification must stay within an explicitly authorized scope. A general request for security research is not permission to target unrelated systems.

Before active operations, establish the authorized assets, permitted techniques, time or rate limits, data-handling restrictions, and potential impact. Prefer non-destructive validation. Avoid persistence, stealth, data extraction, service disruption, or changes to production systems unless specifically authorized and allowed by applicable policy and the selected skill.

If scope or authorization is unclear, ask for the missing boundary before active testing. Continue with safe planning, documentation, or lab-only analysis where possible.

## 8. Conflict resolution

When instructions conflict:

1. Respect higher-priority runtime and repository instructions.
2. Respect the authorized scope and applicable safety requirements.
3. Prefer the most specific specialist instruction for the operation in question.
4. Check whether one skill explicitly declares a prerequisite or specialized extension.
5. Do not silently discard a conflict. If it cannot be resolved, pause the affected operation and report it.

## 9. Failure and incomplete-work handling

If a skill or dependency cannot be read, record its exact path and the reason. If a tool is unavailable, identify the missing capability and any safe alternative. If a command fails, preserve the actual error and distinguish environmental, permission, configuration, and procedural causes where possible.

Never invent tool output, evidence, file contents, or successful execution. Mark incomplete stages as incomplete.

## 10. Execution record for complex tasks

Use this structure for substantial work:

```text
TASK:
  Objective and requested deliverable

SCOPE:
  Authorized targets, boundaries, and restrictions

SELECTED SKILLS:
  skill-directory — primary/supporting/prerequisite/verification/reporting role

LOADED INSTRUCTIONS:
  Exact specialist SKILL.md paths actually read

DEPENDENCIES:
  Additional skills, references, scripts, and templates actually inspected

PLAN:
  Ordered workflow and expected outputs

EXECUTION:
  Operations actually performed and evidence produced

VERIFICATION:
  Checks performed and their results

LIMITATIONS:
  Missing files, unavailable tools, untested assumptions, and incomplete stages

STATUS:
  COMPLETED | PARTIALLY COMPLETED | BLOCKED | NOT STARTED
```

Use `COMPLETED` only when all required workflow stages and verification steps are done. Use `PARTIALLY COMPLETED` when useful work is done but required stages remain. Use `BLOCKED` when a prerequisite prevents safe or reliable progress. Use `NOT STARTED` when only discovery or planning has occurred.

## 11. Maintaining this registry

When a new `chiper-*` directory is added:

1. Discover it from the live filesystem.
2. Confirm that `<new-directory>/SKILL.md` exists.
3. Read its frontmatter and full contents before writing a precise registry description.
4. Add it to the correct category with its exact relative path, purpose, triggers, and useful related skills.
5. Do not remove existing entries simply because they are not visible in an incomplete directory listing.

When a skill is renamed, moved, or removed, verify the filesystem and update this registry. Do not rely on a stale cached list.

## 12. Shared support directories

The following directories are shared ecosystem resources, not `chiper-*` specialist skills unless the repository explicitly defines them as such:

| Directory | Intended role |
|---|---|
| `references/` | Shared technical references and source material |
| `docs/` | Project and ecosystem documentation |
| `validation/` | Validation procedures, test resources, and quality checks |
| `engagement/` | Engagement scope, planning, and operational records |
| `memory/` | Persistent project knowledge and context |
| `chronicle/` | Historical activity, decisions, and change records |

Inspect the actual contents before relying on any of these directories.

## 13. Non-negotiable agent behavior

- Use this master file as the directory and routing index.
- Discover actual directories and files from the current filesystem.
- Select skills based on the full task, not a single keyword.
- Read the complete `SKILL.md` of every selected skill before using its procedures.
- Read required dependencies and references, including cross-linked skills.
- Do not load all specialist skills indiscriminately for ordinary tasks.
- Do not claim to have read files that were not actually accessed.
- Do not treat registry summaries as technical procedures.
- Follow authorization, safety, and operational constraints.
- Verify results and distinguish evidence from assumptions.
- Report selected skills, loaded files, work performed, verification, and limitations for substantial tasks.

## 14. Final orchestration sequence

```text
USER REQUEST
    ↓
UNDERSTAND OBJECTIVE + SCOPE
    ↓
DISCOVER LIVE CHIPER DIRECTORIES
    ↓
USE THIS MASTER REGISTRY TO SELECT CANDIDATES
    ↓
READ COMPLETE SPECIALIST SKILL.md FILES
    ↓
FOLLOW REQUIRED DEPENDENCIES + REFERENCES
    ↓
PLAN AND EXECUTE SPECIALIST WORKFLOWS
    ↓
VERIFY RESULTS
    ↓
REPORT EVIDENCE, STATUS, AND LIMITATIONS
```

**Core rule:** this master file tells the agent what skills exist, what they are for, and where to find them. The individual subfolder `SKILL.md` files contain the authoritative instructions for doing the work. The agent must read those original files before applying their specialist workflows.
