"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ShieldCheck, AlertCircle, Loader2, ArrowRight } from "lucide-react";
import Link from "next/link";
import { exchangeAuthCode } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { loadUserFromBackend } = useAuth();

  const [status, setStatus] = useState<"processing" | "success" | "error">("processing");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    async function processOAuthCallback() {
      const code = searchParams.get("code");
      const state = searchParams.get("state");
      const error = searchParams.get("error");
      const errorDescription = searchParams.get("error_description");

      if (error) {
        setStatus("error");
        setErrorMessage(errorDescription || `Authentication failed: ${error}`);
        return;
      }

      if (!code) {
        setStatus("error");
        setErrorMessage("No authorization code received from Keycloak.");
        return;
      }

      // Verify CSRF state token
      const savedState = sessionStorage.getItem("uka_pkce_state");
      if (savedState && state && savedState !== state) {
        setStatus("error");
        setErrorMessage("Security verification failed: OAuth state mismatch (potential CSRF).");
        return;
      }

      // Retrieve PKCE code verifier
      const codeVerifier = sessionStorage.getItem("uka_pkce_verifier");
      if (!codeVerifier) {
        setStatus("error");
        setErrorMessage("Missing PKCE code verifier. Please initiate login again.");
        return;
      }

      try {
        const redirectUri = `${window.location.origin}/auth/callback`;
        const result = await exchangeAuthCode(code, codeVerifier, redirectUri);

        // Clean up ephemeral PKCE parameters from sessionStorage
        sessionStorage.removeItem("uka_pkce_verifier");
        sessionStorage.removeItem("uka_pkce_state");

        setStatus("success");
        // Reload user session from backend /me
        await loadUserFromBackend(result.user.role as any, result.user.email);
        router.push("/dashboard");
      } catch (err: any) {
        setStatus("error");
        setErrorMessage(err.message || "Failed to complete token exchange with Keycloak.");
      }
    }

    processOAuthCallback();
  }, [searchParams, router, loadUserFromBackend]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-zinc-50 dark:bg-zinc-950">
      <div className="w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-xs p-8 text-center">
        {status === "processing" && (
          <div className="flex flex-col items-center">
            <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center text-accent mb-4">
              <Loader2 className="w-6 h-6 animate-spin text-accent" />
            </div>
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
              Authenticating with Keycloak
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2">
              Exchanging authorization code and verifying RS256 PKCE credentials...
            </p>
          </div>
        )}

        {status === "success" && (
          <div className="flex flex-col items-center">
            <div className="w-12 h-12 rounded-full bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-4">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
              Authentication Successful
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2">
              Session initialized. Redirecting to your dashboard...
            </p>
          </div>
        )}

        {status === "error" && (
          <div className="flex flex-col items-center">
            <div className="w-12 h-12 rounded-full bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 flex items-center justify-center mb-4">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
              Authentication Failed
            </h2>
            <p className="text-xs text-red-600 dark:text-red-400 mt-2 mb-6 text-left p-3 rounded-md bg-red-50/50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/40">
              {errorMessage}
            </p>
            <Link
              href="/login"
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 transition"
            >
              Return to Login
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center p-4 bg-zinc-50 dark:bg-zinc-950">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
