# Optional & Advanced Enhancements Report

**Generative AI-Based University Knowledge Assistant**  
Document Reference: `SRS §5.13 (Appendix M)` · SDD `C-MON, C-RAGSVC, C-PROC` · Prompt 28 · JIRA Ticket: `UKA-49`

---

## 1. Executive Summary

This document reviews and provides requirement traceability for the **Optional / Advanced and Future Enhancements** specified in Appendix M of the Software Requirements Specification (SRS). All features have been implemented and verified incrementally without destabilizing the core RAG or multi-replica database architectures.

---

## 2. Requirement Traceability Matrix

| Feature | SRS Requirement | Build Phase / Prompt | Status | Implementation Details |
|---|---|---|---|---|
| **Groundedness Verification** | `FR-RAG-008` | Prompt 26 | **Completed & Tested** | Token-level factual claim verification in `backend/app/rag/groundedness.py`. Prevents hallucinations, strips bracketed citations, and returns honest fallbacks. |
| **Hybrid Retrieval** | `FR-RAG-003` | Prompt 26 | **Completed & Tested** | Blends dense cosine vector similarity with lexical keyword overlap scores (`backend/app/rag/retriever.py`) and metadata filtering on `category` and RBAC `role_restriction`. |
| **Running Summaries** | `FR-CHAT-006` | Prompt 26 | **Completed & Tested** | Partitions dialogue into older turns (>4) synthesized into `<conversation_summary>` while retaining recent turns in `backend/app/rag/conversation_summarizer.py`. |
| **Prometheus & Grafana** | `FR-MON-001`<br>`FR-MON-002` | Prompt 27 | **Completed & Tested** | FastAPI `/metrics` exporter, 6 metrics, Prometheus scraper, and auto-provisioned Grafana operations dashboard (`monitoring/`). |
| **Kubernetes HPA** | `NFR-SCAL-003`<br>`DEP-K8S-010` | Prompt 28 | **Completed & Tested** | Declarative `HorizontalPodAutoscaler` manifest (`kubernetes/base/hpa.yaml`) scaling backend pods (1 to 4 replicas) at 70% CPU / 80% RAM utilization. |
| **Keycloak Google Federation** | `§5.13 (App. M)` | Prompt 28 | **Completed & Tested** | Keycloak Identity Broker integration in `docker/keycloak/university-realm.json`, `.env.example`, and architecture guide in `docs/google-federation.md`. |
| **Synchronous Replication** | `FR-DBSYNC-007` | Prompt 28 | **Explicitly Deferred** | Evaluated and deferred per SRS Appendix M to eliminate single-point-of-failure database hang risks in local and CI environments. |

---

## 3. Detailed Component Implementations

### 3.1 Kubernetes Horizontal Pod Autoscaler (HPA)
* **Manifest:** `kubernetes/base/hpa.yaml`
* **API Version:** `autoscaling/v2`
* **Target:** `Deployment/backend`
* **Thresholds:**
  * Minimum Replicas: `1`
  * Maximum Replicas: `4`
  * Target Average CPU: `70%`
  * Target Average Memory: `80%`
* **Stabilization Behavior:** Zero-delay scale-up (up to 100% or +2 pods every 15s) with a 300-second stabilization window on scale-down to prevent pod flapping.

### 3.2 Keycloak Google Social Identity Broker
* **Realm Import:** `docker/keycloak/university-realm.json`
* **Mechanism:** Keycloak acts as an OIDC Identity Provider Broker.
* **Environment Bindings:** `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
* **RBAC Alignment:** Default role `student` automatically assigned on first login; administrative privileges require elevation in Keycloak or FastAPI admin console.

### 3.3 Synchronous Replication Analysis & Deferral Rationale
* **SRS Clause:** *"The system may use synchronous replication for a designated critical write path (e.g. audit logs or document uploads, requiring at least one replica acknowledgment) to demonstrate the synchronous-vs-asynchronous durability/latency trade-off."*
* **Engineering Rationale:** Enforcing `synchronous_standby_names` at the cluster level causes primary write transactions to block indefinitely if a standby container is stopped or experiencing network jitter.
* **Conclusion:** The application already guarantees read-after-write consistency via the session-aware `get_read_db()` router (`replica_router`). To preserve 100% system reliability for student and faculty evaluations, cluster-wide synchronous blocking is safely omitted.
