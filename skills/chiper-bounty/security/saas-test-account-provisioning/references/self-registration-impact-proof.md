# Self-Registration Impact Proof — internal collaboration services

**Class:** an internal collaboration/ticketing/wiki service (Mattermost, Rocket.Chat, Zulip, GitLab,
Grafana, Wiki.js, Jitsi…) is publicly reachable, allows **self-registration without an invite**, and its
workspace/teams are **open-join** — so any internet user can read internal engineering channels.

**Why this recipe exists:** "Open registration is enabled" is an *informational* config observation that
triage drops every time. The finding only exists once you show the **join**, and you must do that without
reading a single message (policy: don't access data beyond what is needed to demonstrate). Measured on
Blink's internal Mattermost (`chat.blink.sv`) 2026-10-12 → escalated **medium → high** on the strength of
this proof alone.

## 0. Decide the shape of the claim first
Three separate claims, three separate evidence levels — do not merge them:

| Claim | Proof needed | Severity if alone |
|---|---|---|
| registration is open | config endpoint flags | info |
| a team/workspace is joinable by outsiders | `allow_open_invite`/open-type + your join returns 201 | low |
| internal content is readable | channel inventory (you should NOT go further) | medium–high |

## 1. Read the service's own posture (unauthenticated)
Mattermost exposes this without any token:
```bash
curl -s 'https://<host>/api/v4/config/client?format=old' | jq '{
  Version, SiteName, EnableOpenServer, EnableUserCreation, EnableSignUpWithEmail,
  EnableMultifactorAuthentication, EnforceMultifactorAuthentication, NoAccounts }'
```
Signals that the instance is internal and unintended-to-be-public: `SiteName` = the company's own name,
`SupportEmail` = a staff address, version string, `EnableCustomEmoji` etc. — plus the host being
**unlinked from the public marketing site** (grep the public site's HTML; an unlinked `chat.`/`git.`/
`wiki.` subdomain found by crt.sh is the standard discovery path).

## 2. Create + verify + log in (all over the API, no browser)
```python
# 1) account (disposable mailbox from mail.tm — see SKILL.md Step 1)
POST https://<host>/api/v4/users
     {"email":<mailbox>,"username":"<u>","password":"<p>"}          -> 201
# 2) verification mail arrives from mattermost@<domain>
#    body contains  https://<host>/do_verify_email?token=<T>&email=<E>
POST https://<host>/api/v4/users/email/verify  {"token":"<T>"}      -> 200 {"status":"OK"}
# 3) login — THE TOKEN IS IN A RESPONSE HEADER, NOT THE BODY
POST https://<host>/api/v4/users/login  {"login_id":"<u>","password":"<p>"}
     -> 200 user JSON  +  header  Token: <session-token>
# 4) what can this new outsider see?
GET  /api/v4/teams          -> [ {id, display_name, type:"O", allow_open_invite:true} ]
GET  /api/v4/users/me/teams -> []            (not a member yet — that's the point)
```
Extract the token from `x.headers["Token"]` (`urllib`), **not** from the JSON body. Logging in before
verifying gives `401 api.user.login.not_verified.app_error` — that is the *expected* state, not a failure.

## 3. Prove the join, then leave immediately
```python
uid = GET /api/v4/users/me -> id
POST /api/v4/teams/<team_id>/members  {"team_id":<team_id>,"user_id":<uid>}   -> 201 (roles: team_user)
GET  /api/v4/teams/<team_id>/channels                                          -> channel inventory
DELETE /api/v4/teams/<team_id>/members/<uid>                                   -> 200 (leave)
```
- The join body needs **both** `team_id` and `user_id` — omitting `user_id` returns
  `400 api.context.invalid_body_param.app_error ("Invalid or missing user_id")`, which is easy to misread
  as "the team is not joinable".
- **Stop at the channel inventory.** Channel *names* already carry the impact story
  (`dev`, `ux`, `town-square`, `ai-tools`, `*-integration`, `beta-testers`, and even a staff email used as a
  channel name — an incidental PII leak you can quote). Do **not** call `/channels/<id>/posts`.
- Leave in the same script run (`teams/.../members/...` DELETE) and re-read `/users/me/teams` → `[]` to
  prove the cleanup actually landed.

## 4. Reporting discipline for this class
- Say explicitly in the report: **account created, email verified, join executed, channel names read,
  zero messages read, membership deleted.** That sentence is what keeps the write-up inside safe harbour.
- Disclose the leftover account (`username` / mailbox) as a state change the vendor can remove — you cannot
  self-deactivate on Mattermost, so list it for cleanup instead of pretending it does not exist.
- Repro block = the exact six calls above with their status codes; triagers accept the join-201 as proof.

## 5. Generalising the check to other stacks
- Rocket.Chat: `GET /api/info` + registration flag, then `POST /api/v1/users.register`, workspace join via
  `/api/v1/channels.join` — same three-claim ladder, same "metadata only" stop rule.
- Zulip: `POST /api/v1/register` (realm open), then stream visibility.
- GitLab: `/users/sign_up` open + `visibility=public` on projects/groups.
- Grafana: `POST /api/user` when signup is on, then org/team enumeration.
- Always finish with the *policy* read (join_open / visibility), not with content.
