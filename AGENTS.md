# AGENTS.md — Development Instructions

## Project

**Generative AI-Based University Knowledge Assistant**
B.Tech CSE (AI/ML) Capstone Project · CS4191 Capstone Project II
Student: Aashu Kumar · BT23GCS449

## Source-of-Truth Documents

All development decisions must be traceable to these four project documents
located in `docs/reference/`:

| Document | Use for |
|---|---|
| **Master Project Guide** | Technology stack, architecture, development roadmap, build order, MVP vs Advanced scope, repository structure, API design, database design, demo flow |
| **SRS** (Software Requirements Specification v1.0) | Functional requirements (FR-AUTH, FR-DOC, FR-PROC, FR-RAG, FR-CHAT, FR-CIT, FR-ADMIN, FR-SYNC, FR-CACHE, FR-MON), non-functional requirements, requirement priorities (Must / Should / Optional), acceptance criteria, traceability matrix |
| **SDD** (Software Design Document v1.0) | Component decomposition (C-FE, C-AUTHSVC, C-DOCSVC, C-PROC, C-RAGSVC, C-CHATSVC, C-CIT, C-ADMINSVC, C-DAL, C-CACHE, C-MON), data design, interaction sequences, state machines, algorithms, deployment structure, design rationale |
| **Wireframe Models** (v1.0) | 13 screen wireframes (W-01 through W-13), 5 system states (S-1 through S-5), complete navigation flow (F-1), UI component specifications |

---

## Project Development Rules

1. Follow the uploaded project documents as the source of truth.
2. Use the SRS for functional requirements and priority.
3. Use the Master Project Guide for the technology stack and roadmap.
4. Use the SDD for detailed implementation and architecture.
5. Use Wireframe Models for all UI design decisions.
6. Build **one FastAPI backend application**, not microservices.
7. Use the documented technologies:
   - **Frontend:** Next.js (React) + Tailwind CSS
   - **Backend:** FastAPI (Python)
   - **RAG Framework:** LangChain
   - **Embedding Model:** Sentence Transformers (all-MiniLM-L6-v2)
   - **Vector Database:** Qdrant
   - **Relational Database:** PostgreSQL (primary + 2 read replicas)
   - **Object Storage:** MinIO
   - **Cache / Locking:** Redis
   - **Identity Provider:** Keycloak (OAuth 2.0 / OIDC)
   - **LLM:** Groq OR Google Gemini (free-tier, no local GPU)
   - **Containerization:** Docker + Docker Compose
   - **Orchestration:** Kubernetes (Minikube/Kind)
   - **CI/CD:** GitHub Actions
   - **Project Management:** JIRA
8. Keep code readable and appropriate for a B.Tech student.
9. Do not create unnecessary abstractions or dependencies.
10. Do not replace working code without a clear reason.
11. Work one phase at a time.
12. Run tests after every meaningful implementation phase.
13. Maintain a README, environment example (`.env.example`) and progress checklist.
14. Keep secrets out of source control.
15. Keep frontend access to databases and LLMs **indirect through FastAPI** — the backend is the only component that talks to PostgreSQL, Qdrant, MinIO, Redis, and the LLM API.
16. Use meaningful Git commits and associate changes with JIRA tickets.
17. Do not fabricate citations, test results, deployments or JIRA activity.
18. Never claim that a feature is completed without verifying it.

---

## Git Rules

- `main` must remain deployable.
- Use `feature/<JIRA-ID>-short-description` branches.
- Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).
- Link pull requests with JIRA tickets (`UKA-<number>` in PR title/description).
- Run CI before merging.
- Never commit `.env`, credentials, or API keys.
- `.gitignore` must include: `.env`, `node_modules/`, `__pycache__/`, `*.pyc`, `venv/`, build artifacts.
- Tag milestones: `v0.1-mvp`, `v1.0-final`, etc.

---

## Execution Rules

- Inspect the existing code before editing.
- Make small, logically grouped changes.
- Do not create duplicate files or modules.
- Explain potentially destructive changes.
- Ask for permission before deleting data, merging PRs, or deploying externally.
- After each phase, report: files changed, tests run, and results.

---

## Simplification Rule

When an implementation can be achieved using a simple function, existing module,
or standard library, prefer that over a complicated new abstraction.

This project should be complete and demonstrable, not overengineered.

---

## Architecture Reference

```
Client                    Application Layer              AI / RAG Pipeline         Data & Storage
─────────                 ────────────────               ─────────────────         ──────────────
Browser ──────────────▶  Frontend (Next.js)              RAG Pipeline              PostgreSQL Primary
  student / faculty       │                              (LangChain)                 ├── Replica 1
                          │   Keycloak                    │                           └── Replica 2
Admin console ────────▶  │   OAuth 2.0 / OIDC            ├── Doc Processing
  document upload         │                              │   extract/clean/chunk     Qdrant (vectors)
                          ▼                              │
                        Backend API (FastAPI)             ├── Embedding Model        MinIO (files)
                         /auth /chat /conversations      │   sentence-transformers
                         /documents /admin               │                          Redis (cache+locks)
                                                         └── LLM API
                                                             Groq / Gemini
```

## Repository Structure

