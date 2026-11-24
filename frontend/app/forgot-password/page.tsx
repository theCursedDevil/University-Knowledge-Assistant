import Link from "next/link";
import { ArrowLeft, KeyRound } from "lucide-react";

export default function ForgotPasswordPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-zinc-50 px-4 py-10 dark:bg-zinc-950">
      <section className="w-full max-w-md rounded-xl border border-zinc-200 bg-white p-8 text-center shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100">
          <KeyRound className="h-5 w-5" />
        </div>
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Password recovery</h1>
        <p className="mt-3 text-sm leading-6 text-zinc-600 dark:text-zinc-400">
          Password recovery is handled by Google or your university identity provider. Start from the sign-in page and follow the provider&apos;s recovery process.
        </p>
        <Link href="/login" className="mt-7 inline-flex items-center gap-2 rounded-lg bg-zinc-900 px-4 py-3 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900">
          <ArrowLeft className="h-4 w-4" /> Return to sign in
        </Link>
      </section>
    </main>
  );
}
