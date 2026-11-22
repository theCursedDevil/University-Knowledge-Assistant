/**
 * PKCE (Proof Key for Code Exchange) Utilities for OAuth 2.0 / OpenID Connect.
 * Implements RFC 7636 using native Web Crypto API (SubtleCrypto).
 */

/**
 * Generates a cryptographically random code verifier string (43 to 128 characters).
 */
export function generateCodeVerifier(length: number = 64): string {
  const charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
  const randomValues = new Uint8Array(length);
  window.crypto.getRandomValues(randomValues);
  let verifier = "";
  for (let i = 0; i < length; i++) {
    verifier += charset[randomValues[i] % charset.length];
  }
  return verifier;
}

/**
 * Computes the SHA-256 base64url-encoded code challenge from a code verifier.
 */
export async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await window.crypto.subtle.digest("SHA-256", data);

  // Convert ArrayBuffer to binary string
  const bytes = new Uint8Array(digest);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }

  // Base64URL encode (URL-safe, no padding)
  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

/**
 * Generates a cryptographically random state string for CSRF mitigation.
 */
export function generateState(length: number = 32): string {
  const randomValues = new Uint8Array(length);
  window.crypto.getRandomValues(randomValues);
  return Array.from(randomValues, (byte) => byte.toString(16).padStart(2, "0")).join("");
}
