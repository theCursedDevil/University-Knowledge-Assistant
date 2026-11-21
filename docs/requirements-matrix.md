# Requirements Traceability Matrix

> **Project:** Generative AI-Based University Knowledge Assistant  
> **Document:** Requirements Traceability Matrix (SRS v1.0 Baseline)  
> **Source:** CS4191 Capstone Project II — Software Requirements Specification  

---

## Overview

This document tracks every single functional requirement (FR), non-functional requirement (NFR), deployment requirement (DEP), and engineering process requirement (PROC) from the project Software Requirements Specification (SRS v1.0).

Each entry specifies:
- **Requirement ID:** Normative identifier used across SDD, tests, commits, and JIRA.
- **Requirement Description:** Complete specification of the system behavior.
- **Priority Tier:** **Must Have** (core deliverable for passing evaluation), **Should Have** (secondary graded deliverables), or **Optional** (advanced stretch goals).
- **Planned Implementation Phase:** Mapped to the 14-phase build order from the Master Project Guide.
- **Verification / Testing Method:** Explicit test identifier from SRS Appendix I or verification procedure.

---

## 1. Authentication and Authorization

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `FR-AUTH-001` | The system shall authenticate users via the OAuth 2.0 Authorization Code flow with PKCE against a self-hosted Keycloak identity provider. | **Must Have** | Phase 8 (OAuth & Keycloak) | `TEST-AUTH-001 (JWT & Session Tests)` |
| `FR-AUTH-002` | The system shall redirect unauthenticated users attempting to access protected functionality to the Keycloak login page. | **Must Have** | Phase 8 (OAuth & Keycloak) | `Manual / UI Test (Redirect verification)` |
| `FR-AUTH-003` | The backend shall validate every incoming access token's signature against | **Must Have** | Phase 8 (OAuth & Keycloak) | `TEST-AUTH-001 (JWT & Session Tests)` |
| `FR-AUTH-004` | The backend shall verify the exp (expiration) and iss (issuer) claims of every access token and reject requests bearing expired or wrong-issuer tokens. | **Must Have** | Phase 8 (OAuth & Keycloak) | `TEST-AUTH-001 (JWT & Session Tests)` |
| `FR-AUTH-005` | The system shall define three Keycloak realm roles — student, faculty, admin — and embed the user's role(s) in the issued token's claims. | **Must Have** | Phase 8 (OAuth & Keycloak) | `Manual / Keycloak Config Review` |
| `FR-AUTH-006` | The backend shall enforce role-based authorization on every protected route server- side, independent of any role check performed by the frontend. | **Must Have** | Phase 8 (OAuth & Keycloak) | `TEST-AUTHZ-001 (Role Authorization Tests)` |
| `FR-AUTH-007` | The system shall respond with 401 Unauthorized to requests with a missing, invalid, or expired access token. | **Must Have** | Phase 8 (OAuth & Keycloak) | `TEST-AUTH-001 (JWT & Session Tests)` |
| `FR-AUTH-008` | The system shall respond with 403 Forbidden to requests from an authenticated user whose role does not permit the requested action. | **Must Have** | Phase 8 (OAuth & Keycloak) | `TEST-AUTHZ-001 (Role Authorization Tests)` |
| `FR-AUTH-009` | The system shall support logout, which clears client-held tokens and calls | **Must Have** | Phase 8 (OAuth & Keycloak) | `TEST-AUTH-001 (JWT & Session Tests)` |
| `FR-AUTH-010` | Access tokens shall be short-lived (target range 5–15 minutes; exact value TBD), with refresh tokens used to obtain new access tokens without full re-authentication. | **Should Have** | Phase 8 (OAuth & Keycloak) | `Manual / Keycloak Config Review` |
| `FR-AUTH-011` | The system shall avoid persisting access or refresh tokens in localStorage; session storage shall prefer httpOnly, secure cookies where feasible. | **Should Have** | Phase 8 (OAuth & Keycloak) | `TEST-AUTH-001 (JWT & Session Tests)` |
| `FR-AUTH-012` | All non-local deployments shall serve the application and Keycloak exclusively over HTTPS. | **Should Have** | Phase 8 (OAuth & Keycloak) | `TEST-AUTH-001 (JWT & Session Tests)` |

## 2. User Management

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `FR-USER-001` | The system shall expose the authenticated user's profile and role(s) via GET /me. | **Must Have** | Phase 3 (Backend Skeleton) & Phase 8 (OAuth) | `TEST-AUTH-001 (JWT & Session Tests)` |
| `FR-USER-002` | On a user's first successful login, the system shall provision a corresponding row in the users table (just-in-time provisioning) capturing oauth_sub, name, email, role, and created_at. | **Must Have** | Phase 4 (Database Schema) & Phase 8 (OAuth) | `TEST-AUTH-001 (JWT & Session Tests)` |
| `FR-USER-003` | The system shall support the three defined user classes (student, faculty, admin) described in Section 2.3. | **Must Have** | Phase 3 (Backend Skeleton) & Phase 8 (OAuth) | `TEST-AUTH-001 (JWT & Session Tests)` |
| `FR-USER-004` | The system shall keep authorization decisions tied to the role claim in the current token, not to a possibly stale, locally cached role value. | **Must Have** | Phase 3 (Backend Skeleton) & Phase 8 (OAuth) | `TEST-AUTHZ-001 (Role Authorization Tests)` |

