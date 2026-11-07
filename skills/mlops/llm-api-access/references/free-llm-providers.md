# Free LLM API Providers (condensed, Nov 2026)

Sumber kanonik: `nejib1/Free-LLM` (free-llm.com) — direktori komunitas, di-update berkala. Data di bawah di-condense untuk kebutuhan security testing (garak/promptfoo). Selalu re-verifikasi sebelum dipakai karena kuota berubah.

## Permanent free tiers (kuota tak pernah kedaluwarsa)

| Provider | Kartu? | Kuota | Model gratis terbaik |
|---|---|---|---|
| Google AI Studio | Tidak | per-model, generous | Gemini 3.8 Flash, Gemma 4 31B |
| Groq | Tidak | 30 RPM, ~1000 req/hari | GPT-OSS 120B, Qwen3.8 27B |
| NVIDIA NIM | Telp | ~40 RPM | GLM-5.3 Flash, DiffusionGemma |
| Mistral | Telp | 1 req/s | Mistral Large 4, Codestral |
| Cloudflare Workers AI | Tidak | 10k neuron/hari | GLM-5.3 Flash, FLUX.2 |
| Cohere | Tidak | 20 RPM, 1000/bln | Command A (111B) |
| Z.AI (GLM) | Registrasi | ~1000 req/hari | GLM-4.7 Flash |
| FreeInference | Tidak | generous | GLM-5.3 Flash, DeepSeek V4 Flash, MiniMax M3 |
| ModelScope | Telp | 2000 req/hari | Qwen3.8 27B, ERNIE 4.5 300B |
| Pollinations | Tidak | free | GPT-OSS 20B, Mistral Large 3, Kimi K2.6 |

## Renewable credits (reset periodik)

| Provider | Kartu? | Kuota | Model gratis |
|---|---|---|---|
| OpenRouter | Tidak | 20 RPM, 50 req/hari (:free) | nemotron-3-ultra-550b, crouton-alpha, gemma-4-31b |
| Requesty | Tidak | 200 req/hari | Gemma 4 31B, Nemotron 3 |
| IBM watsonx Lite | Kartu | 300k token/bln | Granite 4, Llama 3.3 70B |
| Experiential Labs | Kartu | **1M token/hari** | **GPT-6 Luna**, DeepSeek V4.1 Flash |

## One-time trial credits

| Provider | Kartu? | Credit | Model |
|---|---|---|---|
| Grokified | Tidak | **$5** | **Grok 4.7**, 4.6, 4.3 |
| Inception Labs | Tidak | 100M token | Mercury 3 (diffusion LLM) |
| Regolo.ai | Tidak | 1M token/hari, 30 hari | GPT-OSS 120B, Qwen3.8 |
| Hyperbolic | Telp | $1 | DeepSeek V4 Flash, Qwen3.8 |
| Cerebras | Kartu | $5 (30 hari) | GPT-OSS 120B, Qwen3.8 |
| Scaleway | Registrasi | 1M token | GPT-OSS 120B, Whisper |
| Voyage AI | Registrasi | 200M token (embeddings) | Voyage 4 |

## OpenRouter model frontier (PAID — bukan gratis)
Cek live: `curl -s https://openrouter.ai/api/v1/models | jq '.data[] | select(.id|test("5.5|opus|gpt-5|gemini-4";"i")) | .id + " | $" + .pricing.prompt'`

Harga referensi (per 1M token):
- anthropic/claude-sonnet-5.5 — $2 in / $10 out
- anthropic/claude-opus-5.5 — $4 in / $20 out
- openai/gpt-5.5 — $5 in / $30 out
- openai/gpt-5.6-luna — $0.2 in / $1.2 out (murah!)
- google/gemini-4-argon — $2 in / $10 out
- openai/gpt-5.6-sol — $4 in / $20 out

Catatan: `gpt-5.6-luna` sangat murah untuk kelas frontier-ish ($0.2/M in) — opsi terbaik kalau harus bayar.

## Model :free di OpenRouter (16 model, live Nov 2026)
stealth/crouton-alpha (1M ctx) · nvidia/nemotron-3-ultra-550b-a55b (550B) · nvidia/nemotron-3.5-lightning · nvidia/nemotron-3.5-super-vl · nvidia/nemotron-3-nano-omni-30b-a3b-reasoning · google/gemma-4-31b-it · google/gemma-4-26b-a4b-it · recursive/flint-v1.0 · cohere/north-mini-code · xingchen-agi/xing4.0-29b-a4b · liquid/lfm-2.5-2.6b · dots-studio/dots-3-note-preview

## Teknik verifikasi cepat
```bash
# Cek model :free OpenRouter (tanpa auth)
curl -s https://openrouter.ai/api/v1/models | python3 -c \
  "import json,sys; d=json.load(sys.stdin); [print(m['id']) for m in d['data'] if m['pricing']['prompt']=='0' and m['pricing']['completion']=='0']"
```

## Gateway agregator baru (buat diwaspadai)
Beberapa "free AI gateway" baru (WusRouter, FreeInference, Routeway, Kilo Gateway) menawarkan model frontier "gratis". Realitas: model frontier tetap berbayar; yang gratis cuma Flash/OSS. Beberapa (WusRouter) punya fitur "Account Pool" = indikasi reseller/pooling akun — abuse promo di sini = ToS violation, TOLAK buat farming.
