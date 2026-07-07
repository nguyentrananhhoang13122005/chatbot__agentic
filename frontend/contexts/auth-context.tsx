"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/api";

export interface User {
  id: string;
  email: string;
  display_name: string;
  avatar_url?: string;
  auth_provider: string;
  created_at: string;
  last_login: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (data: Record<string, string>) => Promise<void>;
  register: (data: Record<string, string>) => Promise<void>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    try {
      const data = await apiClient.get<{ user: User }>("/auth/me");
      if (data && data.user) {
        setUser(data.user);
      } else {
        setUser(null);
      }
    } catch {
      // Not authenticated or token expired
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    void apiClient
      .get<{ user: User }>("/auth/me")
      .then((data) => {
        if (!isMounted) return;
        setUser(data?.user ?? null);
      })
      .catch(() => {
        if (!isMounted) return;
        setUser(null);
      })
      .finally(() => {
        if (!isMounted) return;
        setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (data: Record<string, string>) => {
    await apiClient.post("/auth/login", data);
    await refreshMe();
  }, [refreshMe]);

  const register = useCallback(async (data: Record<string, string>) => {
    await apiClient.post("/auth/register", data);
    await refreshMe();
  }, [refreshMe]);

  const logout = useCallback(async () => {
    await apiClient.post("/auth/logout");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isLoading, login, register, logout, refreshMe }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
