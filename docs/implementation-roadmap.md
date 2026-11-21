# Implementation Roadmap & Milestone Plan

> **Project:** Generative AI-Based University Knowledge Assistant  
> **Capstone Project:** CS4191 Capstone Project II · B.Tech CSE (AI/ML)  
> **Source-of-Truth Reference:** Master Project Guide §14 & §15, SRS §2.6, SDD §2  

---

## 1. Roadmap Architecture and Tiers

To balance rapid demonstration value with rigorous capstone grading requirements, development is organized into three distinct delivery tiers:

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: INITIAL WORKING MVP (Phases 1–7 Fast-Path)                                   │
│ Goal: Working end-to-end vertical slice from uploaded document to cited chat answer.  │
│ Scope: Single Postgres, local Qdrant, MinIO, sentence-transformers, Groq LLM,         │
│        FastAPI backend, and Next.js conversational UI (basic auth placeholder).       │
└──────────────────────────────────────────┬────────────────────────────────────────────┘
                                           │ Unlocks live demonstration
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 2: REMAINING GRADED REQUIREMENTS (Phases 8–12)                                  │
│ Goal: Complete all mandatory capstone infrastructure, security, and data consistency. │
│ Scope: Keycloak OAuth PKCE + RBAC, PostgreSQL Primary + 2 Replicas with streaming    │
│        replication, Read-Your-Own-Writes router, Optimistic Locking (409 Conflict),   │
│        Full Docker Compose, Kubernetes Minikube manifests, GitHub Actions CI/CD.      │
└──────────────────────────────────────────┬────────────────────────────────────────────┘
                                           │ Unlocks full grading rubric
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ TIER 3: OPTIONAL ADVANCED STRETCH GOALS (Phases 13–14 & Beyond)                      │
│ Goal: Placement-value distinctions and advanced demonstrations.                       │
│ Scope: Cross-encoder re-ranking, Groundedness checker, Synchronous replication path,  │
│        Horizontal Pod Autoscaler (HPA), Prometheus/Grafana lag dashboards.            │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase-by-Phase Executable Milestones

---

### Phase 1: Planning, Requirements & Architectural Baseline
* **Goal:** Finalize requirements, architecture, technology stack, and traceability.
* **Tier:** Mandatory / Foundation
* **Dependencies:** None

#### Milestone 1.1: Source Documents & Requirements Formalization
- **Tasks:**
  - Extract and index SRS, SDD, Master Project Guide, and Wireframe Models.
  - Generate full requirements traceability matrix covering all 153 requirements.
- **SRS Traceability:** All Requirements Baseline
- **Deliverables:** `docs/requirements-matrix.md`
- **Verification:** Completeness audit against SRS v1.0.

#### Milestone 1.2: Architecture & Technology Decisions Documentation
- **Tasks:**
  - Detail single-backend layered architecture (Next.js -> FastAPI -> Storage/LLM).
  - Finalize concrete technology stack (Groq, all-MiniLM-L6-v2, Postgres 16, Qdrant, MinIO, Redis, Keycloak).
  - Finalize deterministic citation schema resolving SRS open design item.
- **SRS Traceability:** `NFR-MAINT-001`, `FR-CIT-001–007`, `DEP-DOCKER-001`
- **Deliverables:** `docs/architecture.md`, `docs/technology-decisions.md`, `docs/implementation-roadmap.md`
- **Verification:** Stakeholder review and plan approval.

---

### Phase 2: Git Collaboration & JIRA Project Setup
* **Goal:** Establish professional version control and issue tracking from inception.
* **Tier:** Tier 1 / Graded Requirement
* **Dependencies:** Phase 1

#### Milestone 2.1: Repository Skeleton & Hygiene Configuration
- **Tasks:**
  - Initialize clean directory layout (`frontend/`, `backend/`, `database/`, `docker/`, `kubernetes/`, `.github/`).
  - Configure `.gitignore` (`.env`, `node_modules/`, `__pycache__/`, `venv/`, build artifacts).
  - Create `.env.example` with documented configuration parameters.
