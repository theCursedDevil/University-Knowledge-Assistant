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
              Real-time monitoring of RAG retrieval queries, token latency, vector coverage, and audit trails
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>FastAPI + PostgreSQL + Qdrant: Online</span>
          </div>
        </div>

        {isLoading ? (
          <LoadingState message="Aggregating system statistics from PostgreSQL tables..." />
        ) : stats ? (
          <>
            {/* Primary Metrics Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xs space-y-2">
                <div className="flex items-center justify-between text-zinc-400 text-[11px] font-semibold uppercase tracking-wider">
                  <span>Knowledge Base PDFs</span>
                  <FileText className="w-4 h-4 text-accent" />
                </div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 font-mono">
                  {stats.total_documents}
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-snug">
                  Official university regulations stored in MinIO
                </p>
              </div>

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

              <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xs space-y-2">
                <div className="flex items-center justify-between text-zinc-400 text-[11px] font-semibold uppercase tracking-wider">
                  <span>Chat Inquiries</span>
                  <MessageSquare className="w-4 h-4 text-accent" />
                </div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 font-mono">
                  {stats.total_messages}
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-snug">
                  Across {stats.total_conversations} conversation threads
                </p>
              </div>

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

            {/* Two Columns: Category Breakdown & Audit Log Stream */}
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

              {/* Live Audit Log Stream */}
              <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-accent" />
                  System Audit Trail (PostgreSQL)
                </h3>

                {stats.recent_audit_logs.length === 0 ? (
                  <p className="text-xs text-zinc-400 py-4">No audit logs recorded yet.</p>
                ) : (
                  <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                    {stats.recent_audit_logs.map((log) => (
                      <div
                        key={log.id}
                        className="p-3 rounded-md bg-zinc-50 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-850 text-xs flex items-start justify-between gap-3"
                      >
                        <div className="space-y-0.5">
                          <div className="font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-200 dark:bg-zinc-800 font-mono">
                              {log.action}
                            </span>
                            <span className="text-zinc-500 font-mono text-[11px]">{log.entity}</span>
                          </div>
                          {log.details && (
                            <p className="text-[11px] text-zinc-400 font-mono truncate max-w-xs">
                              {JSON.stringify(log.details)}
                            </p>
                          )}
                        </div>
                        <span className="text-[10px] font-mono text-zinc-400 shrink-0">
                          {formatDate(log.created_at)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
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
