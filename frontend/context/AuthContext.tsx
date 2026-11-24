"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import {
  UserProfile,
  Role,
  UserPreferences,
  DEFAULT_PREFERENCES,
} from "@/lib/mockData";
import {
  fetchCurrentUser,
  loginUser,
  fetchAdminUsers,
  updateAdminUserRole,
  logoutBackend,
  ApiUser,
} from "@/lib/api";

interface AuthContextType {
  currentUser: UserProfile;
  role: Role;
  switchRole: (newRole: Role) => void;
  isAuthenticated: boolean;
  login: (email: string, role?: Role, name?: string) => Promise<void>;
  logout: () => Promise<void>;
  loadUserFromBackend: (targetRole?: Role, targetEmail?: string) => Promise<void>;
  allUsers: UserProfile[];
  updateUserRole: (userId: string, newRole: Role) => Promise<{ success: boolean; error?: string }>;
  toggleUserStatus: (userId: string) => { success: boolean; error?: string };
  preferences: UserPreferences;
  updatePreferences: (updates: Partial<UserPreferences>) => void;
  resetPreferences: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<UserProfile>({
    id: "",
    name: "Guest",
    email: "",
    role: "student",
    createdAt: "",
    status: "active",
  });
  const [role, setRole] = useState<Role>("student");
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [allUsers, setAllUsers] = useState<UserProfile[]>([]);
  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFERENCES);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Synchronize dark/light theme
  useEffect(() => {
    const root = document.documentElement;
    if (preferences.theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [preferences.theme]);

  // Load active user from backend GET /me on startup
  const loadUserFromBackend = useCallback(async (_targetRole?: Role, _targetEmail?: string) => {
    setIsLoading(true);
    try {
      const apiUser: ApiUser = await fetchCurrentUser();
      const profile: UserProfile = {
        id: apiUser.id,
        name: apiUser.name,
        email: apiUser.email,
        role: apiUser.role as Role,
        createdAt: apiUser.created_at,
        status: "active",
      };
      setCurrentUser(profile);
      setRole(profile.role);
      setIsAuthenticated(true);
    } catch {
      setIsAuthenticated(false);
      setRole("student");
      setCurrentUser({
        id: "",
        name: "Guest",
        email: "",
        role: "student",
        createdAt: "",
        status: "active",
      });
      setAllUsers([]);
      if (typeof window !== "undefined") {
        // Remove legacy demo credentials if a previous frontend build stored them.
        localStorage.removeItem("uka_access_token");
        localStorage.removeItem("uka_user_role");
        localStorage.removeItem("uka_user_email");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUserFromBackend();
  }, [loadUserFromBackend]);

  // Load users list for admin user management
  const refreshUsersList = useCallback(async () => {
    try {
      const users = await fetchAdminUsers();
      if (users && users.length > 0) {
        setAllUsers(
          users.map((u) => ({
            id: u.id,
            name: u.name,
            email: u.email,
            role: u.role as Role,
            createdAt: u.created_at,
            status: "active",
          }))
        );
      }
    } catch {
      // Retain existing users list
    }
  }, []);

  useEffect(() => {
    if (role === "admin") {
      refreshUsersList();
    }
  }, [role, refreshUsersList]);

  // This endpoint is unavailable unless both frontend and backend dev flags are enabled.
  const login = async (email: string, overrideRole?: Role, name?: string) => {
    if (process.env.NEXT_PUBLIC_DEV_LOGIN !== "true") {
      throw new Error("Password login is disabled. Use Google or University SSO.");
    }
    setIsLoading(true);
    try {
      const res = await loginUser(email, overrideRole || "student", name);
      const profile: UserProfile = {
        id: res.user.id,
        name: res.user.name,
        email: res.user.email,
        role: res.user.role as Role,
        createdAt: res.user.created_at,
        status: "active",
      };
      setCurrentUser(profile);
      setRole(profile.role);
      setIsAuthenticated(true);
    } catch (error) {
      setIsAuthenticated(false);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Persona switching exists only for an explicitly enabled local development demo.
  const switchRole = async (newRole: Role) => {
    if (process.env.NEXT_PUBLIC_DEV_LOGIN !== "true") return;
    await login(currentUser.email || `${newRole}@university.edu`, newRole);
  };



  const logout = async () => {
    setIsAuthenticated(false);
    localStorage.removeItem("uka_user_role");
    localStorage.removeItem("uka_user_email");
    localStorage.removeItem("uka_access_token");
    setRole("student");
    setCurrentUser({ id: "", name: "Guest", email: "", role: "student", createdAt: "", status: "active" });
    try {
      await logoutBackend();
    } catch {
      // Ignore background logout network errors
    }
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  };

  // Admin user role update (W-18)
  const updateUserRole = async (
    userId: string,
    newRole: Role
  ): Promise<{ success: boolean; error?: string }> => {
    if (currentUser.id === userId && currentUser.role === "admin" && newRole !== "admin") {
      return {
        success: false,
        error: "Safety policy: You cannot remove your own administrative privileges while logged in.",
      };
    }

    const targetUser = allUsers.find((u) => u.id === userId);
    if (targetUser?.role === "admin" && targetUser.id !== currentUser.id && newRole !== "admin") {
      return {
        success: false,
        error: "Safety policy: Administrators cannot demote or modify peer administrators.",
      };
    }

    try {
      await updateAdminUserRole(userId, newRole);
      setAllUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u))
      );
      if (currentUser.id === userId) {
        setCurrentUser((prev) => ({ ...prev, role: newRole }));
        setRole(newRole);
      }
      return { success: true };
    } catch (err: any) {
      return { success: false, error: err.message || "Failed to update role on backend." };
    }
  };

  const toggleUserStatus = (userId: string): { success: boolean; error?: string } => {
    if (currentUser.id === userId && currentUser.role === "admin") {
      return {
        success: false,
        error: "Safety policy: You cannot disable your own active administrator account.",
      };
    }

    const targetUser = allUsers.find((u) => u.id === userId);
    if (targetUser?.role === "admin") {
      return {
        success: false,
        error: "Safety policy: Administrators cannot disable peer administrator accounts.",
      };
    }

    setAllUsers((prev) =>
      prev.map((u) =>
        u.id === userId
          ? { ...u, status: u.status === "active" ? "disabled" : "active" }
          : u
      )
    );
    return { success: true };
  };

  const updatePreferences = (updates: Partial<UserPreferences>) => {
    setPreferences((prev) => ({ ...prev, ...updates }));
  };

  const resetPreferences = () => {
    setPreferences(DEFAULT_PREFERENCES);
  };

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        role,
        switchRole,
        isAuthenticated,
        login,
        logout,
        loadUserFromBackend,
        allUsers,
        updateUserRole,
        toggleUserStatus,
        preferences,
        updatePreferences,
        resetPreferences,
        isLoading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
