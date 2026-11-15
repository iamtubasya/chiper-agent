# Windows: Node_modules Deletion Pitfall

## The Problem
On Windows (Git Bash / MSYS), `rm -rf` on `node_modules` folders (especially large monorepos like Hardhat, Truffle, or Foundry with deeply nested symlinks, read-only files, and npm lockfiles) frequently fails with:

```
rm: cannot remove '.../node_modules/...': Permission denied
```

This happens even after killing all running processes — Windows file indexing (SearchIndexer), antivirus scanners, or lingering file locks from closed-but-not-released terminal processes can hold file handles.

## The Fix
Use the native Windows `rmdir` command via `cmd` instead of bash `rm`:

```bash
# Step 1 (optional): Remove hidden/system/read-only attributes recursively
attrib -r -s -h /s /d 2>&1 | head -3

# Step 2: Delete using native cmd rmdir (unblocks Windows file locks)
cmd /c rmdir /s /q "D:\\data hermes\\bugbounty\\target-repo" 2>&1
```

### MSYS `cmd //c` path caveat
MSYS automatically converts `D:/path/to/dir` to `C:\D:\path\to\dir` — always pass the Windows path in `\\` backslash format inside double quotes:
```bash
# WRONG — MSYS converts to invalid C:\D:... path
cmd //c "rmdir /s /q D:/data hermes/bugbounty/paxos"

# CORRECT
cmd /c rmdir /s /q "D:\\data hermes\\bugbounty\\paxos"
```

## When to Use
- After a target scan is abandoned (user says "delete this target" or "switch target")
- `rm -rf` fails with Permission Denied on node_modules
- Any large cloned repo that needs full recursive deletion on Windows

## Fallback
If `cmd /c rmdir /s /q` also fails:
1. Check `tasklist | grep -i node` — kill orphaned node processes
2. Open Task Manager → Details → kill `SearchIndexer.exe` temporarily
3. Retry `cmd /c rmdir /s /q`
4. Last resort: reboot, then delete

## Background TOOL processes hold audit output files (WinError 32)

The same lock class bites audit workspaces, not just `node_modules`. Long-running tools started
with `terminal(background=true)` keep their output file open after the tracked session is killed —
`nuclei.exe` and `interactsh-client.exe` both did this in one session (2026-10-17): the process
registry said "killed" but the OS process lived on and held `scans/nuclei-all.txt` /
`scans/interactsh.log`, so `shutil.move(workspace, quarantine)` failed with
`PermissionError: [WinError 32]`.

Fix — kill by IMAGE NAME before any move/delete of an audit workspace:

```bash
tasklist //FI "IMAGENAME eq nuclei.exe"        # confirm first
taskkill //F //IM nuclei.exe //T               # //T = child tree
taskkill //F //IM interactsh-client.exe //T
```

Then verify no task matches before proceeding.

## Abort-mid-engagement: QUARANTINE, never destroy (standing owner rule)

When the user says "abort / ganti target / hapus hasil audit" (happened 3× in one session:
CoderPad, Abhieo, Vesync), the correct sequence is:

1. Kill background tool processes by image name (above).
2. Build the manifest FIRST: walk the workspace, record `relpath + size + sha256` per file into
   `MANIFEST.json` with timestamp, source, destination, and the user's reason verbatim.
3. `shutil.move(workspace, _QUARANTINE/<target>_<YYYYmmdd_HHMMSS>/workspace)`.
4. **Verify copy completeness before removing anything** — compare inventories (relpath+hash) of
   source vs quarantine copy. `shutil.move` falls back to copy+`rmtree`, and a mid-run lock can
   leave the source PARTIALLY DELETED (observed: source down to 3 files, copy complete at 19 —
   the copy is the recovery artifact, the partial source is not). Complete any missing/differing
   files from the copy, then `shutil.rmtree(src)` and assert `not os.path.exists(src)`.
5. Rewrite the manifest with the final file list so recovery is exact.

Quarantine root: `D:/data hermes/_QUARANTINE/`. This is recoverable-by-design; a hard purge needs
a separate explicit user instruction.
