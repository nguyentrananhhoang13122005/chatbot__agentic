import { Card, CardContent } from "@/components/ui/card";
import { TrendingUp, Target, Award, BookOpen } from "lucide-react";

interface StrengthAnalysisProps {
  strength: {
    avg_score?: number;
    trend?: string;
    best_subjects?: string[];
    subjects_count?: number;
  };
}

export function StrengthAnalysis({ strength }: StrengthAnalysisProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {/* Average Score (Hero Cell) */}
      <Card className="col-span-2 md:col-span-1 row-span-2 bg-gradient-to-br from-primary/10 to-transparent border-primary/20 backdrop-blur-md relative overflow-hidden group">
        <div className="absolute -right-10 -top-10 w-32 h-32 bg-primary/20 blur-[50px] rounded-full group-hover:bg-primary/30 transition-all duration-500" />
        <CardContent className="p-6 h-full flex flex-col justify-between min-h-[160px]">
          <div>
            <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center mb-3">
              <Target className="w-5 h-5 text-primary" />
            </div>
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Điểm Trung Bình</div>
          </div>
          <div className="text-5xl md:text-6xl font-bold font-heading tracking-tighter text-foreground mt-4">
            {strength.avg_score?.toFixed(2) || "0.00"}
          </div>
        </CardContent>
      </Card>

      {/* Best Subjects */}
      <Card className="col-span-2 md:col-span-1 bg-white/5 border-white/10 backdrop-blur-md">
        <CardContent className="p-5 flex flex-col justify-center h-full">
          <div className="flex items-center gap-2 mb-2">
            <Award className="w-4 h-4 text-green-400" />
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Môn Thế Mạnh</div>
          </div>
          <div className="text-lg md:text-xl font-bold leading-tight break-words whitespace-normal">
            {Array.isArray(strength.best_subjects)
              ? strength.best_subjects.map((s: string | [string, number]) => Array.isArray(s) ? s[0] : s).join(", ")
              : "-"}
          </div>
        </CardContent>
      </Card>

      {/* Trend */}
      <Card className="col-span-1 bg-white/5 border-white/10 backdrop-blur-md">
        <CardContent className="p-5 flex flex-col justify-center h-full">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-secondary" />
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Xu Hướng</div>
          </div>
          <div className="text-lg md:text-xl font-bold leading-tight break-words whitespace-normal">
            {strength.trend || "Chưa rõ"}
          </div>
        </CardContent>
      </Card>

      {/* Subjects Count */}
      <Card className="col-span-1 bg-white/5 border-white/10 backdrop-blur-md">
        <CardContent className="p-5 flex flex-col justify-center h-full">
          <div className="flex items-center gap-2 mb-2">
            <BookOpen className="w-4 h-4 text-orange-400" />
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Đã Nhập</div>
          </div>
          <div className="text-3xl font-bold font-heading tracking-tight mt-1">
            {strength.subjects_count || 0} <span className="text-sm font-normal text-muted-foreground tracking-normal">môn</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
