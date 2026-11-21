"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  Layers,
  Database,
  RefreshCw,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { PermissionDeniedState } from "@/components/SystemStates";
import { useAuth } from "@/context/AuthContext";

export default function DocumentUploadPage() {
  const { role } = useAuth();

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("Academic");
  const [autoIndex, setAutoIndex] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [stageMessage, setStageMessage] = useState("");
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Requirement: Screen must be admin-only
  if (role !== "admin") {
    return (
      <AppShell>
        <PermissionDeniedState requiredRole="admin" />
      </AppShell>
    );
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    const selected = e.target.files?.[0];
    if (selected) {
      if (!selected.name.toLowerCase().endsWith(".pdf")) {
        setError("Invalid file type: Only official PDF documents are accepted.");
        return;
      }
      if (selected.size > 10 * 1024 * 1024) {
        setError("File size exceeds the 10 MB limit.");
        return;
      }
      setFile(selected);
      if (!title) {
        setTitle(selected.name.replace(/\.[^/.]+$/, "").replace(/_/g, " "));
      }
    }
  };

  const handleUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a PDF document to upload.");
      return;
    }
    if (!title.trim()) {
      setError("Please provide an official document title.");
      return;
    }

    setIsUploading(true);
    setUploadProgress(15);
    setStageMessage("Uploading raw PDF to MinIO S3 bucket (university-documents)...");

    setTimeout(() => {
      setUploadProgress(45);
      setStageMessage("Extracting text and page boundaries with PyMuPDF...");
    }, 700);

    setTimeout(() => {
      setUploadProgress(75);
      setStageMessage("Generating embeddings via all-MiniLM-L6-v2 and indexing points in Qdrant...");
    }, 1400);

    setTimeout(() => {
      setUploadProgress(100);
      setStageMessage("Document successfully indexed and verified in PostgreSQL!");
      setIsUploading(false);
      setUploadSuccess(true);
    }, 2100);
  };

  const handleReset = () => {
    setFile(null);
    setTitle("");
    setUploadProgress(0);
    setStageMessage("");
    setUploadSuccess(false);
    setError(null);
  };

  return (
    <AppShell>
      <div className="p-6 sm:p-8 max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <UploadCloud className="w-5 h-5 text-accent" />
              <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Admin: Document Ingestion (W-11)
              </h1>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Upload university ordinances and guidelines to MinIO and synchronously trigger vectorization
            </p>
          </div>

          <Link
            href="/admin/metadata"
            className="text-xs font-semibold text-accent hover:underline flex items-center gap-1 self-start sm:self-auto"
          >
            Manage Existing Metadata (W-12) →
          </Link>
        </div>

        {error && (
          <div className="p-3.5 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 flex items-center gap-2 text-xs text-red-600 dark:text-red-400">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {uploadSuccess ? (
          <div className="p-8 rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/40 dark:bg-emerald-950/20 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                Document Successfully Ingested
              </h3>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1 max-w-md mx-auto">
                &ldquo;{title}&rdquo; is now searchable across the university RAG pipeline with verified page citations.
              </p>
            </div>

            <div className="flex justify-center gap-3 pt-2">
              <button
                onClick={handleReset}
                className="px-4 py-2 text-xs font-medium rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-800 dark:text-zinc-200 hover:bg-zinc-50 transition"
              >
                Upload Another Document
              </button>
              <Link
                href="/documents"
                className="px-4 py-2 text-xs font-semibold rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 transition"
              >
                View in Document Catalog (W-07)
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleUpload} className="space-y-6">
            {/* Drag & Drop Upload Zone */}
            <div className="border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-xl p-8 text-center hover:border-accent transition bg-zinc-50/50 dark:bg-zinc-900/30">
              <input
                type="file"
                id="file-upload"
                accept=".pdf,application/pdf"
                onChange={handleFileChange}
                className="hidden"
                disabled={isUploading}
              />
              <label
                htmlFor="file-upload"
                className="cursor-pointer flex flex-col items-center justify-center space-y-2"
              >
                <div className="w-10 h-10 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-500">
                  <UploadCloud className="w-5 h-5 text-accent" />
                </div>
                <div>
                  <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                    {file ? file.name : "Click to browse or drag PDF file here"}
                  </span>
                  <p className="text-[11px] text-zinc-400 mt-0.5">
                    {file
                      ? `${(file.size / (1024 * 1024)).toFixed(2)} MB · Ready for ingestion`
                      : "Official university circulars, ordinances, syllabi (PDF only, max 10 MB)"}
                  </p>
                </div>
              </label>
            </div>

            {/* Document Details */}
            <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                  Document Title
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Academic Ordinance on Examination Re-evaluation 2026"
                  className="w-full px-3 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-1 focus:ring-accent"
                  required
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                    Knowledge Category
                  </label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
                  >
                    <option value="Academic">Academic Regulations</option>
                    <option value="Examinations">Examinations & Grading</option>
                    <option value="Hostel">Hostel & Student Life</option>
                    <option value="Placements">Placements & Internships</option>
                    <option value="Admissions">Admissions & Scholarships</option>
                    <option value="General">General Administrative Notices</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                    Vector Pipeline
                  </label>
                  <div className="flex items-center gap-2 pt-2">
                    <input
                      type="checkbox"
                      id="auto-index"
                      checked={autoIndex}
                      onChange={(e) => setAutoIndex(e.target.checked)}
                      className="rounded border-zinc-300 text-accent focus:ring-accent"
                    />
                    <label htmlFor="auto-index" className="text-xs text-zinc-700 dark:text-zinc-300">
                      Auto-index vectors in Qdrant upon upload
                    </label>
                  </div>
                </div>
              </div>
            </div>

            {/* Ingestion Progress Bar */}
            {isUploading && (
              <div className="p-4 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-accent" />
                    {stageMessage}
                  </span>
                  <span className="font-mono text-zinc-500">{uploadProgress}%</span>
                </div>
                <div className="w-full bg-zinc-200 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-accent h-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isUploading || !file}
              className="w-full py-2.5 px-4 rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-xs font-semibold hover:bg-zinc-800 dark:hover:bg-zinc-200 transition disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Begin Ingestion & Vector Indexing</span>
            </button>
          </form>
        )}
      </div>
    </AppShell>
  );
}
