# REST API Specification & Endpoint Documentation

> **Project:** Generative AI-Based University Knowledge Assistant  
> **Capstone Project:** CS4191 Capstone Project II · B.Tech CSE (AI/ML)  
> **Student:** Aashu Kumar · **Roll No:** BT23GCS449  
> **Source-of-Truth Reference:** SDD §5, SRS §3.1, Master Project Guide §6  

---

## 1. Authentication & Security Headers

All requests (except public health and OAuth callbacks) require authentication:
- **Production Mode:** Bearer token via `Authorization: Bearer <jwt_access_token>` or secure `httpOnly` cookie (`access_token`).
- **Development/Evaluation Mode:** Development bypass headers:
  - `X-Dev-Role: student | faculty | admin`
  - `X-Dev-Email: user@university.edu`

---

## 2. API Endpoint Catalog

### 2.1 Health & Metrics

| Method | Endpoint | Access | Purpose | Success Status |
|---|---|---|---|---|
| `GET` | `/health` | Public | System liveness probe and core service health indicators | `200 OK` |
| `GET` | `/api/v1/health` | Public | Versioned health check | `200 OK` |
| `GET` | `/metrics` | Public/Monitoring | Prometheus metrics scrape target | `200 OK` |

---

### 2.2 Authentication & User Identity (`/auth`, `/me`)

