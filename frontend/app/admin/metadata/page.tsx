"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Layers,
  Search,
  RefreshCw,
  Trash2,
  Database,
  CheckCircle2,
  AlertTriangle,
  UploadCloud,
  ExternalLink,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { PermissionDeniedState, NoResultsState } from "@/components/SystemStates";
import { useAuth } from "@/context/AuthContext";
import { MOCK_DOCUMENTS, DocumentItem } from "@/lib/mockData";
import { formatDate } from "@/lib/utils";

export default function MetadataManagementPage() {
  const { role } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>(MOCK_DOCUMENTS);
  const [searchQuery, setSearchQuery] = useState("");
  const [reindexingId, setReindexingId] = useState<string | null>(null);
  const [docToDelete, setDocToDelete] = useState<DocumentItem | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  if (role !== "admin") {
    return (
      <AppShell>
        <PermissionDeniedState requiredRole="admin" />
      </AppShell>
    );
  }

  const filteredDocs = documents.filter(
    (d) =>
      d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleReindex = (id: string) => {
    setReindexingId(id);
    setTimeout(() => {
      setDocuments((prev) =>
        prev.map((d) => (d.id === id ? { ...d, status: "ready" as const, updatedAt: new Date().toISOString() } : d))
      );
      setReindexingId(null);
      setToastMessage("Re-indexing complete: Qdrant vector coordinates refreshed.");
      setTimeout(() => setToastMessage(null), 3000);
    }, 1000);
  };

  const handleDelete = (id: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    setDocToDelete(null);
    setToastMessage("Document removed: Cascading deletion completed across PostgreSQL, MinIO, and Qdrant.");
    setTimeout(() => setToastMessage(null), 3500);
  };

  return (
    <AppShell>
      <div className="p-6 sm:p-8 max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Layers className="w-5 h-5 text-accent" />
              <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Admin: Metadata Management (W-12)
              </h1>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Manage chunk coordinates, Qdrant vector payloads, storage integrity, and cascading deletions
            </p>
          </div>

          <Link
            href="/admin/upload"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 transition shadow-xs self-start sm:self-auto cursor-pointer"
          >
            <UploadCloud className="w-4 h-4" />
            Upload PDF (W-11)
          </Link>
        </div>

        {toastMessage && (
          <div className="p-3.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 flex items-center gap-2 text-xs text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        )}

        {/* Search */}
        <div className="relative">
          <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter metadata by document title, filename, or category..."
            className="w-full pl-9 pr-4 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-1 focus:ring-accent"
          />
        </div>

        {/* Table */}
        {filteredDocs.length === 0 ? (
          <NoResultsState query={searchQuery} onClear={() => setSearchQuery("")} />
        ) : (
          <div className="border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-x-auto bg-white dark:bg-zinc-900">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/40 text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Document Title & Filename</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Pages / Chunks</th>
                  <th className="py-3 px-4">Updated</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                {filteredDocs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-zinc-50/70 dark:hover:bg-zinc-800/30 transition">
                    <td className="py-3.5 px-4 min-w-[240px]">
                      <span className="font-semibold text-zinc-900 dark:text-zinc-100 block">
                        {doc.title}
                      </span>
                      <span className="text-[10px] font-mono text-zinc-400 block mt-0.5">
                        {doc.filename} · v{doc.version}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                        {doc.category}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                          doc.status === "ready"
                            ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800"
                            : doc.status === "processing"
                            ? "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 border-amber-200 dark:border-amber-800"
                            : "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400 border-red-200 dark:border-red-800"
                        }`}
                      >
                        {doc.status.toUpperCase()}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 font-mono text-[11px] text-zinc-600 dark:text-zinc-400">
                      {doc.pageCount} pgs · {doc.chunkCount} vectors
                    </td>

                    <td className="py-3.5 px-4 text-zinc-500 text-[11px]">
                      {formatDate(doc.updatedAt)}
                    </td>

                    <td className="py-3.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => handleReindex(doc.id)}
                        disabled={reindexingId === doc.id}
                        className="p-1.5 rounded text-zinc-500 hover:text-accent hover:bg-zinc-100 dark:hover:bg-zinc-800 transition cursor-pointer"
                        title="Trigger Re-indexing in Qdrant"
                      >
                        <RefreshCw
                          className={`w-3.5 h-3.5 ${reindexingId === doc.id ? "animate-spin text-accent" : ""}`}
                        />
                      </button>

                      <button
                        onClick={() => setDocToDelete(doc)}
                        className="p-1.5 rounded text-zinc-500 hover:text-red-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition cursor-pointer"
                        title="Delete Document (Cascading)"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {docToDelete && (
          <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-2xs">
            <div className="w-full max-w-sm rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-6 shadow-xl space-y-4">
              <div className="flex items-center gap-3 text-red-600">
                <AlertTriangle className="w-5 h-5 shrink-0" />
                <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                  Cascading Deletion Saga
                </h3>
              </div>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                Permanently delete{" "}
                <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                  &ldquo;{docToDelete.title}&rdquo;
                </span>
                ? This will cascade across:
              </p>
              <ul className="text-[11px] text-zinc-600 dark:text-zinc-400 list-disc list-inside space-y-1 bg-zinc-50 dark:bg-zinc-800/40 p-2.5 rounded border border-zinc-200/60 dark:border-zinc-700">
                <li>Raw PDF removal from MinIO S3 bucket</li>
                <li>{docToDelete.chunkCount} vectors deleted from Qdrant</li>
                <li>PostgreSQL records & audit log recorded</li>
              </ul>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setDocToDelete(null)}
                  className="px-3 py-1.5 rounded-md text-xs font-medium border border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDelete(docToDelete.id)}
                  className="px-3 py-1.5 rounded-md text-xs font-semibold bg-red-600 text-white hover:bg-red-700 transition"
                >
                  Confirm Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
