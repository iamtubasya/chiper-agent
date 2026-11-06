# GitHub Org Source Code Review — Technique Reference

> When black-box testing is auth-gated (CAPTCHA on all signups, no registration endpoint),
> the target's public GitHub org is a free source code audit. This reference covers the
> full workflow: discovery → verification → analysis → reporting.

## Trigger Conditions

- All signup flows have server-side CAPTCHA (Cloudflare Turnstile, reCAPTCHA)
- No web registration endpoint exists (CLI-only user creation)
- Authenticated endpoints return 401/302 and you can't get an account
- User pushes for findings but black-box surface is exhausted

## Step 1: Discover Public Repos

```bash
# List all public repos for the target's GitHub org
curl -s "https://api.github.com/users/<org>/repos?per_page=100" | \
  python3 -c "
import json, sys
for r in json.load(sys.stdin):
    print(f'{r[\"name\"]:40} {r.get(\"language\") or \"?\":15} {r.get(\"pushed_at\",\"\")[:10]}')
"
```

Look for repos that match deployed services:
- App names matching subdomains (e.g., `sesdashboard` → `ses.<target>.com`)
- Infrastructure tools (terraform, docker, CI configs)
- Internal tools that might be exposed

## Step 2: Verify Deployed = Repo (Build Hash Matching)

**Critical:** A public repo does NOT prove the deployed version matches. Verify via build asset hashes.

1. Get the repo file tree:
```bash
curl -s "https://api.github.com/repos/<org>/<repo>/git/trees/<branch>?recursive=1" | \
  python3 -c "import json,sys; [print(i['path']) for i in json.load(sys.stdin)['tree'] if i['type']=='blob']"
```

2. Compare CSS/JS asset filenames on the live site against `public/build/` in the repo:
```bash
# Live site assets
curl -s "https://<target>/login" | grep -oP 'href="/build/[^"]*"'

# Repo assets
curl -s "https://raw.githubusercontent.com/<org>/<repo>/<branch>/public/build/manifest.json"
```

3. Identical hashed filenames (e.g., `112.069aa3e8.css` on both) = deployed version matches repo.

## Step 3: Prioritize Security-Critical Files

Fetch and review in this order:

| File | Why |
|------|-----|
| `config/packages/security.yaml` | Firewall rules, access_control, PUBLIC_ACCESS paths |
| `src/Controller/*Controller.php` | Route definitions, auth checks, input handling |
| `src/Security/*Authenticator.php` | Auth logic, CSRF, credential handling |
| `src/Controller/WebHookController.php` | SSRF — URL fetching from user input |
| `src/Repository/*Repository.php` | SQL query construction (parameterized vs raw) |
| `src/Form/*Type.php` | Mass assignment surface |
| `src/Entity/*.php` | Data model, validation constraints |
| `.env` / `.env.test` | Secrets (usually templated, but check) |
| `src/DataFixtures/*.php` | Default creds, test data |
| `src/Factory/*Factory.php` | Default passwords, test tokens |
| `docker-compose.yml` | Exposed ports, default configs |
| `phpdocker/nginx/nginx.conf` | Rewrite rules, path handling |

## Step 4: Vulnerability Patterns to Look For

### SSRF in Webhook/Callback Controllers
```php
// VULNERABLE: user-controlled URL fetched by server
$response = $httpClient->request('GET', $jsonData['SubscribeURL']);
```
Check: Is the route PUBLIC_ACCESS? Is there URL validation? Allowlist?

### IDOR — Missing Ownership Checks
```php
// VULNERABLE: no check that entity belongs to current user
public function detailsApi(Request $request, EmailRepository $repo) {
    $email = $repo->find($request->get('id'));  // ANY id
    return $this->json(...);
}
```
Look for: `// TODO Permissions` comments, missing `->getUser()` filters, `find($id)` without ownership scoping.

Compare with sibling methods that DO check:
```php
// SAFE: filters by user
$project = $repo->findOneBy(['user' => $this->getUser()]);
```

### Symfony ParamConverter Gate
```php
// Entity-typed param resolved BEFORE method body
public function index(Project $project, ...) { ... }
```
- GET with invalid token → 405 (route exists, method not allowed)
- POST with invalid token → 404 (ParamConverter failed to find entity)
- POST with valid token → method body executes

**Implication:** SSRF/injection behind ParamConverter requires valid identifiers. Without a token, the vulnerable code never runs.

### Mass Assignment
```php
// Check form types for fields that shouldn't be user-settable
$builder->add('email')->add('username')->add('plainPassword', ...);
```

## Step 5: Live Endpoint Confirmation

Even without valid identifiers, confirm routes exist and are public:

```bash
# Route exists? (405 = yes, method disabled)
curl -s -o /dev/null -w "%{http_code}" https://<target>/webhook/test
# → 405 Method Not Allowed = route EXISTS

# Auth required? (302 to login = yes, 404 = ParamConverter failed)
curl -s -o /dev/null -w "%{http_code}|%{redirect_url}" -X POST https://<target>/webhook/invalid
# → 404 = route matched, ParamConverter looked up entity

# Compare with non-existent route
curl -s -o /dev/null -w "%{http_code}" https://<target>/nonexistent
# → 404 but different body/size = router-level 404 vs app-level 404
```

## Step 6: Report Honestly

Source-code findings without live exploitation MUST be labeled:
- "Requires valid project token to demonstrate"
- "Requires authenticated account to demonstrate"
- Provide: vulnerable code, live endpoint confirmation, version match, PoC script

The vendor can verify in minutes. But it's NOT a live PoC — say so.

## Pitfalls

- **Public repo ≠ deployed version.** Always verify via build hashes. The repo may be months/years behind.
- **Dev environment may differ.** Check `*.dev.*` subdomains — they may run different code or have fixtures loaded.
- **Default creds from fixtures rarely work in production.** `UserFactory` defaults like `admin@admin.com` / `12345678` are test-only.
- **Don't grind CAPTCHA bypass.** Turnstile/reCAPTCHA validated server-side. Headless browsers detected. Time sink.
- **OOS scope is broader than written.** "Username enumeration on signup/password-reset" may be interpreted to cover ANY email existence oracle.
