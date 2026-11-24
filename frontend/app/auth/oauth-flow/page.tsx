import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

export default function OAuthFlowPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-zinc-50 px-4 py-10 dark:bg-zinc-950">
      <section className="w-full max-w-lg rounded-xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100">
          <ShieldCheck className="h-5 w-5" />
        </div>
        <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">Secure sign-in</h1>
        <p className="mt-3 text-sm leading-6 text-zinc-600 dark:text-zinc-400">
          Authentication is performed by Keycloak using the OpenID Connect Authorization Code flow with PKCE. The backend validates the returned token and establishes an HttpOnly cookie session. This page does not simulate authentication.
        </p>
        <Link href="/login" className="mt-6 inline-flex items-center gap-2 rounded-lg bg-zinc-900 px-4 py-3 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900">
          Go to sign in <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </main>
  );
}
