# Runtime-bound tools — Ruby and Perl on Windows

Companion to RULE 1b (matrix → batch by method). The last batch is **runtime-bound**: these
tools are written in a scripting language, so a missing interpreter makes the whole batch
un-runnable — not broken, just un-translated. Both runtimes were stood up and verified
2026-10-07; the CMS/perl batch went from impossible to 3 working tools.

---

## Ruby — silent install (RubyInstaller + DevKit)

Windows Ruby comes from RubyInstaller; the **devkit** build is required for any gem that
compiles a native extension. Pick the x64 devkit asset (arm64 also published — don't grab it):

```bash
curl -sL https://api.github.com/repos/oneclick/rubyinstaller2/releases/latest \
  | grep -oE '"browser_download_url": *"[^"]+\.exe"' | cut -d'"' -f4
#  -> rubyinstaller-devkit-<ver>-x64.exe     <- take THIS one
```

It is an **Inno Setup** installer, so silent install works (this is the durable part — the
installer itself is interactive):

```bash
MSYS_NO_PATHCONV=1 cmd /c "ruby-devkit.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART \
  /DIR=D:\\Ruby40 /TASKS=modifypath,associate.rb"
```

- `MSYS_NO_PATHCONV=1` — otherwise MSYS rewrites `/VERYSILENT` into a bogus path.
- `/DIR=D:\Ruby40` keeps ~150 MB off a tight C: drive.
- `/TASKS=modifypath` appends `D:\Ruby40\bin` to the **Windows** PATH (verify with
  `cmd /c "echo %PATH%" | tr ';' '\n' | grep -i ruby`). No restart needed.

Verify: `D:/Ruby40/bin/ruby.exe --version` and `cmd /c "D:\\Ruby40\\bin\\gem.cmd --version"`.
**gem is `gem.cmd`, not `gem.exe`** — a bash `-f gem.exe` test falsely reports MISSING.

### Two classes of gem — check before promising a tool

| gem kind | example | consequence |
|---|---|---|
| **pure Ruby** | `addressable`, `ipaddr`, `public_suffix` | installs anywhere, no compiler |
| **native extension** | `yajl-ruby` (wpscan's JSON dep) | needs the devkit toolchain; can hard-fail on a new Ruby |

```bash
MSYS_NO_PATHCONV=1 cmd /c "D:\\Ruby40\\bin\\gem.cmd install addressable ipaddr --no-document"
```

### DevKit: initialise it once

```bash
MSYS_NO_PATHCONV=1 cmd /c "D:\\Ruby40\\bin\\ridk.cmd install 3"      # MSYS2 base + toolchain
MSYS_NO_PATHCONV=1 cmd /c "D:\\Ruby40\\bin\\ridk.cmd exec gem install <gem>"   # build WITH devkit env
```

Toolchain lives at `D:\Ruby40\msys64\ucrt64\bin\gcc.exe` (**ucrt64**, not mingw64).

⚠️ **`ridk install 3` does NOT fix `ruby.h: No such file or directory`, and neither does
`ridk exec`, nor `--with-cppflags`, nor `--platform x64-mingw-ucrt`.** All four were tried and
all four failed on 2026-10-07. See the next section for what actually causes it.

### ⛔ `ruby.h: No such file or directory` — the real cause is the generated Makefile

Not the devkit, not the include path, not the Ruby version. **mkmf writes the include dirs in
MSYS form** (`topdir = /D/Ruby40/include/ruby-4.0.0`). When `make` runs through cmd the path
reaches gcc verbatim, and Windows gcc cannot resolve `/D/...`; run the very same gcc from MSYS
bash and it works, because the MSYS runtime rewrites the path first. That asymmetry is why this
looks like an environment problem when it is a *text* problem.

**The tell:** the C files that do not `#include <ruby.h>` compile fine while the one that does
fails — the compiler is working, its search path is not.

**The fix — rewrite the paths, then build:**

```bat
ruby.exe extconf.rb
powershell -NoProfile -Command "(Get-Content Makefile) -replace '/D/Ruby40','D:/Ruby40' | Set-Content Makefile"
ridk.cmd exec make
ridk.cmd exec make install
```

Re-runnable: **`scripts/fix-gem-ext.bat <gem-name> <version> [ext-subdir]`** does all of the
above plus the registration step below.

**Also run `make` serially to see the error.** gem builds with `-j5`; the real failure scrolls off
and the log ends on a bare `make failed, exit code 2` after nothing but warnings. Re-running
`ridk exec make` by hand in the ext dir surfaces `fatal error: ruby.h: No such file`.

### Registering a hand-built gem (4 more things, in order)

Building the `.so` is only half of it. A manually-built gem must also satisfy RubyGems, or
activation fails with `Could not find '<gem>' (~> x.y) among N total gem(s)` **even though the
files are on disk and `require` works**:

1. **`.so` on the load path.** `make install` may drop it in a subdir
   (`site_ruby/<ver>/x64-ucrt/<gem>/<gem>.so`); `require '<gem>'` then misses it. Copy it up one
   level to `site_ruby/<ver>/x64-ucrt/<gem>.so`.
2. **Write `gem.build_complete`.** Without it RubyGems prints
   `Ignoring <gem>-<ver> because its extensions are not built. Try: gem pristine ...` and treats
   the gem as absent. Carry the `.so` into
   `gems/4.0.0/extensions/x64-mingw-ucrt/4.0.0/<gem>-<ver>/` and touch `gem.build_complete`
   there. (`fix-gem-ext.bat` step 4.)
3. **Stub gemspec.** A gem whose install aborted mid-build has files but **no
   `specifications/<gem>-<ver>.gemspec`**, so dependency activation still fails. Copy the shape of
   a real one — `name`, `version`, `require_paths`, `extensions = []`, plus any runtime deps the
   gem declares — into `specifications/<gem>-<ver>.gemspec`. Done for `yajl-ruby` and
   `websocket-driver`.
4. **Install downstream gems with `--ignore-dependencies`.** Once a dep is hand-built,
   `gem install <dependent>` still tries to rebuild it and aborts the whole install. Install the
   dependent's other deps normally, then
   `gem install <dependent> --no-document --ignore-dependencies` (used for `ferrum`).

### `libcurl` — ethon needs an FFI-loadable DLL
### (LoadError 126 is a *dependency* problem, not a missing file)

`ethon`/`FFI` looks for `libcurl.dll`. Both `Errno 126` variants mean the file was found but its
own deps were not — so **do not** fix it by copying the MSYS/git-bash DLL:

| source | result |
|---|---|
| `git/mingw64/bin/libcurl-4.dll` copied + renamed | ❌ `Failed with error 126` — MSVCRT build, deps unfindable by a ucrt64 Ruby |
| **`curl.se/windows` `libcurl-x64.dll`** (UCRT/MSVC, self-contained) | ✅ loads |

```bash
curl -sL https://curl.se/windows/ | grep -oE 'href="[^"]*win64-mingw\.zip"'   # note: NOT win64a
# -> dl-<ver>/curl-<ver>-win64-mingw.zip ; extract, then:
cp bin/libcurl-x64.dll D:/Ruby40/bin/libcurl.dll      # FFI asks for "libcurl"
cp bin/libcurl-x64.dll D:/Ruby40/bin/                 # ...and sometimes by real name
```

Verify with FFI directly rather than through wpscan (faster, isolates the failure):

```ruby
require 'ffi'
FFI::DynamicLibrary.open("libcurl", FFI::DynamicLibrary::RTLD_LAZY | FFI::DynamicLibrary::RTLD_GLOBAL)
```


### Tools that need Ruby

| tool | outcome 2026-10-07 | notes |
|---|---|---|
| **WhatWeb** | ✅ WORKS | pure gems only (`addressable`, `ipaddr`, `public_suffix`). Shim runs the `whatweb` script directly: `ruby.exe "<repo>/whatweb" %*`. High value — fingerprinting drives which vuln class to chase. |
| **wpscan** | ✅ WORKS 4.1.0 | needed `yajl-ruby` (2019 native gem) — **not** a Ruby-version problem. Fixed in place on Ruby 4.0 via the Makefile-path patch, two stub gemspecs, and one DLL swap. See the chain below. |

### wpscan on Ruby 4.0 — the actual six-layer chain

Every layer reported a *different* plausible-looking error, which is why "just install an older
Ruby" is the tempting wrong answer. It is not needed; each layer has a real fix:

| # | Symptom | Real cause | Fix |
|---|---|---|---|
| 1 | `yajl-ruby`: `make failed, exit code 2` / `ruby.h: No such file` | Makefile carries MSYS paths | `scripts/fix-gem-ext.bat yajl-ruby 1.4.3` |
| 2 | `require 'yajl'` → cannot load | `.so` landed in a subdir | copy to `<sitearchdir>/yajl.so` |
| 3 | `Could not find 'yajl-ruby' (~> 1.4.1)` | manual build has no spec | stub `specifications/yajl-ruby-1.4.3.gemspec` |
| 4 | `websocket-driver` (ferrum's dep) builds and fails the same way | same Makefile problem | `fix-gem-ext.bat websocket-driver 0.8.2` + stub spec |
| 5 | `gem install ferrum` still fails | it rebuilds `websocket-driver`, aborting itself | install other deps, then `ferrum --ignore-dependencies` |
| 6 | `Could not open library 'libcurl'` (e126) | `ethon` loads libcurl via FFI; mingw64 build incompatible | `libcurl-x64.dll` from curl.se → `D:/Ruby40/bin/libcurl.dll` |
| — | `Could not find 'fiddle' (~> 1.1)` | **fiddle is no longer a default gem in Ruby 4.0** | `fix-gem-ext.bat fiddle 1.1.8` + stub spec |

The wpscan shim must also prepend the mingw64 runtime dir so libcurl's own deps resolve:

```bat
@echo off
set PATH=~/.chiper/git/mingw64/bin;D:\Ruby40\bin;%PATH%
cd /d "D:\Ruby40\bin"
"D:\Ruby40\bin\ruby.exe" "D:\Ruby40\bin\wpscan" %*
```

Probe: `wpscan --version` → the `WordPress Security Scanner` banner, rc=0.

**Do not record this as "wpscan is broken", and do not lead with a Ruby-version downgrade** —
that costs a ~150 MB side-by-side install and does not address the actual defect. The Makefile
path patch is the fix; the version just determines which gems hit it.


---

## Perl — install modules when `cpan` is dead

The git-bash / MSYS2 perl (`perl -V:archname` → `x86_64-cygwin-thread-multi`) ships a **broken
`cpan`**: any invocation dies with
`Compilation failed in require at /usr/share/perl5/core_perl/App/Cpan.pm line 290`.
`pacman` is absent too, so the package-manager route is out.

**But pure-Perl modules don't need cpan at all — copy the `.pm` into `@INC`:**

```bash
perl -e 'print "$_\n" for @INC'        # e.g. /usr/share/perl5/site_perl
curl -sL -o /tmp/m.tar.gz https://cpan.metacpan.org/authors/id/<A>/<B>/<DIST>-<ver>.tar.gz
cd /tmp && tar xzf m.tar.gz            # NOTE: pure-Perl dists often unpack the .pm at the ROOT,
                                       # not under lib/ — check with `find . -name '*.pm'`
mkdir -p /usr/share/perl5/site_perl/<Namespace>
cp <Mod>.pm /usr/share/perl5/site_perl/<Namespace>/<Mod>.pm
perl -M<Namespace>::<Mod> -e 'print "OK\n"'
```

Concrete: `XML::Writer` (required by nikto) →
`https://cpan.metacpan.org/authors/id/J/JO/JOSEPHW/XML-Writer-0.900.tar.gz`,
then `Writer.pm` → `site_perl/XML/Writer.pm`.

### nikto — end-to-end

1. **Re-clone if AV was ever enabled.** Defender does not only *lock* a payload-bearing file, it
   can **delete** it: after the earlier `Errno 22`, `nikto/program/nikto.pl` was gone entirely
   (`No such file or directory`). `rm -rf` the repo and clone again once AV is off.
2. Install `XML::Writer` (above) — nikto hard-exits `ERROR: Required module not found`.
3. **Create the config**: the repo ships `nikto.conf.default` only. Copy it to `nikto.conf`
   next to `nikto.pl` (and `~/.nikto/nikto.conf`). Without it:
   `Could not find a valid nikto config file`.
4. **The shim must `cd` into the program dir** — nikto resolves its plugin/database paths from
   the working directory, so a bare `perl <abs-path>\nikto.pl` run from elsewhere fails the
   config lookup even with the file present:

```bat
@echo off
cd /d "D:\data hermes\tools\web2\nikto\program"
perl "D:\data hermes\tools\web2\nikto\program\nikto.pl" %*
```

Probe: `nikto -Version` → `Nikto 2.6.1 (LW 2.5)`, rc=0. Same `cd`-in-shim rule applies to
**joomscan** and any repo whose script resolves sibling `plugins/`/`databases/` dirs.

---

## Fold the runtime batch into the matrix

Add these to `scripts/tool-coverage-matrix.py`'s search dirs so a re-run sees them:
`D:/Ruby40/bin`, `~/.gem/ruby/<ver>/bin`, and the Python `Scripts/` dir (where the shims live).
Without that the matrix keeps reporting false MISSING for Ruby/Perl tools that work.

## Wiring the results into the router

New classes worth routing (they were reachable only by hand before):
`fingerprint` → whatweb · `scanner` → nikto · `cms-scan` → wpscan · `cms-scan-joomla` → joomscan.
Register each tool in the router's `TOOL_PATHS` **and** give it a route, or the tool exists but
is never invoked — see `audit-execution-discipline` for the enforcement side.

Three things bite when adding routes to `tool_router.py`:

1. **Dispatch order — a new class silently loses to an earlier prefix match.** `route_and_run` is
   a chain of `if cid == ...` / `cid.startswith(...)` blocks, so a new table placed at the end
   never runs for names an earlier branch already claims. `xss-deep` looked routed to xsstrike but
   actually ran dalfox, because the existing `if cid.startswith("xss")` sits above it. **Check the
   earlier branches for prefix collisions, and put dedicated-tool dispatch ABOVE the generic
   nuclei-tag block** so a specific tool wins over a tag fallback.
2. **Verify by invoking, not by reading.** Call `route_and_run` per class and assert
   `result["tool"]` is the *expected* tool and `evidence_file` exists on disk — 14/14 classes were
   checked this way; the collision in (1) was only visible because the assertion named the tool.
3. **A tool that needs args you cannot invent is not a route.** `ysoserial` (gadget class name),
   `patator` (user/pass wordlists), `websocat` (interactive socket), `grpcurl` (service list) and
   `kr` (wordlist) cannot be driven from a bare target. Record the exact invocation in the
   evidence/note instead of emitting a vague skip — honest "needs a harness", not a fake pass.

`TOOL_PATHS` entries may point at the `.bat` shims (`SCRIPTS/"<tool>.bat"`); the router invokes
with `shell=True`, so those resolve.

