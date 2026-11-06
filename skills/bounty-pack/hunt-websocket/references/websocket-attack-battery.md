# WebSocket Attack Battery — CSWSH, authz bypass, message tampering, socket.io/SignalR

Katalog eksekusi cepat untuk `hunt-websocket`. SKILL.md sudah 7 phase detail; di sini battery
berjenjang + kill-signal + fingerprint per framework. Additive-only.

**Prinsip (dari SKILL.md):** CSWSH butuh (a) handshake auth = cookie SESSION tanpa token per-request,
(b) tidak ada Origin check di message layer, (c) authenticated data bisa di-stream. 101 dari foreign
Origin = KANDIDAT biasa, bukan konfirmasi.

---

## Tier 0 — Discovery (WS surface)

```
grep JS:  new WebSocket( | wss:// | io( | socket.io | SignalR | /negotiate
crawl:    /socket.io/ | /ws | /realtime | /signalr | /cable | /hubs
probe:    handshake 101 = upgrade supported (pakai wscat / Burp)
socket.io /socket.io/?EIO=4&transport=polling  → leak version + sid
```

---

## Tier 1 — CSWSH (Cross-Site WebSocket Hijacking)

1. **Confirm handshake auth model** (DevTools → Network → WS → Headers): cari `Cookie: session=...`
   DAN tidak ada token per-request (`?token=`, `Sec-WebSocket-Protocol`, body nonce).
   Ada token unik → CSWSH TIDAK exploit cross-site.
2. **Probe Origin** (`Origin: https://evil.com` → 101 = candidate).
3. **Konfirmasi**: foreign origin BENER membaca frame authenticated (bukan cuma 101).

**Kill-signal:** origin penyerang stream data user lain / invoke action → CSWSH, High/Critical.

---

## Tier 2 — Missing/weak auth pada WS messages (tanpa cookie)

```
tanpa cookie → server proses app frame?  {"type":"getUserData","userId":1}
low-priv session kirim high-priv action:  {"action":"deleteUser","userId":999}
                                          {"action":"getSecretConfig"}
```

**Kill-signal:** action tanpa auth / lintas-privilege jalan → authz bypass di message layer.

---

## Tier 3 — Message tampering (financial/game/checkout)

Intercept + edit (Burp → WebSockets history → Repeater):
```
{"price":100}   ->  {"price":0.01}
{"amount":1}    ->  {"amount":9999}
{"userId":123}  ->  {"userId":1}      # impersonate admin
{"orderTotal":...} -> recompute downstream
```

**Kill-signal:** server percaya nilai yang di-tamper → financial/business-logic bypass.

---

## Tier 4 — socket.io / SignalR / Phoenix namespace & room authz bypass

socket.io (Engine.IO v4) — namespace = PROTOCOL message, BUKAN URL param:
```
WRONG:  wscat -c "wss://T/socket.io/?EIO=4&transport=websocket&nsp=/admin"   # nsp diabaikan
RIGHT:  open socket → kirim CONNECT packet  40/admin,
        server reply 40/admin,{"sid":"..."} (sukses) atau 44/admin,{...} (error)
        masuk namespace → emit EVENT join room user lain:
        42/admin,["join",{"room":"user_999_private"}]
        42["subscribe",{"channel":"admin_events"}]
```

**Kill-signal:** low/no-priv masuk namespace `/admin` / room user lain → 40 sukses = bug.

---

## Tier 5 — Replay signed message & business-logic abuse

- Replay frame lama (signed tapi tidak expire) → action re-execute.
- Rate-limit evasion via WS (counter tak berlaku di channel realtime).
- State machine bypass (kirim event out-of-order).

---

## Tier 6 — Handshake-layer upgrade smuggling (HTTP-layer, BUKAN frame)

```
A) Upgrade valid tapi versi unsupported:  Sec-WebSocket-Version: 777  (origin harus 426)
B) Upgrade header ada tapi Connection: keep-alive (mismatch)
C) Smuggle second request setelah "101", lalu normal follow-up → desynced response
```

**Detect:** Burp Repeater / `send_http1_request`, toggle 1 variabel handshake, bandingkan
front vs origin behavior.

---

## Fingerprint per framework

| Framework | Endpoint | Handshake / namespace |
|---|---|---|
| socket.io (Engine.IO v4) | `/socket.io/?EIO=4` | `40/admin,` CONNECT packet |
| SignalR (ASP.NET) | `/negotiate` + `/hubs/*` | `Sec-WebSocket-Protocol` + Hub method JSON |
| Phoenix Channels | `/socket` + `cable` | `phx_join` topic |
| GraphQL Subscriptions | `/subscriptions` | `connection_init` + `start` (payload query) |
| ActionCable (Rails) | `/cable` | `subscribe` channel |

---

## Validation (dari SKILL.md, diulang cepat)

- CSWSH: 101 dari foreign origin ≠ konfirmasi — bukti = stream data authenticated / invoke action.
- Message tampering: bukti = server terima nilai (efek state), bukan cuma echo.
- Namespace join: `40/admin,` sukses dari low-priv = bukti, bukan `?nsp=` (jebakan).

## Refusal-pattern

- 101 dari foreign origin TAPI server cek Origin di message layer / perlu token → bukan CSWSH.
- `nsp=/admin` di URL socket.io → SILENT diabaikan, kamu test root namespace, bukan /admin.
- Signed message replay yang sudah expire / di-reject → bukan temuan.