import { ScoreCalculationRequest, ScoreCalculationResponse, MatchRequest } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = {
  async fetchWithCredentials(endpoint: string, options: RequestInit = {}) {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      credentials: "include", // Luôn gửi HTTPOnly cookies
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || "API Request Failed");
    }
    return res.json();
  },

  async calculateScore(data: ScoreCalculationRequest): Promise<ScoreCalculationResponse> {
    return this.fetchWithCredentials("/api/v1/scores/calculate", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async healthCheck(): Promise<{ status: string }> {
    return this.fetchWithCredentials("/health");
  },
  
  async matchSchools(data: MatchRequest) {
    return this.fetchWithCredentials("/api/v1/schools/match", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // --- Auth API ---
  async getMe() {
    return this.fetchWithCredentials("/api/v1/auth/me");
  },

  async login(data: Record<string, string>) {
    return this.fetchWithCredentials("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async register(data: Record<string, string>) {
    return this.fetchWithCredentials("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async logout() {
    return this.fetchWithCredentials("/api/v1/auth/logout", {
      method: "POST",
    });
  },

  async getGoogleUrl() {
    return this.fetchWithCredentials("/api/v1/auth/google/url");
  },
};
