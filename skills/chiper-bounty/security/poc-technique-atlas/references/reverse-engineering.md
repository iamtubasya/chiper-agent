# Reverse Engineering (general)

_Source: reverse-skill package (zhaoxuya520/reverse-skill) + field-journal (43 real cases). Extracted 2026-10-21._

## Technique headings
- (see reverse-skill package section below)


## reverse-skill field-journal (2026-10-21 — 4 kasus nyata)

- **2026-07-22_electron-bytenode-privileged-update-chain**
  - | 分析目录存在既有修改产物 | 修改后的 ASAR/JSC 会污染原始结论 | 仅将 `{sample_dir}`、`{extracted_original_dir}` 作为原始证据源 | 低 |
  - 3. **更新链五元组**：`source URL -> downloader -> archive path -> extractor -> executable`，每个节点都保存证据。
  - 本文仅保留通用版本、API 路径结构、数量级和分析方法。样本名、发布者、真实域名、案件目录、哈希、配置密钥、token 与用户标识均已替换或省略；未附带样本文件。
- **2026-08-01_nextjs-cdk-contract-faithful-local-reconstruction**
  - asset_types: [web, frontend_js, public_openapi, screenshot, local_source]
  - | E-id | source_type | 可复用命令模式 | 关联结论 |
  - | E-002 | frontend_js/openapi | `rg 'sessionStorage|/api/|productType|customerToken' {formatted_chunk}`；`jq '{info,paths,securitySchemes}' openapi.json` | legacy 请求、状态、浏览器存储与 v1 合同 |
  - rg -n 'customerToken|productType|upiExpiresAt|customerResubmitCount|sessionStorage' {formatted_chunk}
- **seed-001_elf-packed-loader**
  - 分析一个伪装成 .sh 脚本的 ARM64 ELF 自解压加载器，还原其解压算法和 payload 注入流程。
  - 8. 分析 payload 内容（包含 /proc/self/exe 引用，说明是进程注入器）
  - | 不确定 payload 入口偏移 | 数据表中 entry_offset 字段含义不明 | 跟踪 loader 函数的 `br mmap_base + 0x14`，确认入口在 +0x14 | 20min |
- **seed-004_js-sign-webpack**
  - | 断点命中但看不懂代码 | webpack 压缩 + 变量名混淆 | 用 Chrome 的 Pretty Print 格式化，再配合 SourceMap（如果有） | 10min |
