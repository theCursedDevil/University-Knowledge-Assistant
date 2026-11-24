# Kubernetes deployment prerequisites

The manifests do not contain usable credentials. Before applying them, create the `uka-secrets` Secret and the Ingress TLS Secret `uka-ingress-tls`.

Create a local `.env.k8s` file (never commit it) with these keys, replacing each `CHANGE_ME` with a unique random secret:

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
GOOGLE_CLIENT_ID=CHANGE_ME
GOOGLE_CLIENT_SECRET=CHANGE_ME
GROQ_API_KEY=CHANGE_ME
GEMINI_API_KEY=
GRAFANA_ADMIN_USER=uka_grafana_admin
GRAFANA_ADMIN_PASSWORD=CHANGE_ME
```

```bash
kubectl create secret generic uka-secrets --from-env-file=.env.k8s -n default
kubectl create secret tls uka-ingress-tls --cert=fullchain.pem --key=privkey.pem -n default
kubectl apply -k kubernetes/
```

The configured ingress/issuer host is `uka.university.edu`. Change the host, Keycloak hostname/issuer/public URL, callback URI, OAuth redirect URI and CORS origin together before deploying elsewhere. Create the first administrator through the secured Keycloak administration workflow; do not reintroduce exported demo accounts. The Keycloak realm includes an audience mapper required by the backend.


## Existing database volumes

The SQL files under `database/` are PostgreSQL first-initialization scripts. They run only
when the primary data directory is empty. If you already have a persistent PostgreSQL
volume from an earlier build, do not delete it to make these changes take effect. Back it
up first, then provision the `uka_app`, `uka_replicator`, and `uka_keycloak` roles and the
`keycloak` database with the new secret values before rolling out the updated backend and
Keycloak. The backend runs Alembic at startup as `uka_app`, so that role has `CREATE` on
`public` for schema migrations; the runtime grant set is limited to the application's
own database schema and CRUD/sequence privileges.

## Local configuration

Copy `.env.example` to `.env` before running Docker Compose. Keep `ENABLE_DEV_AUTH=false`
for normal sign-in. The mock login route is only available when both the backend
`ENABLE_DEV_AUTH=true` and the frontend `NEXT_PUBLIC_DEV_LOGIN=true` flags are deliberately
enabled for a local demonstration.

## Build the frontend image with production public URLs

Next.js inlines `NEXT_PUBLIC_*` values into the browser bundle at image build time. Build the frontend image with the production values (not the Dockerfile localhost defaults):

```bash
docker build -f docker/frontend.Dockerfile -t university-knowledge-assistant-frontend:latest \
  --build-arg NEXT_PUBLIC_API_URL=https://uka.university.edu/api/v1 \
  --build-arg NEXT_PUBLIC_KEYCLOAK_URL=https://uka.university.edu \
  --build-arg NEXT_PUBLIC_KEYCLOAK_REALM=university-realm \
  --build-arg NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=university-assistant-client \
  --build-arg NEXT_PUBLIC_DEV_LOGIN=false .
```

Load/push that image to the registry used by the cluster before applying the frontend Deployment. Runtime environment variables in the Deployment do not rewrite an already-built browser bundle.


## 8 GB laptop demonstration

For a single-node local cluster on an 8 GB Apple Silicon Mac, use the lightweight overlay rather than the full production manifest set:

```bash
kubectl apply -k kubernetes/overlays/laptop
```

This overlay runs one PostgreSQL primary, Redis, Qdrant, MinIO, Keycloak, the backend and frontend. It omits PostgreSQL replicas, HPA, Prometheus/Grafana, ingress and NetworkPolicies. It uses bounded RAG batches and smaller pod memory limits. Its settings are for local-only port-forward demonstrations, not production.

Build backend and frontend images sequentially, then port-forward the `frontend` (3000), `backend` (8000) and `keycloak` (8080) services. Full instructions and the required local secrets are in `LOCAL_DEMO_8GB.md` at the repository root.