## 3. Document Management

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `FR-DOC-001` | Admin-role users shall be able to upload a document (multipart upload) via POST /documents. | **Must Have** | Phase 5 (Document Processing & Upload API) | `TEST-API-001 (API Schemas) & TEST-DOC-001 (Upload Validation)` |
| `FR-DOC-002` | The system shall validate an uploaded file's type against an allow-list of supported MIME types/extensions before accepting it for processing, and shall reject unsupported types with a descriptive error. | **Must Have** | Phase 5 (Document Processing & Upload API) | `TEST-API-001 (API Schemas) & TEST-DOC-001 (Upload Validation)` |
| `FR-DOC-003` | The system shall reject uploads exceeding a configured maximum file size (exact limit TBD) with a descriptive error. | **Must Have** | Phase 5 (Document Processing & Upload API) | `TEST-API-001 (API Schemas) & TEST-DOC-001 (Upload Validation)` |
| `FR-DOC-004` | Authenticated users shall be able to list available documents via GET /documents. | **Must Have** | Phase 5 (Document Processing & Upload API) | `TEST-API-001 (API Schemas) & TEST-DOC-001 (Upload Validation)` |
| `FR-DOC-005` | Admin-role users shall be able to remove a document via DELETE /documents/{id}. | **Must Have** | Phase 5 (Document Processing & Upload API) | `TEST-API-001 (API Schemas) & TEST-DOC-001 (Upload Validation)` |
| `FR-DOC-006` | Deleting a document shall remove (or mark for removal) its stored file in object storage, its metadata record, and its associated vector-database chunks; exact orchestration/ordering of this multi-store deletion is TBD. | **Must Have** | Phase 5 (Document Processing & Upload API) | `TEST-API-001 (API Schemas) & TEST-DOC-001 (Upload Validation)` |
| `FR-DOC-007` | The system shall store original uploaded files in object storage (MinIO) rather than on a web-accessible filesystem path. | **Must Have** | Phase 5 (Document Processing & Upload API) | `TEST-API-001 (API Schemas) & TEST-DOC-001 (Upload Validation)` |
| `FR-DOC-008` | The system shall persist document metadata — title, category, storage_path, uploaded_by, version, created_at — in the documents table. | **Must Have** | Phase 5 (Document Processing & Upload API) | `TEST-API-001 (API Schemas) & TEST-DOC-001 (Upload Validation)` |
| `FR-DOC-009` | The system shall increment a document's version column on every successful metadata update, to support optimistic-locking conflict detection (see FR- DBSYNC-004). | **Must Have** | Phase 4 (DB Schema) & Phase 9 (DB Synchronization) | `TEST-API-001 (API Schemas) & TEST-DOC-001 (Upload Validation)` |
| `FR-DOC-010` | (Should-have) Where a document is marked as restricted to a specific role (e.g., faculty-only circulars), the system shall filter that document out of retrieval and listing results for users without the required role, enforced server-side rather than only in the UI. | **Should Have** | Phase 5 (Document Processing & Upload API) | `TEST-API-001 (API Schemas) & TEST-DOC-001 (Upload Validation)` |

## 4. Document Processing Pipeline

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `FR-PROC-001` | On successful upload, the system shall extract text content from the document (PDF, at minimum; other formats as supported). | **Must Have** | Phase 5 (Document Processing Pipeline) | `TEST-UNIT-001 (Chunking logic) & TEST-INT-001 (Pipeline integration)` |
| `FR-PROC-002` | The system shall clean extracted text (e.g., normalize whitespace, remove extraction artifacts) prior to chunking. | **Must Have** | Phase 5 (Document Processing Pipeline) | `TEST-UNIT-001 (Chunking logic) & TEST-INT-001 (Pipeline integration)` |
| `FR-PROC-003` | For documents containing tabular data (e.g., timetables), the system shall use a table-aware extraction method so that row/column structure is preserved rather than flattened into unreadable text. | **Should Have** | Phase 5 (Document Processing Pipeline) | `TEST-UNIT-001 (Chunking logic) & TEST-INT-001 (Pipeline integration)` |
| `FR-PROC-004` | The system shall split cleaned document text into chunks of approximately 500– 800 tokens with approximately 100 tokens of overlap between consecutive chunks, using a recursive/semantic-aware splitting strategy. | **Must Have** | Phase 5 (Document Processing Pipeline) | `TEST-UNIT-001 (Chunking logic) & TEST-INT-001 (Pipeline integration)` |
| `FR-PROC-005` | The system shall generate a fixed-length embedding vector for each chunk using the configured embedding model. | **Must Have** | Phase 5 (Document Processing Pipeline) | `TEST-UNIT-001 (Chunking logic) & TEST-INT-001 (Pipeline integration)` |
| `FR-PROC-006` | The system shall store each chunk's embedding vector and associated payload metadata in the vector database. | **Must Have** | Phase 5 (Document Processing Pipeline) | `TEST-UNIT-001 (Chunking logic) & TEST-INT-001 (Pipeline integration)` |
| `FR-PROC-007` | The system shall record, for each stored chunk, a linkage back to its originating document (document_id) so that PostgreSQL-side metadata and Qdrant-side vectors remain associated. | **Must Have** | Phase 5 (Document Processing Pipeline) | `TEST-UNIT-001 (Chunking logic) & TEST-INT-001 (Pipeline integration)` |
| `FR-PROC-008` | Processing of a typical document shall complete, making it retrievable, within a target turnaround time to be defined during implementation (TBD; the goal is that a newly uploaded document becomes searchable within minutes). | **Must Have** | Phase 5 (Document Processing Pipeline) | `TEST-UNIT-001 (Chunking logic) & TEST-INT-001 (Pipeline integration)` |
| `FR-PROC-009` | The system shall log document-processing failures without leaving the document's metadata or vector records in a partially processed, inconsistent state; exact atomicity/rollback semantics are TBD. | **Must Have** | Phase 5 (Document Processing Pipeline) | `TEST-UNIT-001 (Chunking logic) & TEST-INT-001 (Pipeline integration)` |

