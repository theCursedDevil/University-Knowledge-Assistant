"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  History,
  Search,
  MessageSquare,
  Trash2,
  Calendar,
  ChevronRight,
  Plus,
  AlertCircle,
  X,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { EmptyState, NoResultsState, LoadingState } from "@/components/SystemStates";
import { fetchConversations, deleteConversation, ApiConversationSummary } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useAuth } from "@/context/AuthContext";

export default function ConversationsPage() {
  const { currentUser } = useAuth();
  const [threads, setThreads] = useState<ApiConversationSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [threadToDelete, setThreadToDelete] = useState<ApiConversationSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const loadThreads = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetchConversations();
      setThreads(data);
    } catch {
      setThreads([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadThreads();
  }, [loadThreads, currentUser.id]);

  const filteredThreads = threads.filter((t) =>
    t.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDelete = async (id: string) => {
    try {
      await deleteConversation(id);
      setThreads((prev) => prev.filter((t) => t.id !== id));
      setThreadToDelete(null);
      setDeleteError(null);
    } catch (err: any) {
      setDeleteError(err.message || "Failed to delete conversation.");
    }
  };

  return (
    <AppShell>
      <div className="p-6 sm:p-8 max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <History className="w-5 h-5 text-accent" />
              <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Conversation History
              </h1>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Browse, resume, or manage past inquiry threads and AI responses
            </p>
          </div>

          <Link
            href="/chat"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition shadow-xs self-start sm:self-auto cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            Start New Thread
          </Link>
        </div>

        {deleteError && (
          <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-xs text-red-700 dark:text-red-400 flex items-center justify-between">
            <span>{deleteError}</span>
            <button onClick={() => setDeleteError(null)}>
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Search Filter */}
        <div className="relative">
          <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations by title or topic..."
            className="w-full pl-9 pr-4 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-1 focus:ring-accent"
          />
        </div>

        {/* Thread List */}
        {isLoading ? (
          <LoadingState message="Loading your conversation threads..." />
        ) : threads.length === 0 ? (
          <EmptyState
            title="No past conversations"
            description="You haven't initiated any inquiry threads yet. Start a conversation with the university assistant."
            actionLabel="Start First Thread"
            actionHref="/chat"
          />
        ) : filteredThreads.length === 0 ? (
          <NoResultsState query={searchQuery} onClear={() => setSearchQuery("")} />
        ) : (
          <div className="divide-y divide-zinc-200 dark:divide-zinc-800 border border-zinc-200 dark:border-zinc-800 rounded-lg bg-white dark:bg-zinc-900 overflow-hidden">
            {filteredThreads.map((thread) => (
              <div
                key={thread.id}
                className="flex items-center justify-between p-4 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition group"
              >
                <Link
                  href="/chat"
                  className="flex-1 flex items-start gap-3 min-w-0 pr-4"
                >
                  <div className="w-8 h-8 rounded-md bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-500 shrink-0 mt-0.5 group-hover:text-accent group-hover:bg-accent/10 transition">
                    <MessageSquare className="w-4 h-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 truncate group-hover:text-accent transition">
                      {thread.title}
                    </h3>
                    <div className="flex items-center gap-3 text-[11px] text-zinc-400 mt-1">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {formatDate(thread.updated_at)}
                      </span>
                      <span>Thread ID: {thread.id.slice(0, 8)}</span>
                    </div>
                  </div>
                </Link>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setThreadToDelete(thread)}
                    className="p-1.5 rounded text-zinc-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition cursor-pointer"
                    title="Delete thread"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <Link
                    href="/chat"
                    className="p-1.5 rounded text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {threadToDelete && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg max-w-sm w-full p-5 space-y-4 shadow-xl animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-red-100 dark:bg-red-950/40 text-red-600 flex items-center justify-center shrink-0">
                  <AlertCircle className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                    Delete Conversation Thread
                  </h4>
                  <p className="text-xs text-zinc-500 mt-1">
                    Are you sure you want to permanently delete &quot;{threadToDelete.title}&quot;?
                    This action cannot be undone.
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setThreadToDelete(null)}
                  className="px-3 py-1.5 text-xs font-medium rounded-md border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition text-zinc-700 dark:text-zinc-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(threadToDelete.id)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-md bg-red-600 text-white hover:bg-red-700 transition cursor-pointer"
                >
                  Delete Permanently
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
