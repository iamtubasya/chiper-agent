---
name: opsec-checker
author: RESEARCHER_NAME
description: "Operational Security Validator: VPN, DNS leaks, virtualization, browser fingerprint, hostname."
category: security
version: 1.0.0
metadata:
  hermes:
    tags: [opsec-checker]
---

# OPSEC Checker

## Triggers
- opsec check, operational security, VPN check, DNS leak, fingerprint
- pre-engagement opsec, red-team opsec, security validation

## Phases
- `pre-engagement` — validate infrastructure before starting
- `during-engagement` — continuous monitoring
- `post-engagement` — cleanup verification

## Checks

### Infrastructure
| Check | Method | Pass Criteria |
|-------|--------|---------------|
| VPN Active | `ip addr show` for tun0/wg0/utun/ppp0 | Interface exists |
| DNS Leak | `/etc/resolv.conf` content | No public ISP DNS |
| Virtualization | `systemd-detect-virt` | VM/container detected |
| Browser Fingerprint | Firefox/Chrome profile check | Config present |
| Hostname | `hostname` output | Not default/generic |

### Identity
| Check | Pass Criteria |
|-------|---------------|
| Separate attacker identity | Not personal accounts |
| Tor/proxy chain | Multiple hops verified |
| Timezone consistency | Matches target region |
| Language/locale | Consistent with assumed identity |

### Artifacts
| Check | Pass Criteria |
|-------|---------------|
| Tool signatures | No default user-agent strings |
| Compiled artifacts | Stripped, no debug symbols |
| Memory artifacts | Encrypted at rest |
| Log files | Rotated, not on disk |

## Quick Usage
```python
from opsec_checker import OpsecChecker, OPSECPhase

checker = OpsecChecker(phase=OPSECPhase.PRE)
results = checker.validate_infra()
print(results)
# {'vpn_active': True, 'dns_leak': False, 'virtualized': True, ...}
```

## Scoring
- **90-100**: Excellent — ready for engagement
- **70-89**: Good — minor gaps, acceptable
- **50-69**: Moderate — address before proceeding
- **0-49**: Poor — significant OPSEC risks, must fix

## Pitfalls
- VPN check is heuristic (interface name match) — may miss custom VPNs
- DNS leak check reads resolv.conf only — doesn't do live DNS test
- Browser fingerprint check is basic (config file presence, not actual fingerprint)
- Windows hosts: many Linux checks won't work — use platform-adaptive logic
- `systemd-detect-virt` not available on all systems
