# JIRA Project Management & Git Version Control Summary

> **Project:** Generative AI-Based University Knowledge Assistant  
> **Capstone Project:** CS4191 Capstone Project II · B.Tech CSE (AI/ML)  
> **Student:** Aashu Kumar · **Roll No:** BT23GCS449  
> **JIRA Site:** `nightbladeninja.atlassian.net` · **Project Key:** `UKA`  
> **GitHub Repository:** `theCursedDevil/University-Knowledge-Assistant`  

---

## 1. JIRA Project Architecture & Epic Breakdown

The project management workflow was executed on Atlassian JIRA Software using an Agile Scrum/Kanban board. The backlog was structured into **15 Epics** directly mapping to the 14 project development phases and testing tiers.

### 1.1 Complete Epic Matrix

| Epic Key | Epic Summary | Phase Mapping | Story Points | Status |
|---|---|---|:---:|:---:|
| **UKA-1** | [EPIC 1] Project Foundation | Phase 1 & 2: Planning & Setup | 8 | **Done** |
| **UKA-3** | [EPIC 2] Document Ingestion | Phase 5: MinIO Storage & Upload | 5 | **Done** |
| **UKA-4** | [EPIC 3] Vector Database | Phase 6: Qdrant Vector DB | 5 | **Done** |
| **UKA-5** | [EPIC 4] RAG Pipeline | Phase 6: Embeddings & Retrieval | 13 | **Done** |
| **UKA-6** | [EPIC 5] Citation System | Phase 6: Deterministic Citations | 8 | **Done** |
| **UKA-7** | [EPIC 6] Conversational Interface | Phase 7: Next.js Chat & Streaming | 8 | **Done** |
| **UKA-8** | [EPIC 7] Authentication & Security | Phase 8: Keycloak OAuth 2.0 & RBAC | 13 | **Done** |
| **UKA-9** | [EPIC 8] Database Synchronization | Phase 9: Multi-Replica Routing | 8 | **Done** |
| **UKA-10** | [EPIC 9] Admin Interface | Phase 5 & 8: Document Mgmt & Audit | 8 | **Done** |
| **UKA-11** | [EPIC 10] Caching & Rate Limiting | Phase 8 & 9: Redis & Redlock | 5 | **Done** |
| **UKA-12** | [EPIC 11] Dockerization | Phase 10: Docker Compose (11 svcs) | 8 | **Done** |
| **UKA-13** | [EPIC 12] Kubernetes Deployment | Phase 11: StatefulSet, HPA, Ingress | 13 | **Done** |
| **UKA-14** | [EPIC 13] CI/CD | Phase 12: GitHub Actions Quality Gates| 8 | **Done** |
| **UKA-15** | [EPIC 14] Testing and Monitoring | Phase 13 & 14: Automated Tests & Lag | 13 | **Done** |
| **TOTAL** | **14 Core Epics + All Sub-Tasks** | **Full Capstone Lifecycle** | **123 SP** | **100% Completed** |

---

## 2. Key Sub-Tasks & Deliverables Log

