"use client";

import { Quote, ShieldCheck } from "lucide-react";
import { AppShell } from "@/components/AppShell";

export default function CitationsPage() {
  return (
    <AppShell>
      <main className="mx-auto max-w-4xl space-y-6 p-6 sm:p-8">
        <header className="space-y-2 border-b border-zinc-200 pb-6 dark:border-zinc-800">
          <div className="flex items-center gap-2">
            <Quote className="h-5 w-5 text-zinc-600 dark:text-zinc-300" />
            <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Source citations</h1>
          </div>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Sources are shown with the assistant response that used them.</p>
        </header>
        <section className="rounded-xl border border-zinc-200 p-6 dark:border-zinc-800">
          <div className="flex items-center gap-2 text-sm font-medium text-zinc-800 dark:text-zinc-200">
            <ShieldCheck className="h-4 w-4" />
            Citation provenance
          </div>
          <p className="mt-3 text-sm leading-6 text-zinc-600 dark:text-zinc-400">
            This page does not display a separate citation archive yet. To inspect a source, open a conversation and use the Sources attached to the relevant answer.
          </p>
        </section>
      </main>
    </AppShell>
  );
}
