# Lightweight local demo profile (8 GB Apple Silicon Mac)

The application is configured to run the RAG embedding model on CPU and call the LLM through Groq. It does **not** load a local generative LLM. The embedding model is `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional vectors); neural cross-encoder reranking is disabled by default.

## Resource-conscious RAG defaults

- Embedding and ingestion batches are limited to 8 chunks.
- PyTorch/BLAS/tokenizer parallelism is limited to one CPU thread in the containers.
- Only one document ingestion runs at a time per backend process, and embedding calls are serialized within that process.
- Ingestion embeds and upserts chunks incrementally instead of holding the entire document's embeddings and Qdrant point objects in memory.
- Retrieval returns 4 chunks in the laptop profile.
- Uploads are limited to 10 MiB in the laptop profile.
- The embedding model is downloaded into the backend image at build time and loaded lazily at runtime. The first image build needs internet access; container runtime can use the cached model offline.

## Docker Compose: recommended everyday demo

1. Copy `.env.example` to `.env` and replace all `CHANGE_ME` secrets. Add your `GROQ_API_KEY`; add Google OAuth client credentials when demonstrating Google sign-in.
2. Build the images one at a time to avoid competing build-time memory peaks:

   ```bash
   docker compose build backend
   docker compose build frontend
   ```

3. Start the laptop-friendly default stack:

   ```bash
   docker compose up -d
   ```

The default stack uses one PostgreSQL primary. PostgreSQL replicas and Prometheus/Grafana are optional Compose profiles, so they do not start by default. The seven default services have combined declared memory ceilings of about 3.55 GiB; this is a safety cap, not a prediction of normal usage.

To demonstrate replication and monitoring separately, first set `DB_READ_REPLICAS_ENABLED=true`, `POSTGRES_REPLICA1_HOST=postgres-replica-1`, and `POSTGRES_REPLICA2_HOST=postgres-replica-2` in `.env`, then run:

```bash
docker compose --profile replication --profile monitoring up -d
```

This full profile consumes more memory. Disable it again for normal laptop work with `docker compose down` followed by `docker compose up -d`.

## Kubernetes: laptop overlay

Use Docker Desktop Kubernetes (or another single-node local cluster). A practical Docker Desktop allocation on an 8 GB Mac is about 5 GB for Docker/Kubernetes, leaving the remainder to macOS and your editor. Do not enable the full replication, HPA, ingress, or monitoring stack for the laptop demo.

Build the same two images sequentially, with the local frontend defaults (API at `http://localhost:8000/api/v1`, Keycloak at `http://localhost:8080`):

```bash
docker build -f docker/backend.Dockerfile -t university-knowledge-assistant-backend:latest .
docker build -f docker/frontend.Dockerfile -t university-knowledge-assistant-frontend:latest .
```

Create a local `uka-secrets.env` file (do not commit it) with the credentials required by the Kubernetes pods. The minimum keys are:

```dotenv
POSTGRES_SUPERUSER=postgres
POSTGRES_SUPERUSER_PASSWORD=CHANGE_ME
POSTGRES_DB=university_assistant
APP_DB_PASSWORD=CHANGE_ME
READONLY_DB_PASSWORD=CHANGE_ME
KEYCLOAK_DB_PASSWORD=CHANGE_ME
REPL_PASSWORD=CHANGE_ME
REDIS_PASSWORD=CHANGE_ME
QDRANT_API_KEY=CHANGE_ME
MINIO_ROOT_USER=uka_minio_admin
MINIO_ROOT_PASSWORD=CHANGE_ME
KEYCLOAK_ADMIN=uka_keycloak_admin
KEYCLOAK_ADMIN_PASSWORD=CHANGE_ME
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GROQ_API_KEY=CHANGE_ME
GEMINI_API_KEY=
```

Create the secret and apply the laptop overlay:

```bash
kubectl create secret generic uka-secrets --from-env-file=uka-secrets.env -n default
kubectl apply -k kubernetes/overlays/laptop
```

The laptop overlay runs one PostgreSQL primary and omits replicas, HPA, Prometheus/Grafana, ingress, and NetworkPolicies. Its application pod memory limits total approximately 3.13 GiB (actual use varies). It is for a local-only demonstration, not a production deployment.

Do not run the full Docker Compose stack and the Kubernetes stack at the same time on this 8 GB machine. Stop the Compose stack before starting Kubernetes, or stop the Kubernetes workloads before returning to Compose.

In separate terminals, forward the frontend, backend, and Keycloak services:

```bash
kubectl port-forward svc/frontend 3000:3000
kubectl port-forward svc/backend 8000:8000
kubectl port-forward svc/keycloak 8080:8080
```

Open `http://localhost:3000`. Ensure the Keycloak realm's local callback and web origin entries include `http://localhost:3000`.

## What to demonstrate

A good live demo is to upload a small university PDF, show the processing status, ask a question supported by the PDF, and open the citations. Keep the dataset modest (a handful of small PDFs) and avoid uploading large scanned/image-only PDFs on this laptop profile.
