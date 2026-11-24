"use client";

import React from "react";
import Link from "next/link";
import {
  User,
  Mail,
  Shield,
  Calendar,
  Building2,
  GraduationCap,
  Briefcase,
  KeyRound,
  Sliders,
  CheckCircle2,
  ArrowRight,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { Role } from "@/lib/mockData";
import { formatDate } from "@/lib/utils";

export default function ProfilePage() {
  const { currentUser, role, switchRole } = useAuth();

  const roleDetails: Record<Role, { badge: string; desc: string; permissions: string[] }> = {
    student: {
      badge: "Student (Undergraduate)",
      desc: "Authorized to query university knowledge base, view citations, access document catalog, and manage personal inquiry threads.",
      permissions: [
        "Natural language Q&A with low-temperature grounding",
        "Browse all public academic ordinances & hostel bylaws",
        "Inspect verified citations and page provenance",
        "Manage personal multi-turn conversational threads",
      ],
    },
    faculty: {
      badge: "Academic Faculty",
      desc: "Authorized for advanced academic regulation lookup, syllabus inquiries, and department policy reference.",
      permissions: [
        "All Student permissions",
        "Faculty committee guidelines & appraisal bylaws access",
        "Prioritized RAG retrieval tokens quota",
        "Export chat history transcripts for academic records",
      ],
    },
    admin: {
      badge: "System Administrator",
      desc: "Full administrative access across document ingestion, metadata management, vector collection controls, and user roles.",
      permissions: [
        "All Student & Faculty permissions",
        "Multipart PDF document ingestion to MinIO S3",
        "Synchronous Qdrant vector indexing and deletion saga",
        "System-wide analytics and audit log inspection",
        "User role assignment and account status management",
      ],
    },
  };

  return (
    <AppShell>
      <div className="p-6 sm:p-8 max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <User className="w-5 h-5 text-accent" />
              <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                User Profile
              </h1>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Institutional profile retrieved via Keycloak OIDC authentication handshake
            </p>
          </div>

          <Link
            href="/preferences"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-zinc-800 dark:text-zinc-200 transition cursor-pointer self-start sm:self-auto"
          >
            <Sliders className="w-3.5 h-3.5 text-accent" />
            Edit Preferences
          </Link>
        </div>

        {/* User Card */}
        <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-100 dark:border-zinc-800/80">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-xl font-bold flex items-center justify-center shrink-0">
                {currentUser.name.charAt(0)}
              </div>
              <div>
                <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                  {currentUser.name}
                </h2>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 font-mono mt-0.5">
                  {currentUser.email}
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20">
                    {roleDetails[role].badge}
                  </span>
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    Status: {currentUser.status.toUpperCase()}
                  </span>
                </div>
              </div>
            </div>

            {/* Demo persona switching is available only in explicitly opted-in development builds. */}
            {process.env.NEXT_PUBLIC_DEV_LOGIN === "true" && (
            <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-left sm:text-right space-y-1">
              <span className="text-[10px] font-medium text-zinc-400 uppercase tracking-wider block">
                Switch Identity (Demo)
              </span>
              <div className="flex items-center gap-1">
                {(["student", "faculty", "admin"] as Role[]).map((r) => (
                  <button
                    key={r}
                    onClick={() => switchRole(r)}
                    className={`px-2 py-0.5 text-xs font-medium rounded capitalize transition ${
                      role === r
                        ? "bg-accent text-white font-semibold"
                        : "bg-white dark:bg-zinc-700 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100"
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
            )}
          </div>

          {/* Institutional Attributes */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-3.5 rounded-lg bg-zinc-50/70 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-800">
              <span className="text-[10px] uppercase font-semibold text-zinc-400 block mb-1">
                University Registration ID
              </span>
              <span className="font-mono font-semibold text-zinc-800 dark:text-zinc-200">
                {currentUser.enrollmentNo || "N/A"}
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-zinc-50/70 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-800">
              <span className="text-[10px] uppercase font-semibold text-zinc-400 block mb-1">
                Academic School / Department
              </span>
              <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                {currentUser.department || "General Enrollment"}
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-zinc-50/70 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-800">
              <span className="text-[10px] uppercase font-semibold text-zinc-400 block mb-1">
                Identity Provider (IdP)
              </span>
              <span className="font-semibold text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-accent" /> Keycloak OAuth 2.0 / OIDC Realm
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-zinc-50/70 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-800">
              <span className="text-[10px] uppercase font-semibold text-zinc-400 block mb-1">
                Account Provisioned
              </span>
              <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                {formatDate(currentUser.createdAt)}
              </span>
            </div>
          </div>

          {/* Role Capabilities & Scope */}
          <div className="space-y-3 pt-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-100">
              Role Permissions & Capabilities
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
              {roleDetails[role].desc}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
              {roleDetails[role].permissions.map((perm, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 p-2 rounded bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-800 text-xs text-zinc-700 dark:text-zinc-300"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                  <span>{perm}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
