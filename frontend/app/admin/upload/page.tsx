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
import { uploadDocument, processDocument, ApiDocument } from "@/lib/api";

export default function DocumentUploadPage() {
  const { role } = useAuth();

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("Academic");
  const [autoIndex, setAutoIndex] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [stageMessage, setStageMessage] = useState("");
  const [uploadedDoc, setUploadedDoc] = useState<ApiDocument | null>(null);
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
      if (selected.size > 25 * 1024 * 1024) {
        setError("File size exceeds the 25 MB limit.");
        return;
      }
      setFile(selected);
      if (!title) {
        setTitle(selected.name.replace(/\.[^/.]+$/, "").replace(/_/g, " "));
      }
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
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
    setError(null);
    setUploadProgress(20);
    setStageMessage("Uploading raw PDF to MinIO S3 bucket (university-documents)...");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", title.trim());
      formData.append("category", category);

      // 1. Upload to FastAPI
      const doc = await uploadDocument(formData, !autoIndex);
      setUploadedDoc(doc);
      setUploadProgress(60);

      // 2. Synchronous processing if auto-index requested
      if (autoIndex) {
        setStageMessage("Extracting text with PyMuPDF, generating embeddings, and indexing points in Qdrant...");
        await processDocument(doc.id);
      }

      setUploadProgress(100);
      setStageMessage("Document successfully indexed and verified in PostgreSQL!");
      setUploadSuccess(true);
    } catch (err: any) {
      setError(err.message || "Upload or indexing failed. Verify file integrity.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setTitle("");
    setUploadProgress(0);
    setStageMessage("");
    setUploadedDoc(null);
    setUploadSuccess(false);
    setError(null);
  };

  return (
    <AppShell>
      <div className="p-6 sm:p-8 max-w-4xl mx-auto space-y-6">
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
              Upload official university PDFs for automated extraction, chunking, and Qdrant vector indexing
            </p>
          </div>

          <Link
            href="/admin/metadata"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition text-zinc-700 dark:text-zinc-300 self-start sm:self-auto cursor-pointer"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Metadata Management (W-12)</span>
          </Link>
        </div>

        {uploadSuccess ? (
          /* Success Card */
          <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/20 p-6 sm:p-8 space-y-5 animate-in fade-in duration-200">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-full bg-emerald-100 dark:bg-emerald-900/60 text-emerald-600 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-emerald-950 dark:text-emerald-100">
                  Document Successfully Ingested
                </h3>
                <p className="text-xs text-emerald-800 dark:text-emerald-300">
                  The document has been securely stored in MinIO, registered in PostgreSQL, and its vector chunks have been indexed into Qdrant.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-white dark:bg-zinc-900 border border-emerald-200 dark:border-emerald-800 text-xs space-y-2">
              <div className="flex justify-between">
                <span className="text-zinc-500">Document Title:</span>
                <span className="font-semibold text-zinc-900 dark:text-zinc-100">{title}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Category:</span>
                <span className="font-semibold text-zinc-900 dark:text-zinc-100">{category}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Status:</span>
                <span className="font-semibold text-emerald-600 uppercase">Ready (Indexed)</span>
              </div>
              {uploadedDoc && (
                <div className="flex justify-between">
                  <span className="text-zinc-500">Document ID:</span>
                  <span className="font-mono text-zinc-700 dark:text-zinc-300 text-[11px]">{uploadedDoc.id}</span>
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              {uploadedDoc && (
                <Link
                  href={`/documents/${uploadedDoc.id}`}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 transition cursor-pointer"
                >
                  <span>Preview Document (W-08)</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              )}
              <Link
                href="/chat"
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-md bg-accent text-white hover:bg-accent-hover transition cursor-pointer"
              >
                <span>Ask RAG Assistant</span>
              </Link>
              <button
                type="button"
                onClick={handleReset}
                className="px-3.5 py-2 text-xs font-medium rounded-md border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition text-zinc-700 dark:text-zinc-300 cursor-pointer"
              >
                Upload Another PDF
              </button>
            </div>
          </div>
        ) : (
          /* Upload Form */
          <form onSubmit={handleUpload} className="space-y-6">
            {error && (
              <div className="p-3.5 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 flex items-center gap-2 text-xs text-red-700 dark:text-red-400">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Drag & Drop File Target */}
            <div className="border-2 border-dashed border-zinc-300 dark:border-zinc-700 rounded-xl p-8 text-center hover:border-accent transition bg-zinc-50/50 dark:bg-zinc-900/30 relative">
              <input
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleFileChange}
                disabled={isUploading}
                className="absolute inset-0 opacity-0 cursor-pointer disabled:cursor-not-allowed"
              />
              <div className="flex flex-col items-center justify-center space-y-2">
                <div className="w-12 h-12 rounded-full bg-accent/10 text-accent flex items-center justify-center mb-1">
                  <UploadCloud className="w-6 h-6" />
                </div>
                {file ? (
                  <div className="space-y-1">
                    <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100 block">
                      {file.name}
                    </span>
                    <span className="text-[11px] text-zinc-400 block font-mono">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB · Valid PDF
                    </span>
                    <span className="text-[11px] text-accent underline block pt-1">
                      Click to choose a different PDF
                    </span>
                  </div>
                ) : (
                  <>
                    <p className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                      Drag and drop university PDF here, or <span className="text-accent underline">browse</span>
                    </p>
                    <p className="text-[11px] text-zinc-400">
                      Supports official circulars, exam manuals, ordinances, and hostel rules (Max 25 MB)
                    </p>
                  </>
                )}
              </div>
            </div>

            {/* Metadata Fields */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Official Document Title
                </label>
                <input
                  type="text"
                  placeholder="e.g. University Examination Regulations 2024-25"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  disabled={isUploading}
                  className="w-full px-3 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:border-accent disabled:opacity-50"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                  Document Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  disabled={isUploading}
                  className="w-full px-3 py-2 text-xs rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:border-accent disabled:opacity-50 cursor-pointer"
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
            </div>

            {/* Automated Ingestion Pipeline Options */}
            <div className="p-4 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-3">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoIndex}
                  onChange={(e) => setAutoIndex(e.target.checked)}
                  disabled={isUploading}
                  className="mt-0.5 rounded border-zinc-300 text-accent focus:ring-accent"
                />
                <div className="space-y-0.5">
                  <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 block">
                    Trigger automated ingestion pipeline immediately
                  </span>
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
                    Extracts pages via PyMuPDF, chunks text, creates embeddings using all-MiniLM-L6-v2, and indexes vector coordinates into Qdrant.
                  </p>
                </div>
              </label>
            </div>

            {/* Active Ingestion Progress Bar */}
            {isUploading && (
              <div className="space-y-2 p-4 rounded-lg bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 animate-in fade-in">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5">
                    <RefreshCw className="w-3.5 h-3.5 text-accent animate-spin" />
                    {stageMessage}
                  </span>
                  <span className="font-mono text-zinc-500">{uploadProgress}%</span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-zinc-200 dark:bg-zinc-800 overflow-hidden">
                  <div
                    className="h-full bg-accent transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Submit Actions */}
            <div className="flex justify-end gap-3 pt-2">
              <Link
                href="/documents"
                className="px-4 py-2 text-xs font-medium rounded-md border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition text-zinc-700 dark:text-zinc-300 cursor-pointer"
              >
                Cancel
              </Link>
              <button
                type="submit"
                disabled={isUploading || !file}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition disabled:opacity-40 cursor-pointer shadow-xs"
              >
                <UploadCloud className="w-4 h-4" />
                <span>{isUploading ? "Ingesting..." : "Ingest Document"}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </AppShell>
  );
}
