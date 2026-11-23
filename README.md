# Generative AI-Based University Knowledge Assistant

[![CI/CD Quality Gates](https://github.com/theCursedDevil/University-Knowledge-Assistant/actions/workflows/pr-check.yml/badge.svg)](https://github.com/theCursedDevil/University-Knowledge-Assistant/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16%20(1%20Primary%20%2B%202%20Replicas)-blue.svg)](https://www.postgresql.org/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20DB-red.svg)](https://qdrant.tech/)
[![Keycloak 24](https://img.shields.io/badge/Keycloak-24.0.5%20(OIDC%20%2B%20PKCE)-orange.svg)](https://www.keycloak.org/)
[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-11%20Services-2496ED.svg)](docker-compose.yml)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-HPA%20%2B%20Ingress-326CE5.svg)](kubernetes/)

> **B.Tech CSE (AI/ML) Capstone Project · CS4191 Capstone Project II**  
> **Student:** Aashu Kumar · **Roll No:** BT23GCS449  
> **GitHub Repository:** [`theCursedDevil/University-Knowledge-Assistant`](https://github.com/theCursedDevil/University-Knowledge-Assistant)  
> **JIRA Project:** `UKA` on [`nightbladeninja.atlassian.net`](https://nightbladeninja.atlassian.net)  

---

## 1. Project Overview & Problem Statement

### The Problem
Universities publish hundreds of notices, circulars, syllabi, fee structures, examination regulations, and hostel guidelines across disconnected department websites, PDF bulletins, and physical notice boards. Students and faculty frequently face:
1. **Information fragmentation:** Difficulty locating the single authoritative source of truth.
2. **Hallucination risk in standard AI chatbots:** Generic LLMs invent policies or quote stale regulations.
3. **Lack of provenance:** Answers lack verifiable citations to the exact official document and page number.
4. **Access control violations:** Sensitive faculty deliberations or fee concession criteria are improperly exposed.

### The Solution: University Knowledge Assistant
The **University Knowledge Assistant** is an enterprise-grade, retrieval-augmented generative AI web platform that centralizes institutional knowledge. It enables students and faculty to ask conversational questions (e.g., *"What is the minimum attendance percentage to appear in semester exams?"*) and receive accurate, streamed answers backed by **deterministic, clickable source citations** (linking to document title, 1-indexed page number, and policy section).

---

## 2. Key Capabilities & Graded Demonstrations

- **Retrieval-Augmented Generation (RAG):** Context-injected question answering with confidence-score thresholding ($0.40$), lexical score boosting, and hallucination fallback guards.
- **Deterministic Citation Engine:** Citations are extracted directly from PostgreSQL chunk metadata mapped to Qdrant vector IDs—never fabricated by the LLM.
- **Conversational Interface:** Multi-turn dialogue, context window memory (last 6 messages), and token-by-token streaming via Server-Sent Events (SSE).
- **OAuth 2.0 / OIDC Authentication:** Standards-compliant identity management via self-hosted Keycloak 24, supporting Authorization Code Flow with PKCE, Google Identity Provider federation, and Role-Based Access Control (RBAC: `student`, `faculty`, `admin`).
- **Multi-Replica Database Synchronization:** PostgreSQL 16 primary with two physical streaming read replicas. Features replication lag monitoring (`POSTGRES_REPLICATION_LAG_BYTES`), session-aware read-your-own-writes consistency routing, and optimistic locking concurrency control (`HTTP 409 Conflict`).
- **Containerization & Orchestration:** Complete Docker Compose stack (11 containers) and declarative Kubernetes manifests (Deployments, StatefulSet, Ingress, Horizontal Pod Autoscaler).
- **Automated CI/CD Quality Gates:** GitHub Actions pipelines enforcing Ruff linting, frontend static builds, and automated pytest execution on all Pull Requests.
- **Rigorous Git & JIRA Workflow:** Professional Conventional Commits and feature-branching linked to JIRA issue tickets (`UKA-1` through `UKA-51`).

---

## 3. System Architecture

The application strictly follows a **Modular Layered Architecture with a Single Backend Application** (no microservices):

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
                                                             (Groq / Gemini)
                                                                                   Redis 7 (RAM)
                                                                                    └── Caching & Locks
```

---

## 4. Technology Stack

| Layer | Chosen Technology | Exact Version / Specification | Rationale |
|---|---|---|---|
| **Frontend Framework** | **Next.js** | Next.js 14+ (React 18, App Router, TypeScript) | Server-Side Rendering (SSR), built-in routing, first-class streaming support, robust standard OAuth PKCE client. |
| **Frontend Styling** | **Tailwind CSS** | Tailwind CSS v3 + Lucide React | Clean, utility-first styling matching Wireframe Models W-01 through W-13. |
| **Backend Framework** | **FastAPI** | FastAPI 0.111+ (Python 3.12+) | Async native, high-throughput, auto-generated OpenAPI documentation, strict Pydantic v2 data validation. |
| **Database ORM & Driver** | **SQLAlchemy + asyncpg** | SQLAlchemy 2.0 (Async Engine) + `asyncpg` | Production-grade async PostgreSQL connectivity; native support for read/write session routing and connection pooling. |
| **Database Migrations** | **Alembic** | Alembic 1.13+ | Version-controlled, reproducible database schema migrations. |
| **RAG Orchestration** | **LangChain** | `langchain` + `langchain-core` | Standardized retriever abstractions, text splitters, and prompt management. |
| **Embedding Model** | **Sentence Transformers** | `sentence-transformers/all-MiniLM-L6-v2` | Runs locally on CPU (~120MB memory, 384 dimensions, zero API cost, fast cosine similarity calculation). |
| **Large Language Model** | **Groq API / Gemini** | `llama-3.1-8b-instant` via Groq & `gemini-1.5-flash` | Sub-second time-to-first-token (<400ms), >300 tokens/sec streaming, strict context boundaries, generous free tier. |
| **Vector Database** | **Qdrant** | Qdrant v1.10+ (Docker image `qdrant/qdrant:latest`) | Open-source, single container footprint, native cosine distance index, fast metadata payload filtering (`category`, `role_restriction`). |
| **Relational Database** | **PostgreSQL** | PostgreSQL 16 (1 Primary + 2 Read Replicas) | Physical streaming replication via WAL slots for multi-node database synchronization demonstration. |
| **Object Storage** | **MinIO** | MinIO (Docker image `cgr.dev/chainguard/minio`) | S3-compliant object storage for raw uploaded PDFs; enables original file preview in Wireframe W-08. |
| **Cache & Distributed Lock** | **Redis** | Redis 7 (Docker image `redis:7-alpine`) | In-memory key-value store for distributed locking, read-after-write session window tracking, and query caching. |
| **Identity Provider** | **Keycloak** | Keycloak 24+ (Docker image `quay.io/keycloak/keycloak:24.0.5`) | Standards-compliant OAuth 2.0 / OIDC provider; controls realm roles (`student`, `faculty`, `admin`) and Google IdP federation. |
| **Monitoring & Metrics** | **Prometheus + Grafana** | Prometheus v2.51 + Grafana v10.4 | Telemetry collection for API latency, request error rates, LLM calls, and live PostgreSQL replication lag in bytes. |
| **Containerization** | **Docker & Docker Compose** | Docker 26+, Compose v2 (11 services) | Standard multi-stage containerization defining all 11 services for unified local development. |
| **Container Orchestration** | **Kubernetes** | Minikube / Kind (Kubernetes v1.28+) | StatefulSet for PostgreSQL replication, Deployments for stateless services, ConfigMaps, Secrets, HPA, and NGINX Ingress. |
| **CI/CD Automation** | **GitHub Actions** | GitHub-hosted runner (`ubuntu-latest`) | Automated linting, pytest backend suite, Next.js build verification, and multi-service test orchestration on PRs. |

---

## 5. Repository Structure

```
University-Knowledge-Assistant/
├── frontend/                          # Next.js 14 web application
│   ├── app/                           # App Router (pages: /, /chat, /documents, /admin, /profile)
│   ├── components/                    # UI Components (ChatView, CitationPanel, DocumentViewer)
│   ├── lib/                           # API client, SSE consumer, auth helpers
│   └── package.json
├── backend/                           # Single FastAPI backend application
│   ├── app/
│   │   ├── api/                       # API Routers (/auth, /chat, /documents, /admin, /metrics)
│   │   ├── core/                      # Config (pydantic-settings), security (JWKS), logging, metrics
│   │   ├── db/                        # SQLAlchemy models, session, ReplicaRouter, repositories
│   │   ├── rag/                       # Extractor, chunker, embeddings, vector_store, prompt, reranker
│   │   ├── services/                  # Business services (Auth, Document, Conversation, Admin, RAG)
│   │   └── main.py                    # App factory & middleware
│   ├── tests/                         # Unit, integration, and E2E verification tests (pytest)
│   └── requirements.txt               # Backend dependencies
├── database/                          # Relational database assets
│   ├── migrations/                    # Alembic migration scripts
│   └── init-replication.sql          # PostgreSQL primary & replica replication configuration
├── docker/                            # Container build assets & Keycloak realm imports
│   ├── backend.Dockerfile             # Multi-stage Python 3.12 build
│   ├── frontend.Dockerfile            # Multi-stage Node 20 build
│   └── keycloak/                      # Keycloak realm seed configuration
├── kubernetes/                        # Declarative Kubernetes resources
│   ├── base/                          # Deployments, Services, ConfigMaps, Secrets, PVCs, HPA
│   ├── postgres/                      # StatefulSet + replication service
│   └── ingress.yaml                   # NGINX Ingress rules
├── .github/
│   └── workflows/
│       ├── pr-check.yml               # PR quality gate workflow (lint + tests + build)
│       └── main-deploy.yml            # Main branch deployment workflow
├── docs/                              # Project documentation
│   ├── architecture.md                # System architecture specification
│   ├── technology-decisions.md        # Concrete technology selection and rationale
│   ├── database-design.md             # Relational schema, replication & indexing strategy
│   ├── api-documentation.md           # REST API specification & request/response schemas
│   ├── deployment-guide.md            # Docker Compose, Kubernetes & native run instructions
│   ├── testing-report.md              # Master QA report across all 5 verification tiers
│   ├── jira-git-summary.md            # JIRA Epics, commit history, and PR log
│   ├── demo-script.md                 # Live university evaluation presentation walkthrough
│   ├── known-limitations.md           # Engineering boundaries & academic appraisal
│   └── verification-report.md         # 34/34 E2E user journey audit evidence
├── scripts/
│   ├── ci/                            # CI execution scripts (lint-backend, test-backend, build-frontend)
│   ├── demo/                          # Automated E2E verification runner (`verify_e2e_journey.py`)
│   └── deploy/                        # Kubernetes rolling update and rollback automation
├── docker-compose.yml                 # 11-container full-stack orchestration
├── .env.example                       # Documented environment variables template
├── AGENTS.md                          # Permanent development instructions & rules
└── README.md                          # This file
```

---

## 6. Quickstart Guide (Local Development)

### 6.1 Launch with Docker Compose (Recommended)
Launch the entire 11-container topology with a single command:
```bash
# 1. Clone repository and copy configuration
git clone https://github.com/theCursedDevil/University-Knowledge-Assistant.git
cd University-Knowledge-Assistant
cp .env.example .env

# 2. Add your Groq API key in .env (or Gemini API key)
# GROQ_API_KEY=gsk_...

# 3. Launch all services
docker compose up -d

# 4. Verify stack health
docker compose ps
```

Visit the application at: `http://localhost:3000`.

### 6.2 Native Development (Fast Hot-Reloading)

```bash
# 1. Start support services in Docker
docker compose up -d postgres-primary redis qdrant minio keycloak

# 2. Run backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
alembic upgrade head
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. In another terminal, run frontend
cd frontend
npm install
npm run dev
```

### 6.3 Execute Automated Verification Suites
```bash
# Run backend test suite (93 automated tests)
./scripts/ci/test-backend.sh

# Run frontend linting & production build
./scripts/ci/lint-frontend.sh && ./scripts/ci/build-frontend.sh

# Run live end-to-end user journey demonstration (all 34 checkpoints)
python scripts/demo/verify_e2e_journey.py
```

---

## 7. Key Verification & Quality Metrics

- **Automated Pytest Suite:** 93/93 tests passing (0 failures).
- **Frontend Quality Gate:** 20/20 routes statically generated and compiled (0 warnings/errors).
- **End-to-End Acceptance:** 34/34 checkpoints verified across Student, Faculty, Admin, Database, and Deployment journeys (Prompt 29).
- **Empirical RAG Benchmark:** 100% precision, 100% recall, 100% factual groundedness across ground-truth university policies.
- **JIRA Project:** 15 Epics (`UKA-1` through `UKA-15`) and 51 sub-tasks completed on `nightbladeninja.atlassian.net`.

---

## 8. Documentation Index

Detailed engineering documentation is organized in [`docs/`](docs/):
- **[System Architecture](docs/architecture.md):** Layered component catalog, RAG sequence diagrams, OAuth flow, and replication routing.
- **[Technology Decisions](docs/technology-decisions.md):** Architectural choices, LLM selection rationale, and citation metadata schema.
- **[Database Design](docs/database-design.md):** Entity-Relationship model, streaming replication configuration, and indexing strategy.
- **[REST API Documentation](docs/api-documentation.md):** Endpoint specifications, request/response models, and error status codes.
- **[Deployment & Operations Guide](docs/deployment-guide.md):** Docker Compose, Kubernetes Minikube setup, HPA autoscaling, and rollback scripts.
- **[Master Testing Report](docs/testing-report.md):** Consolidated test results across unit, integration, RAG benchmark, load testing, and E2E audits.
- **[JIRA & Git Summary](docs/jira-git-summary.md):** Complete project management log, sprint breakdown, pull requests, and CI/CD quality gates.
- **[University Demonstration Script](docs/demo-script.md):** Step-by-step presentation script for the capstone evaluation committee.
- **[Known Limitations](docs/known-limitations.md):** Architectural boundaries, OCR considerations, and future enterprise roadmap.
- **[Final Verification Report](docs/verification-report.md):** Exhaustive 34-checkpoint audit report with terminal logs (Prompt 29).
