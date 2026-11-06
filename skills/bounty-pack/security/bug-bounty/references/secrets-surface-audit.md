# Auditing a product's secret-handling surfaces

From auditing a self-hosted deployment product's masking pipeline (Octopus Deploy, 2026-10).
The finding was real; this file is the *method*, which generalises to any product that stores and
emits secrets: CI/CD, secret managers, deployment tools, log aggregators, note/task apps with
"private" fields.

## The surfaces — check all six, not just the obvious one

A secret set as "sensitive" can escape through any of these. Most audits only check the first.

1. **Job / task / build logs** — the obvious one, and where masking lives.
2. **Preview / expand / interpolate endpoints.** Many products have a UI feature that resolves
   `#{Variable}` or `${VAR}` and shows the result. Check whether it masks. (`GET .../variables/preview`
   returned `"Value": "********"` for the sensitive var and the real value for the non-sensitive one
   — correct, and worth recording as a verified negative.)
3. **Interruption / approval / notification payloads.** A "please approve access" screen may embed
   the resolved value in the JSON the UI renders.
4. **Exported and rendered artifacts.** Anything the product writes out for the user.
5. **The storage layer**, if you have any access (DBA, backup, `/data` volume).
6. **The product's OWN logs** — the server/agent containers, not the user-facing task log. Grep them
   for every secret literal used during the engagement. This surface is usually forgotten.

## Masking-engine audit: partial matches are where it breaks

Masking that matches **whole values** fails on anything that appears transformed. This is not a
corner case — it is precisely how the most important secret types are stored and emitted:

- **PEM private keys**, GCP service-account JSON, kubeconfig, `.env` blocks, multi-line tokens —
  all multi-line, so they practically never appear whole in a log line.
- Truncation: `head -n 1`, `cut -c1-20`, substring in an error message, value embedded in a larger
  string (`x<secret>y`).

Test with a marker set built for this, not one value:

| Probe | What it catches |
|---|---|
| value lengths 1, 2, 3, 4, 8, 16 | minimum-length threshold in the masker (a real one: `< 4` skipped entirely) |
| single-line sensitive value | baseline |
| multi-line value, echoed whole | baseline |
| multi-line value, `head -n 1` / `tail -n 1` / `head -n 2` | per-line leakage — the big one |
| value embedded in surrounding text | boundary/anchor bugs |
| `cut -c1-N` of a long value | truncation leakage |
| 40-line value echoed | scale of the leak |

Also probe the mechanism, not just the behaviour: read the masker's source if available. In this
audit the root causes were visible in the source (`instance.Length < 4 → continue`; a deferred-action
queue that emits a partial match buffer **raw**), which upgraded the report from "I observed X" to
"here is why".

## Proving encryption-at-rest without trusting the docs

Never assert "secrets are encrypted at rest" (or the opposite) from documentation. Plant a known
marker and go look:

```sql
-- 1. write a uniquely-identifiable plaintext marker through the product's own API
--    (e.g. a variable named DbProbeSecret = 'DBPROBESECRET-5f3a9c21', marked sensitive)
-- 2. then search the storage layer for the literal
SELECT CASE WHEN JSON LIKE '%DBPROBESECRET-5f3a9c21%'
            THEN 'PLAINTEXT' ELSE 'encrypted-or-absent' END FROM VariableSet WHERE ...;
```

Then read the stored form to classify it:

- `"Value":"Dix6sqvsRPcK3HXXDVI8ZlutqZ93iTpfdVe/lcYQVHA=|kR6yybN8iWQLFQ+orn1R3g=="` → base64
  `IV/tag|ciphertext`, i.e. genuinely encrypted. Compare against the **non-sensitive** value, which
  should be plaintext — that contrast is what proves the sensitive path is deliberate.
- Check credentials in their own table: `ApiKey.ApiKeyHashed = PBKDF2-SHA256$3E8$salt$hash` is
  correct; a raw key appearing literally is a finding. Confirm by searching for the key you just
  minted.

Sanity-check the search itself. A first sweep returned "not literal" for *both* probes (including a
value that later turned out to be plaintext) — the query was wrong, not the product. Re-run the
check against the non-sensitive control until it reports what you know to be true, then trust the
sensitive result.

## Honesty rules for this class

- **An empty table is "cannot assess", never "clean".** Two secret-bearing tables
  (`KubernetesExecutionSensitiveValues`, `PlatformHub.ProcessTemplateSensitiveParameterValue`) had
  zero rows — nothing to judge. Write it that way; do not fold it into a pass.
- **Secrets-at-rest behind DBA access is often not the finding you think.** Note the access path
  needed and let the severity follow the actual exposure.
- **A fail-open handler is a note, not a claim.** The masker's `catch { action(raw); }` emits
  unmasked text on any exception. Real defect, but if you cannot construct an input that triggers
  it reachably, record it as defense-in-depth — do not present it as an exploitable finding.
- **A control that exists but is void still needs stating.** "Exact matching IS enforced, but the
  attacker registers their own value first" pre-empts the rebuttal and is more credible than hiding
  the control.

## Where the finding usually lands

Log/trace exposure of a secret maps to **CWE-532 (Insertion of Sensitive Information into Log
File)** and, on Bugcrowd, to `Sensitive Data Exposure > Disclosure of Secrets`, with the asset
(public vs internal) setting the priority tier. Check the program brief's exclusion list first —
"non-confidential information disclosure" and "descriptive error messages / stack traces" are
commonly excluded and will sink an otherwise valid report.
