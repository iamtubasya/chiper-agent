# Mobile / APK / iOS Reverse Engineering

_Source: reverse-skill package (zhaoxuya520/reverse-skill) + field-journal (43 real cases). Extracted 2026-10-21._

## Technique headings
- (see reverse-skill package section below)


## reverse-skill field-journal (2026-10-21 — 5 kasus nyata)

- **2026-07-14_android-arm64-self-extract-source-recovery**
  - 6. 保护库保留可读 C++ 符号，逐函数导出伪代码，确认 `/proc` 扫描、`TracerPid`、三级进程终止和后台线程行为。
  - | PowerShell 直接运行 bootstrap 被执行策略拦截 | 系统禁止脚本 | 使用单次 `powershell.exe -ExecutionPolicy Bypass -File ...`，不改永久策略 | 低 |
  - Python 3.13 标准库足够安全处理 bzip2 与 tar.gz；`tarfile.extractall` 不如逐成员校验后写出安全。
- **2026-08-20_apk-flutter-banner-ad-removal**
  - 1. 目标识别：`{target}.apk` — Flutter 3.4.4 (libapp.so 13MB) + 360加固壳（`com.frezrik.jiagu.StubApp`，真实 dex 加密于 classes.dex 尾部 payload 2.58MB）
  - 3. 工具链搭建：gitee 预编译 blutter 为 ARM64-Linux（不可用）→ 下载 blutter-unmgr 源码 → Windows MSVC 构建（VS2026 BuildTools + cmake + ninja）→ 编译 dartvm3.4.4_android_arm64 静态库（~15min）→ blutter.exe 分析 libapp.so → 
  - | E-id | source_type | 可复用命令模式 | 关联 Finding |
- **seed-008_apk-okhttp-ssl-pin-bypass**
  - [种子] APK Frida 绕过 OkHttp SSL Pinning
  - 对一个使用 OkHttp + 自定义 CertificatePinner 的 Android 应用，用 Frida 动态绕过证书校验，让 Burp 能拿到明文流量。
  - 1. 装 Frida + frida-server，启动目标 App，确认进程名
  - 3. 用 jadx 打开 APK 反编译 → 搜 `CertificatePinner` 或 `checkServerTrusted`
- **seed-009_ios-jailbreak-detect-bypass**
  - 1. 越狱机准备（Dopamine / palera1n / unc0ver）→ 装 frida-server（Cydia 源 `build.frida.re`）
  - 2. 把 IPA 拖到机器，AppSync Unified 装签名 → 启动确认能 `frida-ps -U`
  - 4. 用 `frida-trace -U -i 'open' -i 'stat' -i 'access' -i 'fork' com.target.app` 看检测调用
  - 7. 启动成功后用 frida hook NSURLSession 抓包，或配 mitmproxy 装系统证书
- **seed-014_unity-il2cpp-reverse**
  - 一个 Unity 打包的 Android 游戏（IL2CPP 模式），游戏内购或核心算法在 C# 编写但已编译成 native。需要还原方法名、定位关键逻辑、改动 / hook 实现修改。
  - 动态 hook**：Frida 接 il2cpp 方法（用 Frida-Il2CppBridge）
  - | global-metadata.dat 加密了 | 用了 AntiCheatToolkit / 自定义加密 | 找游戏初始化时的解密函数（通常在 il2cpp_init 周围）→ Frida 在 mmap 后 dump | 2h |
  - | Frida hook IL2CPP 方法报错 | IL2CPP 方法不是标准 Java/ObjC，要算 method offset | 用 frida-il2cpp-bridge 库，不要硬写 Interceptor.attach | 1h |
