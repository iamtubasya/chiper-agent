# rules body 05 (moved out of SKILL.md 20261010_094721 to stay under the 100k char limit)

## ⛔ RULE 39b: A gate must never score its OWN echo — unwrap, then strip scaffolding


**Same session, next failure (2026-10-09).** After RULE 39 fixed the fail-open default, the real
83-record `gated.json` *still* produced 22 PASS — because the records scored were not findings but
**echoes of the gate's own output**, re-ingested from `REPORT-survivors.md`:

```
{"title":"# Vector 4: RCE/SSRF",
 "text":"{\"title\":\"# Vector 4: RCE/SSRF\", \"text\":\"**Target**: …\\n**Tool**: curl\\n**Exit code**: 0\"}",
 "impacts":["code-exec","ssrf"],"impact_score":16,"has_evidence":true}
```

1. **The nested JSON *is counted as proof** — an "actual JSON body" pattern matched the echoed
   record itself; `"impacts":["code-exec","ssrf"]` handed the impact class over for free.
2. **Labels survive JSON encoding** — `**Target** … **Exit code**: 0` sit inside a string, so a
   line-anchored label strip never sees them.
3. **Gate metadata looks like content** — `- impact classes: …`, `evidence present: True`,
   `"text":`, code fences.

Class of bug: **a gate that reads a file it (or an earlier step) wrote will grade its own
scaffolding as signal** — the same family as "skip self-generated sources" (RULE 39 §4) and the
dead-dump trap (RULE 25).

**Rules — before any scoring regex runs, in BOTH gates (`finding_gate` and `triage_gate`):**
1. **`unwrap()`** — if `text`/`evidence` is itself JSON, peel inner keys
   (`text|evidence|description|details|body|poc|repro`) up to 3 levels (handle a list too). Score the
   *original* finding, never the envelope.
2. **Strip labels inline, not just at line start** (`vector N: …` anywhere in a line).
3. **Scrub scaffolding** — drop gate/report metadata lines (`impact score|impact classes|evidence
   present|source|severity|verdict|reasons|drop_flags`), JSON keys (`"title":|"text":|"impacts":`),
   not-a-finding titles (`Ref File`, `Payloads (\d+ loaded)`, `Output`, `Index`,
   `REPORT-WORTHY FINDINGS`, `Survivors`), `read_file(` lines and fences; require **≥60 chars of
   surviving content** or it is metadata, not a finding.
4. **Dedupe + skip self-sources** (`REPORT-survivors.md`, `gated.json`, `survivors.json`).

**MECHANICAL 7-QUESTION GATE (new — `triage_gate.py`, wired as E5 between validate and report):**
the `triage-validation` skill's 7 questions are now **enforced, not advised**. PASS requires **all 7
YES** (Q1 real impact · Q2 proven request/response · Q3 in-scope · Q4 chain reaches · Q5 not
by-design · Q6 not info/hygiene · Q7 not tool-error). Chain:
`gate → survivors.json → validate → triage → passed-findings.json`; **0F reads `passed-findings.json`
ONLY**, and 0 PASS ⇒ an explicit **NEGATIVE report** (not silence, not a fake "no findings" shell —
see RULE 41).

**Control-pair validation (extends RULE 0c):** after any gate edit assert BOTH directions — a junk
corpus must yield 0 PASS, and a real finding (`GET /api/patient/2 → HTTP/1.1 200 … {"ssn":…} another
patient PII, reproducible`) must PASS 7/7. A gate that cannot return 0 is not filtering; one that
fails the real case is over-filtering.

**Related — budget-safe reachability:** an always-on phase lists only what runs *every* engagement;
conditional skills go in `bb-audit-launcher/references/situational-skill-router.md` (condition → skill,
loaded on demand) so ~60 correct-but-unreachable skills stop being list-only without bloating the
120 KB phase budget.

Detail, code, and the measured before/after: `references/mechanical-triage-gate-and-self-echo.md`.

## ⛔ RULE 41: A gate must not block on a CORRECT outcome — and a refusal must still leave a record


