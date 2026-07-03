import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, AlertTriangle } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface AIAnalysisPanelProps {
  analysis: string;
  warnings: string[];
  isLoading: boolean;
}

export function AIAnalysisPanel({ analysis, warnings, isLoading }: AIAnalysisPanelProps) {
  return (
    <div className="space-y-4">
      {warnings && warnings.length > 0 && (
        <Card className="bg-destructive/10 border-destructive/20 text-destructive shadow-sm">
          <CardContent className="p-4 space-y-2">
            <div className="font-semibold flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> Cảnh báo quan trọng
            </div>
            <ul className="list-disc pl-5 text-sm space-y-1">
              {warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </CardContent>
        </Card>
      )}

      <Card className="bg-gradient-to-br from-white/5 to-white/0 border-white/10 backdrop-blur-md overflow-hidden relative">
        {/* Glow effect */}
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-32 h-32 bg-primary/20 rounded-full blur-[40px] pointer-events-none" />
        
        <CardHeader className="p-5 pb-2 border-b border-white/5">
          <CardTitle className="font-heading text-lg font-semibold flex items-center gap-2 text-foreground">
            <Sparkles className="w-5 h-5 text-primary" />
            Nhận xét từ UniSearch AI
          </CardTitle>
        </CardHeader>
        
        <CardContent className="p-6 prose prose-sm md:prose-base dark:prose-invert max-w-none text-muted-foreground">
          {!analysis && isLoading ? (
            <div className="flex flex-col items-center justify-center h-48 space-y-4 text-muted-foreground/70">
              <div className="relative">
                <div className="w-12 h-12 rounded-full border-2 border-primary/20" />
                <div className="w-12 h-12 rounded-full border-2 border-primary border-t-transparent animate-spin absolute top-0 left-0" />
                <Sparkles className="w-4 h-4 text-primary absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
              </div>
              <p className="text-sm font-medium animate-pulse">Đang phân tích điểm mạnh yếu của bạn...</p>
            </div>
          ) : (
            <div className="leading-relaxed">
              <ReactMarkdown>{analysis}</ReactMarkdown>
              {isLoading && analysis && (
                <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse" />
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
