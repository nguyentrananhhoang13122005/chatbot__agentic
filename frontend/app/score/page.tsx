"use client";

import { useScoreForm } from "@/hooks/use-score-form";
import { StepWizard } from "@/components/ui/step-wizard";
import { ScoreInputStep } from "./components/score-input-step";
import { MethodStep } from "./components/method-step";
import { ResultStep } from "./components/result-step";
import { Sparkles } from "lucide-react";

const WIZARD_STEPS = [
  { id: 1, label: "Nhập điểm" },
  { id: 2, label: "Tùy chọn" },
  { id: 3, label: "Kết quả" },
];

export default function ScorePage() {
  const { state, dispatch } = useScoreForm();

  return (
    <div className="container mx-auto px-4 py-8 md:py-12 max-w-5xl">
      <div className="flex flex-col items-center mb-10 text-center">
        <div className="inline-flex items-center rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-sm font-medium text-primary mb-4">
          <Sparkles className="mr-2 h-4 w-4" />
          Công cụ tính điểm AI
        </div>
        <h1 className="font-heading text-3xl md:text-5xl font-bold mb-4">
          Phân tích điểm số
        </h1>
        <p className="text-muted-foreground max-w-2xl">
          Nhập điểm thi hoặc điểm học bạ của bạn. Hệ thống sẽ tự động tính toán các tổ hợp môn có lợi nhất và đề xuất danh sách trường Đại học phù hợp.
        </p>
      </div>

      <div className="mb-12">
        <StepWizard steps={WIZARD_STEPS} currentStep={state.step} />
      </div>

      <div className="relative">
        {state.step === 1 && <ScoreInputStep state={state} dispatch={dispatch} />}
        {state.step === 2 && <MethodStep state={state} dispatch={dispatch} />}
        {state.step === 3 && <ResultStep state={state} dispatch={dispatch} />}
      </div>
    </div>
  );
}
