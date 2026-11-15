## 🏆 GOLD STANDARD REPORT — Zinc/Zootbox Case Study (PATUHI, DITIRU!)

Report berikut adalah **STANDAR EMAS** dari `Zinc_Zootbox_SlotHash_Randomness_HIGH.pdf` + `Zinc_Zootbox_PoC_pack.zip`. Ini yang harus jadi patokan untuk semua bug bounty reports, terutama Solana/on-chain.

### Struktur Report (PDF, 4 page)

```
HALAMAN 1 — HEADER + EXECUTIVE SUMMARY
├── Label: "PRIVATE SECURITY DISCLOSURE"
├── Tagline: 1 kalimat inti vulnerability (e.g. "Game outcomes are decided by a value
│   the block producer controls, not the VRF you advertise")
├── Severity: High (dengan Critical case argument terbuka)
├── Vuln Type: Insecure randomness
├── Target: Contract address + network + deployed slot
├── Scope: "the deployed program bytecode and its live on-chain configuration"
├── Summary: 2 paragraph — (1) technical what, (2) why it matters
└── Blast Radius: Scope dampak — "isolated per box, but repeatable box-by-box"

HALAMAN 2 — SEVERITY JUSTIFICATION + ATTACK STEPS
├── Severity table: Impact / Attacker / What proved / Final call
├── Attack step-by-step: Public info → attacker action → outcome
└── Evidence: Live data from mainnet (config values, tx hashes, account addresses)

HALAMAN 3 — NEGATIVE TESTS + FIX + DISCLOSURE
├── "What I checked and could not break" — table of attempted attacks + results
├── Fix recommendation — concrete, actionable, not vague
└── Disclosure statement — what was/wasn't done, compliance statement

HALAMAN 4 — FOOTER
└── Program info + scope reminder + disclaimer
```

### PoC Pack (ZIP accompanying PDF)
```
poc/
├── README.md              — Plain-English explanation of the finding
├── 1_verify_config.js     — Step 1: prove the insecure config exists (read-only)
├── 2_settle_uses_slothashes.js — Step 2: prove the vulnerable path is actually used
└── 3_authorization_sweep.js    — Step 3: negative tests (what IS properly guarded)
```

### Key Patterns to Copy

1. **Title = one sentence**, states root cause clearly — no jargon, no sensationalism
2. **Severity with honest justification table** — show reasoning, let them decide
3. **"What I proved" vs "What I argued"** — be transparent about proof limits
4. **Negative tests table** — shows thoroughness, prevents "did you check X?" back-and-forth
5. **Read-only PoC** — simulateTransaction, no broadcast, no keys needed
6. **Every claim backed by live data** — specific account addresses, tx hashes, config values
7. **Fix is concrete and actionable** — not "use a VRF" but "set magicblockOracleQueue + require randomnessMode = VRF"
8. **Disclosure statement** — clean, professional, compliance-ready
9. **Blast radius explicit** — honest assessment of scope + repeatability

### Severity Justification Table (Template)
```markdown
| Axis | Reading |
|------|---------|
| Impact | [Total loss description — what's the worst?] |
| Attacker | [Who can exploit? Permissioned or permissionless?] |
| What I proved | [Concrete proof vs theoretical argument] |
| Final call | [Your severity + honest reasoning] |
```

### Negative Test Table (Template)
```markdown
| Attack attempted | Result |
|-----------------|--------|
| [Attack variant 1] | [Guarded/Not guarded + why] |
| [Attack variant 2] | [Guarded/Not guarded + why] |
| [Attack variant 3] | [Guarded/Not guarded + why] |
```

### PoC Pack Structure (Template)
```
poc/
├── README.md                    — Plain English explanation (non-technical summary)
├── 1_verify_config.js           — Prove the vulnerable config/state exists
├── 2_exploit_path.js            — Prove the vulnerable path is actually taken
├── 3_negative_tests.js          — Prove other paths ARE guarded (thoroughness)
└── [additional PoC files]       — If more complex exploit chains needed
```
