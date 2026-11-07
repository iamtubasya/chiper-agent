# Cloudflared tunnels & 9router (AI API aggregator)

Session-specific detail for the ChiperFlux agent host. Both are common enough to
re-encounter; commands are reusable.

## cloudflared — check tunnel health without `tunnel list`

Remote-managed (token-based) tunnels have **no origin cert**, so
`cloudflared tunnel list` errors with "Cannot determine default origin certificate
path". Instead read the local Prometheus metrics endpoint. Each running cloudflared
binds a metrics port (commonly 20241/20242 — find them in `ss -tulnp`):

```bash
curl -s http://127.0.0.1:20241/metrics | grep -iE \
  'active_connections|ha_connections|total_requests|request_errors|response_by_code|tcp_active_sessions'
```

Interpretation:
- `cloudflared_tunnel_ha_connections 4` → 4 healthy redundant edge connections = good.
- `cloudflared_tunnel_total_requests` + `request_errors` → traffic + error rate.
- `response_by_code{status_code="401"}` → auth failures; `404` → missing routes.
- `tcp_active_sessions 0` → no live tunneled TCP right now.

A high 401/404 ratio here usually means the app behind the tunnel is rejecting
requests (auth/expired tokens), not that the tunnel itself is broken.

## 9router — AI API aggregator/proxy

9router is a local AI API router that aggregates many AI-provider accounts and
round-robins requests across them. On this host:

- **Binary / run:** `9router` (npm global) → spawns `next-server`, listens on
  `127.0.0.1:20128` (redirects `/` → `/dashboard`).
- **State dir:** `~/.9router/` — `data.sqlite`, `auth/cli-secret`,
  `.jwt_secret`, `model-catalog.json`, `mitm/`, `runtime/`.
- **DB:** `~/.9router/db/data.sqlite` (SQLite; `sqlite3` CLI not installed — use
  Python `sqlite3` module).

### Useful schema (queried to trace auth failures)
| Table | Purpose |
|---|---|
| `providerConnections` | provider, `authType` (apikey/oauth), name/email, `priority`, `isActive` |
| `providerNodes` | node config |
| `apiKeys` | API keys (1 row — the proxy's own key) |
| `usageHistory` | per-request: provider, model, `status`, tokens, cost |
| `usageDaily` | daily aggregate |
| `requestDetails` | detailed logs (often empty) |
| `settings` | `providerStrategies` (round-robin / random) |

Quick probes:
```bash
# list tables + row counts
python3 -c "import sqlite3; c=sqlite3.connect('/home/agentuser/.9router/db/data.sqlite'); \
  [print(t[0], c.execute('SELECT COUNT(*) FROM \"%s\"'%t[0]).fetchone()[0]) \
   for t in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")]"

# group providers by auth type + active count (avoid dumping key/secret columns)
python3 -c "import sqlite3; c=sqlite3.connect('/home/agentuser/.9router/db/data.sqlite'); \
  [print(r) for r in c.execute('SELECT provider, authType, SUM(isActive), COUNT(*) FROM providerConnections GROUP BY provider, authType')]"
```

### Root-cause pattern for "network heavy"
In this session throughput was ~2 KB/s (idle), but the 9router tunnel showed 22×
401s (~20% error rate). Cause: `round-robin` + `stickyRoundRobinLimit: 1` retried
requests across many provider accounts; OAuth providers (`qoder`, `antigravity`,
`grok-cli`, `kiro`, `kilocode`, `codebuddy-intl`) with expired tokens and dead
API-key connections returned 401 until a working account was hit. **Lesson: low
throughput + perceived slowness = inspect the app's auth/retry path, not the NIC.**
