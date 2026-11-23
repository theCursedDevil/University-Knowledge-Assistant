# Keycloak Google Identity Federation Guide

**Generative AI-Based University Knowledge Assistant**  
Architecture Component: `C-AUTHSVC` · SRS Reference: `§5.13 (Appendix M)` · Prompt 28

---

## 1. Overview & Architecture

In the University Knowledge Assistant, **Keycloak acts as a Central Identity Broker (IdP)**. Rather than requiring the Next.js frontend or FastAPI backend to implement direct Google OAuth client code, Keycloak handles external identity federation natively:

```
[Student / Faculty Browser]
       │
       ▼ (1) Clicks "Sign in with Google"
[Keycloak Login Page (port 8080)]
       │
       ▼ (2) Redirects to Google OAuth 2.0
[Google Accounts Consent Screen (accounts.google.com)]
       │
       ▼ (3) Authorizes & returns OAuth authorization code
[Keycloak Identity Broker Endpoint]
  (/realms/university-realm/broker/google/endpoint)
       │
       ▼ (4) Maps Google user, assigns default "student" role, issues university JWT
[Next.js Frontend] ──(5) Bearer JWT──▶ [FastAPI Backend]
```

### Key Advantages:
1. **Single Source of Truth:** The backend FastAPI application validates Keycloak JWTs identically regardless of whether the user logged in via university credentials or Google Social Login.
2. **Zero Secrets in Frontend:** The frontend never stores Google API client secrets.
3. **Role-Based Access Control (RBAC):** Google-federated users are automatically mapped to the default university role (`student`), while administrative rights require explicit promotion by an Admin.

---

## 2. Google Cloud Console Setup (3 Steps)

To enable live Google login with real Google accounts:

### Step 1: Create OAuth 2.0 Client in Google Cloud Console
1. Navigate to the [Google Cloud Console Credentials Page](https://console.cloud.google.com/apis/credentials).
2. Click **Create Credentials** -> **OAuth client ID**.
3. Select Application Type: **Web application**.
4. Set Name: `University Knowledge Assistant Keycloak`.

### Step 2: Configure Authorized Redirect URIs
Add the exact Keycloak broker callback URI to **Authorized redirect URIs**:
```
http://localhost:8080/realms/university-realm/broker/google/endpoint
```
*(For production deployments, replace `localhost:8080` with your fully-qualified domain name).*

### Step 3: Copy Client ID & Client Secret
Copy the generated:
* **Client ID** (e.g. `1234567890-abcdef.apps.googleusercontent.com`)
* **Client Secret** (e.g. `GOCSPX-xyz123abc456`)

---

## 3. Configuration & Deployment

### In `.env`:
Add the credentials to your `.env` file:
```bash
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
```

### Automatic Provisioning via Docker Compose:
The Keycloak container in `docker-compose.yml` mounts `docker/keycloak/university-realm.json`. It dynamically binds the environment variables:
```json
"identityProviders": [
  {
    "alias": "google",
    "displayName": "Google",
    "providerId": "google",
    "enabled": true,
    "config": {
      "clientId": "${env.GOOGLE_CLIENT_ID:placeholder-google-client-id}",
      "clientSecret": "${env.GOOGLE_CLIENT_SECRET:placeholder-google-client-secret}"
    }
  }
]
```

When you start the stack with `docker compose up -d`, Keycloak automatically displays the **"Google"** login button on the university login page.

---

## 4. Local Development Fallback

If `GOOGLE_CLIENT_ID` is left empty, the application runs in local development mode using pre-configured mock credentials:
* **Admin:** `admin` / `AdminPassword123!`
* **Faculty:** `faculty` / `FacultyPassword123!`
* **Student:** `student` / `StudentPassword123!`

This guarantees zero offline development breakage while providing full production-grade social identity broker capability.
