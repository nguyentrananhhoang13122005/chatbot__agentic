import { useReducer } from "react";
import { SchoolMatchResult } from "@/types";

export type InputMode = "exam" | "transcript";

export interface ScoreState {
  step: number;
  mode: InputMode;
  scores: Record<string, number | undefined>;
  notTakenSubjects: Record<string, boolean>;
  
  // Extra certificates
  ielts?: number;
  toefl?: number;
  toeic?: number;
  
  // THPT Info
  gpa12?: number;
  rank12?: string;
  
  // Priority
  kvSelected: string;
  utSelected: string;
  bonus: number;
  
  // Filters
  methods: string[];
  topK: number;
  filterProvince?: string;
  filterMajor?: string;
  
  // Results
  result?: SchoolMatchResult;
  aiAnalysis: string; // Streaming or completed analysis
  isLoading: boolean;
}

export type ScoreAction =
  | { type: "SET_STEP"; payload: number }
  | { type: "SET_MODE"; payload: InputMode }
  | { type: "SET_SCORE"; payload: { subject: string; value: number | undefined } }
  | { type: "TOGGLE_NOT_TAKEN"; payload: { subject: string; notTaken: boolean } }
  | { type: "SET_EXTRA"; payload: { field: "ielts" | "toefl" | "toeic" | "gpa12" | "rank12"; value: number | string } }
  | { type: "SET_PRIORITY"; payload: { kv: string; ut: string; bonus: number } }
  | { type: "SET_FILTERS"; payload: Partial<Pick<ScoreState, "methods" | "topK" | "filterProvince" | "filterMajor">> }
  | { type: "SET_RESULT"; payload: SchoolMatchResult }
  | { type: "APPEND_ANALYSIS"; payload: string }
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "RESET" };

const initialState: ScoreState = {
  step: 1,
  mode: "exam",
  scores: {},
  notTakenSubjects: {},
  kvSelected: "KV3",
  utSelected: "Không",
  bonus: 0.0,
  methods: ["Xét điểm thi THPT"],
  topK: 15,
  aiAnalysis: "",
  isLoading: false,
};

function scoreReducer(state: ScoreState, action: ScoreAction): ScoreState {
  switch (action.type) {
    case "SET_STEP":
      return { ...state, step: action.payload };
    case "SET_MODE": {
      const defaultMethods = action.payload === "exam"
        ? ["Xét điểm thi THPT"]
        : ["Xét điểm Học bạ THPT"];
      return { ...state, mode: action.payload, methods: defaultMethods };
    }
    case "SET_SCORE":
      return {
        ...state,
        scores: { ...state.scores, [action.payload.subject]: action.payload.value },
        notTakenSubjects: { ...state.notTakenSubjects, [action.payload.subject]: false }
      };
    case "TOGGLE_NOT_TAKEN":
      return {
        ...state,
        notTakenSubjects: { ...state.notTakenSubjects, [action.payload.subject]: action.payload.notTaken },
        scores: action.payload.notTaken 
          ? { ...state.scores, [action.payload.subject]: undefined } 
          : state.scores
      };
    case "SET_EXTRA":
      return { ...state, [action.payload.field]: action.payload.value };
    case "SET_PRIORITY":
      return { ...state, kvSelected: action.payload.kv, utSelected: action.payload.ut, bonus: action.payload.bonus };
    case "SET_FILTERS":
      return { ...state, ...action.payload };
    case "SET_RESULT":
      return { ...state, result: action.payload, aiAnalysis: action.payload.analysis ?? "" };
    case "APPEND_ANALYSIS":
      return { ...state, aiAnalysis: state.aiAnalysis + action.payload };
    case "SET_LOADING":
      return { ...state, isLoading: action.payload };
    case "RESET":
      return initialState;
    default:
      return state;
  }
}

export function useScoreForm() {
  const [state, dispatch] = useReducer(scoreReducer, initialState);
  return { state, dispatch };
}
