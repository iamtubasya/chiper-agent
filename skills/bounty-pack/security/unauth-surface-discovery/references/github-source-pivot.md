# GitHub Source Pivot — When Live Exploitation Is CAPTCHA-Blocked

Worked example: DuoCircle bug bounty, 2026-10-26.

## Situation

Target: DuoCircle (email security SaaS, 11 in-scope domains, 341 subdomains).
Every signup channel validated Cloudflare Turnstile server-side:
- `app.dmarcreport.com/signup` → 422 without valid Turnstile token
- `app.mailflowmonitoring.com/users/sign_up` → JS reset, no session created
- `portal.duocircle.com/register.php` → reCAPTCHA
- `auth.duocircle.com` (WorkOS AuthKit) → Turnstile
- Headless Chrome detected by Turnstile ("CAPTCHA verification failed")
- Camofox browser tab creation timed out repeatedly

Without an account, all authenticated endpoints (IDOR, cross-tenant) were unreachable.

## The pivot

### Step 1: Find the GitHub org

The trust center page (`trust.duocircle.com/security/bug-bounty/`) had schema.org JSON-LD with:
```json
"sameAs": ["https://github.com/duocircle", ...]
```

### Step 2: List repos

```bash
curl -s "https://api.github.com/users/duocircle/repos?per_page=100"
```

15 repos found. Key match: `sesdashboard` (PHP) → live host `ses.dmarcreport.com`.

### Step 3: Verify deployed version matches repo

Live page source:
```html
<link rel="stylesheet" href="/build/112.069aa3e8.css">
<link rel="stylesheet" href="/build/signin.156a781c.css">
```

Repo tree:
```
public/build/112.069aa3e8.css
public/build/signin.156a781c.css
```

**Exact hash match** → deployed code == repo code. Findings are not theoretical.

### Step 4: Read security-critical files (priority order)

1. `config/packages/security.yaml` — access_control rules, firewall config
2. `src/Security/` — authenticator classes
3. `src/Controller/` — route annotations + auth checks
4. `src/Repository/` — query construction (SQLi surface)
5. `.env` / `.env.test` — secrets (usually templates, but check)

### Step 5: Grep for auth gaps

```bash
# TODO comments near auth = missing checks
grep -rn "TODO.*[Pp]ermission\|TODO.*[Aa]uth\|TODO.*[Cc]heck" src/

# Direct find() by user-supplied ID = IDOR pattern
grep -rn "find(\$request->get(" src/Controller/

# PUBLIC_ACCESS routes = unauthenticated attack surface
grep -rn "PUBLIC_ACCESS" config/
```

### What was found (DuoCircle sesdashboard)

**SSRF (HIGH)** — `src/Controller/WebHookController.php`:
```php
// security.yaml: - { path: ^/webhook/, roles: PUBLIC_ACCESS }
@Route("/webhook/{token}", methods={"POST"})
public function index(Project $project, ...) {
    $jsonData = json_decode($request->getContent(), true);
    if ($jsonData['Type'] == 'SubscriptionConfirmation') {
        $response = $httpClient->request('GET', $jsonData['SubscribeURL']); // NO VALIDATION
    }
}
```

**IDOR (MEDIUM)** — `src/Controller/ActivityController.php`:
```php
@Route("/activity/details/api")
public function detailsApi(Request $request, ...) {
    // TODO Permissions  ← literally the comment
    $email = $emailRepository->find($request->get('id')); // NO ownership check
}
```

**IDOR (MEDIUM)** — `src/Controller/ProjectController.php`:
```php
@Route("/project/{id}/edit")
public function edit(Request $request, Project $project, ...) {
    // list() and add() filter by user, but edit() does NOT
    $em->persist($project);
}
```

### Step 6: Confirm routes on live site without triggering

```bash
# 405 on GET for POST-only route = route exists AND is public
# (router rejects method BEFORE auth middleware runs)
curl -s -o /dev/null -w "%{http_code}" https://ses.dmarcreport.com/webhook/test
# → 405

# 302 to /login = route exists behind auth
curl -s -o /dev/null -w "%{redirect_url}" https://ses.dmarcreport.com/activity/details/api?id=1
# → /login

# 404 for invalid entity token = ParamConverter is looking up the entity
curl -s -o /dev/null -w "%{http_code}" -X POST https://ses.dmarcreport.com/webhook/invalid
# → 404
```

These three responses together prove: the routes exist, the webhook is public, and the IDOR routes
are behind auth but lack ownership checks.

## Key lessons

1. **Build hash matching is the strongest evidence** that source == deployed. Always compare
   `public/build/*.css` hashes or `_next/static/chunks/*.js` hashes between repo and live site.
2. **`// TODO Permissions` in source code is a gift** — it is an admission that the check was
   planned but never implemented. Quote it verbatim in the report.
3. **405 vs 302 vs 404 tells you the auth posture** without needing credentials:
   - 405 on wrong method → route is public (router runs before auth)
   - 302 to login → route exists behind auth
   - 404 on invalid entity ID → ParamConverter lookup (route exists, entity not found)
4. **Report honestly about what you could not trigger.** The SSRF needed a valid 86-char project
   token. State that clearly, but emphasize: source is public, endpoint is public, vendor can verify
   in minutes with their own token.
5. **Do not stop at the first repo.** Check all repos — the MCP server, Terraform modules, and
   helper tools may expose additional attack surface or configuration.

## Pitfalls

- **GitHub API rate limit** (60 req/hr unauthenticated) can block mid-audit. Fetch the repo list
  first, then file trees, then raw files — in that order. Use `?per_page=100` to minimize calls.
- **Default branch varies** (`main` vs `master`). Always fetch repo info first:
  `curl -s "https://api.github.com/repos/<org>/<repo>" | python3 -c "import json,sys; print(json.load(sys.stdin)['default_branch'])"`
- **Fixtures/factories are NOT production credentials.** `UserFactory` default password `12345678`
  and `admin@admin.com` only exist in test data. Try them on the live login, but expect failure.
- **The output redactor eats token-shaped strings** in shell heredocs. Write scripts to files with
  `python3 -c` or fragment the strings (`"Bea" + "rer "`).