## 5. RAG-Based Question Answering

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `FR-RAG-001` | On receiving a user question, the system shall generate a query embedding using the same embedding model used during ingestion. | **Must Have** | Phase 6 (RAG Core Engine) | `TEST-RAG-001 (Hit-rate & Answer Correctness) & TEST-INT-001` |
| `FR-RAG-002` | The system shall perform a cosine-similarity vector search against the vector database, retrieving the top-K most similar chunks (K configurable; default K = 5). | **Must Have** | Phase 6 (RAG Core Engine) | `TEST-RAG-001 (Hit-rate & Answer Correctness) & TEST-INT-001` |
| `FR-RAG-003` | (Optional/advanced) The system may combine vector similarity search with metadata filters (e.g., a detected document category) when query-intent classification indicates a relevant filter (“hybrid” retrieval). | **Should Have** | Phase 6 (RAG Core Engine) | `TEST-RAG-001 (Hit-rate & Answer Correctness) & TEST-INT-001` |
| `FR-RAG-004` | (Optional/advanced) The system may apply a re-ranking step — retrieving a larger candidate set (e.g., top 20) and re-ranking with a cross-encoder to select the final top-K — to improve answer quality. | **Optional** | Phase 6 (RAG Core Engine) | `TEST-RAG-001 (Hit-rate & Answer Correctness) & TEST-INT-001` |
| `FR-RAG-005` | The system shall construct an LLM prompt composed of: system instructions, the retrieved chunks (with source labels), relevant recent conversation context, and the user's current question. | **Must Have** | Phase 6 (RAG Core Engine) | `TEST-RAG-001 (Hit-rate & Answer Correctness) & TEST-INT-001` |
| `FR-RAG-006` | The system's prompt instructions shall direct the LLM to answer only using the supplied retrieved context, and to explicitly state that the information is not available in the university documents when the context is insufficient. | **Must Have** | Phase 6 (RAG Core Engine) | `TEST-RAG-001 (Hit-rate & Answer Correctness) & TEST-INT-001` |
| `FR-RAG-007` | The system shall invoke the LLM with a low-temperature generation setting (target range 0–0.3; exact value TBD) to reduce hallucination. | **Must Have** | Phase 6 (RAG Core Engine) | `TEST-RAG-001 (Hit-rate & Answer Correctness) & TEST-INT-001` |
| `FR-RAG-008` | (Optional/advanced) The system may perform a groundedness check — verifying that the generated answer is actually supported by the retrieved/cited chunks — before returning it to the user. | **Optional** | Phase 6 (RAG Core Engine) | `TEST-RAG-001 (Groundedness Evaluation)` |
| `FR-RAG-009` | When the top retrieval similarity score falls below a configured confidence threshold (exact value TBD), the system shall skip LLM answer generation and instead return a fallback message indicating the information was not found, optionally including the closest documents retrieved. | **Should Have** | Phase 6 (RAG Core Engine) | `TEST-RAG-001 (Hit-rate & Answer Correctness) & TEST-INT-001` |
| `FR-RAG-010` | The system shall stream the generated answer to the frontend incrementally rather than waiting for full generation to complete. | **Must Have** | Phase 6 (RAG Core Engine) | `TEST-RAG-001 (Hit-rate & Answer Correctness) & TEST-INT-001` |
| `FR-RAG-011` | On completion of streaming, the system shall persist the full generated answer (and any associated citation data) to the messages table. | **Must Have** | Phase 6 (RAG Core Engine) | `TEST-RAG-001 (Hit-rate & Answer Correctness) & TEST-INT-001` |

## 6. Conversational Interface

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `FR-CHAT-001` | Authenticated users shall be able to start a new conversation via POST /conversations. | **Must Have** | Phase 7 (Conversational Interface) | `TEST-INT-001 / SSE Stream Verification` |
| `FR-CHAT-002` | The system shall list a user's own conversations, ordered by most recently updated, via GET /conversations. | **Must Have** | Phase 7 (Conversational Interface) | `TEST-API-001 & Manual UI Test` |
| `FR-CHAT-003` | The system shall retrieve the full message history of a conversation via GET /conversations/{id}, restricted to the conversation's owner. | **Must Have** | Phase 7 (Conversational Interface) | `TEST-API-001 & Manual UI Test` |
| `FR-CHAT-004` | Authenticated users shall be able to submit a question within an existing conversation via POST /conversations/{id}/messages. | **Must Have** | Phase 7 (Conversational Interface) | `TEST-API-001 & Manual UI Test` |
| `FR-CHAT-005` | The system shall incorporate recent conversation turns (the last N messages, N TBD, default target ~6) into the RAG prompt context so that follow-up questions are understood in context. | **Should Have** | Phase 7 (Conversational Interface) | `TEST-API-001 & Manual UI Test` |
| `FR-CHAT-006` | (Optional/advanced) For long conversations, the system may maintain a running LLM-generated summary of older turns, combined with the raw most-recent turns, to keep the prompt size manageable. | **Should Have** | Phase 7 (Conversational Interface) | `TEST-API-001 & Manual UI Test` |
| `FR-CHAT-007` | The system shall persist every user and assistant message, including role, content, and (for assistant messages) any citation data, in the messages table. | **Must Have** | Phase 7 (Conversational Interface) | `TEST-API-001 & Manual UI Test` |
| `FR-CHAT-008` | The system shall restrict access to a conversation and its messages to the owning user, except where an admin capability explicitly requires broader access (TBD whether any such admin access is implemented). | **Must Have** | Phase 7 (Conversational Interface) | `TEST-API-001 & Manual UI Test` |

