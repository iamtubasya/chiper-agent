# Reference: Humanize Gate & Screenshot Standards (BBflow §7)

> Sebelum submit: jalankan report & email lewat humanizer rules.

## Humanize Rules

- **Zero em-dashes (—/–) di prosa.** Pakai koma, titik, atau colon.
- **Active voice** untuk aksi yang diambil.
- Kill collaborative artifacts: no "I hope this helps", no "let me know".
- **Signature: handle only** (mis. "Shaxy"), jangan pernah nama asli.
- Severity/CVSS lines tetep terse.
- **Never invent evidence** — setiap hash, address, number harus byte-identical.

## Screenshot Standards

- **URL bar wajib** di setiap screenshot.
- Annotate **vulnerability point** — jangan kubur di raw JSON.
- **MUST dari live website** — never `localhost`/`file://`/locally-generated HTML.
  Triagers reject local replicas walau data identik.
- Kalau browser nggak bisa load live page (WAF) → pakai `curl` terminal output
  sebagai evidence, dan bilang upfront.
- **Blockchain findings:** screenshot LIVE block explorer (BaseScan/Etherscan/BscScan)
  yang nunjukkin tx hash atau contract, bukan local replica. Tx page, deployed
  contract, dan paymaster/deposit pages = proof terkuat.

## Blockchain CVSS v4.0 (smart-contract / on-chain)

- AV (N) · AC (L) · AT (N) · PR (N) · UI (P) · VC/VI/VA (N/H/L) · SC/SI/SA (N/L/L)
- **VI = High** kalau core invariant break (sybil, nullifier uniqueness, one-person-one-vote).
- **VA = Low** untuk resource drain tanpa chain-wide DoS.