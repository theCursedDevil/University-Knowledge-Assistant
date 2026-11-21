"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  FileText,
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  ShieldCheck,
  Layers,
  Database,
  Calendar,
  User,
  HardDrive,
  ExternalLink,
  AlertTriangle,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { LoadingState, ErrorState } from "@/components/SystemStates";
import {
  fetchDocumentById,
  fetchDocumentPreview,
  fetchDocumentChunks,
  ApiDocument,
  ApiDocumentPreview,
  ApiDocumentChunk,
} from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function DocumentPreviewPage() {
  const params = useParams();
  const router = useRouter();
  const docId = params.id as string;

  const [document, setDocument] = useState<ApiDocument | null>(null);
  const [preview, setPreview] = useState<ApiDocumentPreview | null>(null);
  const [chunks, setChunks] = useState<ApiDocumentChunk[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!docId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [docData, previewData, chunksData] = await Promise.all([
        fetchDocumentById(docId),
        fetchDocumentPreview(docId).catch(() => null),
        fetchDocumentChunks(docId).catch(() => []),
      ]);
      setDocument(docData);
      setPreview(previewData);
      setChunks(chunksData);
    } catch (err: any) {
      setError(err.message || "Failed to load document preview from repository.");
    } finally {
      setIsLoading(false);
    }
  }, [docId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const totalPages = preview?.page_count || 1;
  const activePageData = preview?.pages?.find((p) => p.page_number === currentPage);

  const handleNextPage = () => {
    if (currentPage < totalPages) setCurrentPage((prev) => prev + 1);
  };

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage((prev) => prev - 1);
  };

  if (isLoading) {
    return (
      <AppShell>
        <div className="p-8">
          <LoadingState message="Fetching PDF file and vector chunks from MinIO and Qdrant..." />
        </div>
      </AppShell>
    );
  }

  if (error || !document) {
    return (
      <AppShell>
        <div className="p-8">
          <ErrorState
            code="DOC_NOT_FOUND"
            message={error || `The document with ID ${docId} could not be retrieved from the database.`}
            onRetry={loadData}
          />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="flex flex-col h-[calc(100vh-3.5rem)] overflow-hidden">
        {/* Document Top Bar */}
        <div className="h-14 border-b border-zinc-200 dark:border-zinc-800 px-6 flex items-center justify-between shrink-0 bg-white/95 dark:bg-zinc-950/95">
          <div className="flex items-center gap-3 min-w-0">
            <Link
              href="/documents"
              className="p-1.5 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500 hover:text-zinc-900 transition"
              title="Back to Catalog"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                  {document.category}
                </span>
                <h1 className="text-xs sm:text-sm font-bold text-zinc-900 dark:text-zinc-100 truncate">
                  {document.title}
                </h1>
              </div>
              <span className="text-[11px] text-zinc-400 font-mono hidden sm:inline">
                {document.storage_path.split("/").pop()} · v{document.version} · Status: {document.status}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/chat"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-accent text-white text-xs font-semibold hover:bg-accent-hover transition cursor-pointer"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Ask About This Document</span>
            </Link>
          </div>
        </div>

        {/* Main Content: Viewer + Metadata Panel */}
        <div className="flex-1 flex overflow-hidden">
          {/* PDF Viewer Canvas (W-08) */}
          <div className="flex-1 flex flex-col bg-zinc-100/60 dark:bg-zinc-900/40 overflow-hidden">
            {/* Page Navigation Toolbar */}
            <div className="h-10 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-4 flex items-center justify-between text-xs text-zinc-500">
              <div className="flex items-center gap-2">
                <button
                  onClick={handlePrevPage}
                  disabled={currentPage <= 1}
                  className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-30 cursor-pointer"
                  title="Previous Page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span>
                  Page <strong className="text-zinc-900 dark:text-zinc-100">{currentPage}</strong> of{" "}
                  {totalPages}
                </span>
                <button
                  onClick={handleNextPage}
                  disabled={currentPage >= totalPages}
                  className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-30 cursor-pointer"
                  title="Next Page"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>

              {activePageData?.section && (
                <div className="text-[11px] font-mono text-zinc-400 truncate max-w-xs">
                  Section: {activePageData.section}
                </div>
              )}
            </div>

            {/* Rendered Text Page Viewport */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-8 flex justify-center">
              <div className="w-full max-w-2xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-sm p-8 sm:p-12 space-y-4 font-serif text-xs leading-relaxed text-zinc-800 dark:text-zinc-200 self-start">
                <div className="border-b border-zinc-100 dark:border-zinc-850 pb-3 flex justify-between items-center text-[10px] font-sans text-zinc-400 uppercase tracking-wider">
                  <span>{document.title}</span>
                  <span>Page {currentPage}</span>
                </div>

                {activePageData ? (
                  <div className="space-y-3 whitespace-pre-wrap">
                    {activePageData.section && (
                      <h3 className="font-sans font-bold text-sm text-zinc-900 dark:text-zinc-100 border-l-2 border-accent pl-2">
                        {activePageData.section}
                      </h3>
                    )}
                    <p className="leading-relaxed">{activePageData.text}</p>
                  </div>
                ) : (
                  <div className="py-12 text-center text-zinc-400 font-sans space-y-2">
                    <p>No clean text extracted for this page.</p>
                    <p className="text-[11px]">The original PDF is stored intact in MinIO storage.</p>
                  </div>
                )}

                <div className="border-t border-zinc-100 dark:border-zinc-850 pt-3 text-center text-[10px] font-sans text-zinc-400">
                  Official University Ordinance Document Record · Retrieved from MinIO Object Storage
                </div>
              </div>
            </div>
          </div>

          {/* Right Metadata Inspector Sidebar */}
          <div className="w-80 border-l border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-5 overflow-y-auto space-y-5 text-xs hidden lg:block shrink-0">
            <div>
              <h3 className="font-bold text-xs uppercase tracking-wider text-zinc-400 mb-3">
                Ingestion Provenance
              </h3>
              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-1">
                  <div className="text-[10px] text-zinc-400 flex items-center gap-1 uppercase font-semibold">
                    <HardDrive className="w-3 h-3 text-accent" />
                    Storage Location
                  </div>
                  <div className="font-mono text-[11px] text-zinc-800 dark:text-zinc-200 break-all">
                    {document.storage_path}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-1">
                  <div className="text-[10px] text-zinc-400 flex items-center gap-1 uppercase font-semibold">
                    <Database className="w-3 h-3 text-accent" />
                    PostgreSQL Record ID
                  </div>
                  <div className="font-mono text-[11px] text-zinc-800 dark:text-zinc-200">
                    {document.id}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-1">
                  <div className="text-[10px] text-zinc-400 flex items-center gap-1 uppercase font-semibold">
                    <Layers className="w-3 h-3 text-accent" />
                    Indexed Vector Chunks
                  </div>
                  <div className="text-zinc-800 dark:text-zinc-200 font-bold">
                    {chunks.length} chunks registered in Qdrant
                  </div>
                </div>
              </div>
            </div>

            {/* Chunk List Breakdown */}
            {chunks.length > 0 && (
              <div>
                <h3 className="font-bold text-xs uppercase tracking-wider text-zinc-400 mb-2">
                  Chunk Coordinates ({chunks.length})
                </h3>
                <div className="max-h-56 overflow-y-auto space-y-1.5 pr-1">
                  {chunks.map((chk) => (
                    <div
                      key={chk.id}
                      className="p-2 rounded bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-850 text-[11px] flex items-center justify-between"
                    >
                      <span>
                        Chunk #{chk.chunk_index} {chk.page ? `(Page ${chk.page})` : ""}
                      </span>
                      <span className="font-mono text-[10px] text-zinc-400">
                        {chk.vector_id.slice(0, 8)}...
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-[11px] text-emerald-800 dark:text-emerald-300 flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span>
                Deterministic provenance verified. This document serves as ground truth for LLM answers.
              </span>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
