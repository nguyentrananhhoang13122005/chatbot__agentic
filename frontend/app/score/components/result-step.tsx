"use client";

import { useEffect, useRef, useState } from "react";
import { ScoreState, ScoreAction } from "@/hooks/use-score-form";
import { fetchSSE } from "@/lib/sse-client";
import { Button } from "@/components/ui/button";
import { ArrowLeft, RefreshCw, AlertTriangle, Sparkles, GraduationCap, FileText } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

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
  const abortRef = useRef<AbortController | null>(null);
  const router = useRouter();
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("analysis");

  useEffect(() => {
    if (!state.isLoading) return;

    // Abort any previous in-flight request
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const runMatch = async () => {
      // Clear previous state
      setFetchError(null);
      dispatch({ type: "SET_RESULT", payload: { schools: [], top_combinations: [], strength: {}, warnings: [], analysis: "" } });
      dispatch({ type: "SET_LOADING", payload: true });

      const cleanScores: Record<string, number> = {};
      Object.entries(state.scores).forEach(([k, v]) => {
        if (v !== undefined) cleanScores[k] = v;
      });

      const body: Record<string, unknown> = {
        scores: cleanScores,
        bonus: state.bonus,
        methods: state.methods,
        k: state.topK,
        province: state.filterProvince,
        major: state.filterMajor,
        stream: true,
        skip_analysis: true,
        // Extra fields (HIGH-3 fix)
        ielts: state.ielts || undefined,
        toefl: state.toefl || undefined,
        toeic: state.toeic || undefined,
        gpa12: state.gpa12 || undefined,
        rank12: state.rank12 || undefined,
        not_taken_subjects: Object.entries(state.notTakenSubjects || {})
          .filter(([, v]) => v)
          .map(([k]) => k),
      };

      await fetchSSE("/schools/match", body, {
        onMeta: (meta) => {
          dispatch({ 
            type: "SET_RESULT", 
            payload: { 
              schools: (meta.schools as Record<string, unknown>[]) || [],
              top_combinations: (meta.top_combinations as Record<string, unknown>[]) || [],
              strength: (meta.strength as Record<string, unknown>) || {},
              warnings: (meta.warnings as string[]) || [],
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
          // Defensive: sse-client.ts already silences AbortError, but this
          // guard protects against future refactors removing that check.
          if (err instanceof DOMException && err.name === "AbortError") return;
          const message = err instanceof Error ? err.message : "Lỗi kết nối";
          setFetchError(`Không thể phân tích: ${message}. Vui lòng thử lại.`);
          dispatch({ type: "SET_LOADING", payload: false });
        }
      }, controller.signal);
    };

    runMatch();

    return () => {
      controller.abort();
    };
  }, [state.isLoading, dispatch, state.scores, state.bonus, state.methods, state.topK, state.filterProvince, state.filterMajor, state.ielts, state.toefl, state.toeic, state.gpa12, state.rank12, state.notTakenSubjects]);

  const handleReRun = () => {
    // Abort any in-flight stream before starting a new one
    abortRef.current?.abort();
    setFetchError(null);
    dispatch({ type: "SET_LOADING", payload: true });
    dispatch({ type: "SET_ANALYSIS_TRIGGERED", payload: false });
    dispatch({ type: "SET_ANALYZING", payload: false });
  };

  const handleStartAnalysis = async () => {
    if (state.analysisTriggered) return;
    dispatch({ type: "SET_ANALYSIS_TRIGGERED", payload: true });
    dispatch({ type: "SET_ANALYZING", payload: true });
    
    // Abort any previous in-flight request just in case
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const cleanScores: Record<string, number> = {};
    Object.entries(state.scores).forEach(([k, v]) => {
      if (v !== undefined) cleanScores[k] = v;
    });

    const body: Record<string, unknown> = {
      scores: cleanScores,
      bonus: state.bonus,
      methods: state.methods,
      k: state.topK,
      province: state.filterProvince,
      major: state.filterMajor,
      stream: true,
      skip_analysis: false,
      ielts: state.ielts || undefined,
      toefl: state.toefl || undefined,
      toeic: state.toeic || undefined,
      gpa12: state.gpa12 || undefined,
      rank12: state.rank12 || undefined,
      not_taken_subjects: Object.entries(state.notTakenSubjects || {})
        .filter(([, v]) => v)
        .map(([k]) => k),
    };

    await fetchSSE("/schools/match", body, {
      onMeta: () => {
        // Skip updating meta again to avoid flickering, data is identical
      },
      onChunk: (chunk) => {
        dispatch({ type: "APPEND_ANALYSIS", payload: chunk });
      },
      onDone: () => {
        dispatch({ type: "SET_ANALYZING", payload: false });
      },
      onError: (err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        const message = err instanceof Error ? err.message : "Lỗi kết nối";
        setFetchError(`Không thể phân tích: ${message}. Vui lòng thử lại.`);
        dispatch({ type: "SET_ANALYZING", payload: false });
      }
    }, controller.signal);
  };

  const schools = state.result?.schools || [];
  const combos = (state.result?.top_combinations as Array<{ code: string; subjects: string[]; total: number; below_threshold?: boolean }>) || [];
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

      {/* Error Banner (HIGH-4 fix) */}
      {fetchError && (
        <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl text-destructive flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <p>{fetchError}</p>
        </div>
      )}

      {/* Custom Tabs Navigation */}
      <div className="w-full">
        <div className="flex justify-center mb-10">
          <div className="flex p-1.5 bg-white/5 border border-white/10 rounded-2xl w-full max-w-md shadow-inner relative z-20">
            <button
              onClick={() => setActiveTab("analysis")}
              className={cn(
                "flex-1 py-3 px-4 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all duration-300",
                activeTab === "analysis" 
                  ? "bg-primary/20 text-primary shadow-[0_0_15px_rgba(242,55,161,0.2)] border border-primary/30" 
                  : "text-muted-foreground hover:text-foreground hover:bg-white/5 border border-transparent"
              )}
            >
              <FileText className="w-4 h-4" /> Báo cáo & AI
            </button>
            <button
              onClick={() => setActiveTab("schools")}
              className={cn(
                "flex-1 py-3 px-4 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all duration-300",
                activeTab === "schools" 
                  ? "bg-primary/20 text-primary shadow-[0_0_15px_rgba(242,55,161,0.2)] border border-primary/30" 
                  : "text-muted-foreground hover:text-foreground hover:bg-white/5 border border-transparent"
              )}
            >
              <GraduationCap className="w-4 h-4" /> Đại học Đề xuất
            </button>
          </div>
        </div>

        {/* Tab 1: Analysis */}
        <div className={cn(
          "transition-all duration-500",
          activeTab === "analysis" ? "opacity-100 block animate-in fade-in zoom-in-95" : "opacity-0 hidden"
        )}>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 relative items-start">
            
            {/* Main Content Column */}
            <div className="lg:col-span-7 xl:col-span-8 flex flex-col gap-8 min-w-0 w-full overflow-hidden lg:overflow-visible">
              <div className="order-1">
                <h3 className="font-heading text-2xl md:text-3xl font-bold tracking-tight mb-5 px-1">Tổng quan Năng lực</h3>
                <StrengthAnalysis strength={strength} />
              </div>

              <div className="order-3 space-y-5">
                <h3 className="font-heading text-2xl md:text-3xl font-bold tracking-tight px-1">Tổ hợp xét tuyển</h3>
                <ComboCards combos={combos} />
              </div>

              {/* AI Panel on Mobile */}
              <div className="order-2 block lg:hidden">
                <AIAnalysisPanel 
                  analysis={state.aiAnalysis} 
                  warnings={warnings} 
                  isLoading={state.isLoading} 
                  isAnalyzing={state.isAnalyzing}
                  analysisTriggered={state.analysisTriggered}
                  onStartAnalysis={handleStartAnalysis}
                />
              </div>

              {/* Action Button to Tab 2 */}
              <div className="order-4 pt-4 flex justify-center lg:justify-start">
                <Button 
                  onClick={() => {
                    setActiveTab("schools");
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }} 
                  size="lg" 
                  className="w-full md:w-auto text-base px-8 py-6 rounded-xl bg-gradient-to-r from-primary to-secondary hover:opacity-90 shadow-[0_0_20px_rgba(242,55,161,0.3)] transition-all"
                >
                  Xem danh sách Trường phù hợp ➔
                </Button>
              </div>
            </div>

            {/* Sidebar Column (AI Analysis) - Desktop Only */}
            <div className="hidden lg:block lg:col-span-5 xl:col-span-4 lg:sticky lg:top-6">
              <AIAnalysisPanel 
                analysis={state.aiAnalysis} 
                warnings={warnings} 
                isLoading={state.isLoading} 
                isAnalyzing={state.isAnalyzing}
                analysisTriggered={state.analysisTriggered}
                onStartAnalysis={handleStartAnalysis}
              />
            </div>
          </div>
        </div>

        {/* Tab 2: Schools */}
        <div className={cn(
          "transition-all duration-500",
          activeTab === "schools" ? "opacity-100 block animate-in fade-in zoom-in-95" : "opacity-0 hidden"
        )}>
          <div className="max-w-4xl mx-auto">
            {/* Mini Summary Anchor */}
            <div className="mb-8 bg-primary/5 border border-primary/20 p-5 rounded-2xl flex items-center justify-between backdrop-blur-md">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center">
                  <Sparkles className="text-primary w-6 h-6" />
                </div>
                <div>
                  <div className="text-sm text-muted-foreground font-medium uppercase tracking-wider mb-1">Tổ hợp tốt nhất của bạn</div>
                  <div className="font-bold text-2xl text-foreground font-heading">
                    <span className="text-primary mr-2">{combos[0]?.code || "N/A"}</span> 
                    {combos[0]?.total.toFixed(2) || "0.00"} điểm
                  </div>
                </div>
              </div>
            </div>
            
            <div className="pt-2">
              <h3 className="font-heading text-2xl md:text-3xl font-bold tracking-tight mb-5 px-1">Đại học đề xuất</h3>
              <SchoolTable schools={schools} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
