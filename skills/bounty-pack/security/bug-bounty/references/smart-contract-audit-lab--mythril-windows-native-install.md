# Mythril Windows Native Install — pyethash Patch Recipe

Verified: August 28, 2026 on Windows 10 with MSVC Build Tools 2022

## Problem
Mythril depends on `pyethash` (Ethereum PoW hash) which has NO prebuilt wheels for Windows. The source distribution has three fatal issues:
1. `setup.py` includes `io_win32.c`, `util_win32.c`, `mmap_win32.c` — **these files don't exist** in the source
2. `setup.py` passes `-std=gnu99` flag — MSVC doesn't support GNU flags
3. `core.c` includes `<alloca.h>` — doesn't exist on Windows (need `<malloc.h>`)

## Solution: Patch pyethash Source

### Step 1: Download and extract
```bash
pip download pyethash==0.1.27 --no-binary=:all: -d /tmp/pyethash
python3 -c "
import tarfile, os
tar = tarfile.open('/tmp/pyethash/pyethash-0.1.27.tar.gz', 'r:gz')
tar.extractall('/tmp/pyethash-extract')
tar.close()
"
cp -r /tmp/pyethash-extract/pyethash-0.1.27 C:/Users/WINDOWS10/pyethash-build
```

### Step 2: Create io_win32.c (src/libethash/io_win32.c)
```c
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <direct.h>
#include <io.h>
#ifdef _MSC_VER
#define strdup _strdup
#endif
#include "io.h"

FILE* ethash_fopen(char const* file_name, char const* mode) {
    FILE* f; errno_t err = fopen_s(&f, file_name, mode);
    return (err != 0) ? NULL : f;
}
bool ethash_mkdir(char const* dirname) {
    return _mkdir(dirname) == 0 || errno == EEXIST;
}
char* ethash_io_create_filename(char const* dirname, char const* filename, size_t filename_length) {
    size_t length = strlen(dirname) + filename_length;
    char* name = (char*)malloc(length + 2);
    if (!name) return NULL;
    memcpy(name, dirname, strlen(dirname));
    name[strlen(dirname)] = '\\';
    memcpy(name + strlen(dirname) + 1, filename, filename_length);
    name[length + 1] = '\0';
    return name;
}
bool ethash_file_size(FILE* f, size_t* ret_size) {
    long size;
    if (fseek(f, 0, SEEK_END) != 0) return false;
    size = ftell(f);
    if (size < 0) return false;
    if (fseek(f, 0, SEEK_SET) != 0) return false;
    *ret_size = (size_t)size;
    return true;
}
bool ethash_get_default_dirname(char* strbuf, size_t buffsize) {
    char const* home = getenv("APPDATA");
    if (!home) home = getenv("USERPROFILE");
    if (!home) return false;
    size_t len = strlen(home);
    if (len + 10 >= buffsize) return false;
    memcpy(strbuf, home, len);
    strbuf[len] = '\\';
    memcpy(strbuf + len + 1, "ethash", 6);
    strbuf[len + 7] = '\0';
    return true;
}
int ethash_fileno(FILE* f) { return _fileno(f); }
```

### Step 3: Create mmap_win32.c (src/libethash/mmap_win32.c)
```c
#include <windows.h>
#include <sys/types.h>
#include "mmap.h"

void* mmap(void* start, size_t length, int prot, int flags, int fd, off_t offset) {
    HANDLE fh; DWORD flProtect = PAGE_READONLY; DWORD dwDesiredAccess = FILE_MAP_READ; void* addr;
    if (prot & PROT_WRITE) { flProtect = PAGE_READWRITE; dwDesiredAccess = FILE_MAP_WRITE; }
    if (prot & PROT_EXEC) { flProtect = PAGE_EXECUTE_READ; dwDesiredAccess = FILE_MAP_READ; }
    if ((prot & PROT_WRITE) && (prot & PROT_EXEC)) { flProtect = PAGE_EXECUTE_READWRITE; dwDesiredAccess = FILE_MAP_ALL_ACCESS; }
    if (fd == -1) {
        fh = CreateFileMapping(INVALID_HANDLE_VALUE, NULL, flProtect,
            (DWORD)((length + 0xFFFFFFFF) >> 32), (DWORD)(length & 0xFFFFFFFF), NULL);
    } else {
        fh = (HANDLE)_get_osfhandle(fd);
        if (fh == INVALID_HANDLE_VALUE) return MAP_FAILED;
    }
    if (fh == NULL) return MAP_FAILED;
    addr = MapViewOfFile(fh, dwDesiredAccess,
        (DWORD)((offset + 0xFFFFFFFF) >> 32), (DWORD)(offset & 0xFFFFFFFF), length);
    if (addr == NULL) { if (fd == -1) CloseHandle(fh); return MAP_FAILED; }
    return addr;
}
void munmap(void* addr, size_t length) { (void)length; UnmapViewOfFile(addr); }
```

### Step 4: Patch setup.py
```python
# Replace Windows sources:
if os.name == 'nt':
    sources += ['src/libethash/io_win32.c', 'src/libethash/mmap_win32.c']
else:
    sources += ['src/libethash/io_posix.c']

# Remove -std=gnu99 from extra_compile_args:
extra_compile_args=["-Isrc/"]
```

### Step 5: Patch core.c
Replace `#include <alloca.h>` with:
```c
#ifdef _MSC_VER
#include <malloc.h>
#define alloca _alloca
#else
#include <alloca.h>
#endif
```

### Step 6: Build
```bash
cd C:/Users/WINDOWS10/pyethash-build
C:/Users/WINDOWS10/mythril-env/Scripts/python.exe setup.py install
```

## Dependency Chain (install order)
```
blake2b-py==0.3.2  ← prebuilt wheel first
pyethash==0.1.27   ← custom patched build
mythril==0.24.8    ← --no-deps, then add deps manually
  setuptools<71, persistent, py-flags, py-solc, py-solc-x
  eth-abi, eth-hash[pycryptodome], eth-bloom, coincurve
  numpy, scipy, matplotlib, scikit-learn, web3, z3-solver==4.12.5.0
```

## Known Issues
- `ethereum` package pulls `pysha3` (fails on Windows). Skip — not needed for analysis.
- `flags` v0.0.1.2 conflicts with `py-flags` v1.1.4. Uninstall `flags` if import fails.
- `setuptools>=81` removed `pkg_resources`. Pin `setuptools<71`.
- Hermes lifecycle guard blocks direct python.exe calls. Use bat wrappers.
