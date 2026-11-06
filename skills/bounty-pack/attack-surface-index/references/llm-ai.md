# Reverse Index — LLM / AI Attacks

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| fitur chat / assistant / copilot | prompt injection langsung + sistem prompt extraction | Exploiting LLM APIs with excessive agency · Exploiting vulnerabiliti |
| agent yang menjalankan tool/function | tool-call injection → aksi tak diinginkan | Exploiting LLM APIs with excessive agency · Exploiting vulnerabiliti |
| RAG / knowledge base | poison dokumen → indirect prompt injection | Exploiting LLM APIs with excessive agency · Exploiting vulnerabiliti |
| output model dirender ke HTML | insecure output handling → XSS | Exploiting LLM APIs with excessive agency · Exploiting vulnerabiliti |
| AI yang baca email/web/dokumen | indirect injection lewat konten eksternal | Exploiting LLM APIs with excessive agency · Exploiting vulnerabiliti |

## PoC corpus terkait (2 repo)

- `AdityaBhatt3010_CVE-2025-54794-Hijacking-Claude-AI-with-a-Prompt-Injection-The-Jailbreak-That-Talked-Back`
- `George0Papasotiriou_CVE-2026-1337-AI-Coding-Assistant-Prompt-Injection-to-Sandbox-Escape`

## Lab PortSwigger: llm-attacks (4 lab)

- Exploiting LLM APIs with excessive agency (`lab-exploiting-llm-apis-with-excessive-agency`)
- Exploiting vulnerabilities in LLM APIs (`lab-exploiting-vulnerabilities-in-llm-apis`)
- Indirect prompt injection (`lab-indirect-prompt-injection`)
- Exploiting insecure output handling in LLMs (`lab-exploiting-insecure-output-handling-in-llms`)
