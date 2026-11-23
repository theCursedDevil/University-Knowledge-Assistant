# Known Limitations & Engineering Trade-offs

> **Project:** Generative AI-Based University Knowledge Assistant  
> **Capstone Project:** CS4191 Capstone Project II · B.Tech CSE (AI/ML)  
> **Student:** Aashu Kumar · **Roll No:** BT23GCS449  
> **Source-of-Truth Reference:** SDD §14, SRS §2.4, Master Project Guide §10  

---

## 1. Academic & Architectural Appraisal

In accordance with capstone research integrity rules, this document provides an honest, empirical analysis of architectural boundaries, design trade-offs, and known constraints in the implemented system.

---

## 2. Granular Limitations by System Tier

### 2.1 Document Processing & Extraction
1. **Digital PDFs Only (No Embedded OCR):**
   - **Current Implementation:** Text extraction is powered by PyMuPDF (`fitz`), which extracts digital text, layout coordinates, and font blocks.
   - **Constraint:** Scanned image-only PDFs (photocopied notices or signed circulars without a text layer) yield minimal or zero extractable characters.
   - **Mitigation / Future Work:** Integrating an optical character recognition (OCR) pre-processing step (such as Tesseract OCR or PaddleOCR) when PyMuPDF detects image-only pages. Omitted in MVP to prevent heavy binary dependencies and CPU overhead on standard hardware.

2. **Table & Multi-Column Layout Complexity:**
   - **Current Implementation:** Regex cleaning normalizes irregular spacing and removes header/footer noise.
   - **Constraint:** Complex multi-nested tables spanning multiple pages may experience split rows across chunk boundaries.
   - **Mitigation:** Table-aware chunking boundaries are maintained where explicit tabular blocks are marked, but arbitrary graphic layouts require visual layout parsing (e.g. LayoutLM).

---

### 2.2 Artificial Intelligence & RAG Pipeline
1. **CPU Embedding Latency:**
   - **Current Implementation:** `sentence-transformers/all-MiniLM-L6-v2` executes on CPU cores (~120 MB RAM footprint).
   - **Performance:** Ingestion vectorization takes ~8–12ms per chunk. For typical university policy documents (10–30 pages, ~50 chunks), processing completes in under 2 seconds.
   - **Limitation:** Bulk university library uploads (e.g., 5,000 documents simultaneously) would bottleneck CPU queues without dedicated GPU worker pools.

2. **Cloud LLM Quota Boundaries:**
   - **Current Implementation:** Primary generation uses Groq’s high-throughput LPU cloud API (`llama-3.1-8b-instant`), with Google Gemini 1.5 Flash as secondary.
   - **Constraint:** Free-tier accounts enforce API rate limits (e.g., 30 requests per minute).
   - **Mitigation:** The application enforces a local Redis sliding-window rate limiter (60 req/min user window) and exponential backoff retry logic to prevent 429 quota exhaustion.

3. **Hallucination Fallback Trigger:**
   - When vector similarity scores drop below $0.40$ cosine threshold, the assistant gracefully falls back to an honest rejection response (*"I do not have sufficient information in the university documents..."*). Highly conversational chit-chat queries without university context are intentionally rejected.

---

### 2.3 Database Synchronization & Persistence
1. **Asynchronous Physical Streaming Replication:**
   - **Current Implementation:** PostgreSQL 16 replication operates in asynchronous streaming mode via WAL senders and slots (`replica_1_slot`, `replica_2_slot`).
   - **Trade-off:** Under extreme network partitions or heavy write bursts, standby nodes experience a non-zero replay lag (typically 0–128 bytes under normal load).
   - **Mitigation:** `ReplicaRouter` enforces session-aware read-your-own-writes consistency: any user performing an `INSERT` or `UPDATE` is pinned to the Primary database for 5.0 seconds, completely immunizing active user sessions against stale reads.

2. **Single-Node Vector DB (Qdrant):**
   - **Current Implementation:** Qdrant runs as a single container with persistent volume storage (`10Gi SSD`).
   - **Constraint:** While highly performant for university collections (<100,000 vectors), it does not feature multi-node Raft consensus clustering.

---

### 2.4 Infrastructure & Operations
1. **Standalone Keycloak Deployment:**
   - **Current Implementation:** Keycloak is deployed as a single instance with PostgreSQL backing.
   - **Constraint:** Does not utilize multi-pod distributed Infinispan caching across clustered regions.
2. **Kubernetes Environment:**
   - Designed and verified for local Kubernetes (Minikube / Kind) with Docker drivers. Cloud managed Kubernetes (EKS, GKE, AKS) requires adjusting cloud-specific Ingress classes and CSI storage providers.
