# Luno (Bugcrowd luno-og) — captured scope facts & plan pointers

Session-specific capture (2026-09-10). Raw brief + full plan live in `D:\data hermes\bug-bounty\_progress\luno\` (scope.md, progress.md, snapshot.txt).

## Key facts (verify before reuse — briefs change)
- Staging-only web: `*.staging.luno.com`, `staging.luno.com.ng`, `api.staging.luno.com`, `app.staging.luno.com`. Production web OUT.
- Mobile production apps IN (Android co.bitx.android.wallet, iOS id927362479) + `mobileapi.staging.luno.com`. Mobile P1 $4.5k–7.5k > web P1 $2.5k–3k.
- Bonus +5%: header `x-luno-bugcrowd-id: <username>` lowercase. Signup staging with @BC_ALIAS.com email.
- Stack: AWS + Cloudflare + nginx, Go/gRPC on K8s, Angular frontend.
- Focus areas explicitly include endpoints NOT behind Cloudflare, exposed buckets, leaked source, business logic.
- Excluded: rate-limit bypass testing, DoS, P5, mobile bugs needing malicious app, Firebase debug/empty (= informational), N-day < 14 days public.
- Post-exploitation: STOP and report when found (program policy).

## Announcement-driven surface (pattern: new features = invited testing, low competition)
- Account Recovery V2 (MY-only, flag 663 ON): routing bypass, token replay after 4-min expiry, region enforcement. Header `X-Luno-Announcement-ID: 2fc0a317-9115-43ce-b503-e862c986412b`.
- CARF TIN (ZA): TIN format validation bypass, self-cert hard gate. Header `X-Luno-Announcement-ID: cff8afbf-e8c8-4412-bc64-86a9fc2c4b99`.

## Reusable lesson
When a program has announcements with per-announcement required headers, those features are explicit invitations — prioritize them in the plan and log each header ID into scope.md at capture time.
