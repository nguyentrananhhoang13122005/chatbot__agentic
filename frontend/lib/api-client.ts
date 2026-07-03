import { ScoreCalculationRequest, ScoreCalculationResponse, MatchRequest } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = {
  async calculateScore(data: ScoreCalculationRequest): Promise<ScoreCalculationResponse> {
    const res = await fetch(`${API_BASE_URL}/api/v1/scores/calculate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to calculate score");
    return res.json();
  },

  async healthCheck(): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE_URL}/health`);
    if (!res.ok) throw new Error("Health check failed");
    return res.json();
  },
  
  async matchSchools(data: MatchRequest) {
    const res = await fetch(`${API_BASE_URL}/api/v1/schools/match`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to match schools");
    return res.json();
  }
};