**Operator, 2026-10-08.** After every check finally passed, the run still hard-blocked at 0F
because the pipeline had done the *right* thing: 559 candidates → 105 READY → **0 cleared
validation**, so 0F correctly refused to write a report. `final_coverage_gate` then failed on
`0F:report:AUDIT-REPORT.md [NOT_RUN]` — so an honest, fully successful **negative** audit could
never be marked complete. RULE 39 (below) guards against reporting what was not proven; this
rule guards against the mirror failure, a gate that only accepts a run which found something.

**"Nothing found" is a RESULT, not an absence.** Silence is the right output for a *claim*;
it is the wrong output for a *record*. Every terminal branch that returns `None` because it has
nothing to do must instead write a "nothing to do, and here is why" artefact, with real counts.
Otherwise a correct negative is byte-for-byte indistinguishable from a crash — and the gate
cannot tell them apart either. Create the marker dirs it looks for **present but empty + README**,
so "no drafts because no findings" is distinguishable from "the drafting step never ran".

Four questions to run whenever a gate blocks and the run looks fine:

1. **Does the artefact exist on disk right now?** If not, does anything ever WRITE it?
   (`grep -rn "<name>" scripts/`) — a name nothing produces is an unpassable requirement.
2. **Can the thing it demands exist AT THIS PHASE?** A 0D gate demanding 0E-phase skills
   (`triage-validation`, `onchain-finding-verification` → need `findings.json`) is impossible by
   construction. Split the mandate: `loaded-skills.txt` (0D) vs `late-skills.txt` (final gate).
3. **Are all consumers reading the SAME bar?** 0F demanded drafts from `ready-candidates.json`
   (105) while the report used `validated-findings.json` (0) — two bars, so the gate demanded
   drafts for findings the report had already refused to make. `ready` ≠ `validated`.
4. **Does empty mean FAILED, or NOT APPLICABLE?** A boolean written `X > 0 and all(...)` is
   `False` for the empty case. Empty `poc-execution.json` means "no PoC applied" = N/A, not fail.

Also applies to `audit-checkpoint.py` — it carried four of these at once (0B web-recon files on a
contract target, 0F severity/CWE in a negative report, the dead name `candidates.json`, the C4
empty-list trap) in a *different script* from the gate already fixed, which is why they survived
the first pass. When you fix a gate, grep for its siblings.

Measured end state after all of it: `0A→0F`, 0D gate PASS, `final_coverage_gate` PASS,
`audit-checkpoint 33/33`, report = honest negative.
Detail + code: `references/terminal-state-and-phase-appropriate-gates.md`.

**⛔ Corollary — "the negative report EXISTS" is not the same as "it is sendable".** Verified
2026-10-10: the gate chain produced a correct negative report in **851 bytes** and the operator's
next question was *"review laporan"* — because it named the funnel counts but never said **what was
tested**, **why each READY candidate failed**, or **what was out of scope**. Every one of those facts
was already on disk. A negative report is the artefact that gets forwarded and re-read months later;
write it as a deliverable: result → cause → **coverage per class with the artefact cited** →
**per-candidate rejection reason** → **boundary / N-A grouped by reason** → evidence index.
`N/A` is a boundary, never coverage. Full shape + the four gaps:
`references/negative-report-substance.md`.

## ⛔ RULE 40: Target the CANONICAL host — a bare-host 301 turns every path tool into a false-positive machine


Symptom (riello-ups.com.ar, 2026-10-08): the orchestrator was pointed at `https://<bare-domain>`,
which **301-redirects EVERY path** to `https://www.<domain>/<path>`. Result: ffuf/gobuster matched
**every** path (all 301), nuclei/arjun/dalfox produced zero real signal, and gobuster itself printed
*"the server returns a status code that matches ... for non existing urls"* — the entire 0C batch was
noise against the redirect, not the app. Budget burned, no coverage.

Rules:
1. **Resolve the canonical host BEFORE 0A.** `curl -sI https://<host>/` — if it 3xx-redirects to
   another host, run the pipeline at the **redirect target** (usually `www.`), not the bare host.
   Check both `http://` and `https://` variants first.