```
project-root/
├── frontend/                  # Next.js app
│   ├── app/ or pages/
│   ├── components/
│   └── package.json
├── backend/                   # FastAPI app
│   ├── app/
│   │   ├── api/               # routers: auth, chat, documents, conversations
│   │   ├── rag/               # retrieval, prompt building
│   │   ├── db/                # models, session, replica router
│   │   └── core/              # config, security
│   ├── tests/
│   └── requirements.txt
├── document-processing/       # extraction/chunking (or folded into backend)
├── database/
│   ├── migrations/            # Alembic
│   └── init-replication.sql
├── docker/
│   ├── frontend.Dockerfile
│   └── backend.Dockerfile
├── kubernetes/
│   ├── base/                  # Deployments, Services, ConfigMaps
│   ├── postgres/              # StatefulSet + replication config
│   └── ingress.yaml
├── .github/
│   └── workflows/ci-cd.yml
├── docs/
│   ├── reference/             # SRS, SDD, Master Guide, Wireframes (PDFs)
│   ├── architecture.md
│   └── demo-script.md
├── scripts/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── AGENTS.md                  # This file
└── README.md
```

## API Endpoints

| Method & Path | Purpose | Auth |
|---|---|---|
| `GET /auth/callback` | OAuth redirect handler | Public |
| `GET /me` | Current user profile + roles | User |
| `POST /documents` | Upload a document (multipart) | Admin |
| `GET /documents` | List documents | User |
| `DELETE /documents/{id}` | Remove a document | Admin |
| `POST /conversations` | Start a new conversation | User |
| `GET /conversations` | List user's conversations | User |
| `GET /conversations/{id}` | Get messages in a conversation | User (owner) |
| `POST /conversations/{id}/messages` | Ask a question (streams answer + citations) | User (owner) |
| `GET /admin/stats` | Usage/analytics | Admin |

## Database Schema (PostgreSQL)

```sql
users(id, oauth_sub, name, email, role, created_at)
documents(id, title, category, storage_path, uploaded_by, version, created_at)
document_chunks_meta(id, document_id, chunk_index, page, section, vector_id)
conversations(id, user_id, title, created_at, updated_at)
messages(id, conversation_id, role, content, citations_json, created_at)
audit_log(id, user_id, action, entity, entity_id, created_at)
```

## Development Phases (Build Order)

| Phase | What's Done | Output |
|---|---|---|
| 1. Planning & Requirements | Finalize scope, MVP boundary | Requirements doc |
| 2. Git + JIRA Setup | Repo skeleton, branch protection, JIRA board | Structured repo |
| 3. Backend Skeleton | FastAPI app, health endpoint, project structure | Running API shell |
| 4. Database | Postgres schema, Alembic migrations | Working DB |
| 5. Document Processing | Upload endpoint, text extraction, chunking | Chunks in DB |
| 6. RAG Core | Embeddings + Qdrant + retrieval + LLM call | Working Q&A |
| 7. Conversational Interface | Chat UI, streaming, history | Usable chat app |
| 8. OAuth | Keycloak deployed, login flow, RBAC | Secured app |
| 9. DB Synchronization | Replicas, read routing, optimistic locking | Sync demo |
| 10. Docker | Dockerfiles + Compose for everything | `docker-compose up` works |
| 11. Kubernetes | Manifests, Minikube deploy | App running on K8s |
| 12. CI/CD | GitHub Actions pipeline | Auto build/test/deploy |
| 13. Testing | Unit + integration + load tests | Test report |
| 14. Deployment & Demo Prep | Final deploy, monitoring, demo script | Live demo environment |

## Priority Tiers

| Tier | Items |
|---|---|
| **Must Have** | RAG Q&A with citations, conversational interface, OAuth with roles, document upload (admin), Docker Compose, Kubernetes deployment, CI/CD pipeline, Git + JIRA from Day 1, primary + 2 replica Postgres |
| **Should Have** | Read-after-write consistency fix, optimistic locking demo, streaming chat, rate limiting, role-restricted document access, source citation display |
| **Optional / Advanced** | Re-ranking retrieval, groundedness checker, synchronous replication, HPA autoscaling, Prometheus/Grafana dashboards, Keycloak-federated Google login |

## Integrations

| Tool | Account | Site / Repo |
|---|---|---|
| **GitHub** (MCP) | `theCursedDevil` (Aashu Kumar) | `theCursedDevil/GenerativeAiBasedUniversityKnowledgeAssistant` |
| **JIRA** (TWG CLI) | `nightbladeninja.v@gmail.com` | `nightbladeninja.atlassian.net` · Project key: `UKA` |
| **GitHub Actions** | Same GitHub account | Workflows in `.github/workflows/` |

## Wireframe Screen Index

| ID | Screen | Guide Reference |
|---|---|---|
| W-01 | Login | §7 OAuth |
| W-02 | OAuth Login Flow | §7, §17 |
| W-03 | Dashboard | §1, §6, §17 |
| W-04 | Chat Interface | §1, §6, §17 |
| W-05 | AI Response + Citation Panel | §5, §6 |
| W-06 | Conversation History | §1, §6, §17 |
| W-07 | Document Search | §17, §18 |
| W-08 | Document Preview | §3, §18, §22 |
| W-09 | Citation View | §5, §6, §22 |
| W-10 | User Profile | §7, §17, §18 |
| W-11 | Admin: Document Upload | §1, §17, §19 |
| W-12 | Admin: Metadata Management | §8, §18 |
| W-13 | Admin: Analytics Dashboard | §17 |
| S-1–S-5 | System States | Loading, Empty, No Results, Error, Permission Denied |
| F-1 | Complete Navigation Flow | §5, §6, §7, §17, §22 |
