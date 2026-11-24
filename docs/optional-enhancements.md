# Optional Enhancements & Architecture Traceability

This document records the architectural decisions and requirement traceability for the optional enhancements implemented in the University Knowledge Assistant.

## 1. Requirement Traceability Matrix

| Requirement | Category | Description | Implementation Details |
|---|---|---|---|
| **FR-RAG-008** | Advanced RAG | Semantic Caching & Cache Invalidation | Redis cache with TTL and write-through cache invalidation on document updates. |
| **FR-RAG-003** | Ingestion & Retrieval | Document Ingestion & Chunking | Text extraction with sliding-window chunking and dense vector embeddings (`all-MiniLM-L6-v2`). |
| **FR-CHAT-006** | Conversational UI | Citation Anchoring & Source Attribution | Verifiable document citations linked to page and section indices in RAG response streams. |
| **NFR-SCAL-003** | Scalability & K8s | Horizontal Pod Autoscaling (HPA) | Kubernetes HPA targeting 70% CPU utilization across backend API replicas (`kubernetes/base/hpa.yaml`). |

## 2. Horizontal Pod Autoscaling (`NFR-SCAL-003`)

The backend API deployment is paired with a HorizontalPodAutoscaler targeting CPU utilization:
- `minReplicas`: 1 (laptop overlay) / 2 (base configuration)
- `maxReplicas`: 5
- Target metric: 70% average CPU utilization

## 3. Identity Provider Federation (Google SSO)

Keycloak federates authentication with Google OAuth 2.0 / OIDC:
- PKCE S256 code challenge on the Next.js frontend (`/login` -> Keycloak -> Google).
- Secure httpOnly session cookie storage (`uka_access_token` and `uka_refresh_token`).
- Just-in-time user provisioning in PostgreSQL on first sign-in.
- Role-based access control (RBAC) defaulting to `student`, with admin promotion available via the admin console.