2. **A 301-to-elsewhere is not a finding by itself** — the real app lives at the target. BUT a 301
   whose `Location` is `http://…` (scheme downgrade) IS worth recording.
3. **Filter cross-domain noise from recon.** On a multi-country site, hreflang / `<link rel=alternate>`
   injects foreign hosts (`*.ru`, `*.it`, …) into katana/gau output — scope the URL list to the
   in-scope host (katana `-fs rdn`, or grep-filter) before feeding variants.
4. When a per-path tool returns *"everything matches"* / wildcard-length warnings, **STOP** — you are
   scanning a redirect, not the app. Re-point and re-run; never "triage" the noise.
5. **Fragile origin ⇒ low concurrency.** Some targets drop connections under modest concurrency
   (a 15-thread nuclei pass briefly knocked riello-ups.com.ar offline). That is *not* something to
   exploit — it is a signal to run serial / 1–3 concurrency for that engagement.

## ⛔ RULE 42: A terse continuation names no target — reconstruct the engagement from DISK first


Messaging-platform operators reply with two-word continuations into a **fresh session with no prior
context** (*"Nggak ada temuan sama sekali ya / Kamu saja yg buat, teruskan ceknya sampai tuntas semua
sisi"*). Do not ask which target, and do not answer from imagination. Four reads settle it:
newest `sessions` row in `%LOCALAPPDATA%\hermes\state.db` (recover the pending ask verbatim) →
newest dir in `_progress/` by mtime → that dir's `TRIAGE.md` + `findings.json` (including the items
the gate **DROPPED**) → `deep-audit-mode.py guard <dir>`.

That last call is the **fastest truth instrument available**: `⛔ BLOCKED — tools-usage.json not
found` is a positive fact about the previous session — the earlier "0 findings / clean" statement
was **never gated**, so the honest report to the operator is *"uji belum tuntas"*, never *"platform
bersih"*. Then `arm` + launch the orchestrator backgrounded into the engagement dir; watch it with
the RULE 0c Corollary-2 termination test, not a narrated log tail. Full recipe, exact Python, and
the pitfalls (incl. the recursive-`find` timeout, and answering the operational question instead of
re-litigating identity/system-prompt content): `references/engagement-identification-from-terse-operator-message.md`.

## Config Requirements


- `context_length`: 1,000,000
- `max_iterations`: 200
- `max_tool_calls`: 300

---
*Created: 2026-09-20 | Updated: 2026-09-26 (RULE 27 multi-session resume; caps →150)*
*Source: User-identified failure modes + overclaiming corrections*

---

### Track web3 WAJIB memuat `defi-exploit-forensics-in-pipeline.md`


Tabel insersi per-fase: **0B** pattern-prior sebelum baca kode → **0C** apa yang dites + bentuk
hasil positif → **0E** cek apakah insiden nyata sudah mendemonstrasikan teknik ini → **0F** tx
hash exploit jadi bukti yang bisa dikutip triager.

**Enforcement (bukan sukarela lagi, sejak 2026-10-07):**
- `loaded-skills.txt` untuk track web3 memuat `defi-exploit-forensics` + `onchain-finding-verification`
  + `live-vs-source-bytecode-forensics` → masing-masing WAJIB punya entri `applied:true` + `evidence`
  di `skill-usage.json`, atau **CHECK 13 FAIL di 0D**.
- Kelas `refs_web3` di `asset-coverage.py` menuntut teknik/case library benar-benar **menembakkan
  ≥1 request** (`reference-usage.json`), atau **CHECK 12 FAIL di 0D**.

### Aturan yang berlaku ke SETIAP track (dari run web3 nyata 2026-10-08)


Empat pelajaran yang lahir dari audit Relay v3 Router — semuanya membuat pipeline **tampak jalan
padahal tidak**. Detail + kode: `references/track-aware-gates-and-run-lifecycle.md`.

