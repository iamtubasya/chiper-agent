# GitHub Source Code Review as a Bug Bounty Vector

When a target's authenticated surface is unreachable (CAPTCHA-blocked signup, no registration
endpoint, KYC gate), check whether the vendor publishes source code on GitHub. A public repo
that matches the deployed build turns a "no test account" dead-end into a white-box review
with live-endpoint confirmation.

## When to use this

- Signup is blocked by Cloudflare Turnstile / reCAPTCHA validated **server-side** (dummy token
  returns 422, headless Chrome is detected).
- The target app has NO web registration endpoint (e.g. Symfony app with only CLI user creation).
- WHMCS or similar has registration disabled ("place an order first").
- You have exhausted default creds, dev environments, and auth bypass attempts.

## Step 1 — Find the repo

```bash
# Check schema.org / JSON-LD on the target's marketing pages for sameAs links
curl -s https://target.com/ | grep -oP 'github\.com/[^"]+'

# Check the GitHub org directly
curl -s https://api.github.com/users/<org>/repos?per_page=100

# Check the original project (the vendor may have forked an OSS project)
# composer.json / package.json / README often name the upstream author
```

Look for repos whose name matches the deployed app (e.g. `sesdashboard` for
`ses.dmarcreport.com`). Forks of OSS projects are common — the vendor's repo may be a
lightly-patched fork of the original.

## Step 2 — Prove the deployed version matches the repo

Compare build asset hashes. Symfony/Laravel/Next.js apps emit content-hashed filenames:

```bash
# Live site
curl -s https://ses.example.com/login | grep -oP 'href="/build/[^"]*"'

# Repo
curl -s https://raw.githubusercontent.com/<org>/<repo>/master/public/build/<same-file>
```

Identical hashes (e.g. `112.069aa3e8.css`, `signin.156a781c.css`) prove the deployed
frontend matches the repo. The PHP/backend code may still differ, but the match is strong
evidence and enough to justify a source-code-based report.

## Step 3 — Review the security-critical files

Priority order for Symfony apps:

| File | Why |
|---|---|
| `config/packages/security.yaml` | Firewall patterns, access_control, PUBLIC_ACCESS routes |
| `src/Security/*Authenticator.php` | Custom auth logic, CSRF handling |
| `src/Controller/WebHookController.php` | Webhook endpoints are often PUBLIC_ACCESS + fetch attacker URLs |
| `src/Controller/*Controller.php` | Look for missing ownership checks (`// TODO Permissions`) |
| `src/Entity/*.php` | Field types, validation constraints |
| `src/Repository/*.php` | Custom queries (check for parameterized vs raw SQL) |
| `src/Form/*Type.php` | Mass assignment surface |
| `.env` / `.env.test` | Template placeholders only — real secrets are in `.env.local` (uncommitted) |
| `src/DataFixtures/AppFixtures.php` | Test data patterns (default passwords, admin emails) |
| `src/Factory/*Factory.php` | Factory defaults (e.g. `password => '12345678'`) |

For Laravel: check `routes/api.php`, `app/Http/Controllers/`, `config/services.php`.
For Rails: check `config/routes.rb`, `app/controllers/`, `config/initializers/`.

## Step 4 — Confirm the route exists on the live site

Even without a valid token/account, you can prove the route is reachable:

- `GET /webhook/test` → **405** means the route matched and the method is wrong (route exists).
- `POST /webhook/invalid` → **404** means the ParamConverter ran and failed to find the entity.
- Compare the 404 body: a Symfony error page (`"Oops! An Error Occurred"`) means the request
  reached the application, not nginx.

If authenticated endpoints redirect to `/login` (302), the route exists but requires auth —
still worth reporting the IDOR because the code shows no ownership check.

## Step 5 — Report with the 4-element evidence framework

When you cannot trigger the vulnerability live, the report must carry:

1. **Source code citation** — exact file path, function name, and vulnerable lines.
2. **Live endpoint behavior** — 405/404/302 responses that prove the route is reachable and public.
3. **Version match** — build asset hashes identical between live site and repo.
4. **Ready-to-run PoC** — exact curl command the vendor can execute with their own token/account.

Be explicit: "Source code confirms the vulnerability; live trigger requires a valid project
token which I was unable to obtain." Do not claim a live exploit you did not perform.

## Pitfalls

- **The repo may be behind the deployed code.** Always check the git log for recent commits.
  If the last push is months old but the live site has newer build hashes, the repo is stale.
- **`.env` in the repo is a template.** Real secrets live in `.env.local` which is gitignored.
  Do not report placeholder values (`%CHANGEME%`) as exposed secrets.
- **Factory defaults are not production credentials.** `UserFactory` with `password => '12345678'`
  only applies if fixtures were loaded. Try them, but expect failure in production.
- **Symfony ParamConverter uses the route parameter name as the field name.** `@Route("/webhook/{token}")`
  with `Project $project` looks up by `token`, not `id`. Trying `/webhook/1` will not find
  project id=1 unless the ParamConverter is explicitly configured otherwise.
- **nginx normalizes `..` before the firewall check.** Path-traversal firewall bypass
  (`/js/../project/1/edit`) does not work when nginx resolves the path first. Test with
  `curl -D-` and check if you get 302-to-login (normalized) or 404 (not normalized).
- **The `/index.php/` front-controller prefix works for routing** but does NOT bypass
  authentication or the ParamConverter. It only changes the URL structure.

## Account creation blockers observed (2026-10-26, DuoCircle)

| Service | Blocker | Bypass attempted |
|---|---|---|
| app.dmarcreport.com | Cloudflare Turnstile, server-side validated | Dummy token → 422; headless Chrome detected; Camofox tab timeout |
| app.mailflowmonitoring.com | Cloudflare Turnstile, server-side validated | Same |
| ses.dmarcreport.com | No web registration (CLI only) | SQLi login, default creds, dev env — all failed |
| portal.duocircle.com (WHMCS) | Registration disabled ("place an order first") | Checkout flow requires login |
| partners.duocircle.com | Google OAuth only | No password signup |
| support.duocircle.com (Freshdesk) | Signup redirects to home | No self-registration |

When ALL signup channels are blocked, source code review is the remaining vector. Tell the
operator plainly what is blocked and why, and ask if they can provide a test account.
