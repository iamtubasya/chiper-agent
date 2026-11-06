## 25. DEPENDENCY CONFUSION / SUPPLY CHAIN  📦

> When an org's build pulls from **both** a private registry and the public one, an attacker who publishes a public package with the **same name + a higher version** can get their code executed inside the org's CI/dev machines. Alex Birsan's 2021 research made **$130k+ across 35 companies** (Apple, Microsoft, PayPal, Netflix, Uber, Tesla) this way — and it is still live: Microsoft Security documented 33 malicious npm packages abusing it in May 2026.
>
> **The entire bug is "can your code RIGHT NOW execute on their infra?"** — a DNS/HTTP callback from their network is the proof. No callback = no bug. This class has the hardest ethical line in the skill: **PoC fires a callback ONLY, never a real payload.**

### Root Cause
The package-manager resolver prefers **highest version across all configured registries** instead of pinning name→registry origin.

```bash