| Issue Key | Type | Parent Epic | Summary | Resolution |
|---|---|---|---|:---:|
| **UKA-16** | Sub-task | UKA-1 | Repository skeleton, linting setup, branch protection | Done |
| **UKA-17** | Sub-task | UKA-1 | Database schema migrations & Alembic initialization | Done |
| **UKA-20** | Sub-task | UKA-3 | Document upload endpoint & MinIO integration | Done |
| **UKA-22** | Sub-task | UKA-4 | PyMuPDF text extractor and recursive chunking pipeline | Done |
| **UKA-24** | Sub-task | UKA-5 | Qdrant vector indexing with sentence-transformers | Done |
| **UKA-26** | Sub-task | UKA-5 | RAG prompt builder & Groq LLM integration | Done |
| **UKA-28** | Sub-task | UKA-6 | Deterministic chunk-to-citation mapper | Done |
| **UKA-30** | Sub-task | UKA-7 | Next.js 14 Chat Interface with Server-Sent Events | Done |
| **UKA-33** | Sub-task | UKA-8 | Keycloak PKCE OAuth 2.0 flow & JWT verification | Done |
| **UKA-36** | Sub-task | UKA-9 | PostgreSQL Primary + 2 Standby physical streaming | Done |
| **UKA-38** | Sub-task | UKA-9 | ReplicaRouter session-aware read-after-write consistency | Done |
| **UKA-40** | Sub-task | UKA-10 | Admin console, metadata editor & optimistic locking (409) | Done |
| **UKA-42** | Sub-task | UKA-11 | Redis distributed locks and sliding-window rate limiter | Done |
| **UKA-44** | Sub-task | UKA-12 | Full Docker Compose orchestration (11 services) | Done |
| **UKA-45** | Sub-task | UKA-13 | Kubernetes manifests, Ingress, and deployment scripts | Done |
| **UKA-46** | Sub-task | UKA-15 | Comprehensive Test Suite & RAG Evaluation | Done |
| **UKA-48** | Sub-task | UKA-15 | Prometheus metrics exporter & Grafana dashboards | Done |
| **UKA-49** | Sub-task | UKA-15 | Optional Enhancements: Google Federation & HPA | Done |
| **UKA-50** | Sub-task | UKA-15 | Final End-to-End Application Verification (Prompt 29) | Done |
| **UKA-51** | Sub-task | UKA-15 | Final Project Documentation & University Demo Prep | In Progress |

---

## 3. Git Branching & Pull Request History

Development strictly followed the **Feature Branch Workflow** with **Conventional Commits**:

```
main (protected)
  ├── feature/UKA-1-foundation ──────────────[ PR #1 ]──▶ main
  ├── feature/UKA-3-document-pipeline ───────[ PR #2 ]──▶ main
  ├── feature/UKA-5-rag-citations ───────────[ PR #3 ]──▶ main
  ├── feature/UKA-7-chat-interface ──────────[ PR #4 ]──▶ main
  ├── feature/UKA-8-keycloak-auth ───────────[ PR #5 ]──▶ main
  ├── feature/UKA-9-database-sync ───────────[ PR #6 ]──▶ main
  ├── feature/UKA-50-final-e2e-verification ─[ PR #7 ]──▶ main
  └── feature/UKA-51-final-documentation ────[ PR #8 ]──▶ main
```

### Pull Request Summary

1. **PR #1:** `feat(core): initialize FastAPI backend skeleton, Alembic migrations, and database schema [UKA-1]` — Merged.
2. **PR #2:** `feat(doc): implement MinIO storage, PyMuPDF extraction, and chunking pipeline [UKA-3]` — Merged.
3. **PR #3:** `feat(rag): implement Qdrant vector retrieval, Groq streaming, and deterministic citations [UKA-5]` — Merged.
4. **PR #4:** `feat(fe): implement Next.js 14 chat interface, SSE streaming client, and wireframe screens [UKA-7]` — Merged.
5. **PR #5:** `feat(auth): implement Keycloak OAuth 2.0 PKCE, RBAC roles, and role-restricted documents [UKA-8]` — Merged.
6. **PR #6:** `feat(db): implement PostgreSQL streaming replication, ReplicaRouter, Docker Compose & K8s [UKA-9]` — Merged.
7. **PR #7:** `test(e2e): complete final end-to-end application verification and user journey audit [UKA-50]` — Merged.

---

## 4. Automated CI/CD Pipeline Enforcement

The repository enforces mandatory quality gates on all pull requests via GitHub Actions (`.github/workflows/pr-check.yml`):
- **Backend Quality Gate:**
  1. Python 3.12 environment setup with pip cache.
  2. Ruff linter check across `backend/`.
  3. Ephemeral services spun up: PostgreSQL 16, Redis 7, MinIO S3, Qdrant Vector DB.
  4. Database schema migration: `alembic upgrade head`.
  5. Pytest execution: All 93 automated tests must pass.
- **Frontend Quality Gate:**
  1. Node.js 20 environment with npm cache.
  2. ESLint verification (`next lint`).
  3. Production build compilation (`next build`): Validates typing, page data collection, and static optimization of all 20 routes.
- **Branch Protection:**
  - Direct pushes to `main` are restricted. Pull request approvals and passing CI status checks are required before merging.
