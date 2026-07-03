"use client";

import { ScoreState, ScoreAction } from "@/hooks/use-score-form";
import { MAIN_SUBJECTS, PRIORITY_KV, PRIORITY_UT } from "@/lib/constants";
import { ScoreInput } from "@/components/ui/score-input";
import { TranscriptEditor } from "./transcript-editor";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Info, ArrowRight } from "lucide-react";
import { validateMinSubjects } from "@/lib/validators";

interface ScoreInputStepProps {
  state: ScoreState;
  dispatch: React.Dispatch<ScoreAction>;
}

export function ScoreInputStep({ state, dispatch }: ScoreInputStepProps) {
  const handleScoreChange = (subject: string, value: number | undefined) => {
    dispatch({ type: "SET_SCORE", payload: { subject, value } });
  };

  const handleToggleNotTaken = (subject: string, notTaken: boolean) => {
    dispatch({ type: "TOGGLE_NOT_TAKEN", payload: { subject, notTaken } });
  };

  const canProceed = state.mode === "transcript" || validateMinSubjects(state.scores, 3);

  const calculateTotalBonus = () => {
    const kv = PRIORITY_KV[state.kvSelected] || 0;
    const ut = PRIORITY_UT[state.utSelected] || 0;
    return kv + ut;
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Mode Selection */}
      <div className="flex bg-muted/30 p-1.5 rounded-full w-full max-w-md mx-auto border border-border">
        <button
          className={`flex-1 py-2.5 px-4 rounded-full text-sm font-medium transition-all ${
            state.mode === "exam" 
              ? "bg-background text-foreground shadow-sm ring-1 ring-border" 
              : "text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => dispatch({ type: "SET_MODE", payload: "exam" })}
        >
          Nhập điểm thi THPT
        </button>
        <button
          className={`flex-1 py-2.5 px-4 rounded-full text-sm font-medium transition-all ${
            state.mode === "transcript" 
              ? "bg-background text-foreground shadow-sm ring-1 ring-border" 
              : "text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => dispatch({ type: "SET_MODE", payload: "transcript" })}
        >
          Nhập Học bạ
        </button>
      </div>

      <Card className="border-white/10 bg-white/5 backdrop-blur-md">
        <CardContent className="p-6">
          {state.mode === "exam" ? (
            <div className="space-y-6">
              <h3 className="font-heading text-xl font-semibold mb-4">Điểm thi các môn chính</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {MAIN_SUBJECTS.map((subj) => (
                  <div key={subj} className="space-y-2">
                    <div className="flex justify-between items-center">
                      <label className="text-sm font-medium text-foreground">{subj}</label>
                      <label className="flex items-center space-x-2 text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                        <input
                          type="checkbox"
                          className="rounded border-gray-300 text-primary focus:ring-primary h-3 w-3"
                          checked={state.notTakenSubjects[subj] || false}
                          onChange={(e) => handleToggleNotTaken(subj, e.target.checked)}
                        />
                        <span>Không thi</span>
                      </label>
                    </div>
                    <ScoreInput
                      value={state.notTakenSubjects[subj] ? undefined : state.scores[subj]}
                      onChange={(val) => handleScoreChange(subj, val)}
                      disabled={state.notTakenSubjects[subj]}
                      placeholder={`Điểm ${subj}`}
                      className={state.notTakenSubjects[subj] ? "bg-muted/50 opacity-50" : ""}
                    />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <h3 className="font-heading text-xl font-semibold mb-4">Nhập điểm Học bạ (6 Học kỳ)</h3>
              <TranscriptEditor dispatch={dispatch} />
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Extra Sections (IELTS, etc) */}
        <Card className="border-white/10 bg-white/5 backdrop-blur-md">
          <CardContent className="p-6 space-y-4">
            <h3 className="font-heading text-xl font-semibold">Chứng chỉ Ngoại ngữ & Khác</h3>
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="w-1/3 text-sm font-medium">IELTS</div>
                <Select value={state.ielts ? String(state.ielts) : "0"} onValueChange={(val) => dispatch({ type: "SET_EXTRA", payload: { field: "ielts", value: parseFloat(val ?? "0") } })}>
                  <SelectTrigger className="flex-1">
                    <SelectValue placeholder="Không có" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0">Không có</SelectItem>
                    {[4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0].map(v => (
                      <SelectItem key={v} value={String(v)}>{v.toFixed(1)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Simplified placeholders for TOEFL/TOEIC/GPA for brevity */}
              <div className="text-xs text-muted-foreground italic flex items-center gap-2">
                <Info className="w-4 h-4" /> Có thể nhập thêm chứng chỉ quốc tế khác ở mục nâng cao.
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Priority Section */}
        <Card className="border-white/10 bg-white/5 backdrop-blur-md">
          <CardContent className="p-6 space-y-4">
            <h3 className="font-heading text-xl font-semibold">Đối tượng & Khu vực Ưu tiên</h3>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Khu vực</label>
                <Select 
                  value={state.kvSelected} 
                  onValueChange={(val) => {
                    if (!val) return;
                    dispatch({ type: "SET_PRIORITY", payload: { kv: val, ut: state.utSelected, bonus: PRIORITY_KV[val] + PRIORITY_UT[state.utSelected] } });
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Chọn Khu vực" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.keys(PRIORITY_KV).map(kv => (
                      <SelectItem key={kv} value={kv}>{kv} (+{PRIORITY_KV[kv]} điểm)</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Đối tượng</label>
                <Select 
                  value={state.utSelected} 
                  onValueChange={(val) => {
                    if (!val) return;
                    dispatch({ type: "SET_PRIORITY", payload: { kv: state.kvSelected, ut: val, bonus: PRIORITY_KV[state.kvSelected] + PRIORITY_UT[val] } });
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Chọn Đối tượng ưu tiên" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.keys(PRIORITY_UT).map(ut => (
                      <SelectItem key={ut} value={ut}>{ut} (+{PRIORITY_UT[ut]} điểm)</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="mt-4 p-3 rounded-lg bg-primary/10 border border-primary/20 flex justify-between items-center">
                <span className="text-sm font-medium text-foreground">Tổng điểm ưu tiên:</span>
                <span className="text-lg font-bold text-primary">+{calculateTotalBonus()}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex justify-end pt-4">
        <Button 
          size="lg" 
          disabled={!canProceed}
          onClick={() => dispatch({ type: "SET_STEP", payload: 2 })}
          className="px-8 shadow-lg shadow-primary/20"
        >
          {state.mode === "exam" && !canProceed ? "Vui lòng nhập ít nhất 3 môn" : "Tiếp tục"}
          <ArrowRight className="ml-2 w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
