"use client";

import { useEffect, useRef } from "react";
import { ScoreState, ScoreAction } from "@/hooks/use-score-form";
import { fetchSSE } from "@/lib/sse-client";
import { formatScore, formatTier } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sparkles, ArrowLeft, RefreshCw, AlertTriangle, Building2, BookOpen, GraduationCap } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface ResultStepProps {
  state: ScoreState;
  dispatch: React.Dispatch<ScoreAction>;
}

export function ResultStep({ state, dispatch }: ResultStepProps) {
  const hasFetched = useRef(false);

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

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => dispatch({ type: "SET_STEP", payload: 2 })}>
          <ArrowLeft className="mr-2 w-4 h-4" /> Đổi tùy chọn
        </Button>
        <Button variant="outline" onClick={handleReRun} disabled={state.isLoading}>
          <RefreshCw className={`mr-2 w-4 h-4 ${state.isLoading ? "animate-spin" : ""}`} /> 
          Chạy lại AI
        </Button>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        
        {/* Left Col: Schools List */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="font-heading text-xl font-semibold flex items-center gap-2">
            <Building2 className="w-5 h-5 text-primary" />
            Danh sách trường phù hợp nhất
          </h3>
          
          {state.isLoading && schools.length === 0 ? (
            // Skeleton loader
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <Card key={i} className="bg-white/5 border-white/10 animate-pulse">
                  <CardContent className="p-6 h-32 flex items-center justify-center">
                    <div className="w-8 h-8 rounded-full border-2 border-primary/50 border-t-transparent animate-spin" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : schools.length === 0 ? (
            <Card className="bg-white/5 border-white/10">
              <CardContent className="p-8 text-center text-muted-foreground">
                Không tìm thấy trường nào phù hợp với tiêu chí hiện tại. Vui lòng mở rộng bộ lọc.
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {schools.map((school, i) => {
                const tier = formatTier(school.tier);
                return (
                  <Card key={`${school.school_name}-${school.major_code}-${i}`} className="bg-white/5 border-white/10 backdrop-blur-md overflow-hidden hover:border-primary/30 transition-colors">
                    <CardHeader className="p-5 pb-3 bg-muted/20 border-b border-border/50">
                      <div className="flex justify-between items-start gap-4">
                        <div>
                          <CardTitle className="text-lg font-bold text-foreground">
                            {school.school_name}
                          </CardTitle>
                          <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                            <BookOpen className="w-4 h-4" />
                            <span>{school.major_name} ({school.major_code})</span>
                          </div>
                        </div>
                        <Badge variant="outline" className={`px-2 py-1 text-xs whitespace-nowrap ${tier.colorClass}`}>
                          {tier.icon} {tier.label}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="p-5">
                      <div className="grid sm:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <div className="text-xs text-muted-foreground">Điểm chuẩn {school.year}</div>
                          <div className="text-2xl font-bold font-heading">{formatScore(school.score)}</div>
                        </div>
                        <div className="space-y-2">
                          <div className="text-xs text-muted-foreground">Tổ hợp môn xét tuyển</div>
                          <div className="flex gap-1 flex-wrap">
                            {school.combo?.split(",").map((c: string) => (
                              <Badge key={c} variant="secondary" className="bg-primary/10 text-primary border-primary/20">
                                {c.trim()}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                      <div className="mt-4 pt-4 border-t border-border/50 flex flex-wrap gap-2 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1 bg-muted/50 px-2 py-1 rounded"><GraduationCap className="w-3.5 h-3.5" /> {school.method}</span>
                        {school.notes && <span className="flex items-center gap-1 bg-muted/50 px-2 py-1 rounded"><Info className="w-3.5 h-3.5" /> {school.notes}</span>}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Col: AI Analysis */}
        <div className="space-y-4">
          <h3 className="font-heading text-xl font-semibold flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            Nhận xét từ AI
          </h3>
          
          {state.result?.warnings && state.result.warnings.length > 0 && (
            <Card className="bg-destructive/10 border-destructive/20 text-destructive">
              <CardContent className="p-4 space-y-2">
                <div className="font-semibold flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" /> Cảnh báo
                </div>
                <ul className="list-disc pl-5 text-sm space-y-1">
                  {state.result.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </CardContent>
            </Card>
          )}

          <Card className="bg-white/5 border-white/10 backdrop-blur-md sticky top-20">
            <CardContent className="p-6 prose prose-sm dark:prose-invert max-w-none">
              {!state.aiAnalysis && state.isLoading ? (
                <div className="flex flex-col items-center justify-center h-40 space-y-4 text-muted-foreground">
                  <div className="w-8 h-8 rounded-full border-2 border-primary/50 border-t-transparent animate-spin" />
                  <p className="text-sm">Đang phân tích điểm mạnh yếu...</p>
                </div>
              ) : (
                <ReactMarkdown>{state.aiAnalysis}</ReactMarkdown>
              )}
              {state.isLoading && state.aiAnalysis && (
                <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse" />
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Info(props: any) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
  );
}
