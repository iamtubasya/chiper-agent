# Reverse Engineering


## reverse-skill package (2026-10-21 — 12 skill RE)

### reverse-engineering
- Quick reference for RE challenges. For detailed techniques, see supporting files.
- pip install frida-tools angr qiling uncompyle6 capstone lief z3-solver
- For Python 3.9+ bytecode: build pycdc from source
- apt install gdb radare2 binutils strace ltrace apktool upx
- [field-notes.md](field-notes.md) - Quick reference notes: binary types, anti-debugging bypass, specialized patterns, CTF case notes
- Heap / ROP / kernel exploit after the binary is understood → `pwn-chain/`
- 1. **Start with strings extraction** - many easy challenges have plaintext flags
- 2. **Try ltrace/strace** - dynamic analysis often reveals flags without reversing

### ida-reverse
- 解决办法**：`start.ps1` 只在端口无人监听、或 `tools/list` 快速返回但缺 `py_eval`（旧 supervisor）时替换 managed supervisor；RPC 超时且 13337 仍在听视为忙，不杀。开库时 `open.ps1` 写 `opening.lock`，watchdog 不得 `-Force`
- 死锁例外**：`tools/list` **连续失败超过 3 分钟**（按 last-healthy 时间戳，不是进程创建时间），且没有 in-flight `opening.lock`、不是 GUI 占端口时，才 `-Force` 替换 supervisor，仍不杀 `ida.exe`
- 解决办法**：`run-supervisor.py` 把 HTTP 换成 `ThreadingHTTPServer` 并接受 GET `/mcp`；补丁失败则跳过并仍启动 supervisor。卡住时用 `scripts/recover.ps1`（立刻 `-Force`）
- tools/list` **连续失败超过 3 分钟**（last-healthy 时间戳）且无 `opening.lock` → 视为死锁，输出 `INFO:deadlock` 并 `-Force` 替换 supervisor。进行中的 `idb_open` 和 GUI 不会走这条路径
- watchdog.ps1`：探测 13337；健康 reuse（并刷新 last-healthy）；GUI / `open.ps1` 开库锁 / last-healthy 未满 3 分钟的 busy → reuse；只有 `tools/list` 连续失败超过 3 分钟才 `start.ps1 -Force`
- recover.ps1`：立刻 `start.ps1 -Force`（不杀 `ida.exe`）。HTTP 客户端把 `idapro` 标成 error 时用这个
- idapro_trace_data_flow(addr, direction, max_depth)` — 数据流追踪（forward/backward）
- idapro_trace_data_flow(addr="关键地址", direction="backward", max_depth=5)

### apk-reverse
- description: 在 CLI 环境下做 Android APK 逆向时使用。适用于 APK 解包、Java 反编译、smali 修改、重打包、Frida 动态 Hook，以及按需切换到 so/native 分析。优先使用本机已安装的 jadx、apktool、frida、adb、ida-reverse、radare2。
- 端点提取/Frida 自适应等社区对照：../references/community-security-skills.md；动态分析须 scope 授权设备。
- Frida 设备检查、进程列举、spawn/attach 注入：`scripts/frida-run.ps1`
- pwsh -File "<skill-root>\apk-reverse\scripts\frida-run.ps1" -ListDevices
- pwsh -File "<skill-root>\apk-reverse\scripts\frida-run.ps1" -Usb -ListProcesses
- pwsh -File "<skill-root>\apk-reverse\scripts\frida-run.ps1" -Usb -Spawn -Package com.example.app -ScriptPath "D:\hooks\test.js"
- frida -U -f com.example.app -l hook.js
- frida-trace -U -f com.example.app -j '*!*certificate*'

### radare2
- 需动态分析 → `reverse-engineering/tools-dynamic.md`（Frida/GDB）

### firmware-pentest
- 1. **拿到一份固件文件**（.bin / .img / .trx / .chk / OTA zip），需要从零到 RCE
- | 仿真起来后做 Web/RCE 利用 | `pentest-tools/`、`attack-chain/` |
- └─ Stage 9: 二进制利用  ← AFL++ fuzz / 手工 PoC / ARM / MIPS payload
- ARM / MIPS payload 必须区分大小端（mipsel vs mipseb），别用错
- Stage 4 — 提取文件系统（Extracting Filesystem）
- 详见 `references/extraction-methodology.md`。
- ubireader_extract_files rootfs.ubi # UBI
- grep -rE "(password|passwd|admin|secret|api_key|token)=" squashfs-root/

### dotnet-reverse
- | 混淆器识别 | **Detect It Easy (DIE)** / **file** | 先判断壳类型再决定 de4dot 参数 |
- diec target.exe                        # Detect It Easy CLI
- de4dot --detect target.exe             # 看它识别成什么

