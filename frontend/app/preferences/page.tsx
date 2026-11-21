"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Sliders,
  Sun,
  Moon,
  Laptop,
  Bell,
  Languages,
  CheckCircle2,
  RefreshCw,
  ArrowLeft,
  Quote,
  Eye,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { UserPreferences } from "@/lib/mockData";

export default function PreferencesPage() {
  const { preferences, updatePreferences, resetPreferences } = useAuth();
  const [formData, setFormData] = useState<UserPreferences>(preferences);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    updatePreferences(formData);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  const handleReset = () => {
    resetPreferences();
    setFormData(preferences);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2000);
  };

  return (
    <AppShell>
      <div className="p-6 sm:p-8 max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Sliders className="w-5 h-5 text-accent" />
              <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Account Preferences (W-17)
              </h1>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Customize appearance, display density, notification alerts, and accessibility options
            </p>
          </div>

          <Link
            href="/profile"
            className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 transition self-start sm:self-auto"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Profile (W-10)
          </Link>
        </div>

        {savedSuccess && (
          <div className="p-3.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 flex items-center gap-2 text-xs text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>Preferences saved successfully to local session state.</span>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-6">
          {/* Appearance Section */}
          <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Sun className="w-4 h-4 text-accent" />
              Interface Theme & Appearance
            </h3>

            <div className="grid grid-cols-3 gap-3">
              {[
                { id: "light", label: "Light Theme", icon: Sun },
                { id: "dark", label: "Dark Theme", icon: Moon },
                { id: "system", label: "System Default", icon: Laptop },
              ].map((opt) => {
                const Icon = opt.icon;
                const isSelected = formData.theme === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setFormData({ ...formData, theme: opt.id as any })}
                    className={`p-3 rounded-md border text-center transition flex flex-col items-center gap-2 cursor-pointer ${
                      isSelected
                        ? "border-accent bg-accent/5 dark:bg-accent/10 text-accent font-semibold"
                        : "border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-xs">{opt.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Display Density & Citations */}
          <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Eye className="w-4 h-4 text-accent" />
              Chat Display & Citation Highlighting
            </h3>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-semibold text-zinc-900 dark:text-zinc-100 block">
                    Auto-Scroll Streamed Responses
                  </span>
                  <span className="text-zinc-500 dark:text-zinc-400 text-[11px]">
                    Automatically scroll the chat area as incoming tokens arrive from Groq LLM.
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={formData.autoScrollChat}
                  onChange={(e) => setFormData({ ...formData, autoScrollChat: e.target.checked })}
                  className="rounded border-zinc-300 text-accent focus:ring-accent"
                />
              </div>

              <div className="border-t border-zinc-100 dark:border-zinc-800 pt-3 flex items-center justify-between">
                <div>
                  <span className="font-semibold text-zinc-900 dark:text-zinc-100 block">
                    Highlight Verified Citations
                  </span>
                  <span className="text-zinc-500 dark:text-zinc-400 text-[11px]">
                    Display prominent source badges for all grounded university ordinances.
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={formData.citationHighlighter}
                  onChange={(e) => setFormData({ ...formData, citationHighlighter: e.target.checked })}
                  className="rounded border-zinc-300 text-accent focus:ring-accent"
                />
              </div>
            </div>
          </div>

          {/* Notifications & Language */}
          <div className="p-5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Bell className="w-4 h-4 text-accent" />
              Alerts & Language
            </h3>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-semibold text-zinc-900 dark:text-zinc-100 block">
                    Email Digest of New Regulations
                  </span>
                  <span className="text-zinc-500 dark:text-zinc-400 text-[11px]">
                    Receive email notifications when new academic circulars or exam ordinances are uploaded.
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={formData.emailNotifications}
                  onChange={(e) => setFormData({ ...formData, emailNotifications: e.target.checked })}
                  className="rounded border-zinc-300 text-accent focus:ring-accent"
                />
              </div>

              <div className="border-t border-zinc-100 dark:border-zinc-800 pt-3 flex items-center justify-between">
                <div>
                  <span className="font-semibold text-zinc-900 dark:text-zinc-100 block">
                    Preferred UI Language
                  </span>
                  <span className="text-zinc-500 dark:text-zinc-400 text-[11px]">
                    Select interface language for system prompts and labels.
                  </span>
                </div>
                <select
                  value={formData.language}
                  onChange={(e) => setFormData({ ...formData, language: e.target.value as any })}
                  className="py-1 px-3 text-xs rounded-md border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200"
                >
                  <option value="en">English (Official)</option>
                  <option value="hi">Hindi (हिन्दी)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 text-xs font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5 text-zinc-400" />
              Reset to Defaults
            </button>

            <button
              type="submit"
              className="px-5 py-2 rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-xs font-semibold hover:bg-zinc-800 dark:hover:bg-zinc-200 transition shadow-xs cursor-pointer"
            >
              Save Preferences
            </button>
          </div>
        </form>
      </div>
    </AppShell>
  );
}
