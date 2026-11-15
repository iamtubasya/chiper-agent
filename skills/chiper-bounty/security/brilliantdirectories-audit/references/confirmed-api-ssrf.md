# Confirmed finding — blind SSRF in the REST API v2 image importer (Medium)

Status: **SUBMITTED** by the operator to `bounty@brilliantdirectories.com`
(2026-10-28 15:25:33 UTC, `in:sent` verified). Do not resubmit — check Gmail `in:sent` first.
A duplicate staging draft (`r4245724482462256620`) may still sit in Drafts; it is redundant.

CVSS 3.1 **5.3** `AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:N/A:N`.

## The bug

`POST /api/v2/user/create` (and `/api/v2/user/update`) accept image URLs — `logo`, `profile_photo`,
`cover_photo`. With **`auto_image_import=1`** the platform server fetches that URL itself to re-host the
image. No allow-list, no private-range filter, no scheme restriction.

```
POST /api/v2/user/create
X-Api-Key: <site key>   X-BD-Site-URL: https://<site>
logo=http://f3run1.<oob>/logo.png&auto_image_import=1
-> 200 {"status":"success","message":{"user_id":"24", ...}}
```

## PoC result (3/3, fresh OOB, unique hostname per run)

| run | DNS | HTTP | HTTP source |
|---|---|---|---|
| f3run1 | A + AAAA | 4 | 66.147.238.90 |
| f3run2 | A + AAAA | 4 | 66.147.238.90 |
| f3run3 | A + AAAA | 4 | 66.147.238.90 |

`66.147.238.90` = the platform host, i.e. the request comes from shared infrastructure, not from the
tester. Re-proven on a second independently provisioned install earlier in the engagement.

## Why it stays Medium (do not inflate)

- The response body is **not returned and not stored** when it is not a valid image — the record keeps the
  supplied URL. So the fetch is **blind**: request origination is proven, data exfiltration is not.
- `file:///etc/passwd` and `http://127.0.0.1/` produced **no observable difference** — consistent with a
  blind fetch. No `169.254.169.254` metadata claim was made.
- Requires an API key (default member read/write level suffices).

What it does buy an attacker: requests issued from Brilliant Directories' own IP against systems the
attacker cannot reach — defeats IP allow-lists on internal services.

## Trigger via the front end? (checked, not proven)

Searched all 415 PHP widgets for `logo|profile_photo|cover_photo|auto_image_import` without a session
gate. The upload-capable ones (`Bootstrap Theme - Account - Profile Image Upload`, `... Photo Albums
Upload Form`, `... Reviews - Upload Images`) **are** gated by `user::isUserLogged` and ownership checks;
the rest only *display* the field. So no unauthenticated trigger was found — the API key is required.
Do not claim "unauth SSRF" without proving it.

## Evidence files

`F3_ssrf_requests.txt`, `F3_oob_interactions.txt` (18 lines), `F3_stored_record.txt` — all in
`~/bounty/bd/evidence/`. Interactsh session log: `~/bounty/bd/oob3.log`.

## Remediation to recommend

Resolve-then-validate the destination (reject loopback / link-local / RFC1918 / multicast / IPv6
equivalents, re-check after redirects), allow only http/https, fetch through an egress proxy with a
destination allow-list, move the fetch out of the synchronous request path, and add a regression test
that `http://127.0.0.1/` and `http://169.254.169.254/` are rejected.
