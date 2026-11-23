"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sparkles, Eye, EyeOff, ShieldCheck, ArrowRight, Lock, Mail, ExternalLink, KeyRound } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Role } from "@/lib/mockData";
import { fetchKeycloakConfig } from "@/lib/api";
import { generateCodeVerifier, generateCodeChallenge, generateState } from "@/lib/pkce";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState("student@university.edu");
  const [password, setPassword] = useState("password123");
  const [selectedRole, setSelectedRole] = useState<Role>("student");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isKeycloakLoading, setIsKeycloakLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes("@")) {
      setError("Please provide a valid university email address.");
      return;
    }
    setError(null);
    setIsLoading(true);

    try {
      await login(email, selectedRole);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Login failed. Please check credentials.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeycloakLogin = async (idpHint?: string) => {
    setError(null);
    setIsKeycloakLoading(true);
    try {
      // 1. Fetch Keycloak public configuration
      let config = {
        keycloak_url: process.env.NEXT_PUBLIC_KEYCLOAK_URL || "http://localhost:8080",
        realm: process.env.NEXT_PUBLIC_KEYCLOAK_REALM || "university-realm",
        client_id: process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID || "university-assistant-client",
      };

      try {
        const liveConfig = await fetchKeycloakConfig();
        if (liveConfig?.keycloak_url) {
          // Guard against internal Docker hostname leaking to browser
          if (liveConfig.keycloak_url.includes("://keycloak:")) {
            liveConfig.keycloak_url = liveConfig.keycloak_url.replace("://keycloak:", "://localhost:");
          }
          config = liveConfig;
        }
      } catch {
        // Fall back to default environment variables if backend endpoint unreachable
      }

      // 2. Generate PKCE code verifier and code challenge
      const verifier = generateCodeVerifier(64);
      const challenge = await generateCodeChallenge(verifier);
      const state = generateState(32);

      // 3. Store verifier and CSRF state in sessionStorage (ephemeral, cleared upon token exchange)
      sessionStorage.setItem("uka_pkce_verifier", verifier);
      sessionStorage.setItem("uka_pkce_state", state);

      // 4. Redirect to Keycloak OpenID Connect Authorization endpoint
      const redirectUri = `${window.location.origin}/auth/callback`;
      let authUrl = `${config.keycloak_url}/realms/${config.realm}/protocol/openid-connect/auth?client_id=${encodeURIComponent(
        config.client_id
      )}&response_type=code&scope=openid%20profile%20email&redirect_uri=${encodeURIComponent(
        redirectUri
      )}&code_challenge=${encodeURIComponent(challenge)}&code_challenge_method=S256&state=${encodeURIComponent(
        state
      )}`;

      if (idpHint) {
        authUrl += `&kc_idp_hint=${encodeURIComponent(idpHint)}`;
      }

      window.location.href = authUrl;
    } catch (err: any) {
      setError(err.message || "Failed to initiate Keycloak OAuth redirection.");
      setIsKeycloakLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-zinc-50 dark:bg-zinc-950">
      <div className="w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-xs p-8">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center mb-8">
          <div className="w-10 h-10 rounded-lg bg-zinc-900 dark:bg-zinc-100 flex items-center justify-center text-white dark:text-zinc-900 mb-3 shadow-xs">
            <Sparkles className="w-5 h-5 text-accent" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
            Sign In to University Knowledge Assistant
          </h1>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
            Access regulations, academic guidelines, syllabus & ordinances
          </p>
        </div>

        {error && (
          <div className="mb-5 p-3 rounded-md bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 text-xs text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {/* Primary Action: Google Sign-in & Keycloak SSO */}
        <div className="space-y-2.5 mb-6">
          {/* Sign In with Google */}
          <button
            type="button"
            onClick={() => handleKeycloakLogin("google")}
            disabled={isKeycloakLoading}
            className="w-full py-2.5 px-4 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-700/60 text-zinc-800 dark:text-zinc-100 text-xs font-semibold shadow-xs transition flex items-center justify-center gap-2.5 cursor-pointer disabled:opacity-60"
          >
            <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            Sign in with Google
          </button>

          {/* Keycloak University SSO */}
          <button
            type="button"
            onClick={() => handleKeycloakLogin()}
            disabled={isKeycloakLoading}
            className="w-full py-2.5 px-4 rounded-lg bg-accent hover:bg-accent/90 text-white text-xs font-semibold shadow-xs transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60"
          >
            {isKeycloakLoading ? (
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                Sign In with University SSO
              </>
            )}
          </button>
        </div>

        {/* Divider */}
        <div className="relative my-6 text-center">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-zinc-200 dark:border-zinc-800" />
          </div>
          <span className="relative px-3 text-[11px] uppercase tracking-wider bg-white dark:bg-zinc-900 text-zinc-400">
            or sign in with email
          </span>
        </div>

        {/* Credentials Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
              University Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5 pointer-events-none" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="student@university.edu"
                className="w-full pl-9 pr-3 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-1 focus:ring-accent focus:border-accent"
                required
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                Password
              </label>
              <Link
                href="/forgot-password"
                className="text-[11px] text-accent hover:underline"
              >
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <Lock className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5 pointer-events-none" />
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-9 pr-9 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-1 focus:ring-accent focus:border-accent"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-2.5 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
                aria-label="Toggle password visibility"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Persona selector for quick demo testing */}
          <div className="pt-1">
            <span className="block text-[11px] text-zinc-500 dark:text-zinc-400 mb-1 font-medium">
              Demo Persona Role:
            </span>
            <div className="grid grid-cols-3 gap-2">
              {(["student", "faculty", "admin"] as Role[]).map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => {
                    setSelectedRole(r);
                    setEmail(`${r}@university.edu`);
                  }}
                  className={`py-1.5 px-2 text-xs font-medium rounded capitalize border transition ${
                    selectedRole === r
                      ? "border-accent bg-accent/10 text-accent font-semibold"
                      : "border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800"
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 px-4 rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-xs font-semibold hover:bg-zinc-800 dark:hover:bg-zinc-200 transition flex items-center justify-center gap-1.5 disabled:opacity-60 cursor-pointer"
          >
            {isLoading ? (
              <span className="w-4 h-4 border-2 border-zinc-300 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                Sign In With Password
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </form>

        {/* Footer Link to Sign Up (W-14) */}
        <p className="text-center text-xs text-zinc-500 dark:text-zinc-400 mt-6">
          Don&apos;t have an account yet?{" "}
          <Link href="/signup" className="font-semibold text-accent hover:underline">
            Create an Account
          </Link>
        </p>
      </div>
    </div>
  );
}
