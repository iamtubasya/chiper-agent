# SSRF methodology — prove reachability, then prove the limits

Condensed from the Scribble Maps engagement (2026-10-31), where a public-only SSRF was found
via `POST /api/saml/import-metadata` and `POST /api/oidc/import-metadata`
(`{teamCode, metadataUrl}`). Full detail lives in
`security/scribblemaps-engagement/references/ssrf-and-upload-verification-playbook.md`.

## Order of operations (do not skip to the payload)

1. **OOB first.** `interactsh-client -v -o oob.txt` in the background; read the domain from
   the log. Confirm **both** a DNS interaction and an HTTP interaction, and record both source
   IPs — resolver and egress differ (measured 20.42.77.69 vs 13.72.78.248, Azure).
2. **Three runs, distinct path tags.** One interaction per run, matching timestamps. That is
   the reproducibility evidence the operator requires before anything is submitted.
3. **Extract the oracle.** Compare the error string for a URL that returns 200 against one
   that 401s or times out. Measured pair: `"Failed to parse metadata XML"` (fetched) vs
   `"Could not fetch the metadata"` (failed). The oracle is what makes the finding
   demonstrable rather than asserted.
4. **Attack the private-address filter and report the outcome either way.** Minimum set:
   `127.0.0.1`, `[::1]`, `[::ffff:127.0.0.1]`, `[::ffff:a9fe:a9fe]`, `2130706433`,
   `0x7f000001`, `017700000001`, `127.1`, `0.0.0.0`, `169.254.169.254`, `10.0.0.1`,
   `192.168.1.1`, `240.0.0.1`, `localtest.me`, `127.0.0.1.nip.io`, `10.0.0.1.nip.io`,
   `192.168.0.1.nip.io`. All blocked = public-only SSRF = Low-Medium, and saying so is what
   keeps the report credible.
5. **Credential-carry probe.** Point the URL at auth-required endpoints on the same domain.
   401 to the fetch means no cookie is replayed — a good negative to state.
6. **Record the vendor's own limits** (HTTPS-only, no redirects, timeout, size cap). They set
   the realistic severity ceiling.
7. **Never infer internal reachability.** If a private-resolving hostname and a
   non-resolving hostname produce the same error, reachability is unproven. Write that.

## Pitfall that wastes a round

An SSRF is not automatically High. The difference between a $2,000 report and a dismissed one
is whether the write-up distinguishes *what the server will fetch* from *what the attacker can
read*. Prove the read path (response reflected, parsed, or stored) or state plainly that only
the request path is attacker-controlled.
