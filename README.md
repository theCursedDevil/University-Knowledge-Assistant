# Generative AI-Based University Knowledge Assistant

[![CI/CD Pipeline](https://github.com/theCursedDevil/University-Knowledge-Assistant/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/theCursedDevil/University-Knowledge-Assistant/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-red.svg)](https://qdrant.tech/)

> **B.Tech CSE (AI/ML) Capstone Project · CS4191 Capstone Project II**  
> **Student:** Aashu Kumar · **Roll No:** BT23GCS449  
> **GitHub Repository:** [`theCursedDevil/University-Knowledge-Assistant`](https://github.com/theCursedDevil/University-Knowledge-Assistant)  
> **JIRA Project:** `UKA` on [`nightbladeninja.atlassian.net`](https://nightbladeninja.atlassian.net)  

---

## 1. Project Overview

The **Generative AI-Based University Knowledge Assistant** is a responsive web application designed to solve the problem of scattered university information. Students, faculty, and administrative staff can ask natural-language questions (e.g., *"What is the last date to apply for semester exam re-evaluation?"*) and receive accurate, context-grounded answers extracted from official university notices, circulars, regulations, handbooks, and timetables.

Every generated answer is strictly grounded in the ingested documents and features **deterministic, clickable source citations** (linking to the exact document title, page number, and section).

---

## 2. Key Capabilities & Graded Demonstrations

- **Retrieval-Augmented Generation (RAG):** Context-injected question answering with confidence threshold gating and hallucination fallbacks.
- **Deterministic Citation Mapping:** Source citations are extracted directly from PostgreSQL chunk metadata corresponding to vectors retrieved from Qdrant, never fabricated by the LLM.
- **Conversational Interface:** Multi-turn dialogue, context window memory for dependent follow-ups, and token-by-token streaming via Server-Sent Events (SSE).
- **OAuth 2.0 / OIDC Authentication:** Standards-compliant identity management via self-hosted Keycloak, supporting Authorization Code Flow with PKCE and Role-Based Access Control (RBAC: `student`, `faculty`, `admin`).
- **Multi-Replica Database Synchronization:** PostgreSQL 16 primary with two read replicas using physical streaming replication. Demonstrates replication lag detection, read-your-own-writes consistency routing, and optimistic locking concurrency control (`409 Conflict`).
- **Containerization & Orchestration:** Full Docker Compose local development stack (9 containers) and declarative Kubernetes manifests (StatefulSet, Deployments, Ingress, HPA) for Minikube/Kind deployment.
- **Automated CI/CD:** GitHub Actions pipeline executing linting, unit/integration test suites, Docker image building, and automated deployment gates.
- **Rigorous Git & JIRA Workflow:** Professional Conventional Commits and feature-branching linked to JIRA issue tickets from day one.

---

## 3. System Architecture

The project strictly follows a **Modular Layered Architecture with a Single Backend Application** (no microservices):

```
Client Tier               Application Tier               AI / RAG Pipeline         Storage & Persistence
───────────               ────────────────               ─────────────────         ─────────────────────
Browser ───────────────▶ Frontend (Next.js 14)          RAG Engine (LangChain)     PostgreSQL 16 Primary (RW)
(Student/Faculty/Admin)   │ App Router + Tailwind        │                          ├── Read Replica 1 (RO)
                          │                              ├── Doc Processing         └── Read Replica 2 (RO)
Keycloak IdP ───────────▶ │ Keycloak OIDC                │   (Extract/Clean/Chunk)
(OAuth 2.0 + PKCE)        ▼                              │                         Qdrant (Vector DB)
                        Backend API (FastAPI)            ├── Embedding Model        └── 384d Cosine Index
                         /auth /chat /conversations      │   (all-MiniLM-L6-v2)
                         /documents /admin               │                         MinIO (S3 Object Storage)
                                                         └── LLM API                └── Raw PDF documents
                                                             (Groq Llama 3.1)
                                                                                   Redis 7 (RAM)
                                                                                    └── Caching & Locks
```

---

## 4. Technology Stack Summary

| Layer | Technology | Specification / Version |
|---|---|---|
| **Frontend** | Next.js | Next.js 14+, React 18, Tailwind CSS, TypeScript, Lucide Icons |
| **Backend** | FastAPI | Python 3.11+, Uvicorn, Pydantic v2, SQLAlchemy 2.0 (asyncpg) |
| **RAG Framework** | LangChain | `langchain`, `langchain-core` |
| **Embedding Model** | Sentence Transformers | `all-MiniLM-L6-v2` (384 dimensions, local CPU) |
| **Large Language Model** | Groq API | `llama-3.1-8b-instant` (sub-second streaming, low temperature: 0.1) |
| **Vector Database** | Qdrant | Qdrant v1.10+ (Dockerized, cosine distance metric) |
| **Relational Database** | PostgreSQL | PostgreSQL 16 (1 Primary + 2 Read Replicas via physical WAL) |
| **Object Storage** | MinIO | MinIO S3-compatible object store (raw PDF persistence) |
| **Cache & Distributed Lock** | Redis | Redis 7 (in-memory key-value, locks, read-after-write TTL) |
| **Identity Provider** | Keycloak | Keycloak 24+ (OAuth 2.0 / OIDC, PKCE, realm roles) |
| **Containerization** | Docker | Multi-stage Dockerfiles + Docker Compose v2 |
| **Orchestration** | Kubernetes | Minikube / Kind (StatefulSet, Deployment, Ingress) |
| **CI/CD** | GitHub Actions | Workflows in `.github/workflows/ci-cd.yml` |
| **Issue Tracking** | JIRA Software | Project Key: `UKA` on `nightbladeninja.atlassian.net` |

---

## 5. Repository Structure

```
University-Knowledge-Assistant/
├── frontend/                          # Next.js 14 web application
│   ├── app/                           # App Router (pages: /, /chat, /documents, /admin)
│   ├── components/                    # UI Components (ChatView, CitationPanel, Viewer)
│   ├── lib/                           # API client, SSE consumer, auth helpers
│   └── package.json
├── backend/                           # Single FastAPI backend application
│   ├── app/
│   │   ├── api/                       # API Routers (/auth, /chat, /documents, /admin)
│   │   ├── core/                      # Config (pydantic-settings), security (JWKS), deps
│   │   ├── db/                        # SQLAlchemy models, session, ReplicaRouter
│   │   ├── rag/                       # Extractor, chunker, embeddings, vector_store, prompt
│   │   ├── services/                  # Business services (Auth, Document, Conversation, Admin)
│   │   └── main.py                    # App factory & middleware
│   ├── tests/                         # Unit, integration, and concurrency tests (pytest)
│   └── requirements.txt               # Backend dependencies
├── database/                          # Relational database assets
│   ├── migrations/                    # Alembic migration scripts
│   └── init-replication.sql          # PostgreSQL replication configuration
├── docker/                            # Container build assets
│   ├── backend.Dockerfile             # Multi-stage Python 3.11 build
│   └── frontend.Dockerfile            # Multi-stage Node 20 build
├── kubernetes/                        # Declarative Kubernetes resources
│   ├── base/                          # Deployments, Services, ConfigMaps, PVCs
│   ├── postgres/                      # StatefulSet + replication service
│   └── ingress.yaml                   # NGINX Ingress rules
├── .github/
│   └── workflows/ci-cd.yml            # GitHub Actions CI/CD pipeline
├── docs/                              # Project documentation
│   ├── reference/                     # Source PDFs (SRS, SDD, Master Guide, Wireframes)
│   ├── requirements-matrix.md         # 153 requirements traceability matrix
│   ├── architecture.md                # Detailed system architecture
│   ├── technology-decisions.md        # Technology selections & citation schema
│   └── implementation-roadmap.md      # Milestones & phased build order
├── docker-compose.yml                 # 9-container local development stack
├── .env.example                       # Documented environment variables template
├── .gitignore                         # Version control exclusions
├── AGENTS.md                          # Permanent development instructions & rules
└── README.md                          # Project overview & documentation
```

---

## 6. Git & JIRA Workflow Conventions

### Branch Naming Convention
- Production branch: `main` (always deployable, protected)
- Feature branches: `feature/<JIRA-ID>-short-description`
  - *Example:* `feature/UKA-12-document-chunking-pipeline`
  - *Example:* `feature/UKA-25-read-after-write-routing`

### Commit Message Conventions
Follows the [Conventional Commits](https://www.conventionalcommits.org/) specification with JIRA issue ID cross-referencing:
- `feat: implement vector search retrieval [UKA-15]`
- `fix: resolve race condition in replica router [UKA-28]`
- `docs: update requirements matrix and roadmap [UKA-2]`
- `test: add concurrency test for optimistic locking [UKA-31]`

### Pull Request Rules
- PR title must include JIRA ticket ID: `[UKA-15] Implement vector search retrieval`.
- PR description must summarize changes and link the JIRA ticket.
- All automated CI checks (linting, backend unit tests, frontend build) must pass before merging.

---

## 7. Quickstart Guide (Local Development)

### Prerequisites
- [Docker & Docker Compose](https://www.docker.com/) (Docker 24+)
- [Python 3.11+](https://www.python.org/)
- [Node.js 20+](https://nodejs.org/)
- [Git](https://git-scm.com/)

### Environment Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/theCursedDevil/University-Knowledge-Assistant.git
   cd University-Knowledge-Assistant
   ```
2. Copy environment template:
   ```bash
   cp .env.example .env
   ```
3. Populate secrets in `.env` (notably `GROQ_API_KEY`).

### Running the Backend Locally
To run the FastAPI backend server directly for local development:
```bash
# 1. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Start Uvicorn ASGI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Endpoints:
- **Health Check:** `http://localhost:8000/health` (and `http://localhost:8000/api/v1/health`)
- **Document Management:**
  - `POST /documents` (Multipart PDF upload with MinIO persistence & audit logging, Admin only)
  - `GET /documents` (List documents with metadata & category filtering)
  - `DELETE /documents/{id}` (Cascading document removal & audit logging, Admin only)
- **Swagger Documentation:** `http://localhost:8000/docs`
- **ReDoc Documentation:** `http://localhost:8000/redoc`
- **OpenAPI 3.x Schema:** `http://localhost:8000/openapi.json`

### Implemented API Endpoints

| Method | Path | Purpose | Auth / Access |
|---|---|---|---|
| `GET` | `/health` / `/api/v1/health` | Service health status & external service connectivity | Public |
| `GET` | `/docs` / `/redoc` | Swagger and ReDoc interactive OpenAPI documentation | Public |
| `POST` | `/api/v1/documents` | Multipart PDF upload, MinIO storage, and optional auto-indexing | Admin (`X-Dev-Role: admin`) |
| `GET` | `/api/v1/documents` | List uploaded documents with category filtering and pagination | User (`X-Dev-Role`) |
| `GET` | `/api/v1/documents/{id}/chunks` | Retrieve chunk metadata, page provenance, and vector IDs | User (`X-Dev-Role`) |
| `POST` | `/api/v1/documents/{id}/process` | Trigger synchronous PDF extraction, chunking, and Qdrant indexing | Admin (`X-Dev-Role: admin`) |
| `POST` | `/api/v1/documents/search` | Top-k semantic vector search with cosine similarity | User (`X-Dev-Role`) |
| `POST` | `/api/v1/rag/query` | Natural-language grounded question answering via Groq LLM | User (`X-Dev-Role`) |
| `DELETE` | `/api/v1/documents/{id}` | Cascading deletion across MinIO, Qdrant vectors, and PostgreSQL | Admin (`X-Dev-Role: admin`) |

### Database Migrations (Alembic)
Manage and apply PostgreSQL database schema migrations:
```bash
# Run latest migrations
PYTHONPATH=. alembic upgrade head

# Check current revision status
PYTHONPATH=. alembic current

# Generate new autogenerated migration
PYTHONPATH=. alembic revision --autogenerate -m "migration_description"
```

### Running Backend Tests
Execute the automated test suite using `pytest`:
```bash
PYTHONPATH=. pytest backend/tests -v
```

### Running the Full Stack (Docker Compose)
Bring up the entire local infrastructure via Docker Compose:
```bash
docker-compose up -d
```
The services will be available at:
- **Frontend Chat UI:** `http://localhost:3000`
- **FastAPI Backend Docs:** `http://localhost:8000/docs`
- **Keycloak Auth Console:** `http://localhost:8080`
- **Qdrant Vector Dashboard:** `http://localhost:6333/dashboard`
- **MinIO Storage Console:** `http://localhost:9001`

---

## 8. Source-of-Truth References

All development and design decisions are strictly traceable to the reference documents in `docs/`:
- **[docs/requirements-matrix.md](docs/requirements-matrix.md):** 153 Functional, Non-Functional, and Deployment requirements.
- **[docs/architecture.md](docs/architecture.md):** Layered system architecture, component catalog, and data design.
- **[docs/technology-decisions.md](docs/technology-decisions.md):** Technology choices, Groq LLM integration, and finalized citation schema.
- **[docs/implementation-roadmap.md](docs/implementation-roadmap.md):** Phased milestones across MVP, Graded, and Advanced tiers.
