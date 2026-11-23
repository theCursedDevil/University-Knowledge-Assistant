"use client";

import React, { useState, useEffect, useCallback } from "react";
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
  Edit2,
  X,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { PermissionDeniedState, NoResultsState, LoadingState } from "@/components/SystemStates";
import { useAuth } from "@/context/AuthContext";
import {
  fetchDocuments,
  deleteDocument,
  processDocument,
  updateDocumentMetadata,
  ApiDocument,
} from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function MetadataManagementPage() {
  const { role } = useAuth();
  const [documents, setDocuments] = useState<ApiDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [selectedStatus, setSelectedStatus] = useState("ALL");
  const [reindexingId, setReindexingId] = useState<string | null>(null);
  const [docToDelete, setDocToDelete] = useState<ApiDocument | null>(null);
  const [editingDoc, setEditingDoc] = useState<ApiDocument | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editCategory, setEditCategory] = useState("Academic");
  const [editRoleRestriction, setEditRoleRestriction] = useState("all");
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const loadDocs = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetchDocuments();
      setDocuments(data);
    } catch {
      setDocuments([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (role === "admin") {
      loadDocs();
    }
  }, [role, loadDocs]);

  if (role !== "admin") {
    return (
      <AppShell>
        <PermissionDeniedState requiredRole="admin" />
      </AppShell>
    );
  }

  const categories = Array.from(new Set(documents.map((d) => d.category))).filter(Boolean);

  const filteredDocs = documents.filter((d) => {
    const query = searchQuery.toLowerCase();
    const matchesSearch =
      !query ||
      d.title.toLowerCase().includes(query) ||
      d.category.toLowerCase().includes(query) ||
      d.storage_path.toLowerCase().includes(query);
    const matchesCat = selectedCategory === "ALL" || d.category === selectedCategory;
    const matchesStatus = selectedStatus === "ALL" || d.status === selectedStatus;
    return matchesSearch && matchesCat && matchesStatus;
  });

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const handleReindex = async (id: string) => {
    setReindexingId(id);
    try {
      await processDocument(id);
      await loadDocs();
      showToast("Re-indexing complete: Qdrant vector coordinates refreshed.");
    } catch (err: any) {
      showToast(err.message || "Re-indexing failed.");
    } finally {
      setReindexingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      setDocToDelete(null);
      showToast("Document removed: Cascading deletion completed across PostgreSQL, MinIO, and Qdrant.");
    } catch (err: any) {
      showToast(err.message || "Failed to delete document.");
    }
  };

  const handleOpenEdit = (doc: ApiDocument) => {
    setEditingDoc(doc);
    setEditTitle(doc.title);
    setEditCategory(doc.category);
    setEditRoleRestriction(doc.role_restriction || "all");
  };

  const handleSaveMetadata = async () => {
    if (!editingDoc) return;
    try {
      const updated = await updateDocumentMetadata(editingDoc.id, {
        title: editTitle.trim(),
        category: editCategory.trim(),
        role_restriction: editRoleRestriction === "all" ? "" : editRoleRestriction,
        expected_version: editingDoc.version,
      });
      setDocuments((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
      setEditingDoc(null);
      showToast(`Document metadata successfully updated in PostgreSQL (v${updated.version}).`);
    } catch (err: any) {
      showToast(err.message || "Failed to update metadata.");
      // If version conflict occurred, refresh documents to show latest state
      if (err.message?.includes("Conflict") || err.message?.includes("409") || err.message?.includes("refresh")) {
        await loadDocs();
      }
    }
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
                Document Metadata Management
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
            Upload PDF
          </Link>
        </div>

        {toastMessage && (
          <div className="p-3.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 flex items-center gap-2 text-xs text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        )}

        {/* Search & Metadata Filter Controls */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5 pointer-events-none" />
            <input
              type="text"
              placeholder="Search by title, category, or storage path..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-xs rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-hidden focus:border-accent"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-2.5 py-2 text-xs rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 focus:outline-hidden focus:border-accent"
            >
              <option value="ALL">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-2.5 py-2 text-xs rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 focus:outline-hidden focus:border-accent"
            >
              <option value="ALL">All Statuses</option>
              <option value="ready">Ready (Indexed)</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
            </select>

            {(searchQuery || selectedCategory !== "ALL" || selectedStatus !== "ALL") && (
              <button
                onClick={() => {
                  setSearchQuery("");
                  setSelectedCategory("ALL");
                  setSelectedStatus("ALL");
                }}
                className="px-2.5 py-2 text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors whitespace-nowrap"
              >
                Reset
              </button>
            )}

            <span className="text-[11px] font-mono text-zinc-400 whitespace-nowrap ml-1">
              {filteredDocs.length} / {documents.length} docs
            </span>
          </div>
        </div>

        {/* Ingested Documents Metadata Table */}
        {isLoading ? (
          <LoadingState message="Loading documents from PostgreSQL repository..." />
        ) : filteredDocs.length === 0 ? (
          <NoResultsState query={searchQuery} onClear={() => setSearchQuery("")} />
        ) : (
          <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden shadow-2xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950/50 text-zinc-500 dark:text-zinc-400">
                    <th className="py-3 px-4 font-semibold">Document Title</th>
                    <th className="py-3 px-4 font-semibold">Category</th>
                    <th className="py-3 px-4 font-semibold">Access</th>
                    <th className="py-3 px-4 font-semibold">Status</th>
                    <th className="py-3 px-4 font-semibold">Version</th>
                    <th className="py-3 px-4 font-semibold">Ingested</th>
                    <th className="py-3 px-4 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800 text-zinc-700 dark:text-zinc-300">
                  {filteredDocs.map((doc) => {
                    const isReindexing = reindexingId === doc.id;
                    return (
                      <tr key={doc.id} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-800/40 transition">
                        <td className="py-3 px-4 font-medium text-zinc-900 dark:text-zinc-100 max-w-xs truncate">
                          <div className="flex items-center gap-2">
                            <span className="truncate">{doc.title}</span>
                            <Link
                              href={`/documents/${doc.id}`}
                              className="text-zinc-400 hover:text-accent shrink-0"
                              title="View Document Preview"
                            >
                              <ExternalLink className="w-3 h-3" />
                            </Link>
                          </div>
                          <span className="text-[10px] text-zinc-400 font-mono block truncate">
                            {doc.storage_path.split("/").pop()}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300">
                            {doc.category}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                              doc.role_restriction === "admin"
                                ? "bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800"
                                : doc.role_restriction === "faculty"
                                ? "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800"
                                : "bg-zinc-100 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400"
                            }`}
                          >
                            {doc.role_restriction ? `${doc.role_restriction.toUpperCase()} ONLY` : "PUBLIC"}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                              doc.status === "ready" || doc.status === "indexed"
                                ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800"
                                : doc.status === "processing"
                                ? "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800"
                                : "bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800"
                            }`}
                          >
                            <span
                              className={`w-1.5 h-1.5 rounded-full ${
                                doc.status === "ready" || doc.status === "indexed" ? "bg-emerald-500" : "bg-amber-500"
                              }`}
                            />
                            {doc.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px]">v{doc.version}</td>
                        <td className="py-3 px-4 text-zinc-400 font-mono text-[11px]">
                          {formatDate(doc.created_at)}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="inline-flex items-center gap-1.5">
                            <button
                              onClick={() => handleOpenEdit(doc)}
                              className="p-1 rounded text-zinc-400 hover:text-accent hover:bg-accent/10 transition cursor-pointer"
                              title="Edit Metadata (Requirement 16)"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleReindex(doc.id)}
                              disabled={isReindexing}
                              className="p-1 rounded text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition cursor-pointer disabled:opacity-40"
                              title="Re-index Chunks in Qdrant"
                            >
                              <RefreshCw className={`w-3.5 h-3.5 ${isReindexing ? "animate-spin text-accent" : ""}`} />
                            </button>
                            <button
                              onClick={() => setDocToDelete(doc)}
                              className="p-1 rounded text-zinc-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition cursor-pointer"
                              title="Delete Document"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="p-3 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/50 text-[11px] text-zinc-500 dark:text-zinc-400 flex items-center justify-between">
              <span>Showing {filteredDocs.length} knowledge base documents</span>
              <span>PostgreSQL Primary + MinIO Object Store + Qdrant Vector Collection</span>
            </div>
          </div>
        )}

        {/* Modal: Edit Metadata (Requirement 16) */}
        {editingDoc && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="w-full max-w-md rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="p-5 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Edit2 className="w-4 h-4 text-accent" />
                  <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">Edit Document Metadata</h3>
                </div>
                <button
                  onClick={() => setEditingDoc(null)}
                  className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="p-5 space-y-4 text-xs">
                <div className="space-y-1.5">
                  <label className="font-semibold text-zinc-700 dark:text-zinc-300">Document Title</label>
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:border-accent"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-semibold text-zinc-700 dark:text-zinc-300">Category</label>
                  <select
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:border-accent cursor-pointer"
                  >
                    <option value="Academic">Academic</option>
                    <option value="Examinations">Examinations</option>
                    <option value="Hostel">Hostel</option>
                    <option value="Placements">Placements</option>
                    <option value="Admissions">Admissions</option>
                    <option value="Regulations">Regulations</option>
                    <option value="General">General</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="font-semibold text-zinc-700 dark:text-zinc-300">Access Restriction (RBAC)</label>
                  <select
                    value={editRoleRestriction}
                    onChange={(e) => setEditRoleRestriction(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:border-accent cursor-pointer"
                  >
                    <option value="all">Public (All Users)</option>
                    <option value="faculty">Faculty Only (Faculty & Admin)</option>
                    <option value="admin">Admin Only (Administrative)</option>
                  </select>
                </div>

                <div className="p-3 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-[11px] text-zinc-500">
                  Changes will be committed to PostgreSQL and logged in the system audit trail.
                </div>
              </div>

              <div className="p-4 bg-zinc-50 dark:bg-zinc-950 border-t border-zinc-200 dark:border-zinc-800 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditingDoc(null)}
                  className="px-3.5 py-1.5 text-xs font-medium rounded-md border border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveMetadata}
                  className="px-3.5 py-1.5 text-xs font-semibold rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 cursor-pointer"
                >
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Modal: Cascading Delete Confirmation */}
        {docToDelete && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg max-w-sm w-full p-5 space-y-4 shadow-xl animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-red-100 dark:bg-red-950/40 text-red-600 flex items-center justify-center shrink-0">
                  <AlertTriangle className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                    Confirm Cascading Deletion
                  </h4>
                  <p className="text-xs text-zinc-500 mt-1">
                    Are you sure you want to delete &quot;{docToDelete.title}&quot;?
                    This will permanently delete the raw PDF from MinIO, remove its vector embeddings from Qdrant, and delete all chunk records in PostgreSQL.
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setDocToDelete(null)}
                  className="px-3 py-1.5 text-xs font-medium rounded-md border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition text-zinc-700 dark:text-zinc-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(docToDelete.id)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-md bg-red-600 text-white hover:bg-red-700 transition cursor-pointer"
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
