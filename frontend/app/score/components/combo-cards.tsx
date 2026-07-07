import { Card, CardContent } from "@/components/ui/card";
import { AlertTriangle, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface ComboCardsProps {
  combos: Array<{
    code: string;
    subjects: string[];
    total: number;
    below_threshold?: boolean;
  }>;
}

export function ComboCards({ combos }: ComboCardsProps) {
  if (!combos || combos.length === 0) return null;

  return (
    <div className="flex gap-4 overflow-x-auto pb-4 snap-x scrollbar-none -mx-2 px-2 md:mx-0 md:px-0 md:grid md:grid-cols-2 xl:grid-cols-3 md:overflow-visible md:pb-0">
      {combos.map((combo, i) => (
        <Card 
          key={combo.code} 
          className={cn(
            "w-[85vw] md:w-full shrink-0 snap-center transition-all duration-500 hover:-translate-y-1 relative group overflow-visible",
            combo.below_threshold ? "bg-destructive/5 border-destructive/30" : 
            "bg-white/5 border-white/10 hover:border-white/20"
          )}
        >
          {i === 0 && !combo.below_threshold && (
            <>
              {/* Outer glow effect */}
              <div className="absolute -inset-px bg-gradient-to-r from-primary via-secondary to-primary rounded-xl opacity-50 blur-[2px] group-hover:opacity-100 group-hover:blur-md transition-all duration-500 z-0" />
              {/* Inner card background to cover the glow internally */}
              <div className="absolute inset-[1px] bg-background/95 backdrop-blur-xl rounded-xl z-0" />
            </>
          )}

          <CardContent className="p-5 md:p-6 relative z-10 h-full flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start mb-4">
                <div className="flex flex-col gap-2">
                  <div className={cn(
                    "font-heading text-2xl font-bold tracking-tight",
                    i === 0 && !combo.below_threshold ? "text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary" : "text-foreground"
                  )}>{combo.code}</div>
                  
                  {i === 0 && !combo.below_threshold && (
                    <span className="flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-wider text-primary bg-primary/10 px-2.5 py-1 rounded-full w-fit">
                      <Sparkles className="w-3 h-3" /> Tốt nhất
                    </span>
                  )}
                </div>
                
                <div className={cn(
                  "text-3xl font-bold font-heading tracking-tighter mt-1",
                  combo.below_threshold ? "text-destructive" : (i === 0 ? "text-primary" : "text-foreground")
                )}>
                  {combo.total.toFixed(2)}
                </div>
              </div>
              <div className="text-sm md:text-base text-muted-foreground font-medium leading-relaxed mt-2 whitespace-normal break-words w-full">
                {combo.subjects.join(" + ")}
              </div>
            </div>
            
            {combo.below_threshold && (
              <div className="mt-4 text-xs text-destructive flex items-center gap-2 bg-destructive/10 p-2.5 rounded-lg font-medium">
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
