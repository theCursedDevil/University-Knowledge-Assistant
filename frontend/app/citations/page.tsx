"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Quote,
  Search,
  FileText,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  Filter,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { NoResultsState } from "@/components/SystemStates";
import { MOCK_CITATIONS, CitationItem } from "@/lib/mockData";

export default function CitationsPage() {
  const [citations] = useState<CitationItem[]>(MOCK_CITATIONS);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDoc, setSelectedDoc] = useState<string>("All");

  const uniqueDocs = ["All", ...Array.from(new Set(citations.map((c) => c.document)))];

  const filteredCitations = citations.filter((cit) => {
    const matchesSearch =
      cit.document.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cit.snippet.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (cit.section && cit.section.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesDoc = selectedDoc === "All" || cit.document === selectedDoc;
    return matchesSearch && matchesDoc;
  });

  return (
    <AppShell>
      <div className="p-6 sm:p-8 max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Quote className="w-5 h-5 text-accent" />
              <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Source Citations
              </h1>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Deterministic source references and page provenance extracted from verified institutional PDF documents
            </p>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 self-start sm:self-auto">
            <ShieldCheck className="w-3.5 h-3.5" />
            100% Grounded Provenance
          </div>
        </div>

        {/* Anti-Hallucination Policy Banner */}
        <div className="p-4 rounded-lg bg-zinc-50 dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed flex items-start gap-3">
          <CheckCircle2 className="w-4 h-4 text-accent shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">
              Zero Fabrication Guarantee:
            </span>{" "}
            Every citation below maps to an actual chunk in the PostgreSQL{" "}
            <code className="text-[11px] font-mono bg-zinc-100 dark:bg-zinc-800 px-1 py-0.5 rounded">
              document_chunks_meta
            </code>{" "}
            table and an indexed vector point in Qdrant. The LLM is never prompted or permitted to invent document names, ordinances, or page references.
          </div>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search citations by keywords, section names, or regulations..."
              className="w-full pl-9 pr-4 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-1 focus:ring-accent"
            />
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[11px] font-medium text-zinc-400 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Document:
            </span>
            <select
              value={selectedDoc}
              onChange={(e) => setSelectedDoc(e.target.value)}
              className="text-xs py-2 px-3 rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-800 dark:text-zinc-200 focus:outline-hidden focus:ring-1 focus:ring-accent"
            >
              {uniqueDocs.map((doc) => (
                <option key={doc} value={doc}>
                  {doc === "All" ? "All Documents" : doc}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Citations List */}
        {filteredCitations.length === 0 ? (
          <NoResultsState
            query={searchQuery}
            onClear={() => {
              setSearchQuery("");
              setSelectedDoc("All");
            }}
          />
        ) : (
          <div className="space-y-4">
            {filteredCitations.map((cit) => (
              <div
                key={cit.id}
                className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-700 transition space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-accent shrink-0" />
                    <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                      {cit.document}
                    </span>
                    <span className="text-xs text-zinc-400">•</span>
                    <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                      Page {cit.page}
                    </span>
                    {cit.section && (
                      <>
                        <span className="text-xs text-zinc-400">•</span>
                        <span className="text-xs text-zinc-500 dark:text-zinc-400">
                          {cit.section}
                        </span>
                      </>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 font-semibold">
                      Relevance: {Math.round(cit.relevanceScore * 100)}%
                    </span>
                  </div>
                </div>

                {/* Excerpt Box */}
                <div className="p-3.5 rounded-md bg-zinc-50 dark:bg-zinc-800/40 border-l-2 border-accent text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed italic">
                  &ldquo;{cit.snippet}&rdquo;
                </div>

                <div className="flex items-center justify-between pt-2 text-xs">
                  <span className="text-[10px] font-mono text-zinc-400">
                    Chunk Provenance ID: {cit.id}
                  </span>
                  <Link
                    href={`/documents`}
                    className="inline-flex items-center gap-1 font-semibold text-accent hover:underline text-xs"
                  >
                    <span>View in Document Preview</span>
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
