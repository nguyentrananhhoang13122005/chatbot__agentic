import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface Step {
  id: number;
  label: string;
}

interface StepWizardProps {
  steps: Step[];
  currentStep: number;
}

export function StepWizard({ steps, currentStep }: StepWizardProps) {
  return (
    <div className="w-full">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isActive = step.id === currentStep;
          const isCompleted = step.id < currentStep;
          const isLast = index === steps.length - 1;

          return (
            <div key={step.id} className="flex-1 flex items-center relative">
              <div className="flex flex-col items-center gap-2 relative z-10 w-full">
                <div
                  className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium border-2 transition-colors",
                    isActive
                      ? "border-primary bg-primary text-primary-foreground shadow-[0_0_15px_rgba(242,55,161,0.4)]"
                      : isCompleted
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-muted-foreground/30 bg-background text-muted-foreground"
                  )}
                >
                  {isCompleted ? <Check className="w-4 h-4" /> : step.id}
                </div>
                <span
                  className={cn(
                    "text-xs font-medium absolute -bottom-6 w-max text-center transition-colors",
                    isActive || isCompleted ? "text-foreground" : "text-muted-foreground"
                  )}
                >
                  {step.label}
                </span>
              </div>

              {!isLast && (
                <div
                  className={cn(
                    "absolute top-4 left-[50%] right-[-50%] h-[2px] transition-colors",
                    isCompleted ? "bg-primary" : "bg-muted-foreground/20"
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
      <div className="h-6" /> {/* Spacer for the absolute labels */}
    </div>
  );
}