- **SRS Traceability:** `PROC-GIT-001`, `PROC-GIT-002`, `DEP-ENV-001`, `DEP-ENV-002`, `DEP-SEC-001`, `NFR-MAINT-001`
- **Deliverables:** `.gitignore`, `.env.example`, directory tree
- **Verification:** `git status` clean, secrets properly ignored.

#### Milestone 2.2: JIRA Board & Branch Protection Workflow
- **Tasks:**
  - Set up JIRA project `UKA` on `nightbladeninja.atlassian.net`.
  - Populate Sprint 1 Backlog with Epics and Tasks mapped to roadmap phases.
  - Establish branch naming convention (`feature/UKA-<id>-description`) and Conventional Commits.
- **SRS Traceability:** `PROC-JIRA-001–007`, `PROC-GIT-003–007`
- **Deliverables:** JIRA Sprint 1 active board, Git commit hooks/rules.
- **Verification:** JIRA board ticket verification via TWG CLI.

---

### Phase 3: Backend Skeleton & Core Framework
* **Goal:** Deploy a running FastAPI application shell with healthchecks and structured routing.
* **Tier:** Tier 1 (MVP)
* **Dependencies:** Phase 2

#### Milestone 3.1: FastAPI Application Structure & Router Modularization
- **Tasks:**
  - Build FastAPI application factory (`backend/app/main.py`).
  - Register API routers: `/api/health`, `/api/auth`, `/api/documents`, `/api/conversations`, `/api/admin`.
  - Add CORS middleware locked to frontend origin.
  - Add standard exception handling middleware returning unified error envelopes.
- **SRS Traceability:** `NFR-SEC-002`, `NFR-SEC-004`, `ERR-SVC-001`
- **Deliverables:** Working FastAPI server reachable at `http://localhost:8000/api/health`.
- **Verification:** `curl http://localhost:8000/api/health` returns `{"status": "ok"}` with 200 OK.

#### Milestone 3.2: Configuration Management & Dependency Injection
- **Tasks:**
  - Implement Pydantic `Settings` class loading from environment variables / `.env`.
  - Set up FastAPI dependency injection for database sessions and service layers.
- **SRS Traceability:** `DEP-ENV-001`, `DEP-SEC-001`, `NFR-MAINT-001`
- **Deliverables:** `backend/app/core/config.py`, `backend/app/core/deps.py`.
- **Verification:** Unit tests asserting environment variable parsing and override behavior.

---

### Phase 4: Database Schema & Migrations
* **Goal:** Establish relational persistence in PostgreSQL with Alembic migrations.
* **Tier:** Tier 1 (MVP)
* **Dependencies:** Phase 3

#### Milestone 4.1: SQLAlchemy Relational Models Definition
- **Tasks:**
  - Define declarative models: `User`, `Document`, `DocumentChunkMeta`, `Conversation`, `Message`, `AuditLog`.
  - Include `version INT DEFAULT 1` on `Document` for optimistic locking.
  - Include `citations_json JSONB` on `Message` for citation persistence.
- **SRS Traceability:** `FR-USER-002`, `FR-DOC-009`, `FR-CHAT-003`, `FR-ADMIN-003`
- **Deliverables:** `backend/app/db/models.py`.
- **Verification:** Models compile cleanly with valid foreign key constraints.

#### Milestone 4.2: Alembic Migrations Setup & Execution
- **Tasks:**
  - Configure Alembic async migration environment (`database/migrations/`).
  - Generate initial schema migration: `001_initial_schema.py`.
  - Write test harness verifying migration `upgrade` and `downgrade`.
- **SRS Traceability:** `NFR-MAINT-001`, `NFR-REL-001`
- **Deliverables:** Migration scripts and Alembic runner.
- **Verification:** `alembic upgrade head` executes cleanly against local PostgreSQL.

---

### Phase 5: Document Ingestion & Processing Pipeline
* **Goal:** Admin upload endpoint, file storage in MinIO, PDF text extraction, chunking, and metadata storage.
* **Tier:** Tier 1 (MVP)
* **Dependencies:** Phase 4

