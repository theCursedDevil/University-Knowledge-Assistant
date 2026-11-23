# Technology Decisions and Specifications

> **Project:** Generative AI-Based University Knowledge Assistant  
> **Capstone Project:** CS4191 Capstone Project II · B.Tech CSE (AI/ML)  
> **Student:** Aashu Kumar · **Roll No:** BT23GCS449  
> **Source-of-Truth Reference:** Master Project Guide §4, SDD §14, SRS §2.1.4  

---

## 1. Concrete Technology Selection

In accordance with project development rules, every architectural layer is mapped to one concrete, documented technology. No unnecessary abstractions, mock microservices, or duplicate frameworks are permitted.

| Architectural Layer | Chosen Technology | Exact Version / Specification | Rationale & Trade-off Analysis |
|---|---|---|---|
| **Frontend Framework** | **Next.js** | Next.js 14+ (React 18, App Router, TypeScript) | Server-Side Rendering (SSR), built-in routing, first-class streaming support, robust standard OAuth PKCE client support. |
| **Frontend Styling & UI** | **Tailwind CSS** | Tailwind CSS v3 + Lucide React | Rapid, utility-first styling matching Wireframe Models W-01 through W-13 in clean low-fidelity grayscale styling. |
| **Backend Framework** | **FastAPI** | FastAPI 0.111+ (Python 3.12+) | Async native, high-throughput, auto-generated OpenAPI documentation, strict Pydantic v2 data validation, shared language with AI pipeline. |
| **Database ORM & Driver** | **SQLAlchemy + asyncpg** | SQLAlchemy 2.0 (Async Engine) + `asyncpg` | Production-grade async PostgreSQL connectivity; native support for read/write session routing and connection pooling via NullPool/QueuePool. |
| **Database Migrations** | **Alembic** | Alembic 1.13+ | Version-controlled, reproducible database schema migrations. |
| **RAG Orchestration** | **LangChain** | `langchain` + `langchain-core` | Standardized retriever abstractions, text splitters, and prompt management; allows clean separation of RAG steps. |
| **Embedding Model** | **Sentence Transformers** | `sentence-transformers/all-MiniLM-L6-v2` | **Fixed requirement.** Runs locally on CPU (~120MB memory, 384 dimensions, zero API cost, fast cosine similarity calculation). |
| **Primary LLM** | **Groq API / Gemini** | `llama-3.1-8b-instant` via Groq & `gemini-1.5-flash` | Ultra-low latency streaming (<400ms time-to-first-token), >300 tokens/sec, strict context adherence, generous free tier without local GPU demands. |
| **Vector Database** | **Qdrant** | Qdrant v1.10+ (Docker image `qdrant/qdrant:latest`) | Open-source, single container footprint, native cosine distance index, fast metadata payload filtering (`category`, `role_restriction`). |
| **Relational Database** | **PostgreSQL** | PostgreSQL 16 (1 Primary + 2 Read Replicas) | **Fixed requirement.** Native physical streaming replication via WAL slots for Section 8 database synchronization demonstration. |
| **Object Storage** | **MinIO** | MinIO (Docker image `cgr.dev/chainguard/minio`) | S3-compliant object storage for raw uploaded PDFs; enables original file preview in Wireframe W-08. |
| **Cache & Distributed Lock** | **Redis** | Redis 7 (Docker image `redis:7-alpine`) | In-memory key-value store for distributed locking, read-after-write session window tracking, and query caching. |
| **Identity Provider** | **Keycloak** | Keycloak 24+ (Docker image `quay.io/keycloak/keycloak`) | Standards-compliant OAuth 2.0 / OIDC provider; controls realm roles (`student`, `faculty`, `admin`) and Google IdP federation. |
| **Monitoring & Metrics** | **Prometheus + Grafana** | Prometheus v2.51 + Grafana v10.4 | Telemetry collection for API latency, request error rates, LLM calls, and live PostgreSQL replication lag in bytes. |
| **Containerization** | **Docker & Docker Compose** | Docker 26+, Compose v2 (Compose file format 3.9) | Standard multi-stage containerization defining all 11 services for unified local development. |
| **Container Orchestration** | **Kubernetes** | Minikube / Kind (Kubernetes v1.28+) | StatefulSet for PostgreSQL replication, Deployments for stateless services, ConfigMaps, Secrets, HPA, and NGINX Ingress. |
| **CI/CD Automation** | **GitHub Actions** | GitHub-hosted runner (`ubuntu-latest`) | Automated linting, pytest backend suite, Next.js build verification, and multi-service test orchestration on PRs. |
| **Version Control** | **GitHub** | Repository: `theCursedDevil/University-Knowledge-Assistant` | Public GitHub repository with protected `main` branch and feature-branch PR workflow. |
| **Project Management** | **JIRA Software** | Site: `nightbladeninja.atlassian.net` · Key: `UKA` | Agile Scrum board tracking Epics, Tasks, and Sub-tasks with commits cross-referenced. |

---

## 2. LLM Provider Rationale & Dual Runtime Strategy

1. **Why Cloud LLMs (Groq / Gemini) over Local Ollama/vLLM?**
   - The development environment runs on a standard laptop (MacBook Air) without dedicated high-memory Nvidia GPUs.
   - Running quantized 7B/8B models locally consumes 6–8 GB of RAM and yields 10–15 tokens/sec, causing intolerable latency during live evaluator demonstrations.
   - Groq’s LPU hardware delivers token-by-token streaming at 300+ tokens/sec with sub-second initial response times (<400ms), providing instant UI responsiveness.
   - Google Gemini 1.5 Flash provides a high-context, reliable secondary option with free-tier access.

2. **Why Sentence Transformers (`all-MiniLM-L6-v2`) on CPU?**
   - Embedding generation is performed strictly on local CPU because the MiniLM model requires only ~120 MB of RAM.
   - A single chunk takes ~5–12ms to vectorize on standard CPU cores, completely removing external API costs, rate limits, and network latency from the embedding loop.
   - Embeddings produce a normalized 384-dimensional dense vector space optimal for cosine similarity in Qdrant.

3. **Why PostgreSQL Primary + 2 Standby Replicas?**
   - Capstone grading criteria specifically mandate demonstrating enterprise multi-replica synchronization, read routing, replication lag detection, and read-after-write consistency.
   - Standby replicas offload search queries and conversational history retrievals from the write-heavy primary database.
