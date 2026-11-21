"use client";

import React, { useState } from "react";
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
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { NoResultsState, EmptyState } from "@/components/SystemStates";
import { useAuth } from "@/context/AuthContext";
import { MOCK_DOCUMENTS, DocumentItem } from "@/lib/mockData";
import { formatDate } from "@/lib/utils";

export default function DocumentsPage() {
  const { role } = useAuth();
  const [documents] = useState<DocumentItem[]>(MOCK_DOCUMENTS);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [selectedStatus, setSelectedStatus] = useState<string>("All");

  const categories = ["All", "Academic", "Examinations", "Hostel", "Placements", "Admissions", "General"];
  const statuses = ["All", "ready", "processing", "failed"];

  const filteredDocs = documents.filter((doc) => {
    const matchesSearch =
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === "All" || doc.category === selectedCategory;
    const matchesStatus = selectedStatus === "All" || doc.status === selectedStatus;
    return matchesSearch && matchesCategory && matchesStatus;
  });

  const statusBadges = {
    ready: {
      label: "Ready (Indexed)",
      icon: <CheckCircle2 className="w-3 h-3 text-emerald-500" />,
      style: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800",
    },
    processing: {
      label: "Processing Chunks",
      icon: <Clock className="w-3 h-3 text-amber-500 animate-spin" />,
      style: "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 border-amber-200 dark:border-amber-800",
    },
    failed: {
      label: "Extraction Failed",
      icon: <AlertTriangle className="w-3 h-3 text-red-500" />,
      style: "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400 border-red-200 dark:border-red-800",
    },
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
                Document Catalog (W-07)
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
              Upload PDF (W-11)
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
                placeholder="Search regulations by title, keyword, or filename..."
                className="w-full pl-9 pr-4 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-1 focus:ring-accent"
              />
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400 flex items-center gap-1">
                <Filter className="w-3.5 h-3.5" /> Status:
              </span>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="text-xs py-2 px-3 rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-800 dark:text-zinc-200 focus:outline-hidden focus:ring-1 focus:ring-accent"
              >
                {statuses.map((st) => (
                  <option key={st} value={st}>
                    {st === "All" ? "All Statuses" : st.charAt(0).toUpperCase() + st.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Category Pills */}
          <div className="flex flex-wrap gap-1.5 items-center">
            <span className="text-[11px] font-medium text-zinc-400 mr-1">Category:</span>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`text-[11px] font-medium px-2.5 py-1 rounded-md transition cursor-pointer ${
                  selectedCategory === cat
                    ? "bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900"
                    : "bg-zinc-100 dark:bg-zinc-800/80 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Document Grid / List */}
        {filteredDocs.length === 0 ? (
          <NoResultsState
            query={searchQuery}
            onClear={() => {
              setSearchQuery("");
              setSelectedCategory("All");
              setSelectedStatus("All");
            }}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredDocs.map((doc) => {
              const statusInfo = statusBadges[doc.status];
              return (
                <div
                  key={doc.id}
                  className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-700 transition flex flex-col justify-between space-y-3"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                        {doc.category}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full border ${statusInfo.style}`}
                      >
                        {statusInfo.icon}
                        {statusInfo.label}
                      </span>
                    </div>

                    <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 leading-snug">
                      {doc.title}
                    </h3>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2 leading-relaxed">
                      {doc.description}
                    </p>
                  </div>

                  <div className="pt-3 border-t border-zinc-100 dark:border-zinc-800/80 flex items-center justify-between text-[11px] text-zinc-400">
                    <div className="flex items-center gap-3">
                      <span>{doc.pageCount} pages</span>
                      <span>•</span>
                      <span>{doc.chunkCount} chunks</span>
                      <span>•</span>
                      <span>{doc.fileSize}</span>
                    </div>

                    <Link
                      href={`/documents/${doc.id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-accent hover:underline cursor-pointer"
                    >
                      Preview (W-08) <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
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
