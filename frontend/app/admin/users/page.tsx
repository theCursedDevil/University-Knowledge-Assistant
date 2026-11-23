"use client";

import React, { useState } from "react";
import {
  Users,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  UserCheck,
  UserX,
  Edit2,
  Eye,
  X,
  Filter,
  Info,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { PermissionDeniedState, NoResultsState } from "@/components/SystemStates";
import { useAuth } from "@/context/AuthContext";
import { UserProfile, Role } from "@/lib/mockData";
import { formatDate } from "@/lib/utils";

export default function AdminUserManagementPage() {
  const { role, currentUser, allUsers, updateUserRole, toggleUserStatus } = useAuth();

  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Selected user for inspection drawer/modal
  const [viewingUser, setViewingUser] = useState<UserProfile | null>(null);

  // Role Edit Confirmation Modal State
  const [editingUser, setEditingUser] = useState<UserProfile | null>(null);
  const [selectedNewRole, setSelectedNewRole] = useState<Role>("student");

  // Status Toggle Confirmation Modal State
  const [statusTargetUser, setStatusTargetUser] = useState<UserProfile | null>(null);

  // Feedback notifications
  const [toastMessage, setToastMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Role Guard: S-5 Permission Denied
  if (role !== "admin") {
    return (
      <AppShell>
        <PermissionDeniedState requiredRole="admin" />
      </AppShell>
    );
  }

  // Filtered Users List
  const filteredUsers = allUsers.filter((u) => {
    const matchesSearch =
      u.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.id.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesRole = roleFilter === "all" || u.role === roleFilter;
    const matchesStatus = statusFilter === "all" || (u.status || "active") === statusFilter;

    return matchesSearch && matchesRole && matchesStatus;
  });

  const showToast = (text: string, type: "success" | "error" = "success") => {
    setToastMessage({ type, text });
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleOpenRoleModal = (user: UserProfile) => {
    setEditingUser(user);
    setSelectedNewRole(user.role);
  };

  const handleConfirmRoleChange = async () => {
    if (!editingUser) return;

    const res = await updateUserRole(editingUser.id, selectedNewRole);
    if (!res.success) {
      showToast(res.error || "Failed to update role.", "error");
    } else {
      showToast(`User ${editingUser.name}'s role updated to ${selectedNewRole.toUpperCase()}.`);
    }
    setEditingUser(null);
  };

  const handleConfirmStatusToggle = () => {
    if (!statusTargetUser) return;

    const res = toggleUserStatus(statusTargetUser.id);
    if (!res.success) {
      showToast(res.error || "Failed to toggle user status.", "error");
    } else {
      const nextStatus = statusTargetUser.status === "active" ? "disabled" : "active";
      showToast(`User account ${statusTargetUser.email} has been set to ${nextStatus}.`);
    }
    setStatusTargetUser(null);
  };

  return (
    <AppShell>
      <div className="p-6 sm:p-8 max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Users className="w-5 h-5 text-accent" />
              <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                User Management
              </h1>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Manage university role assignments, audit account access, and enforce security policies
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
              <ShieldCheck className="w-3.5 h-3.5 text-accent" />
              Logged in as Administrator
            </span>
          </div>
        </div>

        {/* Toast Notification */}
        {toastMessage && (
          <div
            className={`p-3.5 rounded-lg border text-xs flex items-center justify-between ${
              toastMessage.type === "success"
                ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300"
                : "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800 text-red-800 dark:text-red-300"
            }`}
          >
            <div className="flex items-center gap-2">
              {toastMessage.type === "success" ? (
                <CheckCircle2 className="w-4 h-4 shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 shrink-0" />
              )}
              <span>{toastMessage.text}</span>
            </div>
            <button
              onClick={() => setToastMessage(null)}
              className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Security Policy Banner */}
        <div className="p-4 rounded-lg bg-zinc-100/80 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-600 dark:text-zinc-400 flex items-start gap-3">
          <Info className="w-4 h-4 text-accent shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-semibold text-zinc-900 dark:text-zinc-100">
              Role Security Policy & Self-Lockout Prevention
            </div>
            <p>
              Administrators cannot revoke their own admin rights or disable their own account while actively logged in.
              All role changes require explicit secondary confirmation to prevent accidental permission escalation.
            </p>
          </div>
        </div>

        {/* Controls: Search and Filters */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5 pointer-events-none" />
            <input
              type="text"
              placeholder="Search user by name, email, or user ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-xs rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-hidden focus:border-accent"
            />
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs text-zinc-600 dark:text-zinc-400">
              <Filter className="w-3.5 h-3.5 text-zinc-400" />
              <span>Role:</span>
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="bg-transparent text-zinc-900 dark:text-zinc-100 font-medium focus:outline-hidden cursor-pointer"
              >
                <option value="all">All Roles</option>
                <option value="student">Student</option>
                <option value="faculty">Faculty</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs text-zinc-600 dark:text-zinc-400">
              <span>Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-transparent text-zinc-900 dark:text-zinc-100 font-medium focus:outline-hidden cursor-pointer"
              >
                <option value="all">All Statuses</option>
                <option value="active">Active</option>
                <option value="disabled">Disabled</option>
              </select>
            </div>
          </div>
        </div>

        {/* Users Table */}
        {filteredUsers.length === 0 ? (
          <NoResultsState
            query={searchQuery || roleFilter}
            onClear={() => {
              setSearchQuery("");
              setRoleFilter("all");
              setStatusFilter("all");
            }}
          />
        ) : (
          <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden shadow-2xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950/50 text-zinc-500 dark:text-zinc-400">
                    <th className="py-3 px-4 font-semibold">User</th>
                    <th className="py-3 px-4 font-semibold">Assigned Role</th>
                    <th className="py-3 px-4 font-semibold">Account Status</th>
                    <th className="py-3 px-4 font-semibold">Created Date</th>
                    <th className="py-3 px-4 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800 text-zinc-700 dark:text-zinc-300">
                  {filteredUsers.map((user) => {
                    const isSelf = user.id === currentUser.id;
                    const isActive = (user.status || "active") === "active";

                    return (
                      <tr
                        key={user.id}
                        className="hover:bg-zinc-50/50 dark:hover:bg-zinc-800/40 transition"
                      >
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center font-bold text-[11px] text-zinc-800 dark:text-zinc-200 shrink-0">
                              {user.name.slice(0, 2).toUpperCase()}
                            </div>
                            <div>
                              <div className="font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
                                {user.name}
                                {isSelf && (
                                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-accent/10 text-accent border border-accent/20">
                                    You
                                  </span>
                                )}
                              </div>
                              <div className="text-[11px] text-zinc-400">{user.email}</div>
                            </div>
                          </div>
                        </td>

                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ${
                              user.role === "admin"
                                ? "bg-purple-100 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800"
                                : user.role === "faculty"
                                ? "bg-blue-100 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800"
                                : "bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700"
                            }`}
                          >
                            {user.role === "admin" && <Shield className="w-3 h-3 text-purple-600" />}
                            {user.role.toUpperCase()}
                          </span>
                        </td>

                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center gap-1.5 text-[11px] font-medium ${
                              isActive
                                ? "text-emerald-600 dark:text-emerald-400"
                                : "text-zinc-400 dark:text-zinc-500"
                            }`}
                          >
                            <span
                              className={`w-2 h-2 rounded-full ${
                                isActive ? "bg-emerald-500 animate-pulse" : "bg-zinc-400"
                              }`}
                            />
                            {isActive ? "Active" : "Disabled"}
                          </span>
                        </td>

                        <td className="py-3.5 px-4 text-zinc-400 font-mono text-[11px]">
                          {formatDate(user.createdAt)}
                        </td>

                        <td className="py-3.5 px-4 text-right">
                          <div className="inline-flex items-center gap-1">
                            <button
                              onClick={() => setViewingUser(user)}
                              title="View User Details"
                              className="p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition cursor-pointer"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>

                            <button
                              onClick={() => handleOpenRoleModal(user)}
                              title="Edit Role"
                              className="p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition cursor-pointer"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>

                            <button
                              onClick={() => setStatusTargetUser(user)}
                              disabled={isSelf}
                              title={
                                isSelf
                                  ? "Cannot disable own admin account"
                                  : isActive
                                  ? "Disable Account"
                                  : "Enable Account"
                              }
                              className={`p-1.5 rounded transition ${
                                isSelf
                                  ? "opacity-30 cursor-not-allowed text-zinc-400"
                                  : isActive
                                  ? "hover:bg-red-50 dark:hover:bg-red-950/30 text-zinc-500 hover:text-red-600 cursor-pointer"
                                  : "hover:bg-emerald-50 dark:hover:bg-emerald-950/30 text-zinc-500 hover:text-emerald-600 cursor-pointer"
                              }`}
                            >
                              {isActive ? (
                                <UserX className="w-3.5 h-3.5" />
                              ) : (
                                <UserCheck className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="p-3 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/50 text-[11px] text-zinc-500 dark:text-zinc-400 flex items-center justify-between">
              <div>
                Showing {filteredUsers.length} of {allUsers.length} registered users
              </div>
              <div>Prepared for Keycloak Admin REST API Synchronization</div>
            </div>
          </div>
        )}

        {/* Modal 1: View User Details */}
        {viewingUser && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="w-full max-w-md rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="p-5 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-accent" />
                  <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">User Profile Details</h3>
                </div>
                <button
                  onClick={() => setViewingUser(null)}
                  className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="p-5 space-y-4 text-xs">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center font-bold text-base text-zinc-800 dark:text-zinc-200">
                    {viewingUser.name.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <h4 className="font-bold text-sm text-zinc-900 dark:text-zinc-100">{viewingUser.name}</h4>
                    <p className="text-zinc-500">{viewingUser.email}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-3 border-t border-zinc-100 dark:border-zinc-800">
                  <div className="p-2.5 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                    <span className="text-[10px] text-zinc-400 block uppercase">User ID</span>
                    <span className="font-mono text-[11px] text-zinc-700 dark:text-zinc-300">{viewingUser.id}</span>
                  </div>
                  <div className="p-2.5 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                    <span className="text-[10px] text-zinc-400 block uppercase">Role</span>
                    <span className="font-semibold text-[11px] text-zinc-700 dark:text-zinc-300 capitalize">{viewingUser.role}</span>
                  </div>
                  <div className="p-2.5 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                    <span className="text-[10px] text-zinc-400 block uppercase">Status</span>
                    <span className="font-semibold text-[11px] text-zinc-700 dark:text-zinc-300 capitalize">{viewingUser.status || "active"}</span>
                  </div>
                  <div className="p-2.5 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800">
                    <span className="text-[10px] text-zinc-400 block uppercase">Enrolled</span>
                    <span className="font-mono text-[11px] text-zinc-700 dark:text-zinc-300">{formatDate(viewingUser.createdAt)}</span>
                  </div>
                </div>

                <div className="p-3 rounded bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-[11px] text-zinc-500 dark:text-zinc-400 space-y-1">
                  <div className="font-semibold text-zinc-700 dark:text-zinc-300">Identity Provider Federation</div>
                  <p>Keycloak Realm: <code className="text-zinc-800 dark:text-zinc-200 font-mono">university-realm</code></p>
                  <p>Authentication Flow: <code className="text-zinc-800 dark:text-zinc-200 font-mono">Authorization Code + PKCE</code></p>
                </div>
              </div>

              <div className="p-4 bg-zinc-50 dark:bg-zinc-950 border-t border-zinc-200 dark:border-zinc-800 flex justify-end">
                <button
                  onClick={() => setViewingUser(null)}
                  className="px-4 py-1.5 text-xs font-medium rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Modal 2: Edit Role Confirmation Dialog */}
        {editingUser && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="w-full max-w-md rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="p-5 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
                <div className="flex items-center gap-2 text-zinc-900 dark:text-zinc-100">
                  <ShieldAlert className="w-4 h-4 text-accent" />
                  <h3 className="text-sm font-bold">Confirm Role Change</h3>
                </div>
                <button
                  onClick={() => setEditingUser(null)}
                  className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="p-5 space-y-4 text-xs">
                <p className="text-zinc-600 dark:text-zinc-400">
                  You are modifying permissions for user{" "}
                  <strong className="text-zinc-900 dark:text-zinc-100 font-semibold">{editingUser.name}</strong> (
                  <span className="font-mono text-zinc-500">{editingUser.email}</span>).
                </p>

                <div className="space-y-1.5">
                  <label className="font-semibold text-zinc-700 dark:text-zinc-300">Select New Role</label>
                  <div className="grid grid-cols-3 gap-2">
                    {(["student", "faculty", "admin"] as Role[]).map((r) => (
                      <button
                        key={r}
                        type="button"
                        onClick={() => setSelectedNewRole(r)}
                        className={`p-2.5 rounded-lg border text-center font-medium capitalize transition cursor-pointer ${
                          selectedNewRole === r
                            ? "border-accent bg-accent/10 text-accent font-bold"
                            : "border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300"
                        }`}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>

                {editingUser.id === currentUser.id && editingUser.role === "admin" && selectedNewRole !== "admin" && (
                  <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-[11px] text-red-700 dark:text-red-400 flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>
                      <strong>Warning:</strong> You cannot remove your own administrative privileges. The policy engine will reject this change.
                    </span>
                  </div>
                )}
              </div>

              <div className="p-4 bg-zinc-50 dark:bg-zinc-950 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="px-3.5 py-1.5 text-xs font-medium rounded-md border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition text-zinc-700 dark:text-zinc-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmRoleChange}
                  className="px-3.5 py-1.5 text-xs font-semibold rounded-md bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 transition cursor-pointer"
                >
                  Confirm Permission Change
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Modal 3: Enable / Disable Status Confirmation Dialog */}
        {statusTargetUser && (
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="w-full max-w-md rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="p-5 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
                <div className="flex items-center gap-2 text-zinc-900 dark:text-zinc-100">
                  <AlertTriangle className="w-4 h-4 text-accent" />
                  <h3 className="text-sm font-bold">
                    {statusTargetUser.status === "active" ? "Disable User Account" : "Activate User Account"}
                  </h3>
                </div>
                <button
                  onClick={() => setStatusTargetUser(null)}
                  className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="p-5 space-y-3 text-xs text-zinc-600 dark:text-zinc-400">
                <p>
                  Are you sure you want to{" "}
                  <strong>{statusTargetUser.status === "active" ? "disable" : "enable"}</strong> account access for{" "}
                  <strong className="text-zinc-900 dark:text-zinc-100">{statusTargetUser.name}</strong> (
                  <span className="font-mono">{statusTargetUser.email}</span>)?
                </p>
                {statusTargetUser.status === "active" ? (
                  <p className="text-[11px] text-zinc-500">
                    Disabling this account will revoke OAuth 2.0 token refresh capabilities and block chat interactions.
                  </p>
                ) : (
                  <p className="text-[11px] text-zinc-500">
                    Enabling this account will restore standard login privileges and document access rights.
                  </p>
                )}
              </div>

              <div className="p-4 bg-zinc-50 dark:bg-zinc-950 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setStatusTargetUser(null)}
                  className="px-3.5 py-1.5 text-xs font-medium rounded-md border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition text-zinc-700 dark:text-zinc-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmStatusToggle}
                  className={`px-3.5 py-1.5 text-xs font-semibold rounded-md text-white transition cursor-pointer ${
                    statusTargetUser.status === "active"
                      ? "bg-red-600 hover:bg-red-700"
                      : "bg-emerald-600 hover:bg-emerald-700"
                  }`}
                >
                  {statusTargetUser.status === "active" ? "Confirm Account Disable" : "Confirm Account Activation"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
