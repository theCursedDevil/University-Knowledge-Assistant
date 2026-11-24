"use client";

import React from "react";
import Link from "next/link";
import { AlertTriangle, ShieldAlert, SearchX, Inbox, RefreshCw, ArrowLeft } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

// S-1 Loading State
export function LoadingState({ message = "Loading university records..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center space-y-4">
      <div className="w-8 h-8 border-2 border-zinc-300 dark:border-zinc-700 border-t-accent rounded-full animate-spin" />
      <p className="text-sm text-zinc-500 dark:text-zinc-400 font-medium">{message}</p>
    </div>
  );
}

// S-2 Empty State
export function EmptyState({
  title = "No items found",
  description = "Get started by adding records or exploring other sections.",
  actionLabel,
  onAction,
  actionHref,
}: {
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  actionHref?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-zinc-200 dark:border-zinc-800 rounded-lg bg-zinc-50/50 dark:bg-zinc-900/20 my-6">
      <div className="w-12 h-12 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-400 mb-3">
        <Inbox className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">{title}</h3>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-sm mt-1 mb-5">{description}</p>
      {actionLabel && (
        actionHref ? (
          <Link
            href={actionHref}
            className="inline-flex items-center justify-center px-4 py-2 text-xs font-medium rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition"
          >
            {actionLabel}
          </Link>
        ) : (
          <button
            onClick={onAction}
            className="inline-flex items-center justify-center px-4 py-2 text-xs font-medium rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition"
          >
            {actionLabel}
          </button>
        )
      )}
    </div>
  );
}

// S-3 No Search Results
export function NoResultsState({
  query,
  onClear,
}: {
  query?: string;
  onClear?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center border border-zinc-200 dark:border-zinc-800 rounded-lg bg-white dark:bg-zinc-950 my-6">
      <div className="w-12 h-12 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-400 mb-3">
        <SearchX className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
        No matching results {query ? `for "${query}"` : ""}
      </h3>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-sm mt-1 mb-5">
        Check your spelling, try broader keywords, or clear your applied category filters.
      </p>
      {onClear && (
        <button
          onClick={onClear}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
        >
          <RefreshCw className="w-3.5 h-3.5 text-zinc-500" />
          Clear filters
        </button>
      )}
    </div>
  );
}

// S-4 Error State
export function ErrorState({
  code = "OPERATION_FAILED",
  message = "An unexpected error occurred while processing your request.",
  onRetry,
}: {
  code?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="border border-red-200 dark:border-red-950/50 bg-red-50/50 dark:bg-red-950/10 rounded-lg p-6 my-6">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 flex items-center justify-center shrink-0">
          <AlertTriangle className="w-4 h-4" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-red-900 dark:text-red-300">System Error</h4>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-400">
              {code}
            </span>
          </div>
          <p className="text-xs text-red-700 dark:text-red-400 mt-1">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-red-600 text-white hover:bg-red-700 transition"
            >
              <RefreshCw className="w-3 h-3" />
              Try Again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// S-5 Permission Denied State
export function PermissionDeniedState({
  requiredRole = "admin",
}: {
  requiredRole?: string;
}) {
  const { role, switchRole } = useAuth();

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center p-8 text-center">
      <div className="w-16 h-16 rounded-2xl bg-amber-50 dark:bg-amber-950/30 text-amber-600 dark:text-amber-500 flex items-center justify-center mb-4 border border-amber-200 dark:border-amber-900/50">
        <ShieldAlert className="w-8 h-8" />
      </div>
      <span className="text-xs font-semibold tracking-wider uppercase text-amber-600 dark:text-amber-500 mb-1">
        Access Restricted
      </span>
      <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">Permission Denied (HTTP 403)</h2>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-md mt-2 mb-6">
        This area requires <span className="font-semibold text-zinc-700 dark:text-zinc-300 capitalize">{requiredRole}</span> privileges.
        Your current role is <span className="font-semibold text-zinc-700 dark:text-zinc-300 capitalize">&quot;{role}&quot;</span>.
      </p>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Return to Dashboard
        </Link>
        {process.env.NEXT_PUBLIC_DEV_LOGIN === "true" && (
          <button
            onClick={() => switchRole("admin")}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-md bg-accent text-white hover:bg-accent-hover transition"
          >
            Switch to Admin Persona (Dev Mode)
          </button>
        )}
      </div>
    </div>
  );
}
