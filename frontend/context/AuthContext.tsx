"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import {
  UserProfile,
  Role,
  MOCK_USERS,
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
  const [currentUser, setCurrentUser] = useState<UserProfile>(MOCK_USERS[0]);
  const [role, setRole] = useState<Role>("student");
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(true);
  const [allUsers, setAllUsers] = useState<UserProfile[]>(MOCK_USERS);
  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFERENCES);
  const [isLoading, setIsLoading] = useState<boolean>(false);

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
  const loadUserFromBackend = useCallback(async (targetRole?: Role, targetEmail?: string) => {
    setIsLoading(true);
    try {
      const activeRole = targetRole || (localStorage.getItem("uka_user_role") as Role) || "student";
      const activeEmail = targetEmail || localStorage.getItem("uka_user_email") || undefined;
      const apiUser: ApiUser = await fetchCurrentUser(activeRole, activeEmail);

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
      localStorage.setItem("uka_user_role", profile.role);
      localStorage.setItem("uka_user_email", profile.email);
    } catch {
      // Fallback to local persona state if backend is unreachable during build
      const fallbackRole = targetRole || "student";
      const fallbackUser = MOCK_USERS.find((u) => u.role === fallbackRole) || MOCK_USERS[0];
      setCurrentUser(fallbackUser);
      setRole(fallbackUser.role);
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

  // 1-Click Role Switcher (Student / Faculty / Admin)
  const switchRole = async (newRole: Role) => {
    setRole(newRole);
    localStorage.setItem("uka_user_role", newRole);
    localStorage.removeItem("uka_user_email"); // reset custom email on role persona switch
    await loadUserFromBackend(newRole);
  };

  // Login entry point connected to POST /auth/login
  const login = async (email: string, overrideRole?: Role, name?: string) => {
    setIsLoading(true);
    try {
      const selectedRole = overrideRole || "student";
      const res = await loginUser(email, selectedRole, name);
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
      localStorage.setItem("uka_user_role", profile.role);
      localStorage.setItem("uka_user_email", profile.email);
    } catch {
      // Fallback local provision
      const newUser: UserProfile = {
        id: `usr-${Date.now()}`,
        name: name || email.split("@")[0].replace(".", " ").toUpperCase(),
        email: email,
        role: overrideRole || "student",
        createdAt: new Date().toISOString(),
        status: "active",
      };
      setCurrentUser(newUser);
      setRole(newUser.role);
      setIsAuthenticated(true);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsAuthenticated(false);
    localStorage.removeItem("uka_user_role");
    localStorage.removeItem("uka_user_email");
    try {
      await logoutBackend();
    } catch {
      // Ignore background logout network errors
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