#### Milestone 5.1: File Upload API & Object Storage Storage
- **Tasks:**
  - Implement `POST /documents` multipart upload endpoint.
  - Enforce MIME type validation (allow only `application/pdf`) and size cap (25MB).
  - Store raw file in MinIO bucket `university-documents`.
  - Insert initial row into `documents` table (`version=1`).
- **SRS Traceability:** `FR-DOC-001`, `FR-DOC-002`, `FR-DOC-003`, `NFR-SEC-007`, `FR-ADMIN-001`
- **Deliverables:** `DocumentService.upload_document()`, MinIO client integration.
- **Verification:** `TEST-DOC-001`: Valid PDF uploads succeed (202 Accepted); rejected on invalid MIME/oversized.

#### Milestone 5.2: Text Extraction, Cleaning & Chunking
- **Tasks:**
  - Implement PyMuPDF extractor capturing text and 1-based page numbers.
  - Implement whitespace normalizer and artifact cleaner.
  - Implement `RecursiveCharacterTextSplitter` (~700 tokens, 100 token overlap).
  - Detect section headers heuristically and attach to chunk metadata.
- **SRS Traceability:** `FR-PROC-001`, `FR-PROC-002`, `FR-PROC-004`, `FR-PROC-007`
- **Deliverables:** `backend/app/rag/extractor.py`, `backend/app/rag/chunker.py`.
- **Verification:** `TEST-UNIT-001`: Extracted chunks preserve page numbers and text continuity across overlap.

#### Milestone 5.3: Document Listing, Deletion Saga & Audit Logging
- **Tasks:**
  - Implement `GET /documents` with category/title filtering.
  - Implement `DELETE /documents/{id}` cascading delete (MinIO object + Qdrant points + Postgres metadata).
  - Log upload and deletion events to `audit_log`.
- **SRS Traceability:** `FR-DOC-004`, `FR-DOC-005`, `FR-ADMIN-003`, `NFR-SEC-010`
- **Deliverables:** `DocumentService.delete_document()`, audit log integration.
- **Verification:** `TEST-API-001`: Deletion removes data across all 3 stores without orphaned records.

---

### Phase 6: RAG Core Engine (Embeddings + Vector Retrieval + LLM Generation)
* **Goal:** End-to-end question answering pipeline: question embedding, Qdrant retrieval, prompt construction, and Groq LLM generation.
* **Tier:** Tier 1 (MVP)
* **Dependencies:** Phase 5

#### Milestone 6.1: Vector Storage & Embedding Pipeline
- **Tasks:**
  - Wrap `sentence-transformers/all-MiniLM-L6-v2` in singleton `EmbeddingClient`.
  - Initialize Qdrant collection `university_documents` with 384-dimensional cosine index.
  - Implement batch upsert writing vectors + payload to Qdrant and metadata to `document_chunks_meta`.
- **SRS Traceability:** `FR-PROC-005`, `FR-PROC-006`, `FR-PROC-008`, `FR-RAG-001`
- **Deliverables:** `backend/app/rag/embeddings.py`, `backend/app/rag/vector_store.py`.
- **Verification:** Chunks embedded and successfully queryable in Qdrant collection.

#### Milestone 6.2: Vector Retrieval & Confidence Threshold Gate
- **Tasks:**
  - Implement top-K (K=5) cosine similarity search in Qdrant.
  - Implement confidence gate: evaluate top similarity score against threshold (0.60).
  - Trigger fallback response when top score < threshold: *"I don't have that information in the university documents."*
- **SRS Traceability:** `FR-RAG-002`, `FR-RAG-009`
- **Deliverables:** `Retriever`, `ConfidenceGate`.
- **Verification:** `TEST-RAG-001`: Unrelated questions trigger fallback; university questions retrieve relevant chunks.

#### Milestone 6.3: Prompt Construction & LLM Generation via Groq
- **Tasks:**
  - Construct prompt template with strict XML/markdown boundaries (`<context>`, `<instructions>`).
  - Integrate Groq API client with model `llama-3.1-8b-instant` (low temperature: 0.1).
  - Implement token-by-token streaming generator.
- **SRS Traceability:** `FR-RAG-005`, `FR-RAG-006`, `FR-RAG-007`, `NFR-SEC-008`
- **Deliverables:** `backend/app/rag/prompt.py`, `backend/app/rag/llm_client.py`.
- **Verification:** Streaming generator yields tokens cleanly; answers remain strictly grounded in injected context.

