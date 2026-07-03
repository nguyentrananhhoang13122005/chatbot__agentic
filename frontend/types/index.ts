export interface ScoreCalculationRequest {
  scores: Record<string, number>;
  bonus: number;
  k: number;
}

export interface CombinationResult {
  code: string;
  subjects: string[];
  total: number;
  below_threshold: boolean;
  rank: number;
}

export interface ScoreCalculationResponse {
  top_combinations: CombinationResult[];
  analysis: Record<string, unknown>;
}

export interface MatchRequest {
  scores: Record<string, number>;
  bonus: number;
  methods?: string[];
  k: number;
  year_priority?: number[];
  top_n_combos?: number;
  province?: string | null;
  major?: string | null;
  stream: boolean;
}

export interface SchoolMatchResult {
  schools: Record<string, unknown>[];
  top_combinations: Record<string, unknown>[];
  strength: Record<string, unknown>;
  warnings: string[];
  analysis: string;
}

export interface RecommendRequest {
  user_query: string;
  stream: boolean;
  pre_extracted_school?: string;
  pre_extracted_location?: string;
  pre_extracted_keyword?: string;
  pre_extracted_year?: number;
}

export interface RecommendResponse {
  answer: string;
}