### malware-analysis
- description: Use when analyzing suspected malware through static, dynamic, and behavioral techniques, including IOC extraction, YARA or Sigma rules, sandboxing, and anti-analysis behavior.
- diec sample.exe                      # Detect It Easy（壳/编译器识别）
- □ P0：strings 空 → 串解密例程 + 宽字符串 UTF-16（E-string-decrypt / E-wide-strings）
- □ P0：可疑签名 → SigCheck；无效/吊销不降威胁（E-sig-forge）
- mitre_id = "T1055"  // Process Injection
- title: Suspicious Process Injection via CreateRemoteThread
- attack.t1055          # Process Injection
- attack.t1055.001      # DLL Injection

### mobile-reverse
- Frida / Objection / OWASP MSTG / SSL Pinning Bypass
- □ APKLeaks: 硬编码 API Key / Token / Secret 扫描
- □ 解密 App Store 二进制: frida-ios-dump / Clutch
- □ frida-trace -U -i "open*" com.app: 追踪函数调用
- □ 注入 frida-gadget.so / FridaGadget.dylib 到 APK/IPA
- □ objection patchapk --source app.apk（全自动）
- □ 证书安装: Android 用户证书 → 系统证书（Magisk + MoveCert）
- □ SSL Pinning 绕过: Frida/Objection/Xposed/SSL Kill Switch 2

### pwn-chain
- 从逆向走到可用利用 (Working Exploit) 的全链路工程化方法。
- 适用场景：拿到了二进制 + 漏洞点 + 目标环境，需要写出一个能稳定打通的 exploit（不是只能本地复现一下、远程一打就崩的脚本）。
- 3. **真实目标的二进制利用** — SRC / 红队场景下，已经识别到内存损坏漏洞，需要构造 RCE
- 前提**：你已经知道"哪里炸了"。本 skill 不负责发现漏洞（那是 fuzzing / 审计），只负责"从漏洞点写出 exploit"。
- | **有漏洞点，写 exploit 打通远程** | **本 skill** |
- ├─ NX 开 + 不给 libc → leak 后 libc-database 反查
- └─ 计算 base：leak_addr - libc.sym['puts']
- ├─ payload = cyclic(N) + p64(ret) + ...

### patch-diff-exploit
- N-day 补丁差分到利用。从厂商发布的补丁里反推漏洞点、写 PoC、做成可用的攻击模块。
- 适用场景：已知 CVE 编号但只有补丁没有 PoC、SRC/红队需要打击未及时更新的资产、N-day 武器化、Patch Tuesday 跟进。
- 核心方法：拿 before/after 二进制 → 对齐符号 → 二进制 diff → 看新增的安全检查反推 bug class → 写 PoC 触发漏洞。
- 1. **已知 CVE 但无公开 PoC** — 厂商公告写了"修复了 XX 组件的越界写"但没放 PoC，需要从补丁反推
- | **从补丁找漏洞、写 PoC 打补丁前版本** | **本 skill** |
- 反推 bug class：OOB / Race / Info Leak / UAF / Integer Overflow
- 用 LLM 看 before/after 伪代码反推 bug class（见 references/root-cause-and-poc.md）
- → LLM 反推 bug class → 写 PoC → 在 unpatched 跑 → 崩 → 收工

### ghidra-reverse
- 与 `binary-diff` / `patch-diff-exploit` 的 ghidriff 联动
- □ 需要动态时交接 Frida/GDB（reverse-engineering 动态章）
- | ghidriff | 补丁差分 | 见 `patch-diff-exploit` |
- 下游**: 动态验证 → Frida/GDB；利用 → `pwn-chain`

## Reverse-skill package — mapping ke fase pipeline (2026-10-21)

12 skill RE dari `zhaoxuya520/reverse-skill`, dipetakan ke sub-fase 0C:

| Skill RE | Fase pipeline | Kapan dipakai |
|---|---|---|
| `reverse-engineering` | 0B/0C | source-code & binary apa pun; entry point umum |
| `ida-reverse` | 0C | target PE/ELF/APK/DLL/SO, butuh IDA Pro |
| `radare2` | 0C | alternatif gratis IDA; analisis cepat |
| `ghidra-reverse` | 0C | headless/scripted RE (gratis) |
| `apk-reverse` | 0C-C2 | target Android: unpack, smali, Frida hook |
| `mobile-reverse` | 0C-C2 | Android/iOS app (gabungan apk+ios) |
| `firmware-pentest` | 0C | IoT/router/appliance: .bin/.img → ekstrak → exploit |
| `dotnet-reverse` | 0C | target .NET/C# (PE dengan CLR) |
| `malware-analysis` | 0C | sampel mencurigakan dari target |
| `pwn-chain` | 0C-C2c | dari vuln binary → working exploit |
| `patch-diff-exploit` | 0C-C4 | N-day: diff patch vendor → PoC |
| `binary-diff` | 0B | migrasi simbol versi lama → baru |

**Aturan pakai** (dari `redteam-mindset`): skill RE hanya untuk target yang kamu
otorisasi. `scope.md` harus punya `auth.status` sebelum ACT. Dynamic analysis
(Frida, emulator) butuh scope device tertulis.
