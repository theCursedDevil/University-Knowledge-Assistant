"use client";

import React, { useState } from "react";
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
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { MOCK_DOCUMENTS, DocumentItem } from "@/lib/mockData";
import { formatDate } from "@/lib/utils";

export default function DocumentPreviewPage() {
  const params = useParams();
  const router = useRouter();
  const docId = params.id as string;

  const doc = MOCK_DOCUMENTS.find((d) => d.id === docId) || MOCK_DOCUMENTS[0];

  const [currentPage, setCurrentPage] = useState(1);
  const totalPages = doc.pageCount || 10;

  const handleNextPage = () => {
    if (currentPage < totalPages) setCurrentPage((prev) => prev + 1);
  };

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage((prev) => prev - 1);
  };

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
                  {doc.category}
                </span>
                <h1 className="text-xs sm:text-sm font-bold text-zinc-900 dark:text-zinc-100 truncate">
                  {doc.title}
                </h1>
              </div>
              <span className="text-[11px] text-zinc-400 font-mono hidden sm:inline">
                {doc.filename} · v{doc.version}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href={`/chat`}
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

              <div className="flex items-center gap-3">
                <span className="text-[11px] font-mono text-zinc-400">PyMuPDF Text Extract</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
                  Verified Ingestion
                </span>
              </div>
            </div>

            {/* Document Page Simulation Sheet */}
            <div className="flex-1 overflow-y-auto p-6 flex justify-center">
              <div className="w-full max-w-2xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-sm p-8 space-y-6 text-zinc-800 dark:text-zinc-200 font-serif leading-relaxed text-xs sm:text-sm">
                <div className="border-b border-zinc-200 dark:border-zinc-800 pb-4 text-center font-sans space-y-1">
                  <span className="text-[10px] uppercase tracking-wider text-zinc-400">
                    Official University Ordinance
                  </span>
                  <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                    {doc.title}
                  </h2>
                  <p className="text-[11px] text-zinc-500 font-mono">
                    Document Ref: UKA-{doc.category.toUpperCase()}-2026/04 · Physical Page {currentPage}
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="p-3 bg-amber-50/50 dark:bg-amber-950/20 border-l-2 border-accent rounded-r-md">
                    <span className="font-sans text-[11px] font-bold text-accent uppercase tracking-wider block mb-1">
                      Chunk Section #{currentPage}.1 · Vectorized for Cosine Search
                    </span>
                    <p className="font-sans text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed">
                      All registered undergraduate students are bound by the regulations codified herein. Continuous Internal Assessment (CIA) accounts for 40% of overall course evaluation, comprising class tests, laboratory assignments, and viva-voce examinations.
                    </p>
                  </div>

                  <p>
                    A minimum of 75% physical attendance across lecture and laboratory sessions registered during the active semester is mandatory for eligibility to appear in the End-Semester Examination. In cases of certified medical emergencies, the Dean of Student Welfare may condone shortages up to 10%, subject to formal hospital discharge certificates.
                  </p>

                  <p>
                    Degree classification adheres strictly to the Cumulative Grade Point Average (CGPA) on a 10.0 scale: First Class with Distinction requires a minimum CGPA of 8.0 without backlogs; First Class requires 6.5; and the minimum graduation threshold is 6.0.
                  </p>

                  <p>
                    Re-evaluation petitions for theory answer books must be registered within 14 calendar days from the official date of declaration of results. The fee of Rs. 500 per theoretical paper applies.
                  </p>
                </div>

                <div className="pt-8 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between font-sans text-[10px] text-zinc-400">
                  <span>University Academic Senate</span>
                  <span>Page {currentPage} of {totalPages}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Sidebar: Ingestion & Vector Metadata (W-08) */}
          <aside className="w-80 border-l border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-5 overflow-y-auto space-y-6 shrink-0 hidden lg:block">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-100 flex items-center gap-2 mb-3">
                <Database className="w-4 h-4 text-accent" />
                Storage & Metadata
              </h3>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-[10px] text-zinc-400 block font-medium">MinIO S3 Storage Path</span>
                  <code className="text-[11px] text-zinc-800 dark:text-zinc-200 font-mono break-all">
                    university-documents/documents/{doc.id}/{doc.filename}
                  </code>
                </div>

                <div>
                  <span className="text-[10px] text-zinc-400 block font-medium">Qdrant Vector Points</span>
                  <span className="text-zinc-800 dark:text-zinc-200 font-semibold">
                    {doc.chunkCount} vectors (dim 384, Cosine)
                  </span>
                </div>

                <div>
                  <span className="text-[10px] text-zinc-400 block font-medium">Ingestion Pipeline</span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    PyMuPDF + LangChain Recursive Splitter
                  </span>
                </div>

                <div>
                  <span className="text-[10px] text-zinc-400 block font-medium">Uploaded By</span>
                  <span className="text-zinc-800 dark:text-zinc-200">{doc.uploadedBy}</span>
                </div>

                <div>
                  <span className="text-[10px] text-zinc-400 block font-medium">Last Synchronized</span>
                  <span className="text-zinc-800 dark:text-zinc-200">{formatDate(doc.updatedAt)}</span>
                </div>

                <div>
                  <span className="text-[10px] text-zinc-400 block font-medium">SHA-256 Checksum</span>
                  <code className="text-[10px] font-mono text-zinc-500 break-all">
                    e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
                  </code>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800 space-y-2">
              <Link
                href="/citations"
                className="w-full py-2 px-3 rounded-md border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-900 text-xs font-medium text-zinc-700 dark:text-zinc-300 transition flex items-center justify-center gap-1.5"
              >
                <Layers className="w-3.5 h-3.5 text-accent" />
                View Document Citations (W-09)
              </Link>
            </div>
          </aside>
        </div>
      </div>
    </AppShell>
  );
}