1. **Manifest harus track-aware.** Daftar aset wajib yang web-sentris menggagalkan 49/76 aset
   pada target kontrak (subfinder/httpx/nuclei tak mungkin jalan tanpa hostname). `needed_for()`
   = satu-satunya sumber kebenaran; web-only dibuang di track kontrak, SC-only dibuang di track
   web. Uji **dua arah** (web2 PASS, web3-tanpa-corpus FAIL, web3-dengan-corpus PASS).
2. **Exit code ≠ status.** slither/echidna/aderyn/medusa **exit non-zero justru saat BERHASIL
   menemukan isu**. Pakai *completion marker* yang mengalahkan exit code — tapi cek
   `FAILED_USAGE` LEBIH DULU, jangan sampai output `--help` dicap EXECUTED.
3. **Verifikasi APA yang dianalisis**, bukan bahwa tool-nya jalan. `slither` exit 0 dengan
   "6 results" pernah berarti ia menganalisis **library yang salah**. Baca `# COMMAND` di header
   bukti sebelum percaya — terutama sebelum melaporkan hasil **negatif**.
4. **Kill parent ≠ kill cucu (Windows).** `force-full-execution` yang jadi yatim tetap selesai
   dan menulis `force-state=complete` → run berikutnya **skip seluruh fase SC**. Saat re-run:
   kill tree (`/T`) + hapus state + hapus bukti **bersamaan**; menghapus salah satu saja lebih
   buruk daripada tidak membersihkan sama sekali.

**Jangan pernah melonggarkan gate yang FAIL.** Tiga run berturut-turut diblokir dan ketiganya
benar; tiap kegagalan menunjuk cacat nyata di script dan diperbaiki di sumbernya. Gate yang
menolak melaporkan pekerjaan yang tidak dilakukan adalah **fiturnya**, bukan bug.

### ⛔ Checklish aset WAJIB track-aware — kalau tidak, target kontrak gagal palsu


Terbukti 2026-10-08 pada run relay.link: manifest-nya **web-sentris**, jadi target **kontrak-only**
(0x…) dituntut `subfinder/httpx/nuclei/ffuf/dalfox/…` yang mustahil jalan tanpa hostname →
**49 dari 76 aset NOT_RUN → 0C FAIL**, padahal tidak ada yang salah dengan targetnya.

Aturan yang berlaku sekarang (`asset-coverage.py`):

| track | 0B recon | 0C tools |
|---|---|---|
| **web** (domain/URL) | subfinder, httpx, katana, gau, … (seperti biasa) | nuclei, ffuf, sqlmap, dalfox, … |
| **web3/kontrak** (`_is_web3()` dari `run-meta.json:tech`, fallback file `.sol`) | **0 aset** — semua web-only di-set N/A, bukan FAIL | **wajib `slither`, `aderyn`, `myth`, `echidna`, `medusa`** |

`WEB_ONLY` = aset yang tak ada artinya tanpa host → di-skip pada track kontrak. `SC_ONLY` =
tools SC → di-skip pada track web (jangan sampai audit web2 dituntut slither).

**Pelajaran umumnya:** setiap kelish aset di manifest harus punya jawaban untuk pertanyaan
*"bisakah ini jalan di SEMUA tipe target yang pipeline terima?"* Kalau tidak, ia akan jadi
**false-FAIL** — dan false-FAIL sama merusaknya dengan false-PASS, karena auditor akan
terbiasa mengabaikan gate.

### ⛔ Tool yang exit≠0 karena MENEMUKAN isu bukan "error"


`force-full-execution.py` sempat menilai status dari exit code saja, sehingga run
slither yang **berhasil menemukan 68 isu** dicatat `RAN_WITH_ERROR`. Analyser kontrak
memang keluar non-zero justru saat bekerja:
slither (ADA deteksi), echidna/medusa (assertion GAGAL = temuannya), aderyn.
Fix: `_SC_DONE_MARKERS` — marker penyelesaian (`analyzed (`, `result(s) found`,
`running 88 detectors`, `report printed`, `total calls`, `assertionfailed`,
`test(s) passed`, `test summary`, `fuzz: elapsed`, `analysis was completed`)
**mengalahkan** exit code dan menetapkan `EXECUTED`.

