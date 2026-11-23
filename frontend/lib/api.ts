/**
 * Centralized API client for communicating with the FastAPI backend.
 * Supports standard REST endpoints and Server-Sent Events (SSE) streaming for RAG chat.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Standard Auth Headers Helper
function getAuthHeaders(role?: string, email?: string): Record<string, string> {
  const headers: Record<string, string> = {};
  if (typeof window !== "undefined") {
    const savedRole = role || localStorage.getItem("uka_user_role") || "student";
    const savedEmail = email || localStorage.getItem("uka_user_email") || `${savedRole}@university.edu`;
    const savedToken = localStorage.getItem("uka_access_token");
    headers["X-Dev-Role"] = savedRole;
    headers["X-Dev-Email"] = savedEmail;
    if (savedToken) {
      headers["Authorization"] = `Bearer ${savedToken}`;
    } else {
      headers["Authorization"] = `Bearer dev-token-${savedRole}`;
    }
  } else {
    headers["X-Dev-Role"] = role || "student";
    headers["X-Dev-Email"] = email || "student@university.edu";
    headers["Authorization"] = `Bearer dev-token-${role || "student"}`;
  }
  return headers;
}

// ---------------------------------------------------------------------------
// Type Definitions matching FastAPI Pydantic Models
// ---------------------------------------------------------------------------

export interface ApiUser {
  id: string;
  name: string;
  email: string;
  role: "student" | "faculty" | "admin";
  roles?: string[];
  oauth_sub: string;
  created_at: string;
}

export interface ApiCitation {
  document: string;
  page?: number | null;
  section?: string | null;
}

export interface ApiMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations_json?: ApiCitation[] | null;
  created_at: string;
}

export interface ApiConversationSummary {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ApiConversationDetail {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ApiMessage[];
}

export interface ApiDocument {
  id: string;
  title: string;
  category: string;
  role_restriction?: string | null;
  storage_path: string;
  uploaded_by?: string | null;
  status: "processing" | "ready" | "indexed" | "failed";
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ApiExtractedPage {
  page_number: number;
  text: string;
  section?: string | null;
  char_count: number;
}

export interface ApiDocumentPreview {
  id: string;
  title: string;
  category: string;
  role_restriction?: string | null;
  status: string;
  storage_path: string;
  page_count: number;
  pages: ApiExtractedPage[];
}

export interface ApiDocumentChunk {
  id: string;
  vector_id: string;
  chunk_index: number;
  page?: number | null;
  section?: string | null;
  created_at: string;
}

export interface ApiSearchResult {
  chunk_id: string;
  document_id: string;
  document_name: string;
  chunk_text: string;
  page?: number | null;
  section?: string | null;
  score: number;
  category?: string | null;
}

export interface ApiAuditLog {
  id: string;
  user_id?: string | null;
  action: string;
  entity: string;
  entity_id?: string | null;
  details?: Record<string, any> | null;
  created_at: string;
}

export interface ApiAdminStats {
  total_documents: number;
  processed_documents: number;
  failed_documents: number;
  processing_documents: number;
  total_chunks: number;
  total_conversations: number;
  total_messages: number;
  total_questions: number;
  total_answers: number;
  total_users: number;
  documents_by_category: Record<string, number>;
  documents_by_status: Record<string, number>;
  recent_audit_logs: ApiAuditLog[];
}

// ---------------------------------------------------------------------------
// 1. Authentication & Profile APIs (Items 1 & 2)
// ---------------------------------------------------------------------------

export async function fetchCurrentUser(role?: string, email?: string): Promise<ApiUser> {
  const headers = getAuthHeaders(role, email);
  const res = await fetch(`${API_BASE_URL}/me`, {
    headers: { ...headers, "Content-Type": "application/json" },
    credentials: "include",
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch current user profile: HTTP ${res.status}`);
  }
  return res.json();
}

export async function loginUser(email: string, role: string, name?: string): Promise<{ user: ApiUser; access_token: string }> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, role, name }),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody?.error?.message || `Login failed: HTTP ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// 2. Conversations APIs (Items 3, 4, 5)
// ---------------------------------------------------------------------------

export async function fetchConversations(): Promise<ApiConversationSummary[]> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/conversations`, {
    headers: { ...headers, "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch conversations: HTTP ${res.status}`);
  }
  return res.json();
}

export async function createConversation(title?: string): Promise<ApiConversationSummary> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/conversations`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) {
    throw new Error(`Failed to create conversation: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchConversationDetail(id: string): Promise<ApiConversationDetail> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/conversations/${id}`, {
    headers: { ...headers, "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch conversation details: HTTP ${res.status}`);
  }
  return res.json();
}

export async function deleteConversation(id: string): Promise<void> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/conversations/${id}`, {
    method: "DELETE",
    headers,
  });
  if (!res.ok) {
    throw new Error(`Failed to delete conversation: HTTP ${res.status}`);
  }
}

// ---------------------------------------------------------------------------
// 3. Chat Messaging & Streaming APIs (Items 6, 7, 8, 9)
// ---------------------------------------------------------------------------

export async function streamChatMessage({
  conversationId,
  message,
  onToken,
  onCitations,
  onComplete,
  onError,
}: {
  conversationId: string;
  message: string;
  onToken: (token: string) => void;
  onCitations: (citations: ApiCitation[]) => void;
  onComplete: (data: { answer: string; citations: ApiCitation[]; messageId?: string }) => void;
  onError: (err: Error) => void;
}) {
  const headers = getAuthHeaders();

  try {
    const res = await fetch(
      `${API_BASE_URL}/conversations/${conversationId}/messages?stream=true`,
      {
        method: "POST",
        headers: {
          ...headers,
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ content: message, message }),
      }
    );

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson?.error?.message || `Chat request failed: HTTP ${res.status}`);
    }

    const reader = res.body?.getReader();
    if (!reader) {
      throw new Error("Response body is not readable for SSE streaming.");
    }

    const decoder = new TextDecoder();
    let buffer = "";
    let accumulatedAnswer = "";
    let accumulatedCitations: ApiCitation[] = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Retain incomplete line fragment

      let currentEvent = "message";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        if (trimmed.startsWith("event:")) {
          currentEvent = trimmed.replace("event:", "").trim();
        } else if (trimmed.startsWith("data:")) {
          const rawData = trimmed.replace("data:", "").trim();
          try {
            const parsed = JSON.parse(rawData);

            if (parsed.token !== undefined) {
              accumulatedAnswer += parsed.token;
              onToken(parsed.token);
            } else if (parsed.citations !== undefined) {
              accumulatedCitations = parsed.citations;
              onCitations(parsed.citations);
            } else if (parsed.done || currentEvent === "done") {
              const finalAnswer = parsed.answer || accumulatedAnswer;
              const finalCitations = parsed.citations || accumulatedCitations;
              onComplete({
                answer: finalAnswer,
                citations: finalCitations,
                messageId: parsed.message_id,
              });
              return;
            } else if (parsed.error || currentEvent === "error") {
              onError(new Error(parsed.error || "Streaming error encountered."));
              return;
            }
          } catch {
            // Raw text fallback if JSON parsing fails
            if (rawData && rawData !== "[DONE]") {
              accumulatedAnswer += rawData;
              onToken(rawData);
            }
          }
        }
      }
    }

    // Fallback completion if stream ends without explicit 'done' event
    onComplete({
      answer: accumulatedAnswer,
      citations: accumulatedCitations,
    });
  } catch (err: any) {
    onError(err instanceof Error ? err : new Error(String(err)));
  }
}

// ---------------------------------------------------------------------------
// 4. Documents & Ingestion APIs (Items 10, 11, 12, 13, 14, 16)
// ---------------------------------------------------------------------------

export async function fetchDocuments(category?: string): Promise<ApiDocument[]> {
  const headers = getAuthHeaders();
  const url = category && category !== "All"
    ? `${API_BASE_URL}/documents?category=${encodeURIComponent(category)}`
    : `${API_BASE_URL}/documents`;

  const res = await fetch(url, {
    headers: { ...headers, "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch documents: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchDocumentById(id: string): Promise<ApiDocument> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/documents/${id}`, {
    headers: { ...headers, "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch document: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchDocumentPreview(id: string): Promise<ApiDocumentPreview> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/documents/${id}/preview`, {
    headers: { ...headers, "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch document preview: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchDocumentChunks(id: string): Promise<ApiDocumentChunk[]> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/documents/${id}/chunks`, {
    headers: { ...headers, "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch document chunks: HTTP ${res.status}`);
  }
  return res.json();
}

export async function uploadDocument(formData: FormData, autoProcess = true): Promise<ApiDocument> {
  const headers = getAuthHeaders();
  const url = `${API_BASE_URL}/documents?auto_process=${autoProcess}`;

  const res = await fetch(url, {
    method: "POST",
    headers, // Do NOT set Content-Type so browser sets multipart boundary
    credentials: "include",
    body: formData,
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody?.error?.message || `Document upload failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function processDocument(id: string): Promise<any> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/documents/${id}/process`, {
    method: "POST",
    headers,
    credentials: "include",
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody?.error?.message || `Processing failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function updateDocumentMetadata(
  id: string,
  payload: { title?: string; category?: string; role_restriction?: string; expected_version?: number }
): Promise<ApiDocument> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/documents/${id}`, {
    method: "PATCH",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    if (res.status === 409) {
      throw new Error(
        errBody?.error?.message ||
        "Conflict (HTTP 409): Document has been modified by another transaction. Please refresh."
      );
    }
    throw new Error(errBody?.error?.message || `Failed to update document metadata: HTTP ${res.status}`);
  }
  return res.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/documents/${id}`, {
    method: "DELETE",
    headers,
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody?.error?.message || `Failed to delete document: HTTP ${res.status}`);
  }
}

export async function searchSemanticDocuments(
  query: string,
  limit = 5,
  category?: string
): Promise<ApiSearchResult[]> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/documents/search`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      limit,
      category: category && category !== "All" ? category : undefined,
    }),
  });
  if (!res.ok) {
    throw new Error(`Semantic search failed: HTTP ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// 5. Admin Analytics & User Management APIs (Item 15)
// ---------------------------------------------------------------------------

export async function fetchAdminStats(): Promise<ApiAdminStats> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/admin/stats`, {
    headers: { ...headers, "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody?.error?.message || `Failed to fetch admin analytics: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchAdminAuditLogs(params?: {
  action?: string;
  entity?: string;
  limit?: number;
  offset?: number;
}): Promise<ApiAuditLog[]> {
  const headers = getAuthHeaders();
  const query = new URLSearchParams();
  if (params?.action) query.set("action", params.action);
  if (params?.entity) query.set("entity", params.entity);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));

  const url = `${API_BASE_URL}/admin/audit-logs${query.toString() ? `?${query.toString()}` : ""}`;
  const res = await fetch(url, {
    headers: { ...headers, "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody?.error?.message || `Failed to fetch audit logs: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchAdminUsers(): Promise<ApiUser[]> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/admin/users`, {
    headers: { ...headers, "Content-Type": "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody?.error?.message || `Failed to fetch users: HTTP ${res.status}`);
  }
  return res.json();
}

export async function updateAdminUserRole(userId: string, role: string): Promise<ApiUser> {
  const headers = getAuthHeaders();
  const res = await fetch(`${API_BASE_URL}/admin/users/${userId}/role`, {
    method: "PATCH",
    headers: { ...headers, "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ role }),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody?.error?.message || `Failed to update user role: HTTP ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// 7. Keycloak OAuth 2.0 / OIDC & PKCE APIs (Phase 8, FR-AUTH)
// ---------------------------------------------------------------------------

export interface KeycloakConfig {
  keycloak_url: string;
  realm: string;
  client_id: string;
}

export async function fetchKeycloakConfig(): Promise<KeycloakConfig> {
  const res = await fetch(`${API_BASE_URL}/auth/config`, {
    cache: "no-store",
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error("Failed to load Keycloak configuration");
  }
  return res.json();
}

export async function exchangeAuthCode(
  code: string,
  codeVerifier: string,
  redirectUri: string
): Promise<{ user: ApiUser; access_token: string }> {
  const res = await fetch(`${API_BASE_URL}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      code,
      code_verifier: codeVerifier,
      redirect_uri: redirectUri,
    }),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody?.error?.message || errBody?.detail || "Authorization code exchange failed");
  }
  return res.json();
}

export async function refreshAuthSession(): Promise<{ user: ApiUser; access_token: string }> {
  const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    throw new Error("Failed to refresh session");
  }
  return res.json();
}

export async function logoutBackend(): Promise<void> {
  await fetch(`${API_BASE_URL}/auth/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({}),
  }).catch(() => {});
}
