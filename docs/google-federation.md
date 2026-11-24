# Google Identity Provider Federation Guide

This document describes the configuration and operational setup for Google Identity Provider federation with the University Knowledge Assistant via Keycloak.

## 1. Overview

The University Knowledge Assistant uses Keycloak as its centralized Identity and Access Management (IAM) broker. Keycloak delegates user authentication to Google OAuth 2.0 / OIDC while issuing application-specific RS256 JWT access and refresh tokens.

## 2. Google Cloud Console Configuration

To enable Google sign-in:

1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select an existing Google Cloud Project.
3. Configure the **OAuth Consent Screen**:
   - User Type: External (or Internal if restricted to a Google Workspace domain).
   - Scopes: `openid`, `.../auth/userinfo.profile`, `.../auth/userinfo.email`.
4. Create **OAuth 2.0 Client IDs**:
   - Application Type: **Web application**.
   - Name: `University Knowledge Assistant Keycloak Broker`.
   - **Authorized JavaScript origins**:
     - `http://localhost:8080`
   - **Authorized redirect URIs** (Critical):
     - `http://localhost:8080/realms/university-realm/broker/google/endpoint`
     *(For production, replace `http://localhost:8080` with your public Keycloak domain, e.g., `https://auth.university.edu/realms/university-realm/broker/google/endpoint`)*.
5. Copy the generated **Client ID** and **Client Secret**.

## 3. Environment Variables

Store your credentials in `.env`:

```dotenv
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## 4. Keycloak Identity Provider Realm Setup

In `docker/keycloak/university-realm.json`, the identity provider is configured under `identityProviders`:

```json
{
  "alias": "google",
  "displayName": "Google",
  "providerId": "google",
  "enabled": true,
  "trustEmail": true,
  "storeToken": false,
  "firstBrokerLoginFlowAlias": "first broker login",
  "config": {
    "clientId": "${env.GOOGLE_CLIENT_ID:placeholder-google-client-id}",
    "clientSecret": "${env.GOOGLE_CLIENT_SECRET:placeholder-google-client-secret}",
    "defaultScope": "openid profile email",
    "syncMode": "IMPORT",
    "useUserinfoEndpoint": "true"
  }
}
```

Key configuration points:
- `trustEmail: true`: Prevents requiring redundant email verification since Google has already verified the user's email address.
- `syncMode: IMPORT`: Provisions users into the Keycloak realm upon their first Google sign-in.
- `email-verified` Protocol Mapper: Emits `email_verified: true` into the access token payload for the backend FastAPI application.

## 5. Troubleshooting Common Issues

1. **`Error 400: redirect_uri_mismatch`**:
   The redirect URI registered in Google Cloud Console must match `http://localhost:8080/realms/university-realm/broker/google/endpoint` exactly (pointing to Keycloak's broker, not the frontend Next.js callback).

2. **Existing Keycloak Database Volume**:
   Keycloak's `--import-realm` CLI flag only runs on the initial container startup. If credentials are changed after Keycloak has already initialized, update the Google provider in the Keycloak Admin Console (`http://localhost:8080/admin`) or reset the database volume with `docker compose down -v`.

3. **Email Verification**:
   Ensure realm-level `verifyEmail` is set to `false` when no SMTP server is provisioned locally, relying on Google's trusted email verification.