## 7. Source & Citation Support

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `FR-CIT-001` | The system shall associate processed document chunks with identifiable source information captured during document processing. | **Should Have** | Phase 6 (RAG Core) & Phase 7 (Conversational UI) | `TEST-UNIT-001 (Citation mapping) & TEST-INT-001` |
| `FR-CIT-002` | The system shall retain metadata required for source traceability for each stored chunk; the exact field set is TBD — to be finalized during document-ingestion/database design (see Section 3.4). | **Should Have** | Phase 6 (RAG Core) & Phase 7 (Conversational UI) | `TEST-UNIT-001 (Citation mapping) & TEST-INT-001` |
| `FR-CIT-003` | The system shall associate any retrieved chunk actually used to generate an answer with its originating document, via the chunk's recorded document_id linkage. | **Should Have** | Phase 6 (RAG Core) & Phase 7 (Conversational UI) | `TEST-UNIT-001 (Citation mapping) & TEST-INT-001` |
| `FR-CIT-004` | The system shall display source information alongside a generated answer only when sufficient metadata is available for the chunks actually used to produce that answer. | **Should Have** | Phase 6 (RAG Core) & Phase 7 (Conversational UI) | `TEST-UNIT-001 (Citation mapping) & TEST-INT-001` |
| `FR-CIT-005` | The system shall never generate or display a fabricated source reference. Citations shall be derived deterministically from the chunk IDs actually retrieved and passed into the prompt — never invented or inferred by the LLM. | **Should Have** | Phase 6 (RAG Core) & Phase 7 (Conversational UI) | `TEST-UNIT-001 (Citation mapping) & TEST-INT-001` |
| `FR-CIT-006` | The exact citation metadata schema (candidate fields include document name, page number, section heading, and upload date) shall be finalized during document- ingestion/database design; until finalized, this remains an explicit open dependency of this SRS (see Appendix F, Section 5.6). | **Should Have** | Phase 6 (RAG Core) & Phase 7 (Conversational UI) | `TEST-UNIT-001 (Citation mapping) & TEST-INT-001` |
| `FR-CIT-007` | When citation metadata for a chunk actually used in an answer is incomplete or unavailable, the system shall present the answer without a broken or partial citation rather than fabricate the missing fields. | **Should Have** | Phase 6 (RAG Core) & Phase 7 (Conversational UI) | `TEST-UNIT-001 (Citation mapping) & TEST-INT-001` |

## 8. Administrative Functions

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `FR-ADMIN-001` | Admin-role users shall be able to upload and delete documents, per Section 3.2.3. | **Must Have** | Phase 5 (Doc API) & Phase 7 (Admin UI) | `TEST-API-001 & TEST-AUTHZ-001` |
| `FR-ADMIN-002` | Admin-role users shall be able to view usage/analytics statistics via GET /admin/stats. | **Must Have** | Phase 5 (Doc API) & Phase 7 (Admin UI) | `TEST-API-001 & TEST-AUTHZ-001` |
| `FR-ADMIN-003` | The system shall log administrative actions (document uploads, deletions, and metadata edits) to an audit_log table, capturing the acting user, action, entity type, entity ID, and timestamp. | **Must Have** | Phase 5 (Doc API) & Phase 7 (Admin UI) | `TEST-API-001 & TEST-AUTHZ-001` |
| `FR-ADMIN-004` | The system shall respond with 403 Forbidden when a non-admin user attempts to access an admin-only endpoint. | **Should Have** | Phase 5 (Doc API) & Phase 7 (Admin UI) | `TEST-API-001 & TEST-AUTHZ-001` |