#### `GET /me`
Returns current authenticated user profile, primary role, and realm role assignments.
- **Access:** Any authenticated user (`student`, `faculty`, `admin`).
- **Response `200 OK`:**
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "oauth_sub": "keycloak-sub-string",
    "name": "Aashu Kumar",
    "email": "student@university.edu",
    "role": "student",
    "roles": ["student"],
    "created_at": "2026-11-23T10:00:00Z"
  }
  ```

#### `POST /auth/login`
Development login endpoint establishing a test session.
- **Request Body:**
  ```json
  {
    "email": "admin@university.edu",
    "role": "admin"
  }
  ```
- **Response `200 OK`:** Sets httpOnly authentication cookies and returns user details.

#### `POST /auth/token`
Authorization code and PKCE exchange endpoint.
- **Request Body:**
  ```json
  {
    "code": "auth-code-from-keycloak",
    "code_verifier": "pkce-code-verifier-string"
  }
  ```

#### `POST /auth/logout`
Revokes active session at Keycloak and clears client cookies.
- **Response `200 OK`:** `{"message": "Logged out successfully"}`.

---

### 2.3 Document Management (`/documents`)

#### `POST /documents`
Uploads a new academic document PDF to MinIO object storage.
- **Access:** `admin` only. Non-admin receives `403 Forbidden`.
- **Form Data:**
  - `file`: Multipart binary PDF file.
  - `title`: Document title (e.g., *"Academic Regulations 2026"*).
  - `category`: Classification (`Academic`, `Examinations`, `Hostel`, `Fees`).
  - `role_restriction`: Access level (`student`, `faculty`, `admin`). Default: `student`.
- **Response `201 Created`:**
  ```json
  {
    "id": "e6a2b89f-8d2b-4fa8-bb36-9a2bb734d70b",
    "title": "Academic Regulations 2026",
    "category": "Academic",
    "role_restriction": "student",
    "storage_path": "documents/e6a2b89f.../regulations.pdf",
    "status": "uploaded",
    "version": 1,
    "created_at": "2026-11-23T10:00:00Z"
  }
  ```

#### `GET /documents`
Lists documents visible to the caller's role.
- **Access:** Authenticated users.
- **Filtering:** Students only see `role_restriction: 'student'`; faculty see `student` and `faculty`; admins see all.
- **Response `200 OK`:** Array of document metadata items.

#### `GET /documents/{id}`
Retrieves metadata of a specific document.
- **Access:** Role-restricted according to document setting.

#### `GET /documents/{id}/preview`
Fetches textual preview of the document (first page text and extracted chunk samples).
- **Access:** Authenticated users with appropriate role.

#### `POST /documents/{id}/process`
Triggers the ingestion pipeline: extracts text with PyMuPDF, performs semantic chunking, generates embeddings with Sentence Transformers, and indexes points in Qdrant.
- **Access:** `admin` only.
- **Response `200 OK`:**
  ```json
  {
    "document_id": "e6a2b89f-8d2b-4fa8-bb36-9a2bb734d70b",
    "status": "ready",
    "pages_count": 12,
    "chunks_count": 28,
    "error": null
  }
  ```

#### `PATCH /documents/{id}`
Updates document title, category, or role restriction with **optimistic concurrency control**.
- **Access:** `admin` only.
- **Request Body:**
  ```json
  {
    "title": "Academic Regulations 2026 (Revised)",
    "category": "Academic",
    "role_restriction": "student",
    "expected_version": 1
  }
  ```
- **Response `200 OK`:** Updated document object with `version: 2`.
- **Conflict `409 Conflict`:** If `expected_version` does not match the database version, returns error: *"Concurrent modification detected. The document was updated by another session."*

#### `DELETE /documents/{id}`
Executes cascading document deletion: purges vectors from Qdrant, deletes PDF from MinIO, and purges database chunks metadata.
- **Access:** `admin` only.
- **Response `200 OK`:** `{"id": "uuid", "message": "Document successfully deleted"}`.

---

### 2.4 Conversations & Chat (`/conversations`)

#### `POST /conversations`
Creates a new conversation thread.
- **Access:** Authenticated user.
- **Request Body:** `{"title": "Optional Custom Title"}` (defaults to *"New Conversation"*).
- **Response `201 Created`:** Conversation object with `id`, `user_id`, `created_at`.

#### `GET /conversations`
Lists all conversations belonging to the caller (enforces strict user isolation).
- **Response `200 OK`:** Chronological list of user threads.

#### `GET /conversations/{id}`
Fetches all messages and citations within a conversation.
- **Access:** Conversation owner only. Non-owning user receives `403 Forbidden`.

#### `DELETE /conversations/{id}`
Deletes a conversation thread and its associated message history.
- **Access:** Conversation owner or admin.

#### `POST /conversations/{id}/messages`
Submits a query to the conversational assistant. Supports both streaming (SSE) and synchronous responses.
- **Query Parameter:** `stream=true` (for token-by-token SSE) or `stream=false` (for single JSON payload).
- **Request Body:**
  ```json
  {
    "content": "When are the final semester examinations scheduled?"
  }
  ```
- **Response (Synchronous, `201 Created`):**
  ```json
  {
    "conversation_id": "8f8b824a-f3ec-4db0-a392-710892095f9a",
    "user_message": {
      "id": "11111111-2222-3333-4444-555555555555",
      "role": "user",
      "content": "When are the final semester examinations scheduled?"
    },
    "assistant_message": {
      "id": "66666666-7777-8888-9999-000000000000",
      "role": "assistant",
      "content": "Final semester examinations commence on December 15, 2026..."
    },
    "citations": [
      {
        "source": "Examination Schedule Circular 2026",
        "page": 2,
        "section": "Section 4.1 Commencement Dates",
        "chunk_id": "c1f72a42-..."
      }
    ]
  }
  ```
- **Response (Streaming, `200 OK`, `text/event-stream`):**
  ```
  event: token
  data: Final

  event: token
  data:  semester

  event: citations
  data: [{"source":"Examination Schedule Circular 2026","page":2,"section":"Section 4.1"}]

  event: done
  data: [DONE]
  ```

---

### 2.5 Administrative Management (`/admin`)

#### `GET /admin/stats`
Aggregated system metrics and usage statistics.
- **Access:** `admin` only. Non-admin receives `403 Forbidden`.
- **Response `200 OK`:** Counts for total users, documents, queries, and vector points.

#### `GET /admin/users`
Lists all registered users and their assigned roles.
- **Access:** `admin` only.

#### `PATCH /admin/users/{id}/role`
Updates a user's role (`student`, `faculty`, `admin`). Protects against self-demotion.
- **Access:** `admin` only.

#### `GET /admin/audit-logs`
Chronological operational audit trail.
- **Access:** `admin` only.
- **Response `200 OK`:** Array of immutable audit records (`action`, `entity`, `user_id`, `timestamp`).
