"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  History,
  FileText,
  Quote,
  User,
  Sliders,
  UploadCloud,
  Layers,
  BarChart3,
  Users,
  LogOut,
  Shield,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
}

export function Sidebar({ isOpen, onClose }: { isOpen?: boolean; onClose?: () => void }) {
  const pathname = usePathname();
  const { role, currentUser, logout } = useAuth();

  const mainNavItems: NavItem[] = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Chat Assistant", href: "/chat", icon: MessageSquare },
    { name: "Conversations", href: "/conversations", icon: History },
    { name: "Document Catalog", href: "/documents", icon: FileText },
    { name: "Source Citations", href: "/citations", icon: Quote },
    { name: "User Profile", href: "/profile", icon: User },
    { name: "Account Preferences", href: "/preferences", icon: Sliders },
  ];

  const adminNavItems: NavItem[] = [
    { name: "Document Upload", href: "/admin/upload", icon: UploadCloud },
    { name: "Metadata Management", href: "/admin/metadata", icon: Layers },
    { name: "Analytics Dashboard", href: "/admin/analytics", icon: BarChart3 },
    { name: "User Management", href: "/admin/users", icon: Users },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden backdrop-blur-xs"
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          "w-64 border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50/70 dark:bg-zinc-950/70 flex flex-col justify-between shrink-0 transition-transform duration-200 ease-in-out z-40 fixed md:static inset-y-0 left-0",
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {/* Main Navigation */}
          <div>
            <div className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
              Main Menu
            </div>
            <nav className="space-y-0.5">
              {mainNavItems.map((item) => {
                const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onClose}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition",
                      isActive
                        ? "bg-zinc-200/70 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-semibold"
                        : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 hover:text-zinc-900 dark:hover:text-zinc-100"
                    )}
                  >
                    <Icon className={cn("w-4 h-4", isActive ? "text-accent" : "text-zinc-400")} />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Admin Navigation (Role-Restricted to Admin) */}
          {role === "admin" && (
            <div>
              <div className="flex items-center justify-between px-3 mb-2">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-accent">
                  Admin Console
                </span>
                <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-accent/10 text-accent font-semibold">
                  PRIVILEGED
                </span>
              </div>
              <nav className="space-y-0.5">
                {adminNavItems.map((item) => {
                  const isActive = pathname === item.href || pathname.startsWith(item.href);
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={onClose}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition",
                        isActive
                          ? "bg-zinc-200/70 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-semibold"
                          : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 hover:text-zinc-900 dark:hover:text-zinc-100"
                      )}
                    >
                      <Icon className={cn("w-4 h-4", isActive ? "text-accent" : "text-zinc-400")} />
                      <span>{item.name}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>
          )}
        </div>

        {/* Footer User Info & Session Card */}
        <div className="p-3 border-t border-zinc-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-900/40">
          <div className="flex items-center justify-between gap-2 p-2 rounded-md bg-zinc-100/80 dark:bg-zinc-800/60">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-7 h-7 rounded-full bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-xs font-semibold flex items-center justify-center shrink-0">
                {currentUser.name.charAt(0)}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                  {currentUser.name}
                </p>
                <p className="text-[10px] text-zinc-500 dark:text-zinc-400 truncate capitalize">
                  {currentUser.role} · {currentUser.status}
                </p>
              </div>
            </div>

            <Link
              href="/login"
              className="p-1.5 text-zinc-400 hover:text-red-500 rounded transition"
              title="Sign Out"
              onClick={logout}
            >
              <LogOut className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </aside>
    </>
  );
}
