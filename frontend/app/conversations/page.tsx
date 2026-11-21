"use client";

import React, { useState } from "react";
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
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { EmptyState, NoResultsState } from "@/components/SystemStates";
import { MOCK_CONVERSATIONS, ConversationThread } from "@/lib/mockData";
import { formatDate } from "@/lib/utils";

export default function ConversationsPage() {
  const [threads, setThreads] = useState<ConversationThread[]>(MOCK_CONVERSATIONS);
  const [searchQuery, setSearchQuery] = useState("");
  const [threadToDelete, setThreadToDelete] = useState<ConversationThread | null>(null);

  const filteredThreads = threads.filter((t) =>
    t.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDelete = (id: string) => {
    setThreads((prev) => prev.filter((t) => t.id !== id));
    setThreadToDelete(null);
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
                Conversation History (W-06)
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
        {threads.length === 0 ? (
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
                  href={`/chat?id=${thread.id}`}
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
                        {formatDate(thread.updatedAt)}
                      </span>
                      <span>•</span>
                      <span>{thread.messageCount} messages</span>
                    </div>
                  </div>
                </Link>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setThreadToDelete(thread)}
                    className="p-1.5 text-zinc-400 hover:text-red-500 rounded transition cursor-pointer"
                    title="Delete Thread"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <Link
                    href={`/chat?id=${thread.id}`}
                    className="p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
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
          <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-2xs">
            <div className="w-full max-w-sm rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-6 shadow-xl space-y-4">
              <div className="flex items-center gap-3 text-red-600">
                <AlertCircle className="w-5 h-5 shrink-0" />
                <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                  Delete Conversation Thread
                </h3>
              </div>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                Are you sure you want to permanently delete{" "}
                <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                  &ldquo;{threadToDelete.title}&rdquo;
                </span>
                ? This action cannot be undone.
              </p>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setThreadToDelete(null)}
                  className="px-3 py-1.5 rounded-md text-xs font-medium border border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDelete(threadToDelete.id)}
                  className="px-3 py-1.5 rounded-md text-xs font-medium bg-red-600 text-white hover:bg-red-700 transition"
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
