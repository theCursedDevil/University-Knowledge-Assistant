# Technology Decisions and Specifications

> **Project:** Generative AI-Based University Knowledge Assistant  
> **Capstone Project:** CS4191 Capstone Project II · B.Tech CSE (AI/ML)  
> **Source-of-Truth Reference:** Master Project Guide §4, SDD §14, SRS §2.1.4  

---

## 1. Concrete Technology Selection

In accordance with project development rules, every architectural layer is mapped to one concrete, documented technology. No unnecessary abstractions or duplicate frameworks are permitted.

| Architectural Layer | Chosen Technology | Exact Version / Specification | Rationale & Trade-off Analysis |
|---|---|---|---|
| **Frontend Framework** | **Next.js** | Next.js 14+ (React 18, App Router, TypeScript) | Server-Side Rendering (SSR), built-in routing, first-class streaming support, robust standard OAuth PKCE client support. |
| **Frontend Styling & UI** | **Tailwind CSS** | Tailwind CSS v3 + Lucide React | Rapid, utility-first styling matching Wireframe Models W-01 through W-13 in clean low-fidelity grayscale styling. |
| **Backend Framework** | **FastAPI** | FastAPI 0.111+ (Python 3.11+) | Async native, high-throughput, auto-generated OpenAPI documentation, strict Pydantic v2 data validation, shared language with AI pipeline. |
| **Database ORM & Driver** | **SQLAlchemy + asyncpg** | SQLAlchemy 2.0 (Async Engine) + `asyncpg` | Production-grade async PostgreSQL connectivity; native support for read/write session routing and connection pooling. |
| **Database Migrations** | **Alembic** | Alembic 1.13+ | Version-controlled, reproducible database schema migrations. |
| **RAG Orchestration** | **LangChain** | `langchain` + `langchain-core` | Standardized retriever abstractions, text splitters, and prompt management; allows clean separation of RAG steps. |
| **Embedding Model** | **Sentence Transformers** | `sentence-transformers/all-MiniLM-L6-v2` | **Fixed requirement.** Runs locally on CPU (~120MB memory, 384 dimensions, zero API cost, fast cosine similarity calculation). |
| **Primary LLM** | **Groq API** | `llama-3.1-8b-instant` via `groq` SDK | **Selected Concrete LLM.** Sub-second time-to-first-token (<400ms), >300 tokens/sec streaming, generous free tier, strictly obeys context boundaries. |
| **Vector Database** | **Qdrant** | Qdrant v1.10+ (Docker image `qdrant/qdrant:latest`) | Open-source, single container footprint, native cosine distance index, fast metadata payload filtering (`category`, `document_id`). |
| **Relational Database** | **PostgreSQL** | PostgreSQL 16 (1 Primary + 2 Read Replicas) | **Fixed requirement.** Native streaming replication via WAL for Section 8 database synchronization demonstration. |
| **Object Storage** | **MinIO** | MinIO (Docker image `minio/minio:latest`) | S3-compliant object storage for raw uploaded PDFs; enables original file preview in Wireframe W-08. |
| **Cache & Distributed Lock** | **Redis** | Redis 7 (Docker image `redis:7-alpine`) | In-memory key-value store for distributed locking (optimistic concurrency), read-after-write session window tracking, and query caching. |
| **Identity Provider** | **Keycloak** | Keycloak 24+ (Docker image `quay.io/keycloak/keycloak`) | Standards-compliant OAuth 2.0 / OIDC provider; controls realm roles (`student`, `faculty`, `admin`) and validates via JWKS. |
| **Containerization** | **Docker & Docker Compose** | Docker 26+, Compose v2 (Compose file format 3.9) | Standard multi-stage containerization defining all 9 services for local development. |
| **Container Orchestration** | **Kubernetes** | Minikube / Kind (Kubernetes v1.28+) | StatefulSet for PostgreSQL replication, Deployments for stateless services, ConfigMaps, Secrets, and NGINX Ingress. |
| **CI/CD Automation** | **GitHub Actions** | GitHub-hosted runner (`ubuntu-latest`) | Automated linting, pytest backend suite, Next.js build verification, Docker image build test on PRs. |
| **Version Control** | **GitHub** | Repository: `theCursedDevil/GenerativeAiBasedUniversityKnowledgeAssistant` | Private repository with protected `main` branch and feature-branch PR workflow. |
| **Project Management** | **JIRA Software** | Site: `nightbladeninja.atlassian.net` · Key: `UKA` | Agile Scrum board tracking Epics, Stories, Tasks, and Bugs with commits cross-referenced. |

---

## 2. LLM Provider Decision & Rationale

### Decision: Groq (`llama-3.1-8b-instant`) as Primary Concrete LLM

Per prompt instructions, one concrete provider is selected for the initial implementation:

1. **Why Groq?**
   - **Ultra-low latency streaming:** Live capstone demonstrations on evaluation projectors require instantaneous streaming. Groq's custom LPU inference engine delivers token-by-token streaming at 300+ tokens/sec with sub-second initial response times.
   - **Strict Grounding Compliance:** The `llama-3.1-8b-instant` instruction-tuned model follows negative constraints reliably (e.g., *"Say 'I don't have that information in the university documents' when context is insufficient"*).
   - **Cost:** Free tier accommodates all capstone testing and evaluation without credit card billing barriers.

