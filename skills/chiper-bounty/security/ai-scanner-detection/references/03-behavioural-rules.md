# 03 — Behavioural detection rules (ours)

**These are our own rules.** Written from the concepts above, not copied from any repository's rule
text. Field names follow the SigmaHQ webserver/proxy taxonomy so they translate with `sigma convert`;
thresholds and windows are placeholders you MUST tune to the local baseline.

## Rule set: same-source multi-stage web attack

Four rules: three low-signal "leg" rules plus one correlation that only fires when a single client
satisfies all three inside a window. The legs are deliberately weak alone — that is the point.

```yaml
title: Web Enumeration Burst From One Source
status: experimental
description: |
  Stage A. A single client produces a burst of 404/400 responses in a short window, consistent with
  directory/endpoint enumeration. Weak alone; meaningful only inside the correlation below.
logsource:
  category: webserver
detection:
  selection:
    sc-status: [400, 404]
  timeframe: 5m
  condition: selection | count() by c-ip > 100
falsepositives:
  - Broken links, authorised scanners, misconfigured clients. Tune the count to your baseline.
level: low
```

```yaml
title: Web Parameter/Path Probe Markers From One Source
status: experimental
description: |
  Stage B. Requests from one client whose URI/body contain probe-shaped tokens (quote, boolean
  pair, template delimiters, traversal sequence, encoded null). Broad on its own.
logsource:
  category: webserver
detection:
  keywords:
    - "' OR "
    - '" OR "'
    - "1=1"
    - "{{"
    - "${"
    - "../"
    - "%00"
  timeframe: 5m
  condition: keywords | count() by c-ip > 20
falsepositives:
  - Legitimate payloads resembling markers. Tune the marker list per application.
level: low
```

```yaml
title: Authentication Or Identity-Verification Attempts From One Source
status: experimental
description: |
  Stage C. Repeated hits on login/OTP/reset/verify endpoints from one client, including failure-heavy
  traffic. Broad on its own.
logsource:
  category: webserver
detection:
  selection:
    cs-uri-path|contains:
      - "/login"
      - "/signin"
      - "/auth"
      - "/otp"
      - "/verify"
      - "/reset"
  timeframe: 5m
  condition: selection | count() by c-ip > 15
falsepositives:
  - Ordinary users signing in. Only meaningful inside the correlation.
level: low
```

```yaml
title: Same-Source Multi-Stage Web Activity (Enumeration, Probe, Auth)
status: experimental
description: |
  Correlates stages A, B and C from one client within one window. This is the durable signal: an
  autonomous agent chains recon -> probing -> auth in a single coherent session, which ordinary
  traffic rarely does. Generic behaviour - it does not depend on any tool's User-Agent, so it survives
  an operator disguising their fingerprint.
correlation:
  type: temporal
  rules:
    - <uuid-of-stage-A>
    - <uuid-of-stage-B>
    - <uuid-of-stage-C>
  group-by: [c-ip]
  timespan: 15m
level: high
falsepositives:
  - Authorised penetration tests (allow-list by engagement window/source), aggressive crawlers.
```

```yaml
title: Bypass Persistence After Repeated Refusals (One Source)
status: experimental
description: |
  A client keeps issuing new variants toward the same path family after a run of 401/403/429.
  Humans stop or switch target; an agent adapts and continues. Tune the run length and window.
logsource:
  category: webserver
detection:
  refusal:
    sc-status: [401, 403, 429]
  condition: refusal | count() by c-ip > 30
  # then correlate with continued distinct-path hits from the same c-ip in the following window
level: medium
```

## Suricata (network) — supporting

Write these against **your own** expected scan User-Agents, and keep the comment that says they are
bypassable. Skeleton:

```
alert http any any -> any any (msg:"[OUR-ORG] automation UA observed (supporting indicator, bypassable)"; \
  http.user_agent; content:"<scanner-ua>"; nocase; \
  classtype:network-scan; sid:9000001; rev:1; \
  metadata: note "UA is operator-changeable; do not treat absence as safety";)
```

## Rules of engagement for writing these

1. Every static rule carries its own `falsepositives` AND a sentence saying it is bypassable.
2. Behaviour rules state their window/count and say "tune to baseline".
3. Never publish a rule that would block a whole ASN, CDN range, or cloud provider.
4. Every rule must be runnable — if you cannot test it against sample events, it is a claim, not a rule.
