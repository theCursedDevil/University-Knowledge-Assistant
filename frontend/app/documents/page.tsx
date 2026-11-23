"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  FileText,
  Search,
  Filter,
  UploadCloud,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ChevronRight,
  ExternalLink,
  Layers,
  Sparkles,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { NoResultsState, EmptyState, LoadingState } from "@/components/SystemStates";
import { useAuth } from "@/context/AuthContext";
import { fetchDocuments, searchSemanticDocuments, ApiDocument, ApiSearchResult } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function DocumentsPage() {
  const { role } = useAuth();
  const [documents, setDocuments] = useState<ApiDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [selectedStatus, setSelectedStatus] = useState<string>("All");
  const [isSemanticSearch, setIsSemanticSearch] = useState<boolean>(false);
  const [semanticResults, setSemanticResults] = useState<ApiSearchResult[] | null>(null);

  const categories = ["All", "Academic", "Examinations", "Hostel", "Placements", "Admissions", "Regulations", "General"];
  const statuses = ["All", "ready", "indexed", "processing", "failed"];

  const loadDocs = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetchDocuments(selectedCategory);
      setDocuments(data);
    } catch {
      setDocuments([]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    loadDocs();
  }, [loadDocs]);

  // Execute Semantic Vector Search if user toggles or searches
  const handleSemanticSearch = async () => {
    if (!searchQuery.trim()) {
      setSemanticResults(null);
      return;
    }
    setIsLoading(true);
    try {
      const results = await searchSemanticDocuments(
        searchQuery,
        10,
        selectedCategory !== "All" ? selectedCategory : undefined
      );
      setSemanticResults(results);
    } catch {
      setSemanticResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredDocs = documents.filter((doc) => {
    const matchesSearch =
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.storage_path.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === "All" || doc.category.toLowerCase() === selectedCategory.toLowerCase();
    const matchesStatus =
      selectedStatus === "All" ||
      doc.status === selectedStatus ||
      (selectedStatus === "ready" && doc.status === "indexed");
    return matchesSearch && matchesCategory && matchesStatus;
  });

  const getStatusBadge = (status: string) => {
    if (status === "ready" || status === "indexed") {
      return {
        label: "Ready (Indexed)",
        icon: <CheckCircle2 className="w-3 h-3 text-emerald-500" />,
        style: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800",
      };
    }
    if (status === "processing") {
      return {
        label: "Processing Chunks",
        icon: <Clock className="w-3 h-3 text-amber-500 animate-spin" />,
        style: "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 border-amber-200 dark:border-amber-800",
      };
    }
    return {
      label: "Failed",
      icon: <AlertTriangle className="w-3 h-3 text-red-500" />,
      style: "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400 border-red-200 dark:border-red-800",
    };
  };

  return (
    <AppShell>
      <div className="p-6 sm:p-8 max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <FileText className="w-5 h-5 text-accent" />
              <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Document Catalog
              </h1>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Browse, search, and verify university ordinances, regulations, and circulars indexed in Qdrant
            </p>
          </div>

          {role === "admin" && (
            <Link
              href="/admin/upload"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-md bg-accent text-white hover:bg-accent-hover transition shadow-xs cursor-pointer self-start sm:self-auto"
            >
              <UploadCloud className="w-4 h-4" />
              Upload PDF
            </Link>
          )}
        </div>

        {/* Filter Toolbar */}
        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && isSemanticSearch && handleSemanticSearch()}
                placeholder="Search regulations by title, keyword, or filename..."
                className="w-full pl-9 pr-4 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-1 focus:ring-accent"
              />
            </div>

            <button
              onClick={() => {
                const next = !isSemanticSearch;
                setIsSemanticSearch(next);
                if (!next) setSemanticResults(null);
                else handleSemanticSearch();
              }}
              className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium border transition cursor-pointer ${
                isSemanticSearch
                  ? "bg-accent/10 border-accent text-accent font-semibold"
                  : "bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Semantic Vector Search</span>
            </button>

            <div className="flex items-center gap-2">
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="px-2.5 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 focus:outline-hidden cursor-pointer"
              >
                {statuses.map((s) => (
                  <option key={s} value={s}>
                    Status: {s.charAt(0).toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Category Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
            <span className="text-[11px] text-zinc-400 font-medium mr-1 flex items-center gap-1">
              <Filter className="w-3 h-3" />
              Category:
            </span>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium whitespace-nowrap transition cursor-pointer ${
                  selectedCategory === cat
                    ? "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-semibold"
                    : "bg-zinc-100 dark:bg-zinc-900 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-200/60"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Semantic Vector Search Results Mode */}
        {isSemanticSearch && semanticResults !== null ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-zinc-500">
              <span>Showing {semanticResults.length} semantic chunk coordinates retrieved from Qdrant:</span>
              <button
                onClick={() => {
                  setIsSemanticSearch(false);
                  setSemanticResults(null);
                }}
                className="text-accent underline text-xs"
              >
                Back to Document Catalog
              </button>
            </div>

            {semanticResults.length === 0 ? (
              <NoResultsState query={searchQuery} onClear={() => setSearchQuery("")} />
            ) : (
              <div className="grid grid-cols-1 gap-3">
                {semanticResults.map((result) => (
                  <div
                    key={result.chunk_id}
                    className="p-4 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-2 shadow-2xs"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <FileText className="w-3.5 h-3.5 text-accent" />
                        <span className="font-bold text-zinc-900 dark:text-zinc-100">{result.document_name}</span>
                        {result.page && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-100 dark:bg-zinc-800 font-mono">
                            Page {result.page}
                          </span>
                        )}
                        {result.section && (
                          <span className="text-zinc-400 text-[11px] truncate">{result.section}</span>
                        )}
                      </div>
                      <span className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 font-bold">
                        Score: {(result.score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <p className="text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed font-serif bg-zinc-50 dark:bg-zinc-950 p-3 rounded border border-zinc-100 dark:border-zinc-850">
                      &quot;{result.chunk_text}&quot;
                    </p>
                    <div className="flex justify-end">
                      <Link
                        href={`/documents/${result.document_id}`}
                        className="text-xs text-accent hover:underline inline-flex items-center gap-1 font-medium"
                      >
                        Preview Document <ChevronRight className="w-3 h-3" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : isLoading ? (
          <LoadingState message="Loading document repository from PostgreSQL..." />
        ) : documents.length === 0 ? (
          <EmptyState
            title="No documents uploaded yet"
            description="The university knowledge base is currently empty. Ingest official PDF circulars and regulations to begin querying."
            actionLabel={role === "admin" ? "Upload First PDF" : undefined}
            actionHref={role === "admin" ? "/admin/upload" : undefined}
          />
        ) : filteredDocs.length === 0 ? (
          <NoResultsState query={searchQuery || selectedCategory} onClear={() => {
            setSearchQuery("");
            setSelectedCategory("All");
            setSelectedStatus("All");
          }} />
        ) : (
          /* Document Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDocs.map((doc) => {
              const badge = getStatusBadge(doc.status);

              return (
                <div
                  key={doc.id}
                  className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4 flex flex-col justify-between hover:border-zinc-300 dark:hover:border-zinc-700 transition shadow-2xs"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
                        {doc.category}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${badge.style}`}
                      >
                        {badge.icon}
                        <span>{badge.label}</span>
                      </span>
                    </div>

                    <div>
                      <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 leading-snug line-clamp-2">
                        {doc.title}
                      </h3>
                      <p className="text-[11px] text-zinc-400 font-mono mt-1 truncate">
                        {doc.storage_path.split("/").pop()}
                      </p>
                    </div>

                    <div className="p-2.5 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800 text-[11px] text-zinc-500 space-y-1">
                      <div className="flex justify-between">
                        <span>Version:</span>
                        <span className="font-mono text-zinc-800 dark:text-zinc-200 font-semibold">v{doc.version}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Ingested:</span>
                        <span className="font-mono text-zinc-800 dark:text-zinc-200">{formatDate(doc.created_at)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-zinc-100 dark:border-zinc-800 mt-4 flex items-center justify-between">
                    <Link
                      href={`/documents/${doc.id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-accent hover:underline cursor-pointer"
                    >
                      <span>Preview Document</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </Link>

                    {role === "admin" && (
                      <Link
                        href="/admin/metadata"
                        className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
                        title="Manage in Metadata"
                      >
                        <Layers className="w-3.5 h-3.5" />
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
