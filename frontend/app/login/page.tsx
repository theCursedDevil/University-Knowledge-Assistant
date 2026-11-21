"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sparkles, Eye, EyeOff, ShieldCheck, ArrowRight, Lock, Mail } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Role } from "@/lib/mockData";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState("student@university.edu");
  const [password, setPassword] = useState("password123");
  const [selectedRole, setSelectedRole] = useState<Role>("student");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes("@")) {
      setError("Please provide a valid university email address.");
      return;
    }
    setError(null);
    setIsLoading(true);

    setTimeout(() => {
      login(email, selectedRole);
      setIsLoading(false);
      router.push("/dashboard");
    }, 400);
  };

  const handleOAuthLogin = () => {
    router.push("/auth/oauth-flow");
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

        {/* Credentials Form (W-01) */}
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

        {/* Divider */}
        <div className="relative my-6 text-center">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-zinc-200 dark:border-zinc-800" />
          </div>
          <span className="relative px-3 text-[11px] uppercase tracking-wider bg-white dark:bg-zinc-900 text-zinc-400">
            or Institutional SSO
          </span>
        </div>

        {/* Keycloak OAuth SSO Button (W-01 / W-02) */}
        <button
          type="button"
          onClick={handleOAuthLogin}
          className="w-full py-2.5 px-4 rounded-md border border-zinc-200 dark:border-zinc-700 bg-zinc-50/50 dark:bg-zinc-800/50 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-semibold text-zinc-800 dark:text-zinc-200 transition flex items-center justify-center gap-2 cursor-pointer"
        >
          <ShieldCheck className="w-4 h-4 text-accent" />
          Sign In with University SSO (Keycloak OIDC)
        </button>

        {/* Footer Link to Sign Up (W-14) */}
        <p className="text-center text-xs text-zinc-500 dark:text-zinc-400 mt-6">
          Don&apos;t have an account yet?{" "}
          <Link href="/signup" className="font-semibold text-accent hover:underline">
            Create an Account (W-14)
          </Link>
        </p>
      </div>
    </div>
  );
}
