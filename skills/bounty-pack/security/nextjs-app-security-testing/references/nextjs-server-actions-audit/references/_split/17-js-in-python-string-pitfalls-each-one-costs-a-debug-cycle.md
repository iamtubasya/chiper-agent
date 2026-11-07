## JS-in-Python string pitfalls (each one costs a debug cycle)

- **git-bash / MSYS silently rewrites a leading-slash argument into a Windows path.** On this
  host a bare `/api/...` value — and even a curl `-w` label like `/api/foo -> %{http_code}` —
  becomes `/home/agentuser/.../git/api/...`, so the request or the printed label is wrong and
  reads like a real result. Prefix each call with `MSYS_NO_PATHCONV=1` (or avoid bare
  leading-slash args) for every curl / harness invocation on Windows.

- Inside `page.evaluate("""() => …""")` you are writing JAVASCRIPT: `" ".join(x.split())`,
  `len(x)` and `str(x)[:200]` raise `TypeError: " ".join is not a function`. Use
  `x.split(String.fromCharCode(10)).join(' ')`, `.length`, `.slice(0,200)`.
- In `act.json` files JSON forbids `\.`, so a regex like `/\.xls/` invalidates the whole file
  (`Invalid \escape`). Write `[.]xls` or `\\.`.
- Never build act/action JSON with `printf`/heredoc — backslashes and control characters get
  mangled. Use the file tool, then run the runner.

