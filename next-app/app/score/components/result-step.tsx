"use client";

import { useEffect, useRef } from "react";
import { ScoreState, ScoreAction } from "@/hooks/use-score-form";
import { fetchSSE } from "@/lib/sse-client";
import { Button } from "@/components/ui/button";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";

// Dashboard Components
import { StrengthAnalysis } from "./strength-analysis";
import { ComboCards } from "./combo-cards";
import { SchoolTable } from "./school-table";
import { AIAnalysisPanel } from "./ai-analysis-panel";

interface ResultStepProps {
  state: ScoreState;
  dispatch: React.Dispatch<ScoreAction>;
}

export function ResultStep({ state, dispatch }: ResultStepProps) {
  const hasFetched = useRef(false);
  const router = useRouter();

  useEffect(() => {
    if (hasFetched.current || !state.isLoading) return;
    hasFetched.current = true;

    const runMatch = async () => {
      // Clear previous analysis
      dispatch({ type: "SET_RESULT", payload: { schools: [], top_combinations: [], strength: {}, warnings: [], analysis: "" } });
      dispatch({ type: "SET_LOADING", payload: true });

      const cleanScores: Record<string, number> = {};
      Object.entries(state.scores).forEach(([k, v]) => {
        if (v !== undefined) cleanScores[k] = v;
      });

      const body = {
        scores: cleanScores,
        bonus: state.bonus,
        methods: state.methods,
        k: state.topK,
        province: state.filterProvince,
        major: state.filterMajor,
        stream: true
      };

      await fetchSSE("/api/v1/schools/match", body, {
        onMeta: (meta) => {
          dispatch({ 
            type: "SET_RESULT", 
            payload: { 
              schools: meta.schools || [],
              top_combinations: meta.top_combinations || [],
              strength: meta.strength || {},
              warnings: meta.warnings || [],
              analysis: ""
            } 
          });
        },
        onChunk: (chunk) => {
          dispatch({ type: "APPEND_ANALYSIS", payload: chunk });
        },
        onDone: () => {
          dispatch({ type: "SET_LOADING", payload: false });
        },
        onError: (err) => {
          console.error("Match error:", err);
          dispatch({ type: "SET_LOADING", payload: false });
        }
      });
    };

    runMatch();
  }, [state.isLoading, dispatch, state.scores, state.bonus, state.methods, state.topK, state.filterProvince, state.filterMajor]);

  const handleReRun = () => {
    hasFetched.current = false;
    dispatch({ type: "SET_LOADING", payload: true });
  };

  const schools = state.result?.schools || [];
  const combos = state.result?.top_combinations || [];
  const strength = state.result?.strength || {};
  const warnings = state.result?.warnings || [];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-500">
      
      {/* Header Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Button variant="ghost" onClick={() => dispatch({ type: "SET_STEP", payload: 2 })} className="text-muted-foreground hover:text-foreground">
          <ArrowLeft className="mr-2 w-4 h-4" /> Sửa tùy chọn
        </Button>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => router.push("/")} className="bg-background">
            Về Trang chủ
          </Button>
          <Button onClick={handleReRun} disabled={state.isLoading} className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_15px_rgba(242,55,161,0.3)]">
            <RefreshCw className={`mr-2 w-4 h-4 ${state.isLoading ? "animate-spin" : ""}`} /> 
            Phân tích lại
          </Button>
        </div>
      </div>

      {/* Dashboard Composition */}
      <div className="space-y-8">
        
        {/* Row 1: Strength Analysis (Metric Cards) */}
        <div>
          <h3 className="font-heading text-lg font-semibold mb-4 px-1">Tổng quan Năng lực</h3>
          <StrengthAnalysis strength={strength} />
        </div>

        {/* Row 2: Combos & AI Analysis */}
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <h3 className="font-heading text-lg font-semibold px-1">Tổ hợp môn xét tuyển</h3>
            <ComboCards combos={combos} />
          </div>
          <div className="lg:col-span-1">
            <AIAnalysisPanel 
              analysis={state.aiAnalysis} 
              warnings={warnings} 
              isLoading={state.isLoading} 
            />
          </div>
        </div>

        {/* Row 3: School Table */}
        <div className="pt-4">
          <h3 className="font-heading text-lg font-semibold mb-4 px-1">Danh sách Trường phù hợp</h3>
          <SchoolTable schools={schools} />
        </div>
        
      </div>
    </div>
  );
}
