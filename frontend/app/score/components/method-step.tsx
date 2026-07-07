"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ScoreState, ScoreAction } from "@/hooks/use-score-form";
import { useApi } from "@/hooks/useApi";
import { apiClient } from "@/lib/api";
import { CombinationResult } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Loader2, AlertTriangle, CheckCircle2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface MethodStepProps {
  state: ScoreState;
  dispatch: React.Dispatch<ScoreAction>;
}

export function MethodStep({ state, dispatch }: MethodStepProps) {
  const { data, isLoading: loading, error, execute: fetchCombosApi } = useApi(
    (body: any) => apiClient.post<{ top_combinations: CombinationResult[] }>("/scores/calculate", body),
    { showErrorToast: false }
  );

  const combos = data?.top_combinations || [];

  // Serialize scores to a stable string key to avoid re-fetch on every reference change
  const scoresKey = useMemo(() => {
    // Only include entries with defined values
    const clean: Record<string, number> = {};
    Object.entries(state.scores).forEach(([k, v]) => {
      if (v !== undefined) clean[k] = v;
    });
    return JSON.stringify(clean);
  }, [state.scores]);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Fetch combinations when step 2 mounts, debounced by 300ms
    const fetchCombos = async () => {
      const cleanScores: Record<string, number> = JSON.parse(scoresKey);

      await fetchCombosApi({
        scores: cleanScores,
        bonus: state.bonus,
        k: 3 // top 3 combos
      });
    };

    // Clear previous debounce timer and set a new one
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(fetchCombos, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [scoresKey, state.bonus]);

  const handleStartAnalysis = async () => {
    dispatch({ type: "SET_LOADING", payload: true });
    dispatch({ type: "SET_STEP", payload: 3 });
    // Note: The actual API call for /match will happen in Step 3 (ResultStep)
    // so it can handle the SSE streaming directly into the result state.
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-500">
      
      {/* Combinations Preview */}
      <div className="space-y-4">
        <h3 className="font-heading text-xl font-semibold">Tổ hợp môn xét tuyển tốt nhất</h3>
        
        {loading ? (
          <div className="flex items-center justify-center p-12 bg-white/5 border border-white/10 rounded-xl backdrop-blur-md">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <div className="p-6 bg-destructive/10 border border-destructive/20 text-destructive rounded-xl flex items-center gap-3">
            <AlertTriangle className="w-5 h-5" />
            <p>{error.message}</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-3 gap-4">
            {combos.map((combo, i) => (
              <Card key={combo.code} className={cn(
                "relative overflow-hidden transition-all",
                i === 0 ? "border-primary/50 shadow-[0_0_20px_rgba(242,55,161,0.1)]" : "border-white/10",
                combo.below_threshold ? "border-destructive/50 bg-destructive/5" : "bg-white/5 backdrop-blur-md"
              )}>
                {i === 0 && !combo.below_threshold && (
                  <div className="absolute top-0 right-0 bg-primary text-primary-foreground text-[10px] font-bold px-2 py-1 rounded-bl-lg">
                    TỐT NHẤT
                  </div>
                )}
                <CardContent className="p-5">
                  <div className="flex justify-between items-start mb-2">
                    <div className="font-heading text-2xl font-bold">{combo.code}</div>
                    <div className={cn(
                      "text-xl font-bold",
                      combo.below_threshold ? "text-destructive" : "text-primary"
                    )}>
                      {combo.total.toFixed(2)}
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground line-clamp-1">
                    {combo.subjects.join(" + ")}
                  </div>
                  {combo.below_threshold && (
                    <div className="mt-3 text-xs text-destructive flex items-center gap-1.5 bg-destructive/10 p-1.5 rounded">
                      <AlertTriangle className="w-3.5 h-3.5" /> Điểm liệt hoặc &lt; 15đ
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Card className="border-white/10 bg-white/5 backdrop-blur-md">
        <CardContent className="p-6 space-y-6">
          <h3 className="font-heading text-xl font-semibold">Tùy chọn Xét tuyển</h3>
          
          <div className="grid md:grid-cols-2 gap-8">
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Phương thức xét tuyển</label>
                <div className="flex flex-col gap-2">
                  <label className="flex items-center gap-3 p-3 rounded-lg border border-border bg-background/50 cursor-pointer hover:bg-muted/50 transition-colors">
                    <input 
                      type="checkbox" 
                      className="rounded border-gray-300 text-primary focus:ring-primary"
                      checked={state.methods.includes("Xét điểm thi THPT")}
                      onChange={(e) => {
                        const m = e.target.checked 
                          ? [...state.methods, "Xét điểm thi THPT"]
                          : state.methods.filter(x => x !== "Xét điểm thi THPT");
                        dispatch({ type: "SET_FILTERS", payload: { methods: m } });
                      }}
                    />
                    <span className="text-sm font-medium">Xét điểm thi THPT</span>
                  </label>
                  <label className="flex items-center gap-3 p-3 rounded-lg border border-border bg-background/50 cursor-pointer hover:bg-muted/50 transition-colors">
                    <input 
                      type="checkbox" 
                      className="rounded border-gray-300 text-primary focus:ring-primary"
                      checked={state.methods.includes("Xét điểm Học bạ THPT")}
                      onChange={(e) => {
                        const m = e.target.checked 
                          ? [...state.methods, "Xét điểm Học bạ THPT"]
                          : state.methods.filter(x => x !== "Xét điểm Học bạ THPT");
                        dispatch({ type: "SET_FILTERS", payload: { methods: m } });
                      }}
                    />
                    <span className="text-sm font-medium">Xét điểm Học bạ THPT</span>
                  </label>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Số lượng trường gợi ý</label>
                <Select value={String(state.topK)} onValueChange={(v) => dispatch({ type: "SET_FILTERS", payload: { topK: parseInt(v || "5") } })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="5">Top 5 trường</SelectItem>
                    <SelectItem value="10">Top 10 trường</SelectItem>
                    <SelectItem value="15">Top 15 trường</SelectItem>
                    <SelectItem value="20">Top 20 trường</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Lọc theo Khu vực / Tỉnh thành (Tùy chọn)</label>
                <Select value={state.filterProvince || "all"} onValueChange={(v) => dispatch({ type: "SET_FILTERS", payload: { filterProvince: v === "all" ? undefined : (v ?? undefined) } })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Tất cả khu vực" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tất cả khu vực</SelectItem>
                    <SelectItem value="Hà Nội">Hà Nội</SelectItem>
                    <SelectItem value="TP. Hồ Chí Minh">TP. Hồ Chí Minh</SelectItem>
                    <SelectItem value="Đà Nẵng">Đà Nẵng</SelectItem>
                    <SelectItem value="Cần Thơ">Cần Thơ</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">Lọc theo Ngành học (Tùy chọn)</label>
                <Input 
                  placeholder="VD: Công nghệ thông tin, Kinh tế..." 
                  value={state.filterMajor || ""}
                  onChange={(e) => dispatch({ type: "SET_FILTERS", payload: { filterMajor: e.target.value } })}
                  className="bg-background/50"
                />
              </div>
              
              <div className="bg-primary/5 border border-primary/20 rounded-lg p-4 mt-4">
                <h4 className="text-sm font-bold text-primary flex items-center gap-2 mb-1">
                  <CheckCircle2 className="w-4 h-4" /> UniSearch AI Ready
                </h4>
                <p className="text-xs text-muted-foreground">
                  Hệ thống sẽ tự động quét hàng ngàn điểm chuẩn và so sánh để đưa ra dự báo: <strong className="text-green-500">An toàn</strong>, <strong className="text-yellow-500">Vừa sức</strong>, hoặc <strong className="text-red-500">Thử thách</strong>.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={() => dispatch({ type: "SET_STEP", payload: 1 })}>
          <ArrowLeft className="mr-2 w-4 h-4" /> Quay lại
        </Button>
        <Button 
          size="lg" 
          onClick={handleStartAnalysis}
          disabled={state.methods.length === 0}
          className="px-8 bg-gradient-to-r from-primary to-secondary hover:opacity-90 shadow-[0_0_20px_rgba(242,55,161,0.4)]"
        >
          Phân tích ngay!
          <Sparkles className="ml-2 w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
