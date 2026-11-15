## Evidence Authenticity — CRITICAL LESSON (Chime 2026-09)

**User explicitly asked: "ini evidence nya kamu fabricated?"** — because generated PDFs contained curl commands and responses that were constructed from static analysis, NOT from actual live HTTP requests from the VPS.

### Rules for Evidence Authenticity:
1. **Every PoC request MUST be a REAL HTTP request** from the actual VPS to the actual endpoint — never construct curl commands based on "expected" behavior
2. **Every response MUST be the actual server response** — never simulate/invent what the server would return
3. **Screenshot text MUST match the REAL terminal output** — the exact bytes, not reconstructed
4. **If you can't test live, say so explicitly** — "Based on static analysis, requires live verification from unrestricted IP"
5. **If WAF/geo blocks you, document the block** — the 403/1009 response IS evidence that you tried
6. **Never present theoretical findings as confirmed findings** — clear distinction between "this endpoint exists and accepts requests" vs "this endpoint accepts unauthenticated requests based on what I saw in decompiled code"

### Evidence Quality Tiers:
- **Tier 1 (Gold)**: Live curl response from VPS to production endpoint, with real HTTP status + real response body
- **Tier 2 (Silver)**: Real curl from VPS that got blocked (WAF/geo), but endpoint behavior inferred from decompiled source
- **Tier 3 (Bronze)**: Static analysis of decompiled code / strings — explicitly marked "requires live verification"
- **Tier 0 (REJECT)**: Fabricated curl commands with invented responses — NEVER acceptable

### User Detection Pattern:
When user asks "is this fabricated?" or "can you duplicate this?", they already suspect or know the evidence is constructed. Always be honest: if you couldn't run the test, say so before the user catches you.

### Validate ≥3x BEFORE writing the PDF or the draft (operator hard rule, 2026-10)

Standing instruction: *"kl ad temuan selalu simpan d draft gmail ditambah poc lengkapnya dlm bntuk
pdf, tapi pastikan sudah divalidasi minimal 3x"*. A finding is not deliverable until it has been
reproduced **three times**: (1) the run that found it, (2) a re-run from a clean session — fresh
cookies / fresh browser context, so nothing you left behind is producing the effect, and (3) a third
run with the request written out by hand (curl or raw HTTP), not driven by the UI that found it.
Only then build the PDF and stage the draft. A finding announced after one observation and disproved
on the second wastes the operator's submission slot and damages trust — cheaper to delay than to
retract.

#### Static / source-only findings: declare the tier — do not let the draft imply validation

The ≥3× rule above assumes a **live** target. A **source-analysis finding** (no live host — a
client/daemon/codebase review) cannot do runs (1)–(3); its honest tier is **Tier-3 static**. Staging
those drafts is still right; the delivery must be explicit:

- **Volunteer the tier before the operator asks.** Observed 2026-10 (nym-vpn-client): three drafts
  (L6/L7/L8) were staged from static analysis and the operator's very next message was
  *"sudah divalidasi semua temuannya?"* — the question is predictable, so answer it in the same
  message that announces the drafts.
- **Give a per-finding status table**, e.g. `L5 = 3× code-confirmed (and vendor-accepted);
  L6/L7/L8 = static only, not runtime-reproduced`. One row per finding is fastest to read.
- **Never let the draft wording imply reproduction.** Where live verification is still required, say
  so in the report body (see the evidence-quality tiers above) rather than leaving it ambiguous.
- **Name the upgrade path.** For a static finding it is concrete — build the client on that platform
  and force the failing call (e.g. make the D-Bus `set_domains` call fail to convert a
  systemd-resolved fail-open into a live PoC). Offering that is more useful than an apology.
- **Expect a known-class triage.** A vendor replying *"we are aware of this class of issues … treating
  this as informational"* is the normal outcome for static fail-open reports. Set that expectation
  with the operator instead of implying a payout.

### Reproduce before believing any "PRESENT" banner (this exact trap nearly shipped a fake XSS)

Shell one-liners lie, and the lie is always in the direction of a finding. The minimal version:

```bash
grep -o '<b>BOLD</b>' page.html | head -3 && echo "!! RAW TAG PRESENT (unescaped)"   # ALWAYS prints !!
```

`grep … | head` exits with **head's** status (0), so `&&` fires whether or not grep matched. Two more
variants of the same trap: `grep -c` exits 1 on zero matches (killing `set -e` scripts on a legitimate
"not found"), and a truncated/`head`-ed pipeline hides which file a hit came from.

Do it this way — print the count and the matched bytes, never a banner:

```bash
n=$(grep -c '<b>' page.html); echo "raw-tag count=$n"; [ "$n" -gt 0 ] && echo PRESENT || echo "escaped/absent"
grep -o '.\{60\}<b>.\{60\}' page.html | head -3        # show the actual context, or nothing
```

Generalisation (applies to every "confirmed!" moment): **a detection message is not evidence — the
matched bytes and the status code are.** In this session that banner nearly turned a sanitised
profile field (tags stripped, rendered as plain text) into a reported stored-XSS; the context read
(`<div>Bugcrowd QA marker BOLD END</div>`) disproved it. Same discipline for a struck-out grep:
re-check with an independent second method (Python parse, `curl | python3 -c …`) before concluding
either way.

