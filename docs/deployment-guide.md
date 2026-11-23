# Deployment and Operations Guide

> **Project:** Generative AI-Based University Knowledge Assistant  
> **Capstone Project:** CS4191 Capstone Project II · B.Tech CSE (AI/ML)  
> **Student:** Aashu Kumar · **Roll No:** BT23GCS449  
> **Source-of-Truth Reference:** SDD §12, Master Project Guide §11 & §12  

---

## 1. Prerequisites and System Requirements

- **Operating System:** Linux (Ubuntu 22.04+), macOS (macOS 14 Sonoma / macOS 15 Sequoia), or Windows via WSL2.
- **Docker & Docker Compose:** Docker Engine 24.0+ and Docker Compose v2.
- **Python:** Python 3.12.x.
- **Node.js:** Node.js 18.x or 20.x LTS with `npm`.
- **Kubernetes (Optional for local K8s demo):** Minikube v1.32+ or Kind v0.20+ with `kubectl`.

---

## 2. Configuration & Environment Variables

Copy the reference environment template to create your active configuration:
```bash
cp .env.example .env
```

### Essential Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Deployment environment (`development`, `staging`, `production`). |
| `SECRET_KEY` | *(Generate 32-char string)* | Session signing key for FastAPI. |
| `POSTGRES_HOST` | `localhost` / `postgres-primary` | PostgreSQL Primary database host. |
| `POSTGRES_PORT` | `5432` | PostgreSQL Primary port. |
| `POSTGRES_USER` | `postgres` | Database superuser. |
| `POSTGRES_PASSWORD` | `postgres` | Database password. |
| `POSTGRES_DB` | `university_assistant` | Application database name. |
| `POSTGRES_REPLICA_1_URL` | `postgresql+asyncpg://...:5433/...` | Read Replica 1 connection URI. |
| `POSTGRES_REPLICA_2_URL` | `postgresql+asyncpg://...:5434/...` | Read Replica 2 connection URI. |
| `REDIS_HOST` | `localhost` / `redis` | Redis caching and locking host. |
| `REDIS_PORT` | `6379` | Redis port. |
| `MINIO_ENDPOINT` | `localhost:9000` / `minio:9000` | MinIO S3 API host. |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key. |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key. |
| `QDRANT_HOST` | `localhost` / `qdrant` | Qdrant vector database host. |
| `QDRANT_PORT` | `6333` | Qdrant HTTP REST API port. |
| `KEYCLOAK_URL` | `http://localhost:8080` | Keycloak identity server root. |
| `GROQ_API_KEY` | `gsk_...` | Free-tier Groq API key (for Llama 3.1 streaming). |
| `GEMINI_API_KEY` | `AIza...` | Google Gemini API key (secondary LLM option). |

---

## 3. Deployment Method A: Full Docker Compose (Recommended)

Docker Compose orchestrates the complete 11-service topology with a single command:

```bash
docker-compose up -d
```

### Container Stack Topology

| Service Name | Container Image | Port Binding | Purpose |
|---|---|---|---|
| `frontend` | `uka-frontend:latest` (Node 20 alpine) | `3000:3000` | Next.js 14 Web UI. |
| `backend` | `uka-backend:latest` (Python 3.12 slim) | `8000:8000` | FastAPI REST & SSE API. |
| `postgres-primary` | `postgres:16-alpine` | `5432:5432` | Relational DB Primary (RW). |
| `postgres-replica-1` | `postgres:16-alpine` | `5433:5432` | Read Replica 1 (Hot Standby). |
| `postgres-replica-2` | `postgres:16-alpine` | `5434:5432` | Read Replica 2 (Hot Standby). |
| `redis` | `redis:7-alpine` | `6379:6379` | Cache, locks, and write-window flags. |
| `qdrant` | `qdrant/qdrant:latest` | `6333:6333` | 384d Cosine Vector Store. |
| `minio` | `cgr.dev/chainguard/minio:latest` | `9000:9000`, `9001:9001` | S3 Object Storage & Console. |
| `keycloak` | `quay.io/keycloak/keycloak:24.0.5` | `8080:8080` | OAuth 2.0 / OIDC Identity Provider. |
| `prometheus` | `prom/prometheus:v2.51.0` | `9090:9090` | Operational metrics collection. |
| `grafana` | `grafana/grafana:10.4.0` | `3001:3000` | Visual dashboards and lag graphs. |

### Verifying Service Health
```bash
docker-compose ps
curl -s http://localhost:8000/health | jq .
```

---

## 4. Deployment Method B: Kubernetes (Minikube / Kind)

Declarative production-ready manifests reside in `kubernetes/base/`:

```
kubernetes/
├── base/
│   ├── backend.yaml              # Backend Deployment & ClusterIP Service
│   ├── frontend.yaml             # Frontend Deployment & ClusterIP Service
│   ├── configmap.yaml            # Environment and config variables
│   ├── secrets.yaml              # Encrypted secrets and API keys
│   ├── pvc.yaml                  # PersistentVolumeClaims for storage
│   ├── qdrant.yaml               # Qdrant Deployment & Service
│   ├── minio.yaml                # MinIO Deployment & Service
│   ├── redis.yaml                # Redis Deployment & Service
│   ├── keycloak.yaml             # Keycloak Deployment & Service
│   ├── monitoring.yaml           # Prometheus & Grafana Deployments
│   └── hpa.yaml                  # HorizontalPodAutoscaler for Backend
├── postgres/
│   └── statefulset.yaml          # PostgreSQL Primary + Standby StatefulSet
├── ingress.yaml                  # NGINX Ingress Controller routing rules
└── kustomization.yaml            # Declarative base bundle
```

### 1. Launch Minikube & Enable Addons
```bash
minikube start --cpus=4 --memory=8192
minikube addons enable ingress
minikube addons enable metrics-server
```

### 2. Deploy Manifests
```bash
kubectl apply -f kubernetes/base/
kubectl apply -f kubernetes/postgres/
kubectl apply -f kubernetes/ingress.yaml
```

### 3. Verify Pod Readiness
```bash
kubectl get pods -w
kubectl get services
kubectl get ingress
```

### 4. Demonstrate Rolling Update (Zero Downtime)
```bash
./scripts/deploy/deploy-k8s.sh
# Executes: kubectl rollout status deployment/uka-backend --timeout=120s
```

### 5. Demonstrate Instant Rollback
```bash
./scripts/deploy/rollback-k8s.sh
# Executes: kubectl rollout undo deployment/uka-backend
```

---

## 5. Deployment Method C: Local Native Development

For day-to-day code editing and fast hot-reloading:

```bash
# 1. Start support services in Docker
docker-compose up -d postgres-primary redis qdrant minio keycloak

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

Visit the application at: `http://localhost:3000`.