Jangan pernah menyimpulkan "tool gagal" dari exit code pada analyser — cari marker
penyelesaian di body bukti, dan pastikan `# COMMAND:` menunjuk file yang benar.

## ➕ Additive companion — `autonomous-exploration` (optional sidecar)


> Purely additive. Nothing above changes. These tools only CREATE files under
> `<target_dir>/_graph`, `/_plan`, `/_traces`, `/_traffic`; they never modify pipeline scripts,
> and the 0A–0F pipeline runs identically with or without them.

- `dualgraph.py` — asset graph + exploration graph + anchors (SQLite); coverage/lineage queries
- `chainplan.py` — dependency-gated step ledger; `next` = the ONLY step you may dispatch now
- `tracestore.py` — cross-step trace exchange (reuse raw observations from other steps/subagents)
- `trafficrec.py` — on-demand mitmproxy recorder (automatic PoC transcript, port 8081)

Load skill **`autonomous-exploration`** when you need queryable coverage, a dependent multi-step
chain, or automatic PoC capture. Optional — a normal run does not require it.

> This is a *tooling sidecar*, not a rule change: the execution discipline above still governs.
> If a rule and a sidecar convenience ever conflict, the rule wins.

---

## ➕ Runtime execution policy (2026-10-10)


Unbounded runs, stall = WARN (never kill), auto-diagnose → auto-fix → **re-run** the tool,
and **no curl fallback** (a vector that cannot run is NO RESULT, never a hand curl).
GENTLE rate envelope + distillation cadence + **§8 multi-product engagements (one product per run,
restart at 0A)** + **§9 reporting cadence (per phase CHANGE only, terse — operator: "knp lama")** +
**§10 neutralising a budget breaks its arithmetic consumers** +
**§11 GENTLE flags belong to GENTLE MODE ONLY — a command written into a script carries NO rate
flags; `apply_gentle` is the single choke point** +
**§12 Windows process triage (MSYS mangles `taskkill /F` → `F:/`; prove a process is STALE via
`CreationDate`+`CommandLine` before killing it, then re-assert your own run survived)**:
`references/runtime-execution-policy-2026-10-10.md`.
Tools: `toolguard.py` (stall) · `autofix.py` (repair+re-run) · `bundle-sync.py` (drift).

## ➕ The "failure that pretends to be a result" family — INDEX (2026-10-10)


The gates can be **all green while the run tested nothing**, and a document can be **honest but
useless**. Before trusting any "0 findings", any gate failure that looks impossible, or any number the
pipeline printed, read `references/coverage-lies-and-report-quality.md`.

It is a **map, not a manual**: eight hard failures in one session were all one shape — *nothing
crashes, a number/status/document looks produced and is wrong*. Each has its own sibling reference
(phantom requirements · unreadable/AV-quarantined evidence · aggregator junk-ingestion · negative-report
substance · gates blocking a correct outcome · gates scoring their own echo); the index tells you which
one to open, gives the one-line discriminators, and records the meta-rule:

> after patching pipeline code, pick the verification bar that matches the change —
> **syntax → import → call → effect** — each bar passed while the next failed.

Cross-reference: when the gates are green but the vectors never reached a real surface (a redirector, a
catch-all, an edge rule), the fix is in `bug-bounty-exhaustive-testing` →
`references/cdn-redirector-signed-url-audit.md`.
`phase-watch.py` (silent phase-transition reporter for the operator).


## ➕ STANDING: deep-dive proaktif + verifikasi 3x (2026-10-10)


JANGAN tunggu diminta. Sebelum payload apa pun: `deep-endpoints.py` menetapkan PERAN host
dan mengenumerasi endpoint NYATA. Sebelum kesimpulan apa pun: `reverify.py` — 3 putaran
independen dari awal (kandidat DAN kesimpulan). Kandidat yg tak bereproduksi = UNSTABLE,
tidak boleh dilaporkan. Bukti destruktif = di luar batas; karakterisasi aman + nyatakan
eksperimen yg vendor bisa jalankan. Detail: `references/runtime-execution-policy-2026-10-10.md` §13.
