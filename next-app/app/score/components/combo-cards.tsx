import { Card, CardContent } from "@/components/ui/card";
import { CombinationResult } from "@/types";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface ComboCardsProps {
  combos: CombinationResult[];
}

export function ComboCards({ combos }: ComboCardsProps) {
  if (!combos || combos.length === 0) return null;

  return (
    <div className="flex gap-4 overflow-x-auto pb-4 snap-x">
      {combos.map((combo, i) => (
        <Card 
          key={combo.code} 
          className={cn(
            "min-w-[280px] shrink-0 snap-center transition-colors relative overflow-hidden",
            combo.below_threshold ? "bg-destructive/5 border-destructive/30" : 
            i === 0 ? "bg-primary/5 border-primary/30" : "bg-white/5 border-white/10"
          )}
        >
          {i === 0 && !combo.below_threshold && (
            <div className="absolute top-0 right-0 bg-primary text-primary-foreground text-[10px] font-bold px-2 py-1 rounded-bl-lg flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> TỐT NHẤT
            </div>
          )}
          <CardContent className="p-5">
            <div className="flex justify-between items-start mb-2">
              <div className="font-heading text-xl font-bold">{combo.code}</div>
              <div className={cn(
                "text-2xl font-bold",
                combo.below_threshold ? "text-destructive" : "text-primary"
              )}>
                {combo.total.toFixed(2)}
              </div>
            </div>
            <div className="text-sm text-muted-foreground font-medium">
              {combo.subjects.join(" + ")}
            </div>
            
            {combo.below_threshold && (
              <div className="mt-3 text-xs text-destructive flex items-center gap-1.5 bg-destructive/10 p-2 rounded-md font-medium">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                Dưới 15 điểm hoặc có điểm liệt
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
