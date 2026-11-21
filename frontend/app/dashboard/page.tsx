"use client";

import React from "react";
import Link from "next/link";
import {
  MessageSquare,
  FileText,
  Quote,
  UploadCloud,
  ArrowRight,
  Sparkles,
  Clock,
  Layers,
  ChevronRight,
  Shield,
  GraduationCap,
  Briefcase,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { MOCK_DOCUMENTS, MOCK_CONVERSATIONS, MOCK_ANALYTICS, Role } from "@/lib/mockData";
import { formatDate } from "@/lib/utils";

export default function DashboardPage() {
  const { currentUser, role } = useAuth();

  const roleBadgeStyles: Record<Role, { label: string; icon: React.ReactNode; style: string }> = {
    student: {
      label: "Enrolled Student",
      icon: <GraduationCap className="w-3.5 h-3.5" />,
      style: "bg-orange-50 text-orange-700 dark:bg-orange-950/40 dark:text-orange-400 border-orange-200 dark:border-orange-800",
    },
    faculty: {
      label: "Academic Faculty",
      icon: <Briefcase className="w-3.5 h-3.5" />,
      style: "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400 border-blue-200 dark:border-blue-800",
    },
    admin: {
      label: "System Administrator",
      icon: <Shield className="w-3.5 h-3.5" />,
      style: "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400 border-red-200 dark:border-red-800",
    },
  };

  return (
    <AppShell>
      <div className="p-6 sm:p-8 max-w-6xl mx-auto space-y-8">
        {/* Welcome Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span
                className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full border ${roleBadgeStyles[role].style}`}
              >
                {roleBadgeStyles[role].icon}
                {roleBadgeStyles[role].label}
              </span>
              {currentUser.enrollmentNo && (
                <span className="text-xs font-mono text-zinc-400 dark:text-zinc-500">
                  {currentUser.enrollmentNo}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
              Welcome back, {currentUser.name}
            </h1>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
              Ask questions on university regulations, syllabi, exam rules, or browse indexed institutional documents.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/chat"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-md bg-accent text-white hover:bg-accent-hover transition shadow-xs cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              New Chat Inquiry
            </Link>
          </div>
        </div>

        {/* Quick Action Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            href="/chat"
            className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-accent dark:hover:border-accent transition group"
          >
            <div className="w-9 h-9 rounded-md bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-900 dark:text-zinc-100 mb-3 group-hover:bg-accent/10 group-hover:text-accent transition">
              <MessageSquare className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center justify-between">
              Chat Assistant
              <ArrowRight className="w-3.5 h-3.5 text-zinc-400 group-hover:text-accent group-hover:translate-x-0.5 transition" />
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
              Ask natural-language questions with verified citations from official records.
            </p>
          </Link>

          <Link
            href="/documents"
            className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-accent dark:hover:border-accent transition group"
          >
            <div className="w-9 h-9 rounded-md bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-900 dark:text-zinc-100 mb-3 group-hover:bg-accent/10 group-hover:text-accent transition">
              <FileText className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center justify-between">
              Document Catalog
              <ArrowRight className="w-3.5 h-3.5 text-zinc-400 group-hover:text-accent group-hover:translate-x-0.5 transition" />
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
              Browse 68+ academic circulars, hostel rules, bylaws, and timetables.
            </p>
          </Link>

          <Link
            href="/citations"
            className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-accent dark:hover:border-accent transition group"
          >
            <div className="w-9 h-9 rounded-md bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-900 dark:text-zinc-100 mb-3 group-hover:bg-accent/10 group-hover:text-accent transition">
              <Quote className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center justify-between">
              Source Citations
              <ArrowRight className="w-3.5 h-3.5 text-zinc-400 group-hover:text-accent group-hover:translate-x-0.5 transition" />
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
              Inspect grounded page provenances and excerpt references.
            </p>
          </Link>

          {role === "admin" ? (
            <Link
              href="/admin/upload"
              className="p-5 rounded-lg border border-accent/40 bg-accent/5 dark:bg-accent/10 hover:border-accent transition group"
            >
              <div className="w-9 h-9 rounded-md bg-accent text-white flex items-center justify-center mb-3">
                <UploadCloud className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center justify-between">
                Upload New Document
                <ArrowRight className="w-3.5 h-3.5 text-accent group-hover:translate-x-0.5 transition" />
              </h3>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
                Ingest PDF files directly to MinIO and index into Qdrant vector store.
              </p>
            </Link>
          ) : (
            <Link
              href="/conversations"
              className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-accent dark:hover:border-accent transition group"
            >
              <div className="w-9 h-9 rounded-md bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-900 dark:text-zinc-100 mb-3 group-hover:bg-accent/10 group-hover:text-accent transition">
                <Clock className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center justify-between">
                Past Conversations
                <ArrowRight className="w-3.5 h-3.5 text-zinc-400 group-hover:text-accent group-hover:translate-x-0.5 transition" />
              </h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                Access your archived threads, search past queries, and resume chat.
              </p>
            </Link>
          )}
        </div>

        {/* System Metrics Banner (W-03) */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 p-4 rounded-lg bg-zinc-50 dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800">
          {MOCK_ANALYTICS.metrics.map((m) => (
            <div key={m.title} className="p-2">
              <span className="text-[11px] text-zinc-500 dark:text-zinc-400 block">{m.title}</span>
              <span className="text-xl font-bold text-zinc-900 dark:text-zinc-100 mt-0.5 block">
                {m.value}
              </span>
              <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                {m.change}
              </span>
            </div>
          ))}
        </div>

        {/* Two Columns: Recent Conversations + Recently Added Documents */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Conversations */}
          <div className="border border-zinc-200 dark:border-zinc-800 rounded-lg p-5 bg-white dark:bg-zinc-900">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-accent" />
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                  Recent Conversations (W-06)
                </h3>
              </div>
              <Link href="/conversations" className="text-xs text-accent hover:underline flex items-center gap-1 font-medium">
                View all <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="space-y-2">
              {MOCK_CONVERSATIONS.slice(0, 3).map((conv) => (
                <Link
                  key={conv.id}
                  href={`/chat?id=${conv.id}`}
                  className="flex items-center justify-between p-3 rounded-md hover:bg-zinc-50 dark:hover:bg-zinc-800/60 border border-transparent hover:border-zinc-200 dark:hover:border-zinc-700 transition"
                >
                  <div className="min-w-0 pr-3">
                    <h4 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                      {conv.title}
                    </h4>
                    <span className="text-[10px] text-zinc-400 mt-0.5 block">
                      Updated {formatDate(conv.updatedAt)} · {conv.messageCount} messages
                    </span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                </Link>
              ))}
            </div>
          </div>

          {/* Recently Added Documents */}
          <div className="border border-zinc-200 dark:border-zinc-800 rounded-lg p-5 bg-white dark:bg-zinc-900">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-accent" />
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                  Indexed University Documents (W-07)
                </h3>
              </div>
              <Link href="/documents" className="text-xs text-accent hover:underline flex items-center gap-1 font-medium">
                Browse all <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="space-y-2">
              {MOCK_DOCUMENTS.slice(0, 3).map((doc) => (
                <Link
                  key={doc.id}
                  href={`/documents/${doc.id}`}
                  className="flex items-center justify-between p-3 rounded-md hover:bg-zinc-50 dark:hover:bg-zinc-800/60 border border-transparent hover:border-zinc-200 dark:hover:border-zinc-700 transition"
                >
                  <div className="min-w-0 pr-3">
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                        {doc.category}
                      </span>
                      <h4 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                        {doc.title}
                      </h4>
                    </div>
                    <span className="text-[10px] text-zinc-400 mt-1 block">
                      {doc.pageCount} pages · {doc.chunkCount} chunks indexed · v{doc.version}
                    </span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