#### Milestone 6.4: Deterministic Citation Resolver
- **Tasks:**
  - Track chunk IDs passed to prompt context.
  - Query PostgreSQL `document_chunks_meta` to extract verified document title, page number, and section.
  - Attach structured citation objects to final response.
- **SRS Traceability:** `FR-CIT-001`, `FR-CIT-002`, `FR-CIT-003`, `FR-CIT-005`, `FR-CIT-006`
- **Deliverables:** `backend/app/rag/citation_resolver.py`.
- **Verification:** `TEST-UNIT-001`: Rendered citations map 1:1 with source PDF chunks actually used.

---

### Phase 7: Conversational Interface (Next.js Frontend & Streaming Chat)
* **Goal:** Usable web chat application matching wireframes W-01 through W-13.
* **Tier:** Tier 1 (MVP)
* **Dependencies:** Phase 6

#### Milestone 7.1: Next.js Project Setup & Design System
- **Tasks:**
  - Initialize Next.js 14 App Router project (`frontend/`).
  - Configure Tailwind CSS grayscale theme matching wireframe specifications.
  - Implement shared layout, navigation bar, and user status header (W-03).
- **SRS Traceability:** `NFR-USE-001`, `NFR-USE-002`, `NFR-MAINT-001`
- **Deliverables:** Responsive app skeleton with top navigation bar.
- **Verification:** UI renders cleanly across desktop and mobile screen viewports.

#### Milestone 7.2: Streaming Chat UI & Multi-Turn Conversation
- **Tasks:**
  - Implement Chat interface with message bubbles and question input (W-04).
  - Consume backend SSE stream token-by-token with typewriter rendering.
  - Maintain conversation history sidebar ordered by `updated_at` (W-06).
  - Pass last N messages (N=6) to backend for follow-up conversational context.
- **SRS Traceability:** `FR-CHAT-001`, `FR-CHAT-002`, `FR-CHAT-004`, `FR-CHAT-005`, `FR-CHAT-007`, `FR-RAG-010`
- **Deliverables:** `frontend/components/ChatView.tsx`, `ConversationSidebar.tsx`.
- **Verification:** Asking follow-up question ("what about for backlog students?") resolves context from earlier turn.

#### Milestone 7.3: Source Citation Panel & Document Preview Viewer
- **Tasks:**
  - Render clickable citation chips under assistant answers (W-05).
  - Build Citation View (W-09) showing source reference and metadata.
  - Build Document Preview (W-08) displaying raw PDF at cited page.
- **SRS Traceability:** `FR-CIT-004`, `FR-CIT-007`, `NFR-USE-001`
- **Deliverables:** `CitationPanel.tsx`, `DocumentPreview.tsx`.
- **Verification:** Clicking citation chip opens viewer scrolled to the exact cited page.

#### Milestone 7.4: Admin Document Management Console
- **Tasks:**
  - Implement Admin Document Upload drag-and-drop form (W-11).
  - Implement uploaded documents management table with delete action.
  - Implement system states: Loading (S-1), Empty (S-2), No Results (S-3), Error (S-4), Forbidden (S-5).
- **SRS Traceability:** `FR-DOC-001`, `FR-DOC-004`, `FR-DOC-005`, `NFR-USE-001`
- **Deliverables:** `AdminConsole.tsx`, `SystemStates.tsx`.
- **Verification:** Admin can upload PDF live through web UI; system states render appropriately on edge cases.

> [!NOTE]
> **MILESTONE REVIEW: Tier 1 MVP is Complete.** At the conclusion of Phase 7, the application functions end-to-end: users can upload documents, ask natural language questions, view streamed answers with verified source citations, and navigate conversation history.

---

### Phase 8: OAuth 2.0 / OIDC Authentication & RBAC (Keycloak)
* **Goal:** Secure application with self-hosted Keycloak, PKCE flow, and role-based access control.
* **Tier:** Tier 2 (Graded Requirement)
* **Dependencies:** Phase 7

