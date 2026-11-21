"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import {
  UserProfile,
  Role,
  MOCK_USERS,
  UserPreferences,
  DEFAULT_PREFERENCES,
} from "@/lib/mockData";

interface AuthContextType {
  currentUser: UserProfile;
  role: Role;
  switchRole: (newRole: Role) => void;
  isAuthenticated: boolean;
  login: (email: string, role?: Role) => void;
  logout: () => void;
  allUsers: UserProfile[];
  updateUserRole: (userId: string, newRole: Role) => { success: boolean; error?: string };
  toggleUserStatus: (userId: string) => { success: boolean; error?: string };
  preferences: UserPreferences;
  updatePreferences: (updates: Partial<UserPreferences>) => void;
  resetPreferences: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [usersList, setUsersList] = useState<UserProfile[]>(MOCK_USERS);
  const [currentUser, setCurrentUser] = useState<UserProfile>(MOCK_USERS[0]); // default: student
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(true);
  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFERENCES);

  // Synchronize dark/light class with preferences
  useEffect(() => {
    const root = document.documentElement;
    if (preferences.theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [preferences.theme]);

  // Switch role by picking a corresponding mock persona
  const switchRole = (newRole: Role) => {
    const match = usersList.find((u) => u.role === newRole) || {
      id: `usr-${newRole}`,
      name: `${newRole.toUpperCase()} User`,
      email: `${newRole}@university.edu`,
      role: newRole,
      createdAt: new Date().toISOString(),
      status: "active",
    };
    setCurrentUser(match);
  };

  const login = (email: string, overrideRole?: Role) => {
    const existing = usersList.find((u) => u.email.toLowerCase() === email.toLowerCase());
    if (existing) {
      setCurrentUser(existing);
    } else {
      const newUser: UserProfile = {
        id: `usr-${Date.now()}`,
        name: email.split("@")[0].replace(".", " ").toUpperCase(),
        email: email,
        role: overrideRole || "student",
        createdAt: new Date().toISOString(),
        status: "active",
      };
      setUsersList((prev) => [newUser, ...prev]);
      setCurrentUser(newUser);
    }
    setIsAuthenticated(true);
  };

  const logout = () => {
    setIsAuthenticated(false);
  };

  // Admin user management functions (W-18)
  const updateUserRole = (userId: string, newRole: Role): { success: boolean; error?: string } => {
    // Safety Requirement: Do not allow an administrator to accidentally remove their own admin access
    if (currentUser.id === userId && currentUser.role === "admin" && newRole !== "admin") {
      return {
        success: false,
        error: "Safety policy: You cannot remove your own administrative privileges while logged in.",
      };
    }

    setUsersList((prev) =>
      prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u))
    );

    // If updating current user's profile
    if (currentUser.id === userId) {
      setCurrentUser((prev) => ({ ...prev, role: newRole }));
    }

    return { success: true };
  };

  const toggleUserStatus = (userId: string): { success: boolean; error?: string } => {
    // Safety Requirement: Cannot disable own admin account
    if (currentUser.id === userId && currentUser.role === "admin") {
      return {
        success: false,
        error: "Safety policy: You cannot disable your own active administrator account.",
      };
    }

    setUsersList((prev) =>
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
        role: currentUser.role,
        switchRole,
        isAuthenticated,
        login,
        logout,
        allUsers: usersList,
        updateUserRole,
        toggleUserStatus,
        preferences,
        updatePreferences,
        resetPreferences,
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
