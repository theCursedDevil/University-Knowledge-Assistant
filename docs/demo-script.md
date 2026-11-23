# University Demonstration Script & Evaluation Walkthrough

> **Project:** Generative AI-Based University Knowledge Assistant  
> **Capstone Project:** CS4191 Capstone Project II · B.Tech CSE (AI/ML)  
> **Candidate:** Aashu Kumar (BT23GCS449)  
> **Source-of-Truth Reference:** Master Project Guide §22, SDD §12  

---

## 1. Demonstration Overview & Setup

This script outlines the exact live demonstration flow for the final university capstone evaluation committee. Every step corresponds directly to verified, operational features in the codebase.

### Quick Launch Command (Unified Automated Rehearsal)
To demonstrate all 34 end-to-end checkpoints automatically in under 60 seconds with colored terminal logging:
```bash
python scripts/demo/verify_e2e_journey.py
```

---

## 2. Act I: Core Academic RAG Demonstration (The Golden Path)

### Step 1: Admin Document Upload
1. **Action:** Navigate to the Admin Console at `http://localhost:3000/admin/upload` (or execute `POST /documents`).
2. **Input:** Select an official university document: `Academic_Regulations_2026.pdf`.
3. **Payload:**
   - Category: `Academic`
   - Role Restriction: `student`
4. **Observer Result:** The document is stored in MinIO object storage (`university-documents/documents/...`), and a metadata record is created in PostgreSQL with `status: "uploaded"` and `version: 1`.

### Step 2: Document Processing & Vector Indexing
1. **Action:** Click **"Process Document"** (or execute `POST /documents/{id}/process`).
2. **Terminal Output / Log:**
   ```
   INFO: Extracting text with PyMuPDF: 12 pages extracted.
   INFO: Chunking into 28 semantic segments (500 tokens, 50 overlap).
   INFO: Computing dense embeddings via sentence-transformers/all-MiniLM-L6-v2 on CPU.
   INFO: Upserted 28 vectors to Qdrant collection 'university_documents'.
   INFO: Status transitioned to 'ready'.
   ```
3. **Observer Result:** The document card in the UI displays `Status: Ready (28 Chunks)`.

### Step 3: Student Question Asking & Real-Time Streaming
1. **Action:** Switch to student persona and open the Chat Interface (`http://localhost:3000/chat`).
2. **Input Query:** *"What is the minimum attendance percentage required to sit for semester examinations?"*
3. **Observer Result:**
   - The query generates an embedding and executes a top-$5$ cosine similarity search in Qdrant.
   - Retrieval confidence score ($0.88$) exceeds the fallback threshold ($0.40$).
   - The answer streams token-by-token via Server-Sent Events (SSE):
     > *"According to the Academic Regulations, students must maintain a minimum of 75% attendance in each course to be eligible to appear for the semester end examinations. A relaxation up to 65% is permitted on medical grounds with valid documentation."*

### Step 4: Deterministic Source Citation Jump
1. **Action:** Click the citation pill below the answer: `[Academic Regulations, Page 4, Section 3.2]`.
2. **Observer Result:** The right-hand Citation View panel opens, displaying:
   - Document Title: `Academic Regulations 2026`
   - Page Attribution: `Page 4`
   - Verbatim Extracted Text Chunk highlighting the exact 75% attendance clause.
   - **Academic Note to Evaluators:** Point out that citations are resolved deterministically from PostgreSQL chunk metadata corresponding to Qdrant vector IDs, ensuring zero LLM hallucination.

### Step 5: Conversational Follow-Up Query
1. **Input Query:** *"What happens if my medical certificate is rejected?"*
2. **Observer Result:**
   - The system retrieves the last 6 messages from PostgreSQL memory and injects conversational context.
   - The assistant understands *"medical certificate"* refers to the attendance condonation mentioned in the previous turn and answers:
     > *"If the condonation request is rejected, the student will be awarded an 'I' (Incomplete) grade for that course and must re-register during the subsequent academic cycle."*

---

## 3. Act II: OAuth 2.0 & Role-Based Access Control (RBAC)

1. **Student Access:**
   - Student queries `/me`: Role returned is `student`.
   - Student attempts to access `/admin/stats`: Receives **HTTP 403 Forbidden** (*"Administrator privileges required"*).
2. **Faculty Access:**
   - Faculty logs in with role `faculty`.
   - Faculty can search both student and faculty-restricted circulars, but cannot delete documents or update user roles.
3. **Admin Access:**
   - Admin logs in with role `admin`.
   - Full access to Analytics Dashboard, Metadata Editor, and Audit Logs.

---

## 4. Act III: Multi-Replica Database Synchronization & Concurrency

### 1. Multi-Replica Topology Verification
```bash
# Verify Primary on 5432 and Replicas on 5433, 5434
docker exec -it postgres-primary psql -U postgres -d university_assistant -c "SELECT client_addr, application_name, state, sync_state FROM pg_stat_replication;"
```
*Expected Output:* Two active WAL streaming standbys: `replica_1` and `replica_2` in `streaming` state.

### 2. Live Replication Lag Demonstration
- Open Prometheus metrics: `curl -s http://localhost:8000/metrics | grep uka_postgres_replication_lag`
- Replay lag is dynamically recorded in bytes per standby replica.

### 3. Read-Your-Own-Writes Consistency Demonstration
- Execute a document update on Primary.
- The user's ID is registered in `ReplicaRouter` with a 5.0-second TTL.
- Immediate read query shows routing reason: `User is within active read-after-write window (5.0s). Routing read to Primary.`
- After 5 seconds, subsequent reads automatically return to round-robin load balancing across `replica_1` and `replica_2`.

### 4. Optimistic Locking & 409 Conflict Demonstration
1. Admin Session A opens document metadata (`version: 1`).
2. Admin Session B opens the same document (`version: 1`).
3. Admin Session A saves title as `"Regulations (Rev A)"` -> Commit succeeds, version increments to `2`.
4. Admin Session B attempts to save as `"Regulations (Rev B)"` with `expected_version: 1`.
5. **System Response:** **HTTP 409 Conflict**:
   ```json
   {
     "detail": "Concurrent modification detected. The document was updated by another session."
   }
   ```

---

## 5. Act IV: DevOps, Kubernetes & CI/CD

### 1. Kubernetes Orchestration & HPA
```bash
kubectl get pods
kubectl get hpa uka-backend-hpa
```
*Shows horizontal pod autoscaler targeting 70% CPU scaling from 2 to 5 pods.*

### 2. Zero-Downtime Rolling Update Demonstration
```bash
./scripts/deploy/deploy-k8s.sh
```
*Shows `deployment "uka-backend" successfully rolled out` using Kubernetes rolling update strategy.*

### 3. Instant Rollback Demonstration
```bash
./scripts/deploy/rollback-k8s.sh
```
*Shows `deployment.apps/uka-backend rolled back` restoring the previous stable revision.*

### 4. GitHub Actions CI/CD Proof
- Navigate to GitHub repository: `https://github.com/theCursedDevil/University-Knowledge-Assistant/actions`.
- Point out that every PR undergoes automated linting, build verification, and execution of all 93 pytest test cases before merging.