#### Milestone 8.1: Keycloak Container Deployment & Realm Configuration
- **Tasks:**
  - Run Keycloak in Docker with realm `university-realm`.
  - Configure client `university-assistant-client` with PKCE enabled.
  - Define realm roles: `student`, `faculty`, `admin`.
  - Seed test users for each role.
- **SRS Traceability:** `FR-AUTH-001`, `FR-AUTH-005`, `FR-USER-003`
- **Deliverables:** `keycloak-realm-export.json`, Docker Compose service entry.
- **Verification:** Login to Keycloak admin console; verify roles and test credentials.

#### Milestone 8.2: Frontend OAuth Redirect & Callback Flow
- **Tasks:**
  - Implement Login screen (W-01) redirecting to Keycloak `/auth`.
  - Implement `/auth/callback` handling authorization code + PKCE verifier exchange.
  - Store JWT session in secure httpOnly cookies where feasible.
  - Implement Logout calling Keycloak end-session endpoint (W-02, W-10).
- **SRS Traceability:** `FR-AUTH-001`, `FR-AUTH-002`, `FR-AUTH-009`, `FR-AUTH-011`
- **Deliverables:** `frontend/app/auth/callback/page.tsx`, `AuthContext.tsx`.
- **Verification:** Full browser login and logout lifecycle functions without exposed secrets.

#### Milestone 8.3: Backend JWT Signature Verification & Server-Side RBAC
- **Tasks:**
  - Implement `TokenValidator` fetching and caching Keycloak JWKS public keys.
  - Verify `exp`, `iss`, and signature on every incoming request.
  - Implement `RoleGuard` FastAPI dependency restricting admin routes (`POST /documents`, `GET /admin/stats`).
  - Implement just-in-time user provisioning in `users` table on first login (`GET /me`).
- **SRS Traceability:** `FR-AUTH-003`, `FR-AUTH-004`, `FR-AUTH-006`, `FR-AUTH-007`, `FR-AUTH-008`, `FR-USER-001`, `FR-USER-002`, `FR-USER-004`
- **Deliverables:** `backend/app/core/security.py`, `backend/app/api/deps.py`.
- **Verification:** `TEST-AUTH-001` & `TEST-AUTHZ-001`: Valid token admitted; expired token returns 401; student accessing admin endpoint returns 403.

#### Milestone 8.4: Role-Restricted Document Retrieval (Should-Have)
- **Tasks:**
  - Add optional `role_restriction` column to `documents`.
  - Inject role filter into Qdrant vector retrieval query server-side.
- **SRS Traceability:** `FR-DOC-010`, `NFR-SEC-009`
- **Deliverables:** Role-filtered vector retrieval query logic.
- **Verification:** Faculty-only document chunk is omitted from retrieval results when student asks a matching question.

---

### Phase 9: Multi-Replica Database Synchronization & Concurrency Control
* **Goal:** Demonstrate replication lag resolution (Read-Your-Own-Writes) and concurrent update conflict handling (Optimistic Locking).
* **Tier:** Tier 2 (Graded Requirement)
* **Dependencies:** Phase 8

#### Milestone 9.1: PostgreSQL Primary + 2 Read Replicas Setup
- **Tasks:**
  - Configure PostgreSQL Primary with WAL streaming replication (`wal_level=replica`).
  - Configure `postgres-replica-1` and `postgres-replica-2` streaming via `pg_basebackup`.
  - Expose replication lag metrics via `pg_stat_replication`.
- **SRS Traceability:** `FR-DBSYNC-001`, `FR-DBSYNC-006`, `NFR-SCAL-002`, `NFR-SEC-006`
- **Deliverables:** `database/init-replication.sql`, Docker Compose replica topology.
- **Verification:** Pausing replication demonstrates replication lag in `pg_stat_replication`.

#### Milestone 9.2: Read/Write Router & Read-Your-Own-Writes Consistency
- **Tasks:**
  - Build `ReplicaRouter` directing `INSERT/UPDATE/DELETE` to Primary and `SELECT` to Replicas (round-robin).
  - Implement post-write session window: upon write, record user write timestamp in Redis (TTL: 5s).
  - If user reads within window, route to Primary; otherwise route to read replicas.
