# 02 — Forensic view (a host where the framework ran)

Use these when triaging a suspected relay/transit host. Here static artefacts ARE useful, because a
running deployment is much harder to disguise than a single HTTP request.

## Artefacts worth checking, in order

1. **A local listener serving a management UI** on a non-standard port, bound internally. Ask: does an
   internal host serve a dashboard nobody asked for?
2. **A loopback MITM proxy endpoint**, plus the tell that makes it specific: **a proxy env var
   (`HTTP_PROXY`/`HTTPS_PROXY`) co-occurring with a CA-trust env var
   (`SSL_CERT_FILE` / `CURL_CA_BUNDLE` / `REQUESTS_CA_BUNDLE` / `NODE_EXTRA_CA_CERTS`) on the same
   process line**, pointing at loopback. That combination is far more specific than a bare port.
3. **A generated proxy CA certificate** written by the recorder (typically a `*-ca-cert.pem` under the
   tool's own directory). Note the caveat: the *bare filename* is shared with the stock mitmproxy
   family, so it is a triage lead, not a unique fingerprint.
4. **The tool's own database schema** — a distinctive set of table names that only its store creates.
   Inspect the DB, do not build a network rule for it.
5. **Egress from the host to a code-hosting service** carrying the updater's own UA. Suggests an
   installed binary rather than a compromised browser.
6. **Environment leakage in process listings** (`/proc/<pid>/environ` on Linux) — proxy + CA vars
   together, as in (2).

> ARTEX's own material lists equivalents (`:8787` UI, `127.0.0.1:8788` recorder, an updater UA, the
> dual-graph table set, an audit-log framing string). We do **not** reuse their values; the *shape* of
> the artefact list is the transferable idea.

## Destructive-command hunting (host audit)

Watch command lines for the family an autonomous agent might attempt:

- filesystem destruction: recursive force delete, filesystem creation, raw device writes, secure-erase;
- database destruction: `DROP DATABASE` / `DROP TABLE` / `TRUNCATE`, Mongo `drop`/`dropDatabase`,
  Redis `FLUSHALL`/`FLUSHDB`;
- HTTP destructive verbs: `-X DELETE` on curl/wget.

Keep **data-exfiltration pipes** (`... | nc ...`, `... | curl ...`) as a *separate, heavily tuned*
indicator — they overlap legitimate transfer work and will misfire if blocked outright.
