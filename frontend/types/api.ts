export interface User {
  id: string;
  email: string;
  name?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ApiErrorResponse {
  detail: string | Array<{ loc: string[]; msg: string; type: string }>;
}

export interface ScoreRequest {
  scores: Record<string, number>; // e.g. { "Toan": 8.0, "Ly": 7.5 }
}

export interface ScoreCalculationResponse {
  total_score: number;
  block: string; // e.g. "A00"
}

export interface SchoolMatchRequest {
  block: string;
  score: number;
  preferences?: string[];
}

export interface SchoolMatchResult {
  matches: Array<{
    school_id: string;
    school_name: string;
    match_rate: number;
    safe_score: number;
  }>;
}