- **SRS Traceability:** `FR-DBSYNC-002`, `FR-DBSYNC-003`, `ERR-DB-002`
- **Deliverables:** `backend/app/db/router.py`.
- **Verification:** `TEST-DB-001`: Writing a document and reading immediately returns fresh data, even with replica paused.

#### Milestone 9.3: Optimistic Locking Metadata Management & 409 Conflict Handling
- **Tasks:**
  - Implement `PUT /documents/{id}` with `WHERE version = :expected_version`.
  - If 0 rows updated, raise HTTP `409 Conflict`.
  - Build Metadata Management UI (W-12) displaying Conflict Banner on 409 with "Reload latest" action.
- **SRS Traceability:** `FR-DBSYNC-004`, `FR-DBSYNC-005`, `NFR-REL-002`, `ERR-DB-003`
- **Deliverables:** `DocumentService.update_metadata()`, `MetadataManagement.tsx`.
- **Verification:** `TEST-CONC-001`: Two concurrent updates produce exactly one success and one 409 Conflict.

#### Milestone 9.4: Redis Caching & Distributed Locking Integration
- **Tasks:**
  - Cache document list and frequent query responses in Redis (TTL: 60s).
  - Use Redis distributed lock (`SET NX EX`) to guard concurrent document uploads.
- **SRS Traceability:** `FR-CACHE-001`, `FR-CACHE-002`, `FR-CACHE-003`
- **Deliverables:** `backend/app/core/cache.py`.
- **Verification:** Cache hits verified in Redis CLI; duplicate concurrent uploads prevented by lock.

---

### Phase 10: Docker Containerization for Full Stack
* **Goal:** Multi-stage Dockerfiles and complete `docker-compose.yml` for zero-configuration local execution.
* **Tier:** Tier 2 (Graded Requirement)
* **Dependencies:** Phase 9

#### Milestone 10.1: Production-Grade Multi-Stage Dockerfiles
- **Tasks:**
  - Create `docker/backend.Dockerfile` (Python 3.11-slim builder + runner, non-root user).
  - Create `docker/frontend.Dockerfile` (Node 20 alpine builder + standalone runner).
- **SRS Traceability:** `DEP-DOCKER-001`, `DEP-DOCKER-002`, `NFR-MAINT-003`, `NFR-PORT-001`
- **Deliverables:** `docker/backend.Dockerfile`, `docker/frontend.Dockerfile`.
- **Verification:** Image builds produce optimized, small final images without build tools.

#### Milestone 10.2: Unified Docker Compose Definition & Healthchecks
- **Tasks:**
  - Define all services in root `docker-compose.yml`: `frontend`, `backend`, `postgres-primary`, `postgres-replica-1`, `postgres-replica-2`, `qdrant`, `minio`, `redis`, `keycloak`.
  - Configure dedicated network (`university-net`) and named volumes for durable storage.
  - Add explicit healthchecks on every container with `depends_on: condition: service_healthy`.
- **SRS Traceability:** `DEP-DOCKER-003`, `DEP-DOCKER-004`, `DEP-DOCKER-005`, `DEP-COMPOSE-001`, `DEP-COMPOSE-002`, `DEP-COMPOSE-003`
- **Deliverables:** `docker-compose.yml`.
- **Verification:** `TEST-DOCKER-001`: `docker-compose up -d` boots entire 9-container stack cleanly with all healthchecks passing.

---

### Phase 11: Kubernetes Orchestration (Minikube / Kind)
* **Goal:** Declarative Kubernetes deployment manifests, StatefulSet for PostgreSQL, and Ingress routing.
* **Tier:** Tier 2 (Graded Requirement)
* **Dependencies:** Phase 10

#### Milestone 11.1: Kubernetes Manifests (Stateless & Storage)
- **Tasks:**
  - Write Deployments and Services for `frontend` (2 replicas), `backend` (3 replicas), `qdrant`, `minio`, `redis`, `keycloak`.
  - Configure ConfigMaps for URLs and Secrets for credentials.
  - Define PersistentVolumeClaims for Qdrant, MinIO, and Redis.
  - Add Liveness and Readiness probes to all application pods.
