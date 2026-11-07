# Search Engine Fallback Chain (when the primary engine blocks)

Search engines aggressively bot-block headless/curl requests. Symptom: `html.duckduckgo.com`
returns the body **"Unfortunately, bots use DuckDuckGo too"** with a duck-selection CAPTCHA,
and `lite.duckduckgo.com` returns the same behind an `error-lite+...@duckduckgo.com` code.
Degraded queries also return generic *homepage* results (openai.com, wikipedia.org) instead
of topical ones — that's the tell that the engine didn't actually search.

## Escalation order

1. **Bing via curl + HTML parse** — most reliable, no JS, no captcha at low volume.
   ```bash
   curl -sL --max-time 25 \
     -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36" \
     "https://www.bing.com/search?q=<url+encoded>&count=20" -o bing.html
   ```
   Quick title-only extract (works when the result markup is `<h2>`-based):
   ```bash
   grep -oE '<h2[^>]*>.*?</h2>' bing.html | sed -E 's/<[^>]*>//g' | head -15
   ```
   Full title + snippet + URL (robust, handles multiline blocks) — pipe into python3:
   ```python
   import re, html
   s = open('bing.html', encoding='utf-8', errors='ignore').read()
   for it in re.findall(r'<li class="b_algo".*?</li>', s, re.S)[:12]:
       t = re.search(r'<h2[^>]*>(.*?)</h2>', it, re.S)
       p = re.search(r'<p[^>]*>(.*?)</p>', it, re.S)
       c = lambda x: html.unescape(re.sub(r'<[^>]+>', '', x)).strip() if x else ''
       if t: print('-', c(t.group(1)))
       if p: print('  ', c(p.group(1))[:220])
   ```
2. **Bing in the browser + DOM query** — when curl parse returns junk, navigate to the
   Bing search URL and read results out of the live DOM:
   ```js
   Array.from(document.querySelectorAll('li.b_algo')).slice(0,15).map(li => {
     const a = li.querySelector('h2 a');
     const p = li.querySelector('li p, p');
     return (a ? a.innerText : '') + ' :: ' + (a ? a.href : '') + ' :: ' + (p ? p.innerText : '');
   }).join('\n\n')
   ```
   Note: Bing `href`s are wrapped in `/ck/a?...&u=a1<base64url>` redirects. The target URL
   is base64url in the `u=a1...` param; the innerText usually names the real site anyway.
3. **Marginalia** (`search.marginalia.nu`) — no bot-block, but indexes a small indie web;
   useful for niche/technical queries, useless for mainstream "how do I X" questions.
4. **Fetch a known source directly with curl** — when search fails entirely, go straight to
   a site known to have the data. `curl -sL ... | sed 's/<[^>]*>//g'` on a listicle/blog
   can yield the whole article. This was the actual win in the session: search was blocked
   end-to-end, but fetching `whop.com/blog/ai-side-hustles/` and grepping `<h2>`/`<h3>`
   returned a complete, concrete 21-item list with tools and dollar figures.

## Pitfalls
- **Don't fabricate results when search is blocked.** Degraded/generic engine output is a
  failure signal, not data. Say the engine blocked, then escalate or fetch the source URL.
- `html.duckduckgo.com` + `lite.duckduckgo.com` both CAPTCHA. Don't retry the same engine;
  move to step 1.
- Google `?num=20` via curl returns near-empty HTML (JS-rendered) — skip it, use Bing.
- Bing sometimes serves results where every entry is a generic homepage. Treat as blocked
  and go to a direct source fetch rather than reporting those as findings.
- Set a short `--max-time 20-25`; dead/slow sources otherwise stall the whole research loop.

## Delegate-task caveat
`delegate_task` subagents do not reliably drive web_search — in the session all three
research subagents returned only their *intended* tool-call text instead of results
(`api_calls: 1`, `tool_trace: []`). Do the curl/Bing fetch in the main session and hand
subagents a concrete source URL to summarize, rather than delegating "go search for X".
