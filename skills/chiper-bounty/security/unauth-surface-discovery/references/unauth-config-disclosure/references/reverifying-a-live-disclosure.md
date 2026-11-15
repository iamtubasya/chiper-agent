# Re-verifying a live pre-auth disclosure on a later round

Continuing engagements (a report was filed, the vendor has not shipped a fix, a later round
revisits the target) need a different question from the first round. Round 1 asked *"what
leaks?"*. Later rounds must answer three, in this order:

1. **Is it still live?** If it is, the existing report still stands and any new round's job is
   to prove nothing changed underneath it.
2. **Did anything NEW leak?** New tenants get provisioned, config schemas gain fields, staging
   gets promoted. A new secret is a genuinely new reportable value.
3. **Did the schema change in a way that matters?** A field that became populated, or a default
   that flipped, is worth a sentence even when no secret is new.

Do not re-litigate round 1. The output of this pass is a diff, not a re-write.

## Step 1 — full re-dump, one file per host

Re-run the sweep over the **current** host list (re-enumerate; hosts get added), against every
known alias, and write every raw body to disk under a *new* dated directory so the previous
round's evidence stays intact and diffable:

```python
PATHS = ["/api/settings", "/settings"]          # alias found on a sibling API tier
# one file per (host, path): <host>_api_settings.json / <host>_settings.json
```

Thread the requests across hosts (12 workers over 344 hosts is ~1 request per host — still
inside a 5 req/s-per-host cap). Never thread a single host at speed.

**Sanity check the count against the last round.** If it moved (137 → 145 here), find out why
before writing anything: a newly enumerated alias, a `:8443` duplicate, or hosts that were
previously unreachable all produce a bigger number without a new finding.

## Step 2 — the key-path union and the rare-key diff

Flatten every dump to dotted key paths and count on how many hosts each path appears. This is
the cheapest way to spot a field that only exists on a few — i.e. the newest — deployments.

```python
keys, hostkeys = collections.Counter(), {}
for f in glob.glob(f"{RAW}/*.json"):
    host = os.path.basename(f).replace("_api_settings.json", "").replace("_settings.json", "")
    ks = set(flatten(json.load(open(f, encoding="utf-8"))))   # recursive dotted paths
    hostkeys[host] = ks
    for k in ks:
        keys[k] += 1

rare = [(k, n) for k, n in keys.items() if n <= 3 and not k.startswith("themes")]
```

Interpretation on the worked case: **8254 distinct paths, only 2 with `<= 3` hosts**, and both
were benign (`defaultRealm`, one `passwordResetSettings.requiredFields` array index). That is a
*clean* result — a uniform schema with no hidden sensitive field — and it is worth stating in
one line ("no additional field is present on only some deployments").

**Exclude the `themes.*` namespace before you read the output**, or the rare-key list fills up
with per-tenant theme names (`themes.<host>.id`, `.loginLogo`, `.webmailLogo` on every host)
and you will scroll past the real signal. Same for any other per-tenant keyed namespace.

## Step 3 — credential inventory as `key -> value -> hosts`

For each credential-bearing sub-object, parse **the JSON string inside the value** (these fields
are usually serialised JSON stored in a string column) and build `key -> distinct value ->
host list`:

```python
for k in ("googleDrivePickerConfig", "dropboxPickerConfig", "onedrivePickerConfig"):
    raw = j.get(k)
    if isinstance(raw, str) and raw.strip():
        for kk, vv in json.loads(raw).items():
            if vv:
                inv[f"{k}.{kk}"][str(vv)].add(host)
```

Then print, per distinct value: `len`, `sha256[:10]`, host count and host list. **Never the value
itself** — the display layer will redact it anyway, and re-testing a redacted string is the
classic false negative (see the SKILL.md pitfall on this).

The deliverable is a comparison: *"identical credential set to round 7 — no new tenant, no new
key"*, or *"a fourth `devKey` appeared on host X"*. On the worked case the answer was the
former, which correctly suppressed a new report.

## Step 4 — check the control fields that carry meaning

Beyond credentials, re-read the handful of keys that are evidence *for other findings*:

- the lockout/throttle setting (`blockDuration` etc.) and its distribution across hosts — the
  fleet-wide "disabled on the majority" claim needs the counts re-derived, not assumed;
- `allow2FA` vs what the auth capability endpoint advertises (a mismatch is a posture note, not
  a finding);
- monitoring hook keys — on this target `airbrakeProjectId` / `airbrakeProjectKey` exist on all
  142 hosts and are **empty everywhere**, so an "Airbrake write key leaked" hypothesis dies here.
  Check the value before you build a chain on the key's presence.

## Step 5 — write the diff, not the story

Close with three lines: (a) still exposed — N hosts, still unfixed; (b) delta versus the last
round — usually "none"; (c) whether the standing report needs an update. If the delta is empty,
**do not create a new report and do not resubmit** — the correct output of this pass is the
log entry and the refreshed evidence bundle.

## What this pass is NOT

- It is not a reason to re-scan the fleet with a full scanner. Nothing about later rounds makes
  automated output eligible.
- It is not a reason to split the finding per host. One root cause, one reward.
- It is not a reason to re-test the disclosed keys again "to be sure". The classification from
  round 1 stands unless the value changed; re-testing a redacted display string actively
  manufactures a wrong correction.
