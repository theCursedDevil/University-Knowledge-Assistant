"use client";

import React from "react";
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
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { PermissionDeniedState } from "@/components/SystemStates";
import { useAuth } from "@/context/AuthContext";
import { MOCK_ANALYTICS } from "@/lib/mockData";

export default function AnalyticsDashboardPage() {
  const { role } = useAuth();

  if (role !== "admin") {
    return (
      <AppShell>
        <PermissionDeniedState requiredRole="admin" />
      </AppShell>
    );
  }

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
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>FastAPI + Qdrant Node: Healthy</span>
          </div>
        </div>

        {/* Primary Metrics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {MOCK_ANALYTICS.metrics.map((m) => (
            <div
              key={m.title}
              className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xs space-y-2"
            >
              <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block">
                {m.title}
              </span>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 font-mono">
                  {m.value}
                </span>
                <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center">
                  <TrendingUp className="w-3.5 h-3.5 mr-0.5" />
                  {m.change.split(" ")[0]}
                </span>
              </div>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-snug">
                {m.description}
              </p>
            </div>
          ))}
        </div>

        {/* Two Columns: Category Demand & Confidence Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Query Demand by Category */}
          <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Search className="w-4 h-4 text-accent" />
              Most Queried Knowledge Categories
            </h3>

            <div className="space-y-3.5">
              {MOCK_ANALYTICS.popularCategories.map((cat) => (
                <div key={cat.name} className="space-y-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-zinc-800 dark:text-zinc-200">{cat.name}</span>
                    <span className="font-mono text-zinc-500">
                      {cat.queries.toLocaleString()} ({cat.percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-accent h-full rounded-full transition-all"
                      style={{ width: `${cat.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cosine Confidence Distribution */}
          <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-accent" />
              Retrieval Confidence Distribution
            </h3>

            <div className="border border-zinc-200 dark:border-zinc-800 rounded-md overflow-hidden text-xs">
              <table className="w-full text-left">
                <thead className="bg-zinc-50 dark:bg-zinc-800/40 text-[10px] uppercase font-semibold text-zinc-500 border-b border-zinc-200 dark:border-zinc-800">
                  <tr>
                    <th className="py-2.5 px-3">Cosine Score Range</th>
                    <th className="py-2.5 px-3">Category</th>
                    <th className="py-2.5 px-3 text-right">Queries</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                  {MOCK_ANALYTICS.confidenceDistribution.map((row) => (
                    <tr key={row.range} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/20">
                      <td className="py-2.5 px-3 font-mono font-medium text-zinc-800 dark:text-zinc-200">
                        {row.range}
                      </td>
                      <td className="py-2.5 px-3 text-zinc-600 dark:text-zinc-400">
                        {row.label}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-semibold text-zinc-900 dark:text-zinc-100">
                        {row.count.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-relaxed">
              Confidence scores below 0.60 trigger the standardized gating fallback to avoid hallucinations without invoking the LLM.
            </p>
          </div>
        </div>

        {/* Audit Log Stream */}
        <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Clock className="w-4 h-4 text-accent" />
              Recent System Audit Log
            </h3>
            <span className="text-[10px] font-mono text-zinc-400">PostgreSQL audit_log table</span>
          </div>

          <div className="border border-zinc-200 dark:border-zinc-800 rounded-md overflow-hidden text-xs">
            <table className="w-full text-left">
              <thead className="bg-zinc-50 dark:bg-zinc-800/40 text-[10px] uppercase font-semibold text-zinc-500 border-b border-zinc-200 dark:border-zinc-800">
                <tr>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Actor</th>
                  <th className="py-2.5 px-3">Target Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800 font-mono text-[11px]">
                {MOCK_ANALYTICS.recentAuditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/20">
                    <td className="py-2.5 px-3 text-zinc-400">{log.timestamp}</td>
                    <td className="py-2.5 px-3">
                      <span className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 font-semibold text-[10px]">
                        {log.action}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-zinc-600 dark:text-zinc-400">{log.user}</td>
                    <td className="py-2.5 px-3 text-zinc-800 dark:text-zinc-200">{log.target}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