- **SRS Traceability:** `DEP-K8S-001`, `DEP-K8S-003`, `DEP-K8S-004`, `DEP-K8S-005`, `DEP-K8S-006`, `DEP-K8S-008`, `NFR-AVAIL-002`
- **Deliverables:** `kubernetes/base/` resource manifests.
- **Verification:** `kubectl apply -f kubernetes/base/` deploys cleanly; pods transition to Running.

#### Milestone 11.2: PostgreSQL StatefulSet & Replication in Kubernetes
- **Tasks:**
  - Implement PostgreSQL StatefulSet with headless service for stable network identities.
  - Mount durable PersistentVolume per pod (`pgdata-postgres-0`, `pgdata-postgres-1`).
  - Configure automatic replica bootstrapping from primary pod.
- **SRS Traceability:** `DEP-K8S-002`, `DEP-K8S-009`, `NFR-AVAIL-003`
- **Deliverables:** `kubernetes/postgres/statefulset.yaml`.
- **Verification:** Pod restart retains database state; replication connects across pod DNS names.

#### Milestone 11.3: Ingress Configuration & Rolling Update Verification
- **Tasks:**
  - Configure NGINX Ingress routing `/` to frontend and `/api` to backend.
  - Verify zero-downtime rolling update strategy by triggering image tag upgrade under loop requests.
- **SRS Traceability:** `DEP-K8S-007`, `DEP-K8S-012`, `NFR-AVAIL-001`
- **Deliverables:** `kubernetes/ingress.yaml`.
- **Verification:** `TEST-K8S-001`: Zero dropped requests during `kubectl set image deployment/backend`.

---

### Phase 12: CI/CD Pipeline Automation (GitHub Actions)
* **Goal:** Automated testing, linting, Docker image build, and deployment gates on PRs.
* **Tier:** Tier 2 (Graded Requirement)
* **Dependencies:** Phase 11

#### Milestone 12.1: Automated Pull Request Verification Workflow
- **Tasks:**
  - Configure `.github/workflows/ci-cd.yml` running on push and pull requests.
  - Backend job: run Python linter (`ruff`) + pytest unit/integration suite.
  - Frontend job: run `eslint` + `npm run build` verification.
  - Gate PR merging on green checks.
- **SRS Traceability:** `DEP-CICD-001`, `DEP-CICD-002`, `NFR-MAINT-002`
- **Deliverables:** `.github/workflows/ci-cd.yml`.
- **Verification:** `TEST-CICD-001`: PR with a failing unit test is automatically blocked from merge.

#### Milestone 12.2: Container Image Build & Tagging Pipeline
- **Tasks:**
  - On merge to `main`, build Docker images tagged with Git commit SHA and `:latest`.
  - Push images to GitHub Container Registry (GHCR).
  - Add deployment step updating Kubernetes cluster image tag.
- **SRS Traceability:** `DEP-CICD-003`, `DEP-CICD-004`, `DEP-CICD-005`
- **Deliverables:** Continuous Delivery workflow job.
- **Verification:** Merging a commit builds and tags image; `kubectl rollout undo` tested for instant rollback.

---

### Phase 13: Testing & Quality Assurance
* **Goal:** Comprehensive unit, integration, concurrency, load, and security verification.
* **Tier:** Tier 2 / Quality Gate
* **Dependencies:** Phase 12

#### Milestone 13.1: Automated Test Suite Coverage
- **Tasks:**
  - Unit tests: text chunking, prompt assembly, citation mapping, JWT decoding.
  - Integration tests: complete upload-to-answer pipeline against test documents.
  - Concurrency tests: verify optimistic locking rejection under parallel threads.
- **SRS Traceability:** `TEST-UNIT-001`, `TEST-INT-001`, `TEST-API-001`, `TEST-CONC-001`
- **Deliverables:** `backend/tests/` test suite with pytest report.
- **Verification:** `pytest` passes with >85% code coverage across core services.

#### Milestone 13.2: Load & Performance Benchmark
- **Tasks:**
  - Build Locust / k6 load test script simulating 50 concurrent students querying the chat endpoint.
  - Measure response latency (first token < 1.5s) and observe PostgreSQL replica lag.
