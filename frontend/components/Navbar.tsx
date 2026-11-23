"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sparkles,
  Sun,
  Moon,
  Search,
  User as UserIcon,
  Shield,
  GraduationCap,
  Briefcase,
  Menu,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Role } from "@/lib/mockData";

export function Navbar({ onToggleSidebar }: { onToggleSidebar?: () => void }) {
  const pathname = usePathname();
  const { currentUser, role, switchRole, preferences, updatePreferences } = useAuth();

  const toggleTheme = () => {
    updatePreferences({ theme: preferences.theme === "dark" ? "light" : "dark" });
  };

  const roleIcons: Record<Role, React.ReactNode> = {
    student: <GraduationCap className="w-3.5 h-3.5 text-accent" />,
    faculty: <Briefcase className="w-3.5 h-3.5 text-blue-500" />,
    admin: <Shield className="w-3.5 h-3.5 text-red-500" />,
  };

  return (
    <header className="h-14 border-b border-zinc-200 dark:border-zinc-800 bg-white/95 dark:bg-zinc-950/95 backdrop-blur-md sticky top-0 z-30 flex items-center justify-between px-4 sm:px-6">
      <div className="flex items-center gap-3">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="p-1.5 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-600 dark:text-zinc-400 md:hidden"
            aria-label="Toggle Navigation"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        <Link href="/dashboard" className="flex items-center gap-2 group">
          <div className="w-7 h-7 rounded-md bg-zinc-900 dark:bg-zinc-100 flex items-center justify-center text-white dark:text-zinc-900 shadow-sm">
            <Sparkles className="w-4 h-4 text-accent" />
          </div>
          <span className="font-semibold text-sm tracking-tight text-zinc-900 dark:text-zinc-100">
            University <span className="font-normal text-zinc-500 dark:text-zinc-400">Knowledge Assistant</span>
          </span>
        </Link>
      </div>

      <div className="flex items-center gap-3">
        {/* Quick Document Search Bar */}
        <Link
          href="/documents"
          className="hidden md:flex items-center gap-2 px-3 py-1.5 text-xs text-zinc-400 dark:text-zinc-500 bg-zinc-50 dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-800 rounded-md transition"
        >
          <Search className="w-3.5 h-3.5" />
          <span>Search regulations, bylaws...</span>
          <kbd className="text-[10px] bg-zinc-200 dark:bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-500">⌘K</kbd>
        </Link>

        {/* Official University Institutional Role Badge */}
        <div className="flex items-center">
          {role === "admin" && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
              <Shield className="w-3.5 h-3.5" />
              <span>Administrator</span>
            </span>
          )}
          {role === "faculty" && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
              <Briefcase className="w-3.5 h-3.5" />
              <span>Faculty</span>
            </span>
          )}
          {role === "student" && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
              <GraduationCap className="w-3.5 h-3.5" />
              <span>Student</span>
            </span>
          )}
        </div>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-md text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
          aria-label="Toggle dark mode"
          title={`Switch to ${preferences.theme === "dark" ? "light" : "dark"} mode`}
        >
          {preferences.theme === "dark" ? (
            <Sun className="w-4 h-4 text-zinc-300" />
          ) : (
            <Moon className="w-4 h-4 text-zinc-600" />
          )}
        </button>

        {/* Profile Link */}
        <Link
          href="/profile"
          className="flex items-center gap-2 p-1 rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
          title={`${currentUser.name} (${currentUser.role})`}
        >
          <div className="w-7 h-7 rounded-full bg-accent/10 border border-accent/30 text-accent flex items-center justify-center text-xs font-semibold">
            {currentUser.name.charAt(0)}
          </div>
        </Link>
      </div>
    </header>
  );
}
