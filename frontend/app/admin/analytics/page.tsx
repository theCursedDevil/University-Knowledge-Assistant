"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  BarChart3,
  TrendingUp,
  ShieldAlert,
  Database,
  Search,
  Clock,
  Layers,
  ArrowUpRight,
  ShieldCheck,
  FileText,
  MessageSquare,
  Users,
  Activity,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Filter,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { PermissionDeniedState, LoadingState } from "@/components/SystemStates";
import { useAuth } from "@/context/AuthContext";
import { fetchAdminStats, ApiAdminStats } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function AnalyticsDashboardPage() {
  const { role } = useAuth();
  const [stats, setStats] = useState<ApiAdminStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [auditFilter, setAuditFilter] = useState<string>("ALL");

  const loadStats = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetchAdminStats();
      setStats(data);
    } catch {
      setStats(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (role === "admin") {
      loadStats();
    }
  }, [role, loadStats]);

  if (role !== "admin") {
    return (
      <AppShell>
        <PermissionDeniedState requiredRole="admin" />
      </AppShell>
    );
  }

  const categoryEntries = stats?.documents_by_category ? Object.entries(stats.documents_by_category) : [];
  const totalCategoryDocs = categoryEntries.reduce((acc, [, count]) => acc + count, 0) || 1;

  const statusEntries = stats?.documents_by_status ? Object.entries(stats.documents_by_status) : [];
  const totalStatusDocs = stats?.total_documents || 1;

  const filteredAuditLogs = stats?.recent_audit_logs.filter((log) => {
    if (auditFilter === "ALL") return true;
    return log.action.toUpperCase() === auditFilter.toUpperCase();
  }) || [];

  return (
    <AppShell>
      <div className="p-6 sm:p-8 max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <BarChart3 className="w-5 h-5 text-accent" />
              <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Admin: Analytics & System Health (W-13)
              </h1>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Live monitoring of ingestion pipeline status, vector index coverage, user inquiries, and audit trails
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => loadStats()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-200 transition-colors"
            >
              <Activity className="w-3.5 h-3.5 text-accent" />
              Refresh
            </button>
            <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>FastAPI Backend Online</span>
            </div>
          </div>
        </div>

        {isLoading ? (
          <LoadingState message="Aggregating system statistics from PostgreSQL tables..." />
        ) : stats ? (
          <>
            {/* Primary Metrics Grid (8 KPI cards) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Total Documents */}
              <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xs space-y-2">
                <div className="flex items-center justify-between text-zinc-400 text-[11px] font-semibold uppercase tracking-wider">
                  <span>Total Uploaded</span>
                  <FileText className="w-4 h-4 text-accent" />
                </div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 font-mono">
                  {stats.total_documents}
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-snug">
                  Knowledge PDFs stored in MinIO object storage
                </p>
              </div>

              {/* Successfully Processed */}
              <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xs space-y-2">
                <div className="flex items-center justify-between text-zinc-400 text-[11px] font-semibold uppercase tracking-wider">
                  <span>Processed (&apos;ready&apos;)</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                </div>
                <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                  {stats.processed_documents ?? (stats.documents_by_status?.ready || 0)}
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-snug">
                  Vectorized and available for RAG retrieval
                </p>
              </div>

              {/* Failed Ingestions */}
              <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xs space-y-2">
                <div className="flex items-center justify-between text-zinc-400 text-[11px] font-semibold uppercase tracking-wider">
                  <span>Failed Documents</span>
                  <AlertCircle className="w-4 h-4 text-red-500" />
                </div>
                <div className="text-2xl font-bold text-red-600 dark:text-red-400 font-mono">
                  {stats.failed_documents ?? (stats.documents_by_status?.failed || 0)}
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-snug">
                  Ingestion or parsing failures flagged
                </p>
              </div>

              {/* Vector Chunks */}
              <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xs space-y-2">
                <div className="flex items-center justify-between text-zinc-400 text-[11px] font-semibold uppercase tracking-wider">
                  <span>Vector Chunks</span>
                  <Layers className="w-4 h-4 text-accent" />
                </div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 font-mono">
                  {stats.total_chunks}
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-snug">
                  Indexed with all-MiniLM-L6-v2 in Qdrant
                </p>
              </div>

              {/* Total Conversations */}
              <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xs space-y-2">
                <div className="flex items-center justify-between text-zinc-400 text-[11px] font-semibold uppercase tracking-wider">
                  <span>Conversations</span>
                  <MessageSquare className="w-4 h-4 text-accent" />
                </div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 font-mono">
                  {stats.total_conversations}
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-snug">
                  Multi-turn dialogue sessions created
                </p>
              </div>

              {/* User Questions */}
              <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xs space-y-2">
                <div className="flex items-center justify-between text-zinc-400 text-[11px] font-semibold uppercase tracking-wider">
                  <span>Questions Asked</span>
                  <HelpCircle className="w-4 h-4 text-accent" />
                </div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 font-mono">
                  {stats.total_questions || Math.ceil(stats.total_messages / 2)}
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-snug">
                  User queries routed through RAG pipeline
                </p>
              </div>

              {/* Total Messages */}
              <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xs space-y-2">
                <div className="flex items-center justify-between text-zinc-400 text-[11px] font-semibold uppercase tracking-wider">
                  <span>Total Messages</span>
                  <Activity className="w-4 h-4 text-accent" />
                </div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 font-mono">
                  {stats.total_messages}
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-snug">
                  Persisted user and assistant chat turns
                </p>
              </div>

              {/* Registered Users */}
              <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xs space-y-2">
                <div className="flex items-center justify-between text-zinc-400 text-[11px] font-semibold uppercase tracking-wider">
                  <span>Registered Users</span>
                  <Users className="w-4 h-4 text-accent" />
                </div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 font-mono">
                  {stats.total_users}
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-snug">
                  Enrolled under Student, Faculty, & Admin RBAC
                </p>
              </div>
            </div>

            {/* Two Columns: Category Breakdown & Ingestion Status */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Category Breakdown */}
              <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                  <Search className="w-4 h-4 text-accent" />
                  Knowledge Category Distribution
                </h3>

                {categoryEntries.length === 0 ? (
                  <p className="text-xs text-zinc-400 py-4">No categories recorded yet.</p>
                ) : (
                  <div className="space-y-3.5">
                    {categoryEntries.map(([catName, count]) => {
                      const pct = Math.round((count / totalCategoryDocs) * 100);
                      return (
                        <div key={catName} className="space-y-1.5">
                          <div className="flex justify-between text-xs">
                            <span className="font-medium text-zinc-800 dark:text-zinc-200">{catName}</span>
                            <span className="font-mono text-zinc-500">
                              {count} docs ({pct}%)
                            </span>
                          </div>
                          <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-2 rounded-full overflow-hidden">
                            <div
                              className="bg-accent h-full rounded-full transition-all duration-300"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Document Status Breakdown */}
              <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-accent" />
                  Ingestion Pipeline Status Breakdown
                </h3>

                {statusEntries.length === 0 ? (
                  <p className="text-xs text-zinc-400 py-4">No document status data available.</p>
                ) : (
                  <div className="space-y-3.5">
                    {statusEntries.map(([stName, count]) => {
                      const pct = Math.round((count / totalStatusDocs) * 100);
                      const isReady = stName === "ready";
                      const isFailed = stName === "failed";
                      const barColor = isReady
                        ? "bg-emerald-500"
                        : isFailed
                        ? "bg-red-500"
                        : "bg-amber-500";

                      return (
                        <div key={stName} className="space-y-1.5">
                          <div className="flex justify-between text-xs">
                            <span className="font-medium capitalize text-zinc-800 dark:text-zinc-200">
                              {stName}
                            </span>
                            <span className="font-mono text-zinc-500">
                              {count} docs ({pct}%)
                            </span>
                          </div>
                          <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-2 rounded-full overflow-hidden">
                            <div
                              className={`${barColor} h-full rounded-full transition-all duration-300`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Live Audit Log Stream with Filter Controls */}
            <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-accent" />
                  System Audit Trail (PostgreSQL audit_log)
                </h3>

                {/* Filter buttons */}
                <div className="flex flex-wrap items-center gap-1.5 text-xs">
                  {["ALL", "DOCUMENT_UPLOAD", "DOCUMENT_PROCESSED", "DOCUMENT_DELETE", "DOCUMENT_METADATA_UPDATE", "USER_ROLE_UPDATE"].map(
                    (filterVal) => (
                      <button
                        key={filterVal}
                        onClick={() => setAuditFilter(filterVal)}
                        className={`px-2.5 py-1 rounded text-[11px] font-mono transition-colors ${
                          auditFilter === filterVal
                            ? "bg-accent text-white font-semibold"
                            : "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700"
                        }`}
                      >
                        {filterVal === "ALL" ? "All Events" : filterVal.replace(/_/g, " ")}
                      </button>
                    )
                  )}
                </div>
              </div>

              {filteredAuditLogs.length === 0 ? (
                <p className="text-xs text-zinc-400 py-6 text-center">
                  No audit logs matching filter &apos;{auditFilter}&apos;.
                </p>
              ) : (
                <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1 divide-y divide-zinc-100 dark:divide-zinc-800">
                  {filteredAuditLogs.map((log) => (
                    <div
                      key={log.id}
                      className="pt-2.5 first:pt-0 pb-1 text-xs flex items-start justify-between gap-3"
                    >
                      <div className="space-y-1">
                        <div className="font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-medium ${
                              log.action.includes("DELETE")
                                ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
                                : log.action.includes("UPLOAD") || log.action.includes("PROCESSED")
                                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                                : "bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300"
                            }`}
                          >
                            {log.action}
                          </span>
                          <span className="text-zinc-500 font-mono text-[11px]">
                            entity: {log.entity}
                          </span>
                          {log.entity_id && (
                            <span className="text-zinc-400 font-mono text-[10px] truncate max-w-40">
                              id: {log.entity_id}
                            </span>
                          )}
                        </div>
                        {log.details && (
                          <div className="text-[11px] text-zinc-500 font-mono bg-zinc-50 dark:bg-zinc-950 p-2 rounded border border-zinc-100 dark:border-zinc-800">
                            {Object.entries(log.details).map(([k, v]) => (
                              <span key={k} className="mr-3 inline-block">
                                <strong className="text-zinc-700 dark:text-zinc-300">{k}:</strong>{" "}
                                {typeof v === "object" ? JSON.stringify(v) : String(v)}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <span className="text-[10px] font-mono text-zinc-400 shrink-0 whitespace-nowrap">
                        {formatDate(log.created_at)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="p-8 text-center text-zinc-400 text-xs">
            Unable to connect to FastAPI analytics service. Verify backend is running on port 8000.
          </div>
        )}
      </div>
    </AppShell>
  );
}
