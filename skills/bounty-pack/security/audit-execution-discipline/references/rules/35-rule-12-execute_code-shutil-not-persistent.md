## ⛔ RULE 12: execute_code shutil Not Persistent

**User correction (2026-09-22): "execute_code shutil.copy2 tidak persistent — gunakan terminal cp untuk file copy"**

`execute_code` runs in a sandboxed Python kernel. Files created/modified via `shutil.copy2()`, `write_file()` inside `execute_code` **may not persist to disk** — the script reports success but the file doesn't actually exist when checked via `terminal`.

**FORBIDDEN for file operations:**
- ❌ `shutil.copy2(src, dst)` in execute_code
- ❌ `os.rename()` in execute_code
- ❌ `open(path, 'w').write()` in execute_code

**REQUIRED:**
- ✅ Use `terminal(command="cp src dst")` for file copy
- ✅ Use `terminal(command="mv src dst")` for file move
- ✅ Use `write_file()` tool (NOT execute_code) for file creation
- ✅ Verify with `terminal(command="ls -la path")` after any file op

**Why:** The execute_code kernel has a separate filesystem view. Writes may succeed in-kernel but not flush to the host disk. The `terminal` tool runs directly on the host filesystem.

