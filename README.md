# Generative AI-Based University Knowledge Assistant

A university-document question-answering application built around Retrieval-Augmented Generation (RAG). Administrators can upload university PDFs; the backend extracts and indexes their content; signed-in users can ask questions and receive answers with source citations, subject to document-role restrictions.

This repository contains the Next.js frontend, FastAPI backend, database migrations, Docker Compose stack, Kubernetes manifests, monitoring configuration, and verification scripts.

> **Recommended for an 8 GB Apple Silicon Mac:** use the default Docker Compose profile for the everyday demo, or `kubernetes/overlays/laptop` for a local Kubernetes demonstration. Do not run both stacks at the same time on the laptop.

## Contents

- [Features](#features)
- [How the RAG pipeline works](#how-the-rag-pipeline-works)
- [Technology stack](#technology-stack)
- [Requirements](#requirements)
- [Quick start with Docker Compose](#quick-start-with-docker-compose)
- [Run the lightweight Kubernetes profile](#run-the-lightweight-kubernetes-profile)
- [Optional replication and monitoring](#optional-replication-and-monitoring)
- [Useful URLs and commands](#useful-urls-and-commands)
- [Repository structure](#repository-structure)
- [Security and deployment notes](#security-and-deployment-notes)
- [More documentation](#more-documentation)

## Features

- PDF upload and document processing for the university knowledge base.
- RAG-based question answering using retrieved document passages.
- Source citations attached to generated answers.
- Role-aware document access for student, faculty, and administrator roles.
- Conversation history and user-specific conversation access.
- Keycloak-based OpenID Connect sign-in, with Google identity-provider federation configurable in the imported realm.
- Administrative pages for document and user management, plus analytics/metadata views.
- PostgreSQL persistence, Redis caching/distributed locks, and MinIO object storage.
- Qdrant vector search, Prometheus metrics, and provisioned Grafana dashboards.
- Docker Compose and Kubernetes deployment definitions, including a reduced-resource laptop profile.

Google sign-in requires real Google OAuth credentials. The repository's local Keycloak realm contains the Google identity-provider configuration and the local callback URL; configure the corresponding credentials in `.env` before testing Google login.

## How the RAG pipeline works

1. An authorized administrator uploads a PDF through the frontend.
2. The original file is stored in MinIO and its metadata/status is recorded in PostgreSQL.
3. The backend extracts PDF text, splits it into chunks, and creates embeddings using `sentence-transformers/all-MiniLM-L6-v2`.
4. Embeddings and chunk payloads are indexed in Qdrant; chunk metadata and document access restrictions are stored in PostgreSQL.
5. When a user asks a question, the backend retrieves eligible chunks, builds a grounded prompt, and requests an answer from the configured LLM provider.
6. The response includes citations to the retrieved document passages. Access filtering is applied so users only retrieve documents permitted for their role.

The local profile runs the embedding model on the CPU. It does **not** run a generative LLM locally: with `GROQ_API_KEY` configured, completion requests are sent to Groq. Without a configured Groq key, the code uses a deterministic mock response intended for offline wiring/demo checks, not real AI answers.

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Backend API | Python 3.12, FastAPI, Uvicorn |
| Relational database | PostgreSQL 16, SQLAlchemy, Alembic |
| Vector database | Qdrant |
| Embeddings | Sentence Transformers — `all-MiniLM-L6-v2` (384 dimensions) |
| LLM provider | Groq API (remote) |
| Object storage | MinIO |
| Cache and distributed locks | Redis |
| Identity provider | Keycloak / OpenID Connect; Google federation configurable |
| Monitoring | Prometheus and Grafana (optional local profile) |
| Deployment | Docker Compose and Kubernetes/Kustomize |

## Requirements

For the recommended local Docker workflow:

- Apple Silicon Mac (the lightweight settings are designed with an 8 GB M2 Air in mind).
- Docker Desktop with Docker Compose v2.
- Internet access for the initial image builds and embedding-model download.
- A Groq API key for real LLM-generated answers.
- Google OAuth client credentials only when demonstrating Google sign-in.

For Kubernetes, enable the Kubernetes feature in Docker Desktop and ensure `kubectl` is available. The laptop overlay uses local container images and a single-node local cluster.

## Quick start with Docker Compose

Run these commands from the repository root.

### 1. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and replace **every** `CHANGE_ME...` placeholder with a separate, unique secret. You can generate a random value with:

```bash
openssl rand -hex 32
```

Use a newly generated value for each secret; do not reuse one secret for multiple services. Keep `.env` private and never commit it to Git. Set `GROQ_API_KEY` to your Groq API key for actual LLM answers. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` when configuring Google sign-in.

Keep these local demo settings unless you have a reason to change them:

```dotenv
ENVIRONMENT=development
DEBUG=false
ENABLE_DEV_AUTH=false
DB_READ_REPLICAS_ENABLED=false
EMBEDDING_BATCH_SIZE=8
EMBEDDING_NUM_THREADS=1
RAG_INGESTION_BATCH_SIZE=8
RAG_MAX_CONCURRENT_INGESTIONS=1
RAG_TOP_K=4
MAX_UPLOAD_SIZE_BYTES=10485760
```

`ENABLE_DEV_AUTH` should remain `false` for the normal authentication demonstration. Do not enable the development login path in a shared or production environment.

### 2. Build images sequentially

Build one image at a time to avoid competing memory peaks on an 8 GB machine:

```bash
docker compose build backend
docker compose build frontend
```

The backend image build downloads and caches the MiniLM embedding model. The first build therefore needs internet access and can take longer; subsequent container starts use the model cached in the image.

### 3. Start the default lightweight stack

```bash
docker compose up -d
docker compose ps
```

The default stack starts seven services: PostgreSQL primary, Redis, Qdrant, MinIO, Keycloak, backend, and frontend. PostgreSQL read replicas and Prometheus/Grafana are excluded unless their Compose profiles are explicitly enabled.

### 4. Check logs and open the application

```bash
docker compose logs -f backend
```

Open the frontend at **http://localhost:3000**. The backend health endpoint is **http://localhost:8000/api/v1/health**. In the local development environment, the API documentation is available at **http://localhost:8000/docs**.

For Google login, ensure the Google OAuth credentials are configured in `.env` and the authorized redirect URI in the Google provider setup matches the Keycloak broker configuration. The local OIDC client redirect URI registered in the Keycloak realm is `http://localhost:3000/auth/callback`. Google must separately be configured with the Keycloak Google-broker redirect URI shown in the Keycloak identity-provider settings.

### 5. Stop the stack

```bash
docker compose down
```

This stops containers but retains named data volumes. **Do not add `-v`** unless you deliberately want to remove the database, vector-store, Redis, and object-storage data.

## Run the lightweight Kubernetes profile

Use this workflow when you need to demonstrate Kubernetes on the Mac. Stop the Docker Compose stack first:

```bash
docker compose down
```

Make sure Docker Desktop Kubernetes is enabled and the current `kubectl` context points to that local cluster.

### 1. Build the local images sequentially

Run from the repository root:

```bash
docker build -f docker/backend.Dockerfile -t university-knowledge-assistant-backend:latest .
docker build -f docker/frontend.Dockerfile -t university-knowledge-assistant-frontend:latest .
```

The Kubernetes deployments use these image names and `IfNotPresent` image-pull behavior, so the images must be available to the local cluster.

### 2. Create the Kubernetes secret

Create a local file named `uka-secrets.env` and supply the credential values required by the laptop-profile pods. The key list and example format are documented in [`LOCAL_DEMO_8GB.md`](LOCAL_DEMO_8GB.md). Do not commit this secrets file.

Create the secret:

```bash
kubectl create secret generic uka-secrets --from-env-file=uka-secrets.env -n default
```

If you have already created the secret and need to update it, delete/recreate it or use an explicit `kubectl create secret ... --dry-run=client -o yaml | kubectl apply -f -` workflow.

### 3. Apply the laptop overlay

```bash
kubectl apply -k kubernetes/overlays/laptop
kubectl get pods -w
```

The laptop overlay runs one PostgreSQL primary, Redis, Qdrant, MinIO, Keycloak, backend, and frontend. It omits PostgreSQL replicas, HPA, Prometheus/Grafana, ingress, and NetworkPolicies. Its configured application pod memory limits total approximately 3.13 GiB; this is a set of resource ceilings, not a measurement of actual runtime usage.

### 4. Port-forward the services

Run each command in a separate terminal:

```bash
kubectl port-forward svc/frontend 3000:3000
kubectl port-forward svc/backend 8000:8000
kubectl port-forward svc/keycloak 8080:8080
```

Open **http://localhost:3000**. The local Keycloak realm includes the frontend callback `http://localhost:3000/auth/callback` and the frontend web origin `http://localhost:3000`.

For complete environment-variable examples and laptop-specific notes, see [`LOCAL_DEMO_8GB.md`](LOCAL_DEMO_8GB.md). For the full Kubernetes deployment requirements (including ingress TLS and production host configuration), see [`kubernetes/README.md`](kubernetes/README.md).

## Optional replication and monitoring

The full Docker Compose stack can demonstrate PostgreSQL read replicas and Prometheus/Grafana separately from the lightweight default profile. In `.env`, set:

```dotenv
DB_READ_REPLICAS_ENABLED=true
POSTGRES_REPLICA1_HOST=postgres-replica-1
POSTGRES_REPLICA2_HOST=postgres-replica-2
```

Then start the additional services:

```bash
docker compose --profile replication --profile monitoring up -d
```

This profile uses additional memory. Return to the laptop-friendly stack by stopping the services and starting the default Compose profile again. Do not enable these optional services for the normal 8 GB demo unless you specifically need to demonstrate replication or monitoring.

## Useful URLs and commands

| Service | Local URL / port | Purpose |
|---|---|---|
| Frontend | [http://localhost:3000](http://localhost:3000) | Web application |
| Backend API | [http://localhost:8000](http://localhost:8000) | FastAPI service |
| API documentation | [http://localhost:8000/docs](http://localhost:8000/docs) | Development-only Swagger UI |
| Keycloak | [http://localhost:8080](http://localhost:8080) | Identity provider |
| MinIO Console | [http://localhost:9001](http://localhost:9001) | Object-storage console |
| Qdrant | [http://localhost:6333](http://localhost:6333) | Vector database API |
| PostgreSQL | `localhost:5432` | Relational database |
| Prometheus | [http://localhost:9091](http://localhost:9091) | Optional monitoring profile (port 9091 to avoid Jenkins conflict) |
| Grafana | [http://localhost:3001](http://localhost:3001) | Optional dashboards profile |

Useful Docker commands:

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose restart backend
docker compose down
```

Useful Kubernetes commands:

```bash
kubectl get pods
kubectl get services
kubectl logs deployment/backend
kubectl describe pod <pod-name>
kubectl get events --sort-by=.lastTimestamp
```

## Repository structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes: auth, documents, RAG, conversations, admin, health
│   │   ├── core/         # Configuration, security, errors, logging, cache, metrics
│   │   ├── db/           # SQLAlchemy models, sessions, database routing
│   │   ├── rag/          # PDF extraction, chunking, embeddings, retrieval, citations, LLM
│   │   └── services/     # External storage and service integrations
│   └── tests/            # Backend tests
├── frontend/             # Next.js application and UI routes
├── database/             # SQL initialization and Alembic migrations
├── docker/               # Backend/frontend Dockerfiles and service initialization
├── kubernetes/
│   ├── base/              # Full Kubernetes resources
│   ├── overlays/laptop/   # Reduced-resource single-node overlay
│   └── postgres/          # PostgreSQL primary/replica manifests
├── monitoring/           # Prometheus and Grafana configuration
├── scripts/              # Deployment, CI, demo, and verification scripts
├── docker-compose.yml
├── .env.example
├── LOCAL_DEMO_8GB.md
└── PATCH_NOTES.md
```

## Security and deployment notes

- Never commit `.env`, `uka-secrets.env`, OAuth client secrets, API keys, database passwords, or Kubernetes secret material.
- The laptop Kubernetes overlay is for local demonstration, not production deployment. It intentionally omits ingress TLS, NetworkPolicies, autoscaling, read replicas, and monitoring.
- Before a public deployment, configure TLS, production hostnames, trusted CORS origins, Keycloak redirect URIs/web origins, Kubernetes Secrets, persistent-volume backups, and image/dependency scanning.
- The regular Keycloak realm requires valid OAuth credentials for Google federation. Do not use placeholder values for a real login demonstration.
- The backend Swagger/OpenAPI endpoints are enabled only in development/testing mode.
- Back up persistent data before changing database initialization or migration setup. Initialization SQL only runs when the PostgreSQL data directory is first created.

## More documentation

- [`LOCAL_DEMO_8GB.md`](LOCAL_DEMO_8GB.md) — detailed resource-conscious Docker and Kubernetes instructions for an 8 GB Apple Silicon Mac.
- [`kubernetes/README.md`](kubernetes/README.md) — full Kubernetes prerequisites, secrets, TLS, production build arguments, and existing-volume notes.
- [`PATCH_NOTES.md`](PATCH_NOTES.md) — code changes, resource optimizations, validation performed, and known remaining work.
