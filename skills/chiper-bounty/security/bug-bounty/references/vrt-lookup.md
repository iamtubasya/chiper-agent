# Bugcrowd VRT lookup (do not guess the category)

Bugcrowd triage rates by VRT, **not** CWE — so the reported category is what sets the default
priority. Never invent it from memory; fetch the taxonomy and query it.

## Fetch

```bash
curl -sL -m 45 -o vrt.json \
  https://raw.githubusercontent.com/bugcrowd/vulnerability-rating-taxonomy/master/vulnerability-rating-taxonomy.json
```

~105 KB. Shape: `{"metadata": {"release_date": ...}, "content": [ ...categories ]}`, where each node is
`{id, name, type, children?}` and the **leaves** carry `priority` (1-5). Internal nodes have no
`priority` — read the variant, not the category.

## Query (walk to leaves, match on the full path)

```python
import json
d = json.load(open("vrt.json"))
print(d["metadata"])                       # record the release_date in the report
def walk(node, path=()):
    for c in node:
        p = path + (c["name"],)
        if c.get("children"):
            yield from walk(c["children"], p)
        else:
            yield p, c.get("id"), c.get("priority")
for p, i, prio in walk(d["content"]):
    if any(k in " ".join(p).lower() for k in ("sensitive", "secret", "log")):
        print(" | ".join(p), "->", i, "P%s" % prio)
```

## Notes that matter for the report

- Write the full three-level path in the report: `Category > Subcategory > Variant`, plus the
  variant's default priority and the VRT `release_date`. Octopus Deploy's brief explicitly says
  "Rating by Bugcrowd VRT, may be modified by likelihood/impact" — so state the default and do not
  claim it as the final payout.
- **`For Internal Asset` vs `For Publicly Accessible Asset` changes the priority by two steps**
  (P3 vs P1 under `Sensitive Data Exposure > Disclosure of Secrets`). A self-hosted/on-prem product
  instance that you installed yourself is the *internal* variant even though you reached it over
  HTTP on localhost. Getting this wrong is a two-priority overclaim and gets the report corrected
  down at triage.
- Where a program pays only P1-P4, a VRT leaf with priority 5 is effectively out of the money band.
- Still cite the CWE alongside the VRT: programs commonly ask for both, and CWE is what other
  trackers (self-hosted VDPs) rate by. For secrets written to a log the precise one is
  **CWE-532: Insertion of Sensitive Information into Log File** (CWE-200 is the looser parent).
