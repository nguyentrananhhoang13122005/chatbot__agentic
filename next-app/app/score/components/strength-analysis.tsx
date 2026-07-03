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
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Card className="bg-white/5 border-white/10 backdrop-blur-md">
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center mb-2">
            <Target className="w-5 h-5 text-primary" />
          </div>
          <div className="text-sm text-muted-foreground mb-1">Điểm Trung Bình</div>
          <div className="text-xl font-bold">{strength.avg_score?.toFixed(2) || "0.00"}</div>
        </CardContent>
      </Card>
      
      <Card className="bg-white/5 border-white/10 backdrop-blur-md">
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="w-10 h-10 rounded-full bg-secondary/10 flex items-center justify-center mb-2">
            <TrendingUp className="w-5 h-5 text-secondary" />
          </div>
          <div className="text-sm text-muted-foreground mb-1">Xu Hướng Năng Lực</div>
          <div className="text-xl font-bold truncate w-full">{strength.trend || "Chưa rõ"}</div>
        </CardContent>
      </Card>
      
      <Card className="bg-white/5 border-white/10 backdrop-blur-md">
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center mb-2">
            <Award className="w-5 h-5 text-green-500" />
          </div>
          <div className="text-sm text-muted-foreground mb-1">Môn Thế Mạnh</div>
          <div className="text-lg font-bold truncate w-full">
            {strength.best_subjects?.join(", ") || "-"}
          </div>
        </CardContent>
      </Card>
      
      <Card className="bg-white/5 border-white/10 backdrop-blur-md">
        <CardContent className="p-4 flex flex-col items-center text-center">
          <div className="w-10 h-10 rounded-full bg-orange-500/10 flex items-center justify-center mb-2">
            <BookOpen className="w-5 h-5 text-orange-500" />
          </div>
          <div className="text-sm text-muted-foreground mb-1">Môn Đã Nhập</div>
          <div className="text-xl font-bold">{strength.subjects_count || 0}</div>
        </CardContent>
      </Card>
    </div>
  );
}