## 9. Database Synchronization & Concurrency Control

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `FR-DBSYNC-001` | The system's relational data store shall run as one PostgreSQL primary instance with at least two read replicas, using PostgreSQL's built-in (asynchronous, by default) streaming replication. | **Must Have** | Phase 9 (DB Synchronization & Replication) | `TEST-DB-001 (Read-After-Write & Streaming Replication)` |
| `FR-DBSYNC-002` | The backend shall route write queries exclusively to the primary instance and shall route read-only queries across the available read replicas (e.g., round-robin). | **Must Have** | Phase 9 (DB Synchronization & Replication) | `TEST-DB-001 (Read-After-Write & Streaming Replication)` |
| `FR-DBSYNC-003` | Immediately following a write by a given user, the system shall route that user's subsequent reads (within a short session window; exact duration TBD) to the primary instance rather than a replica, providing read-your-own-writes consistency. | **Should Have** | Phase 9 (DB Synchronization & Replication) | `TEST-DB-001 (Read-After-Write & Streaming Replication)` |
| `FR-DBSYNC-004` | The system shall implement optimistic locking on document metadata updates using a version integer column: every UPDATE shall include a WHERE version = :expected_version clause and increment the version on success. | **Should Have** | Phase 4 (DB Schema) & Phase 9 (DB Synchronization) | `TEST-CONC-001 (Concurrent Metadata Edits / 409 Conflict)` |
| `FR-DBSYNC-005` | When an optimistic-locking UPDATE affects zero rows (indicating a stale write), the system shall respond with 409 Conflict and require the client to retry against refreshed data. | **Should Have** | Phase 4 (DB Schema) & Phase 9 (DB Synchronization) | `TEST-CONC-001 (Concurrent Metadata Edits / 409 Conflict)` |
| `FR-DBSYNC-006` | The system shall expose PostgreSQL replication lag as a monitorable metric (see | **Should Have** | Phase 9 (DB Synchronization & Replication) | `Manual / Dashboard Review (pg_stat_replication)` |
| `FR-DBSYNC-007` | (Optional/advanced) The system may use synchronous replication for a designated critical write path (e.g., the primary document-metadata write waiting for at least one replica acknowledgment) to demonstrate the synchronous-vs-asynchronous durability/latency trade-off. | **Optional** | Phase 9 (DB Synchronization & Replication) | `TEST-DB-001 (Read-After-Write & Streaming Replication)` |

## 10. Caching and Distributed Locking

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `FR-CACHE-001` | The system shall use Redis to cache frequently requested read data in order to reduce database load; exact cache keys and TTLs are TBD. | **Should Have** | Phase 9 (DB Synchronization & Caching) | `TEST-INT-001 / Redis CLI & Mocked Cache Hit-Rate Test` |
| `FR-CACHE-002` | The system shall use Redis to implement distributed locks for concurrent-write scenarios that require coordination beyond optimistic locking; specific lock use cases are TBD. | **Should Have** | Phase 9 (DB Synchronization & Caching) | `TEST-INT-001 / Redis CLI & Mocked Cache Hit-Rate Test` |
| `FR-CACHE-003` | Cache entries shall carry a defined expiration policy so that the cache cannot indefinitely serve stale data; exact TTL values are TBD. | **Should Have** | Phase 9 (DB Synchronization & Caching) | `TEST-INT-001 / Redis CLI & Mocked Cache Hit-Rate Test` |

## 11. Monitoring & Observability

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `FR-MON-001` | (Optional/advanced) The system may expose application and database metrics in a | **Optional** | Phase 14 (Deployment & Monitoring) | `Manual / Prometheus & Grafana Metric Review` |
| `FR-MON-002` | (Optional/advanced) The system may provide Grafana dashboards visualizing key operational metrics, including PostgreSQL replication lag. | **Optional** | Phase 14 (Deployment & Monitoring) | `Manual / Prometheus & Grafana Metric Review` |
| `FR-MON-003` | Monitoring capability is treated as an optional/advanced enhancement for this project's MVP scope (Section 2.6); its absence shall not block a passing minimum demonstration. | **Optional** | Phase 14 (Deployment & Monitoring) | `Manual / Prometheus & Grafana Metric Review` |

## 12. Non-Functional: Performance

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `NFR-PERF-001` | The system shall begin streaming a generated answer to the client within a target latency to be defined during implementation (TBD); the intent is a responsive, incrementally rendering chat experience rather than a long blocking wait. | **Should Have** | Phase 13 (Testing & Load Testing) | `TEST-LOAD-001 (Locust / k6 Load Testing)` |
| `NFR-PERF-002` | Vector similarity search over the ingested document corpus shall return top-K results within a target latency to be defined during implementation (TBD). | **Should Have** | Phase 13 (Testing & Load Testing) | `TEST-LOAD-001 (Locust / k6 Load Testing)` |
| `NFR-PERF-003` | The system's concurrent-user capacity shall be established through load testing rather than assumed; no specific concurrent-user figure is asserted in this SRS. | **Should Have** | Phase 13 (Testing & Load Testing) | `TEST-LOAD-001 (Locust / k6 Load Testing)` |

## 13. Non-Functional: Reliability

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `NFR-REL-001` | Document-processing failures shall be logged and shall not leave a document's metadata or vector records in a partially processed, inconsistent state (see FR- PROC-009). | **Must Have** | Phase 5 (Processing) & Phase 9 (Optimistic Locking) | `TEST-CONC-001 & Transaction Rollback Test` |
| `NFR-REL-002` | A stale optimistic-lock write shall always be detected and rejected with 409 | **Must Have** | Phase 5 (Processing) & Phase 9 (Optimistic Locking) | `TEST-CONC-001 & Transaction Rollback Test` |

## 14. Non-Functional: Availability

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `NFR-AVAIL-001` | Kubernetes rolling updates shall be used for backend and frontend Deployments such that a new deployment causes no dropped requests. | **Must Have** | Phase 11 (Kubernetes Deployments) | `TEST-K8S-001 (Liveness / Readiness Probe & Pod Lifecycle)` |
| `NFR-AVAIL-002` | Liveness and readiness probes shall be configured for each containerized service so | **Must Have** | Phase 11 (Kubernetes Deployments) | `TEST-K8S-001 (Liveness / Readiness Probe & Pod Lifecycle)` |
| `NFR-AVAIL-003` | Single-replica components (postgres-primary, Qdrant, MinIO) are accepted single points of failure for this project's academic scope; true high availability for these components is explicitly out of scope. | **Scope Note (N/A)** | Phase 11 (Kubernetes Deployments) | `TEST-K8S-001 (Liveness / Readiness Probe & Pod Lifecycle)` |

## 15. Non-Functional: Security

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `NFR-SEC-001` | Authentication shall use OAuth 2.0 / OIDC (Keycloak) with JWT validated on every request; a role claim shall never be trusted from the frontend alone and shall always be re-checked server-side. | **Must Have** | Phase 3, 5, 8, 11 (Security hardening across layers) | `TEST-AUTH-001, TEST-AUTHZ-001 & Security Code Review` |
| `NFR-SEC-002` | Every FastAPI endpoint shall validate its input using Pydantic models, rejecting malformed requests. | **Must Have** | Phase 3, 5, 8, 11 (Security hardening across layers) | `TEST-AUTH-001, TEST-AUTHZ-001 & Security Code Review` |
| `NFR-SEC-003` | Rate limiting shall be applied to POST /conversations/{id}/messages (and other LLM-invoking routes) to limit the cost/abuse surface of LLM calls. | **Should Have** | Phase 3, 5, 8, 11 (Security hardening across layers) | `TEST-AUTH-001, TEST-AUTHZ-001 & Security Code Review` |
| `NFR-SEC-004` | CORS shall be configured to allow only the deployed frontend origin. | **Must Have** | Phase 3, 5, 8, 11 (Security hardening across layers) | `TEST-AUTH-001, TEST-AUTHZ-001 & Security Code Review` |
| `NFR-SEC-005` | Secrets shall be managed via .env locally, GitHub Actions secrets in CI, and | **Must Have** | Phase 3, 5, 8, 11 (Security hardening across layers) | `TEST-AUTH-001, TEST-AUTHZ-001 & Security Code Review` |
| `NFR-SEC-006` | Database roles shall follow least privilege: the application's database user shall not be a PostgreSQL superuser, and read replicas shall be configured read-only at the | **Must Have** | Phase 3, 5, 8, 11 (Security hardening across layers) | `TEST-AUTH-001, TEST-AUTHZ-001 & Security Code Review` |
| `NFR-SEC-007` | File uploads shall be restricted to expected MIME types/extensions, size-limited, stored outside the web root (in MinIO), and never executed. | **Must Have** | Phase 3, 5, 8, 11 (Security hardening across layers) | `TEST-AUTH-001, TEST-AUTHZ-001 & Security Code Review` |
| `NFR-SEC-008` | The system shall mitigate prompt-injection risk (e.g., a malicious document containing text such as “ignore previous instructions”) by clearly delimiting retrieved document content from system instructions in the prompt template. | **Should Have** | Phase 3, 5, 8, 11 (Security hardening across layers) | `TEST-AUTH-001, TEST-AUTHZ-001 & Security Code Review` |
| `NFR-SEC-009` | Where documents are role-restricted (FR-DOC-010), retrieval shall filter by the requesting user's role server-side, not only at the UI level. | **Should Have** | Phase 3, 5, 8, 11 (Security hardening across layers) | `TEST-AUTH-001, TEST-AUTHZ-001 & Security Code Review` |
| `NFR-SEC-010` | Administrative actions shall be logged to the audit_log table (see FR-ADMIN-003). | **Must Have** | Phase 3, 5, 8, 11 (Security hardening across layers) | `TEST-AUTH-001, TEST-AUTHZ-001 & Security Code Review` |
| `NFR-SEC-011` | All non-local deployments shall enforce HTTPS end-to-end (see FR-AUTH-012). | **Must Have** | Phase 3, 5, 8, 11 (Security hardening across layers) | `TEST-AUTH-001, TEST-AUTHZ-001 & Security Code Review` |

## 16. Non-Functional: Maintainability

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `NFR-MAINT-001` | The codebase shall follow the documented repository structure (Appendix B, | **Should Have** | Phase 2, 10, 12 (Repo structure, Dockerfiles, Linting) | `Linter CI Check (ruff, flake8, eslint) & Structure Audit` |
| `NFR-MAINT-002` | Backend code shall pass configured Python linting (ruff/flake8) and frontend code shall pass configured JavaScript/TypeScript linting (eslint) as a required CI gate. | **Should Have** | Phase 2, 10, 12 (Repo structure, Dockerfiles, Linting) | `Linter CI Check (ruff, flake8, eslint) & Structure Audit` |
| `NFR-MAINT-003` | Dockerfiles shall use multi-stage builds to minimize final image size and separate build-time from run-time dependencies. | **Should Have** | Phase 2, 10, 12 (Repo structure, Dockerfiles, Linting) | `Linter CI Check (ruff, flake8, eslint) & Structure Audit` |

## 17. Non-Functional: Portability

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `NFR-PORT-001` | Every service shall run as a Docker container so behavior is consistent across local development, Docker Compose, and Kubernetes environments. | **Must Have** | Phase 10 (Docker) & Phase 11 (K8s) | `TEST-DOCKER-001 & TEST-K8S-001` |
| `NFR-PORT-002` | The system shall be deployable to any conformant Kubernetes cluster (a local | **Must Have** | Phase 10 (Docker) & Phase 11 (K8s) | `TEST-DOCKER-001 & TEST-K8S-001` |

## 18. Non-Functional: Scalability

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `NFR-SCAL-001` | The frontend and backend services shall be independently horizontally scalable via their Kubernetes Deployment replica counts. | **Must Have** | Phase 9 (Postgres Replicas) & Phase 11 (K8s Scaling) | `TEST-LOAD-001 & Replication Verification` |
| `NFR-SCAL-002` | PostgreSQL read capacity shall be scalable by adding further read replicas, without requiring application code changes beyond configuration (i.e., the read-router in the backend shall be configuration-driven). | **Should Have** | Phase 9 (Postgres Replicas) & Phase 11 (K8s Scaling) | `TEST-LOAD-001 & Replication Verification` |
| `NFR-SCAL-003` | (Optional/advanced) The system may support Kubernetes Horizontal Pod | **Optional** | Phase 9 (Postgres Replicas) & Phase 11 (K8s Scaling) | `TEST-LOAD-001 & Replication Verification` |

## 19. Non-Functional: Usability

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `NFR-USE-001` | The chat interface shall follow familiar conversational-UI conventions (message bubbles, streaming text rendering, a conversation sidebar) to minimize the learning curve for first-time users. | **Should Have** | Phase 7 (Conversational Interface) | `Manual UI / Wireframe Compliance Review` |
| `NFR-USE-002` | The system shall clearly and visibly distinguish a low-confidence or “not found in university documents” response from a normal, grounded answer, rather than presenting an ungrounded response as authoritative. | **Should Have** | Phase 7 (Conversational Interface) | `Manual UI / Wireframe Compliance Review` |
| `NFR-USE-003` | The admin console shall clearly surface document-processing status (e.g., success/failure of ingestion) so administrators are not left uncertain whether an uploaded document is searchable. 4. Change Management Process | **Should Have** | Phase 7 (Conversational Interface) | `Manual UI / Wireframe Compliance Review` |

## 20. Deployment: Docker & Containerization

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `DEP-DOCKER-001` | Each service — frontend, backend, postgres-primary, postgres-replica-1, postgres- replica-2, qdrant, minio, redis, keycloak, and (optional/advanced) prometheus/grafana — shall run as its own Docker container. | **Must Have** | Phase 10 (Docker & Containerization) | `TEST-DOCKER-001 (docker-compose up & healthchecks)` |
| `DEP-DOCKER-002` | Dockerfiles shall use multi-stage builds to produce minimized final images (see | **Must Have** | Phase 10 (Docker & Containerization) | `TEST-DOCKER-001 (docker-compose up & healthchecks)` |
| `DEP-DOCKER-003` | Stateful services (PostgreSQL instances, Qdrant, MinIO) shall use named Docker volumes so data survives container restarts. | **Must Have** | Phase 10 (Docker & Containerization) | `TEST-DOCKER-001 (docker-compose up & healthchecks)` |
| `DEP-DOCKER-004` | Services shall communicate over a dedicated Docker network, addressing each other by service name. | **Must Have** | Phase 10 (Docker & Containerization) | `TEST-DOCKER-001 (docker-compose up & healthchecks)` |
| `DEP-DOCKER-005` | Every service shall define a healthcheck so that Compose/Kubernetes can determine actual readiness rather than assuming it. | **Must Have** | Phase 10 (Docker & Containerization) | `TEST-DOCKER-001 (docker-compose up & healthchecks)` |

## 21. Deployment: Docker Compose

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `DEP-COMPOSE-001` | A docker-compose.yml shall define all services listed above for local development, with backend depending on postgres-primary, qdrant, and redis, and frontend depending on backend. | **Must Have** | Phase 10 (Docker & Containerization) | `TEST-DOCKER-001 (docker-compose up & healthchecks)` |
| `DEP-COMPOSE-002` | Running docker-compose up shall bring the full local stack up end-to-end without manual post-start steps beyond documented environment configuration (see | **Must Have** | Phase 10 (Docker & Containerization) | `TEST-DOCKER-001 (docker-compose up & healthchecks)` |
| `DEP-COMPOSE-003` | Secrets (e.g., DB_PASSWORD) shall be injected via environment variables/.env files, never hard-coded into docker-compose.yml. | **Must Have** | Phase 10 (Docker & Containerization) | `TEST-DOCKER-001 (docker-compose up & healthchecks)` |

## 22. Deployment: Kubernetes Orchestration

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `DEP-K8S-001` | frontend and backend shall be deployed as Kubernetes Deployment resources with a configurable replica count. | **Must Have** | Phase 11 (Kubernetes Deployment) | `TEST-K8S-001 (kubectl apply & zero-downtime rolling update)` |
| `DEP-K8S-002` | PostgreSQL instances shall be deployed as a Kubernetes StatefulSet (stable network identity and a persistent volume per pod are required for replication to function correctly). | **Must Have** | Phase 11 (Kubernetes Deployment) | `TEST-K8S-001 (kubectl apply & zero-downtime rolling update)` |
| `DEP-K8S-003` | Each service shall be exposed via a Kubernetes Service: ClusterIP for internal-only components, and an Ingress-routed service for the frontend (and, where applicable, the backend API path). | **Must Have** | Phase 11 (Kubernetes Deployment) | `TEST-K8S-001 (kubectl apply & zero-downtime rolling update)` |
| `DEP-K8S-004` | Non-secret configuration (e.g., VECTOR_DB_URL) shall be supplied via | **Must Have** | Phase 11 (Kubernetes Deployment) | `TEST-K8S-001 (kubectl apply & zero-downtime rolling update)` |
| `DEP-K8S-005` | Secrets (database passwords, OAuth client secret, LLM API key) shall be supplied via Kubernetes Secret resources, never embedded in manifests or images. | **Must Have** | Phase 11 (Kubernetes Deployment) | `TEST-K8S-001 (kubectl apply & zero-downtime rolling update)` |
| `DEP-K8S-006` | Durable storage for PostgreSQL, Qdrant, and MinIO shall be provisioned via | **Must Have** | Phase 11 (Kubernetes Deployment) | `TEST-K8S-001 (kubectl apply & zero-downtime rolling update)` |
| `DEP-K8S-007` | An Ingress resource shall route external traffic to frontend (/) and backend (/api, or equivalent). | **Must Have** | Phase 11 (Kubernetes Deployment) | `TEST-K8S-001 (kubectl apply & zero-downtime rolling update)` |
| `DEP-K8S-008` | Liveness and readiness probes shall be defined for every service (see NFR-AVAIL-002). | **Must Have** | Phase 11 (Kubernetes Deployment) | `TEST-K8S-001 (kubectl apply & zero-downtime rolling update)` |
| `DEP-K8S-009` | Backend/frontend deployments shall use the default Kubernetes rolling-update strategy, demonstrated by pushing a new image tag and observing zero-downtime pod replacement. | **Must Have** | Phase 11 (Kubernetes Deployment) | `TEST-K8S-001 (kubectl apply & zero-downtime rolling update)` |
| `DEP-K8S-010` | (Optional/advanced) A Horizontal Pod Autoscaler may be configured to scale backend pods on CPU load. | **Optional** | Phase 11 (Kubernetes Deployment) | `TEST-K8S-001 (kubectl apply & zero-downtime rolling update)` |
| `DEP-K8S-011` | postgres-replica-1 and postgres-replica-2 shall run as multiple replicas by design (this is the subject of the database-synchronization demonstration); postgres- primary, qdrant, and minio are accepted as single-replica deployments for this project's scope (see Appendix L). | **Must Have** | Phase 11 (Kubernetes Deployment) | `TEST-K8S-001 (kubectl apply & zero-downtime rolling update)` |
| `DEP-K8S-012` | Local deployment/demonstration shall target Minikube or Kind; a managed cloud | **Must Have** | Phase 11 (Kubernetes Deployment) | `TEST-K8S-001 (kubectl apply & zero-downtime rolling update)` |

## 23. Deployment: CI/CD Automation

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `DEP-CICD-001` | A CI/CD pipeline (GitHub Actions) shall run on every push/pull request: lint, then automated tests (backend pytest, frontend npm test/lint). | **Must Have** | Phase 12 (CI/CD Pipeline) | `TEST-CICD-001 (GitHub Actions pipeline execution & gate verification)` |
| `DEP-CICD-002` | A pull request shall be blocked from merging to main if any CI step (lint or test) fails. | **Must Have** | Phase 12 (CI/CD Pipeline) | `TEST-CICD-001 (GitHub Actions pipeline execution & gate verification)` |
| `DEP-CICD-003` | On merge to main, the pipeline shall build a Docker image for each changed service and push it to a container registry (GitHub Container Registry), tagged with the Git commit SHA (and additionally :latest). | **Must Have** | Phase 12 (CI/CD Pipeline) | `TEST-CICD-001 (GitHub Actions pipeline execution & gate verification)` |
| `DEP-CICD-004` | On a successful build from main, the pipeline shall deploy the new image(s) to the | **Must Have** | Phase 12 (CI/CD Pipeline) | `TEST-CICD-001 (GitHub Actions pipeline execution & gate verification)` |
| `DEP-CICD-005` | The team shall be able to roll back a deployment via kubectl rollout undo, and this rollback shall be demonstrated as part of project evaluation. | **Must Have** | Phase 12 (CI/CD Pipeline) | `TEST-CICD-001 (GitHub Actions pipeline execution & gate verification)` |

## 24. Deployment: Environment & Secrets

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `DEP-ENV-001` | Local configuration shall be supplied via a .env file, excluded from version control via .gitignore. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / Config & Secret Review` |
| `DEP-ENV-002` | A .env.example file with placeholder values shall be committed to the repository so contributors know which variables are required. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / Config & Secret Review` |
| `DEP-ENV-003` | Kubernetes non-secret configuration shall be supplied via ConfigMap resources (see DEP-K8S-004). | **Must Have** | Phase 2 & Phase 10 / 11 | `Manual / Config & Secret Review` |
| `DEP-SEC-001` | Secrets shall never be committed to source control or baked into container images. | **Must Have** | Phase 2 & Phase 10 / 11 | `Manual / Config & Secret Review` |
| `DEP-SEC-002` | CI secrets (registry credentials, deployment credentials) shall be stored as GitHub | **Must Have** | Phase 2 & Phase 10 / 11 | `Manual / Config & Secret Review` |
| `DEP-SEC-003` | Runtime secrets in the cluster (DB passwords, OAuth client secret, LLM API key) shall be stored as Kubernetes Secret resources (see DEP-K8S-005). | **Must Have** | Phase 2 & Phase 10 / 11 | `Manual / Config & Secret Review` |

## 25. Process: Git Collaboration Workflow

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `PROC-GIT-001` | The project shall use GitHub as its Git hosting platform, with the repository created and structured (Appendix B, Section 5.2) from project inception, not retrofitted after development. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / Repository & PR Review` |
| `PROC-GIT-002` | The main branch shall be protected and always deployable. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / Repository & PR Review` |
| `PROC-GIT-003` | Development shall occur on short-lived feature/<ticket-id>-short-desc branches, one per JIRA ticket, merged into main via pull request. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / Repository & PR Review` |
| `PROC-GIT-004` | Every feature branch shall be merged into main only via a pull request whose description links the corresponding JIRA ticket. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / Repository & PR Review` |
| `PROC-GIT-005` | A pull request shall require CI to pass (Appendix G, CI/CD) before it is eligible for merge. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / Repository & PR Review` |
| `PROC-GIT-006` | Every pull request shall receive at least one reviewer approval (a teammate is sufficient for a small student team) before merge, with genuine review comments recorded. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / Repository & PR Review` |
| `PROC-GIT-007` | Commits shall follow the Conventional Commits convention (e.g., feat: add citation rendering, fix: replica read routing bug, chore: update deps). JIRA Epics, Stories, and Tasks ID | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / Repository & PR Review` |

## 26. Process: JIRA Project Management

| Requirement ID | Description | Priority | Planned Phase | Verification Method |
|---|---|:---:|---|---|
| `PROC-JIRA-001` | The project shall maintain a JIRA board (free tier is sufficient) structured as Epics → Stories → Tasks/Subtasks → Bugs. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / JIRA Board & Ticket Review` |
| `PROC-JIRA-002` | Epics shall correspond to major functional areas: Authentication, Document | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / JIRA Board & Ticket Review` |
| `PROC-JIRA-003` | Each Epic shall be broken into Stories and Tasks/Subtasks sized to be completed within a single sprint. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / JIRA Board & Ticket Review` |
| `PROC-JIRA-004` | Defects found post-merge shall be tracked as JIRA Bugs (optionally mirrored to/from GitHub Issues), not left undocumented. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / JIRA Board & Ticket Review` |
| `PROC-JIRA-005` | Work shall be organized into sprints of approximately 1–2 weeks, drawn from a single backlog. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / JIRA Board & Ticket Review` |
| `PROC-JIRA-006` | Tickets shall move through the states To Do → In Progress → In Review → Done, with an optional Blocked state. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / JIRA Board & Ticket Review` |
| `PROC-JIRA-007` | A ticket shall be considered Done only when its code is merged to main, CI tests pass, the change is deployed to the development cluster, and (where relevant) the change is documented in the README. | **Must Have** | Phase 2 (Git + JIRA Setup) | `Manual / JIRA Board & Ticket Review` |
