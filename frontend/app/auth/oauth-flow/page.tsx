"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield, Key, ArrowRight, CheckCircle2, Lock, Sparkles, RefreshCw } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function OAuthFlowPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [currentStep, setCurrentStep] = useState(1);
  const [isSimulating, setIsSimulating] = useState(false);

  const steps = [
    {
      num: 1,
      title: "PKCE Code Challenge & Client Redirect",
      protocol: "GET /auth/realms/university/protocol/openid-connect/auth",
      details: "Client generates SHA-256 code verifier & code challenge with cryptographic nonce to prevent authorization code interception.",
    },
    {
      num: 2,
      title: "Keycloak Identity Verification",
      protocol: "OIDC Authentication Endpoint (Port 8080)",
      details: "Keycloak verifies university LDAP/database credentials, multi-factor authentication (MFA), and resolves user realm roles (student/faculty/admin).",
    },
    {
      num: 3,
      title: "Authorization Code Exchange",
      protocol: "POST /auth/realms/university/protocol/openid-connect/token",
      details: "Backend exchanges ephemeral authorization code along with code verifier for signed JWT Access Token and ID Token.",
    },
    {
      num: 4,
      title: "JWKS Signature Verification & Session",
      protocol: "FastAPI /auth/callback & RoleGuard",
      details: "FastAPI validates RS256 signature using Keycloak public keys (/protocol/openid-connect/certs), provisions user record, and grants authenticated session.",
    },
  ];

  const handleRunSimulation = () => {
    setIsSimulating(true);
    setCurrentStep(1);

    const timer1 = setTimeout(() => setCurrentStep(2), 700);
    const timer2 = setTimeout(() => setCurrentStep(3), 1400);
    const timer3 = setTimeout(() => setCurrentStep(4), 2100);
    const timer4 = setTimeout(() => {
      setIsSimulating(false);
      login("student@university.edu", "student");
      router.push("/dashboard");
    }, 2900);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
    };
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-zinc-50 dark:bg-zinc-950">
      <div className="w-full max-w-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-xs p-8">
        <div className="flex items-center justify-between pb-6 border-b border-zinc-200 dark:border-zinc-800 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 flex items-center justify-center">
              <Shield className="w-5 h-5 text-accent" />
            </div>
            <div>
              <h1 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                Keycloak OAuth 2.0 / OIDC Flow (W-02)
              </h1>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Authorization Code Flow with PKCE (Proof Key for Code Exchange)
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono px-2 py-1 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300">
            Phase 8 Handshake
          </span>
        </div>

        {/* Steps Timeline */}
        <div className="space-y-4 mb-8">
          {steps.map((step) => {
            const isCompleted = currentStep > step.num;
            const isCurrent = currentStep === step.num;
            return (
              <div
                key={step.num}
                className={`p-4 rounded-lg border transition ${
                  isCurrent
                    ? "border-accent bg-accent/5 dark:bg-accent/10"
                    : isCompleted
                    ? "border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/40 opacity-80"
                    : "border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/20 opacity-40"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold shrink-0 mt-0.5 ${
                      isCompleted
                        ? "bg-emerald-500 text-white"
                        : isCurrent
                        ? "bg-accent text-white"
                        : "bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400"
                    }`}
                  >
                    {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : step.num}
                  </div>

                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                        {step.title}
                      </h4>
                      <code className="text-[10px] font-mono text-zinc-400 dark:text-zinc-500 hidden sm:inline">
                        {step.protocol}
                      </code>
                    </div>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                      {step.details}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Action Controls */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
          <button
            onClick={() => router.push("/login")}
            className="text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 font-medium cursor-pointer"
          >
            ← Back to Password Login
          </button>

          <button
            onClick={handleRunSimulation}
            disabled={isSimulating}
            className="w-full sm:w-auto px-5 py-2.5 rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-xs font-semibold hover:bg-zinc-800 dark:hover:bg-zinc-200 transition flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60"
          >
            {isSimulating ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-accent" />
                <span>Simulating Handshake (Step {currentStep} of 4)...</span>
              </>
            ) : (
              <>
                <span>Complete SSO Handshake & Enter</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
