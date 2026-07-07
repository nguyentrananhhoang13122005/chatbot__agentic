"use client";

import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/api";
import { AuthResponse, User } from "@/types/api";
import { toast } from "sonner";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize from local storage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem("token");
    const storedUser = localStorage.getItem("user");
    
    if (storedToken && storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (e) {
        console.error("Failed to parse stored user", e);
      }
    }
    
    setIsLoading(false);
  }, []);

  const login = useCallback(async (credentials: Record<string, string>) => {
    try {
      const response = await apiClient.post<AuthResponse>("/login", credentials);
      localStorage.setItem("token", response.access_token);
      localStorage.setItem("user", JSON.stringify(response.user));
      setUser(response.user);
      toast.success("Đăng nhập thành công!");
      return response;
    } catch (error: any) {
      toast.error(error.message || "Đăng nhập thất bại");
      throw error;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
    toast.info("Đã đăng xuất");
  }, []);

  return {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout
  };
}
