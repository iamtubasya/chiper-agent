# Vector-DB Fingerprint & Unauthenticated-Endpoint Matrix

Katalog fingerfprint semua vector-store/embedding backend yang umum di RAG pipeline, untuk
`hunt-rag-vector`. SKILL.md hanya menyebut Chroma/Qdrant/Weaviate; di sini matriks lengkap:
default port, endpoint unauth, header/signature, lokasi API key. Additive-only.

---

## A. Vector database — default port + unauth endpoint

| DB | Default port | Unauth probe (200 = full corpus read) | Fingerprint header/body |
|---|---|---|---|
| **Chroma** | `:8000` | `GET /api/v1/heartbeat` · `GET /api/v1/collections` · `GET /api/v2/tenants` | JSON, `{"nanosecond heartbeat"}` |
| **Qdrant** | `:6333` | `GET /collections` · `GET /collections/{name}/points` | `X-Qdrant-*` header / REST `/collections` |
| **Weaviate** | `:8080` | `POST /v1/graphql` `{Get{<Class>(limit:5){content _additional{id}}}}` · `GET /v1/schema` | GraphQL endpoint berjudul `Weaviate` |
| **Milvus** | `:19530` | `GET /healthz` · gRPC `milvus.proto.milvus.MilvusService/ShowCollections` | `code`/`message` JSON; `milvus` banner |
| **Pinecone** (managed) | HTTPS `*.pinecone.io` | API key di `Authorization: Bearer` → `GET /indexes` · `GET /indexes/{i}` | `{"indexes":[...]}` |
| **pgvector** | Postgres `:5432` | `\dt` / query `information_schema` untuk kolom `vector` | Postgres banner |
| **Elasticsearch/OpenSearch** (`dense_vector`/kNN) | `:9200` | `GET _cat/indices` · `GET /_search` | `"cluster_name"` ES/OS |
| **Redis + RediSearch VSS** | `:6379` | `FT._LIST` · `INFO` (jika unauth) | Redis banner `redis_version` |
| **Vespa** | `:8080` (`:19071` config) | `GET /state/v1/health` · `/search/?yql=...` | `vtag`/`vespa` banner |
| **Typesense** | `:8108` | `GET /collections` · `GET /health` (jika key kosong) | JSON `{"name":"typesense-server"}` |
| **Marqo** | `:8882` | `GET /indexes` | JSON Marqo API |
| **txtai** | `:8000` (default app) | `GET /search?query=*` | — |
| **LanceDB** | `:8080` (REST) / file | `GET /v1/table/...` | — |
| **FAISS** | library, no default server | cari `/search`/`/query` custom wrapper | — |

**Proof bar unauthenticated:** 200 + konten dokumen NYATA tanpa kredensial = full corpus read
(Critical, no chaining needed). Response kosong/error namun endpoint hidup = fingerfprint saja.

---

## B. API key location (managed / cloud vector DB — chain ke `hunt-cloud-misconfig`)

| Provider | Key tempat biasa bocor | Signal |
|---|---|---|
| Pinecone | JS bundle `pinecone` client init | `apiKey` / `PINECONE_API_KEY` |
| Weaviate Cloud | bundle `X-OpenAI-Api-Key` pass-through | header `Authorization` |
| Qdrant Cloud | bundle `api_key` | `qdrant_client(api_key=...)` |
| Zilliz (Milvus) | bundle token | `ZILLIZ_CLOUD_URI`+`token` |
| Elastic Cloud | bundle `apiKey` | `cloud_id`+`api_key` |

Grep bundle: `api[_-]?key|apiKey|PINECONE|WEAVIATE|QDRANT|ZILLIZ|ELASTIC`. Jangan lapor "key ada di
bundle" secara buta — cek OOS/IAM scope key itu dulu (lesson keyset demo/vendor).

---

## C. Sink yang HARUS diuji sebelum selainnya

1. **Unauth vector port langsung** (A) — kalau sampe, full corpus read = Critical.
2. **App API `namespace`/`tenant_id`/`document_id` client-controlled** — cross-tenant retrieval.
3. **`filter` metadata bypass** — filter yang UI kirim, coba edit `tenant_id`/`namespace`.
4. **Tool-schema SSRF** (`$ref`/`image_url` ke OAST) — lihat `references/tool-schema-ref-ssrf.md`.
5. **Embedding cache probe** — same query, beda `X-Tenant-Id`, bandingkan `source`/`metadata`.

---

## D. Cross-reference

- Cross-tenant retrieval proof bar & False-Positive Gate → `hunt-rag-vector/SKILL.md` Technique 2 + Gate.
- Managed key leak → `hunt-cloud-misconfig` (S3/GCS/role) + `hunt-source-leak` (bundle).
- Tool-schema `$ref` SSRF deep-dive → `hunt-ssrf/references/ai-tool-schema-ref-ssrf.md`.
- Confabulation/run-twice rule → `hunt-llm-ai` False-Positive Gate.