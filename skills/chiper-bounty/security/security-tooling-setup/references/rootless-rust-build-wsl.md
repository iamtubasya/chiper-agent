# Building a Rust/deno_core service rootlessly in WSL (no sudo, no system packages)

Written for auditing `lit-actions` (the Deno-based Lit Actions sandbox: `deno_core =0.401.0`,
`deno_runtime =0.256.0`, `v8 149.2.0`), but the chain is generic to any Rust crate that pulls
`tonic-build` / `bindgen` / `openssl-sys`. Every step below works **without root** — the trick is
`apt-get download` + `dpkg-deb -x` into `$HOME` instead of `apt-get install`.

Budget: ~45 min of wall clock on 2 vCPU, of which the first ~20 min is dependency fetch/compile and
the last linker step is seconds IF you set `CARGO_PROFILE_DEV_DEBUG=0` (see §5 — this is the one
thing that actually blocks you).

## 0. Measure the host first, and raise the WSL cap deliberately

```bash
wsl -d Ubuntu -- /bin/sh -c 'nproc; free -m | sed -n 2p; df -h / | tail -1; . /etc/os-release; echo $PRETTY_NAME'
```

A 1 GB WSL cap (an audit-time default set to keep `vmmem` from starving a 6 GB host) cannot build
this. Back up and raise it, then **restore it afterwards**:

```bash
cp ~/.wslconfig ~/.wslconfig.bak_litbuild
printf '[wsl2]\nmemory=3500MB\nprocessors=2\nswap=2048MB\n' > ~/.wslconfig
wsl --shutdown          # required — .wslconfig is read at VM boot
```

Also put the source on the **ext4** filesystem, never `/mnt/c`: `cargo` over 9P is several times
slower and the target dir grows past 10 GB. Copy a tarball in:

```bash
cd <repo> && tar czf /tmp/src.tgz --exclude='*/target' --exclude='*/.git' lit-actions lit-core vendor
MSYS_NO_PATHCONV=1 wsl -d Ubuntu -- bash -c 'mkdir -p ~/chipotle && tar xzf /mnt/c/.../src.tgz -C ~/chipotle'
```

`MSYS_NO_PATHCONV=1` is mandatory for the `/mnt/c` path (see RULE 2b/2c in the parent skill).

## 1. `protoc` — tonic-build

Anything with `build.rs` calling `tonic_build::compile_protos` needs a protoc binary AND
`PROTOC` pointing at it (the crate shells out and does not search `PATH` reliably).

```bash
mkdir -p ~/.local/bin && cd /tmp
curl -sSL -o protoc.zip https://github.com/protocolbuffers/protobuf/releases/download/v25.3/protoc-25.3-linux-x86_64.zip
python3 -c "import zipfile;zipfile.ZipFile('protoc.zip').extractall('protocdir')"
cp protocdir/bin/protoc ~/.local/bin/ && chmod +x ~/.local/bin/protoc
export PROTOC=$HOME/.local/bin/protoc
```

## 2. `libclang` + `libLLVM` — bindgen (e.g. via `libsqlite3-sys`)

`bindgen` needs the *shared library*, not just headers, and this is the error you will see:

```
Unable to find libclang: "couldn't find any valid shared libraries matching: ['libclang.so', …]"
```

Extract both packages — `libclang-18.so.1` links `libLLVM.so.18.1`, so libclang alone gives the
**second** failure (`could not be opened: libLLVM.so.18.1: cannot open shared object file`):

```bash
ROOT=$HOME/clangroot; mkdir -p "$ROOT"; cd "$ROOT"
apt-get download libclang1-18 libllvm18        # no root needed for `download`
for f in *.deb; do dpkg-deb -x "$f" "$ROOT"; done
export CLANG_ROOT=$ROOT/usr/lib/x86_64-linux-gnu
export LIBCLANG_PATH=$CLANG_ROOT
export LD_LIBRARY_PATH=$CLANG_ROOT:${LD_LIBRARY_PATH:-}
ln -sf "$CLANG_ROOT/libclang-18.so.1" "$CLANG_ROOT/libclang.so"
ldd "$CLANG_ROOT/libclang-18.so.1" | grep 'not found' || echo "all deps resolved"
```

Verify with `ldd` before building — "all deps resolved" is the gate, not "the file exists".

## 3. `BINDGEN_EXTRA_CLANG_ARGS` — libclang cannot find libc headers on its own

The next failure after libclang is fixed:

```
sqlite3/sqlite3.h:35:10: fatal error: 'stdarg.h' file not found
```

