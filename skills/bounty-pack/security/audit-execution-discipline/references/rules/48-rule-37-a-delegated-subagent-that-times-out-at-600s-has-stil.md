## ⛔ RULE 37: A delegated subagent that times out at 600s has still WRITTEN TO DISK

`delegate_task` children are killed at 600s and **their summaries are discarded** — but their files are not.
Verified 2026-10-01: three batch children timed out; the disk held subfinder/httpx/nuclei output (402 KB of nuclei
JSONL), full-git-history patches for 3 repos, the decoded malware payload, and two aderyn reports. That partial
output turned out to be the session's most valuable material.

Before redoing a timed-out child's work, ALWAYS harvest first:

```bash
ls -la <out_dir>/            # per child: did it create its output folder?
find <out_dir> -type f -newermt '-2 hours' | head -40
wc -c <out_dir>/*            # a 0-byte json + a populated sibling = tool ran but produced nothing
```

Then judge each artifact on its own: a `trufflehog.json` of 0 bytes WITH a populated `.stderr` means the tool ran
and found nothing; a 0-byte file with no stderr means it never started. Write the child's intended summary yourself
from the artifacts.

Design children so this is cheap: make each one write raw tool output to its own directory **first** and reason
afterwards, and put the output path in the task so the artifacts are findable. A child whose only product is prose
in its final message loses everything on timeout.