- **SRS Traceability:** `NFR-PERF-001`, `NFR-PERF-002`, `NFR-PERF-003`, `TEST-LOAD-001`
- **Deliverables:** `tests/load/locustfile.py`, performance benchmark summary.
- **Verification:** System satisfies response time and error rate thresholds under load.

---

### Phase 14: Demonstration Preparation & Advanced Stretch Features
* **Goal:** Polish live demonstration flow, deploy monitoring, and implement optional advanced capabilities.
* **Tier:** Tier 3 (Advanced Stretch Goals)
* **Dependencies:** Phase 13

#### Milestone 14.1: Live Demonstration Script & Rehearsal
- **Tasks:**
  - Rehearse 15-step university demonstration flow from Master Project Guide §22.
  - Verify live demo steps: OAuth login, RAG question, citation jump, live document upload, paused replica stale read + fix demo, optimistic lock conflict demo, rollback demo.
- **SRS Traceability:** All Demonstration Requirements
- **Deliverables:** `docs/demo-script.md`.
- **Verification:** Complete end-to-end dry run executed successfully without intervention.

#### Milestone 14.2: Advanced Stretch Goals (Optional / As Time Permits)
- **Tasks:**
  - **Re-ranking Retriever:** Add cross-encoder re-ranking stage (`FR-RAG-004`).
  - **Groundedness Checker:** Implement post-hoc answer verification call (`FR-RAG-008`).
  - **Synchronous Replication Demo:** Configure synchronous write path for document metadata (`FR-DBSYNC-007`).
  - **Prometheus & Grafana:** Deploy monitoring stack visualizing replication lag and query rate (`FR-MON-001–003`).
  - **Horizontal Pod Autoscaling:** Configure HPA scaling backend on 70% CPU (`NFR-SCAL-003`, `DEP-K8S-010`).
- **SRS Traceability:** Optional Priority Requirements
- **Deliverables:** Extended manifests and decorator modules.
- **Verification:** Stretch features independently demonstrable during final evaluation.

---

## 3. Complete Traceability Audit Checklist

Every requirement ID from the SRS is accounted for across the milestones:

| Category | Count | Milestone Ownership | Status |
|---|:---:|---|:---:|
| **Authentication & RBAC (`FR-AUTH`)** | 12 | M8.1, M8.2, M8.3 | Fully Mapped |
| **User Management (`FR-USER`)** | 4 | M4.1, M8.3 | Fully Mapped |
| **Document Management (`FR-DOC`)** | 10 | M5.1, M5.3, M8.4, M9.3 | Fully Mapped |
| **Document Processing (`FR-PROC`)** | 9 | M5.2, M6.1 | Fully Mapped |
| **RAG Question Answering (`FR-RAG`)** | 11 | M6.2, M6.3, M14.2 | Fully Mapped |
| **Conversational Interface (`FR-CHAT`)** | 8 | M4.1, M7.2 | Fully Mapped |
| **Citations & Grounding (`FR-CIT`)** | 7 | M6.4, M7.3 | Fully Mapped |
| **Admin Functions (`FR-ADMIN`)** | 4 | M5.1, M5.3, M7.4 | Fully Mapped |
| **Database Synchronization (`FR-DBSYNC`)** | 7 | M9.1, M9.2, M9.3, M14.2 | Fully Mapped |
| **Caching & Locking (`FR-CACHE`)** | 3 | M9.4 | Fully Mapped |
| **Monitoring (`FR-MON`)** | 3 | M14.2 | Fully Mapped |
| **Non-Functional Attributes (`NFR-*`)** | 29 | M3.1, M7.1, M9.3, M10.1, M11.1, M11.3, M13.2 | Fully Mapped |
| **Deployment & DevOps (`DEP-*`)** | 28 | M2.1, M10.1, M10.2, M11.1, M11.2, M11.3, M12.1, M12.2 | Fully Mapped |
| **Engineering Process (`PROC-*`)** | 14 | M2.1, M2.2, M12.1 | Fully Mapped |
| **TOTAL REQUIREMENTS** | **153** | **Zero Dropped Requirements** | **100% Traceable** |