libclang does not inherit gcc's builtin include path. Point it at the distro's gcc + multiarch dirs
(check the version — it is `13` on Ubuntu 24.04):

```bash
export BINDGEN_EXTRA_CLANG_ARGS="-I/usr/include -I/usr/include/x86_64-linux-gnu -I/usr/lib/gcc/x86_64-linux-gnu/13/include"
```

## 4. `openssl-sys` — needs pkg-config, headers and libs

```
Could not find directory of OpenSSL installation … requires the `pkg-config` utility
```

Same rootless pattern, and you must set all four vars because there is no system install:

```bash
ROOT=$HOME/deproot; mkdir -p "$ROOT"; cd "$ROOT"
apt-get download libssl-dev pkgconf
for f in *.deb; do dpkg-deb -x "$f" "$ROOT"; done

export PATH=$ROOT/usr/bin:$PATH                       # gives you pkg-config
export OPENSSL_DIR=$ROOT/usr
export OPENSSL_LIB_DIR=$ROOT/usr/lib/x86_64-linux-gnu
export OPENSSL_INCLUDE_DIR=$ROOT/usr/include
export PKG_CONFIG_PATH=$ROOT/usr/lib/x86_64-linux-gnu/pkgconfig:$ROOT/usr/share/pkgconfig
pkg-config --modversion openssl      # confirm BEFORE building
```

## 5. ⛔ THE BLOCKER: full debug info makes `rust-lld` thrash for 30+ min and look hung

Symptom, and it is genuinely indistinguishable from a hung build by watching CPU alone:

- `rust-lld` sits at ~750 MB–850 MB RSS, load average ~5 on 2 vCPU, for **25+ minutes**
- `target/` grows (7 GB → 12 GB) but no `deps/<test-binary>` ever appears
- `cargo` prints nothing further; it is not stuck on the network
- a `deno_runtime` integration-test binary carries full DWARF and reaches **326 MB as a test binary**
  (316 MB for the server lib rlib) before linking

Fix — drop debug info for the dev profile. Symbols are irrelevant to assertions:

```bash
export CARGO_PROFILE_DEV_DEBUG=0
export CARGO_PROFILE_DEV_INCREMENTAL=false
export CARGO_BUILD_JOBS=2
```

After that the same final link finished in **24.6 s**. Do this **before** the first long build; if you
only add it after a thrash, `cargo` reuses the existing fingerprints and you may need
`cargo clean -p <crate>` (or just accept the rebuild).

## 6. Run the build DETACHED, and poll the log — a foreground wrapper dying hides all state

`wsl -d Ubuntu -- bash script.sh` invoked through the agent's terminal can be killed by the
wrapper/host before the build finishes, and then you have no idea whether the build is still alive.
Launch it into its own session with a log, then poll the log:

```bash
LOG=$HOME/build.log; : > "$LOG"
setsid nohup bash -c 'cargo build --tests >> '"$LOG"' 2>&1; echo "EXIT=$?" >> '"$LOG"' \
  >/dev/null 2>&1 < /dev/null &
```

Poll with a tiny script (avoid long sleeps inside a `wsl … -lc` call — they look identical to a hang):

```bash
grep -c '^   Compiling' $HOME/build.log; tail -6 $HOME/build.log
pgrep -a cargo >/dev/null && echo RUNNING || echo "cargo not running"
du -sh ~/chipotle/lit-actions/target; ls ~/chipotle/lit-actions/target/debug/deps | wc -l
```

**Progress signal, in order of usefulness:** `EXIT=` line in the log → presence of
`deps/<test-name>-<hash>` → `deps/` file count climbing → `target/` size. `target/` size alone is
misleading (it grows while linking and while thrashing).

Note: `wsl -d Ubuntu -- bash -lc '...'` sometimes returns
`Wsl/Service/WSAETIMEDOUT` / `A connection attempt failed …` when the VM is loaded. It is a
transport hiccup, not a dead build — re-issue with `/bin/sh -c` and pipe through `tr -d '\000'`,
and do **not** `wsl --shutdown` to "recover" mid-build.

## 7. Cleanup discipline

```bash
cp ~/.wslconfig.bak_litbuild ~/.wslconfig   # restore the audit-time memory cap
# target/ can be 10 GB+ on ext4; delete after the assertions are recorded
```

Record in the ledger what was **built** vs what was only **read**, and note the cargo profile used —
"tests pass" from a `debug=0` build is still valid for behavioural assertions, but say so.