2. **Google Gemini Compatibility Layer:**
   - Both Groq and Google Gemini use standard OpenAI-compatible or Google GenAI streaming patterns.
   - The backend encapsulates LLM invocation behind a minimal `LLMClient` interface.
   - Configuration is driven by `.env`:
     ```bash
     LLM_PROVIDER=groq
     GROQ_API_KEY=gsk_...
     GROQ_MODEL=llama-3.1-8b-instant
     # Optional fallback:
     # GEMINI_API_KEY=AIza...
     # GEMINI_MODEL=gemini-1.5-flash
     ```
   - Only Groq will be wired into the initial implementation to avoid dual-dependency complexity.

---

## 3. Finalized Citation Metadata Schema

### Background & Context
The SRS (Sections 1.2, 3.2.7, 3.4, and Appendix F) specifies source citations as a core requirement but deliberately notes that the exact metadata schema was an open design item pending finalization. 

Here we **finalize a minimal, practical, and deterministic schema** that satisfies all functional requirements (`FR-CIT-001` through `FR-CIT-007`) without relying on LLM-generated citations.

### 3.1 Relational Schema (`document_chunks_meta`)

Stored in PostgreSQL on primary database:

```sql
CREATE TABLE document_chunks_meta (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    page INT NULL,                  -- 1-based page number from PDF
    section VARCHAR(255) NULL,       -- Extracted section title/heading (e.g., "5.3 Backlog Exam")
    vector_id VARCHAR(64) NOT NULL,  -- Unique point ID in Qdrant collection
    char_length INT NOT NULL,        -- Length of raw chunk text
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_doc_chunk UNIQUE (document_id, chunk_index)
);

CREATE INDEX idx_chunks_meta_doc ON document_chunks_meta(document_id);
CREATE INDEX idx_chunks_meta_vector ON document_chunks_meta(vector_id);
```

### 3.2 Qdrant Vector Payload Schema

Stored alongside each 384-dimensional vector in Qdrant:

```json
{
  "document_id": "c1f7a2d4-3b1e-4f2a-9e2c-1a2b3c4d5e6f",
  "document_title": "Examination Regulations 2024",
  "category": "regulations",
  "chunk_index": 12,
  "page": 12,
  "section": "5.3 Backlog Exam Registration",
  "text": "Students registering for backlog examinations must submit Form B..."
}
```

### 3.3 Client-Facing Citation Response Schema

Appended to the final message in the SSE stream (`POST /conversations/{id}/messages`):

```json
{
  "answer": "The deadline to apply for backlog exam registration is November 30, 2026. A late fee applies after this date.",
  "citations": [
    {
      "citation_index": 1,
      "document_id": "c1f7a2d4-3b1e-4f2a-9e2c-1a2b3c4d5e6f",
      "document_title": "Examination Regulations 2024",
      "page": 12,
      "section": "5.3 Backlog Exam Registration",
      "chunk_id": "b3e94a12-8c2d-4e1b-9f3a-7a8b9c0d1e2f",
      "snippet": "Students registering for backlog examinations must submit Form B to the academic office by November 30, 2026..."
    }
  ]
}
```

### 3.4 Key Assumptions & Open Item Resolutions

| Assumption | Rationale | Fallback Behavior (`ERR-CIT-001`) |
|---|---|---|
| **Assumption 1: Page Extraction** | Source documents are predominantly PDF files. PyMuPDF (`fitz`) reliably extracts 1-based physical page indices during ingestion. | For plain text or unpaginated files, `page` is set to `NULL`. Frontend renders `Page: N/A` without breaking layout. |
| **Assumption 2: Section Extraction** | Headings are detected heuristically during text extraction (regex matching `^(?:Section|\d+\.|\b[A-Z\s]{4,}\b)` and font size cues). | When no explicit header is found in a chunk, `section` is stored as `NULL`. Frontend renders document title and page only. |
| **Assumption 3: Zero LLM Fabrication** | The LLM is **never** asked to output citations. The backend `CitationResolver` takes the exact chunk IDs returned by Qdrant and injects verified metadata directly from PostgreSQL. | Guaranteed 100% citation grounding; impossible for the LLM to invent nonexistent circulars or pages. |
| **Assumption 4: Metadata Incompleteness** | If a document is deleted while a chat message citing it is viewed, the citation remains in the message JSON but clicking "Open Source" displays a graceful "Document no longer available" notice. | Complies with `ERR-CIT-001` and avoids UI crashes. |

---

## 4. Environment Variables Specification (`.env.example`)

```bash
# Application Environment
ENVIRONMENT=development
LOG_LEVEL=info
SECRET_KEY=change-me-in-production-to-a-secure-random-string

# FastAPI Server
HOST=0.0.0.0
PORT=8000
FRONTEND_ORIGIN=http://localhost:3000

# PostgreSQL Configuration (Primary + Replicas)
DB_USER=app
DB_PASSWORD=university_secret_pw
DB_NAME=university_db
DB_HOST_PRIMARY=postgres-primary
DB_PORT_PRIMARY=5432
DB_HOST_REPLICA_1=postgres-replica-1
DB_PORT_REPLICA_1=5432
DB_HOST_REPLICA_2=postgres-replica-2
DB_PORT_REPLICA_2=5432

# Vector Store (Qdrant)
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=university_documents

# Object Storage (MinIO)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=university-documents
MINIO_SECURE=false

# Cache & Distributed Locking (Redis)
REDIS_HOST=redis
REDIS_PORT=6379

# Identity Provider (Keycloak)
KEYCLOAK_SERVER_URL=http://keycloak:8080
KEYCLOAK_REALM=university-realm
KEYCLOAK_CLIENT_ID=university-assistant-client
KEYCLOAK_CLIENT_SECRET=

# Large Language Model (Groq)
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
LLM_TEMPERATURE=0.1

# Embedding Model
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```
