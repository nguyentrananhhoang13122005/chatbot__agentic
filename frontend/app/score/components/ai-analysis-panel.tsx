"use client";

import { useState, useMemo, useEffect } from "react";
import { createPortal } from "react-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  Sparkles, 
  AlertTriangle, 
  Bot, 
  Copy, 
  Check, 
  Maximize2, 
  Minimize2, 
  RefreshCw,
  Calendar,
  ShieldAlert,
  Flame,
  CheckCircle2,
  HelpCircle,
  X
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";

interface AIAnalysisPanelProps {
  analysis: string;
  warnings: string[];
  isLoading: boolean;
  isAnalyzing?: boolean;
  analysisTriggered?: boolean;
  onStartAnalysis?: () => void;
  onReanalyze?: () => void;
}

export function AIAnalysisPanel({ 
  analysis, 
  warnings, 
  isLoading, 
  isAnalyzing, 
  analysisTriggered, 
  onStartAnalysis,
  onReanalyze 
}: AIAnalysisPanelProps) {
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Lock body scroll and listen for ESC key when modal is open
  useEffect(() => {
    if (isExpanded) {
      document.body.style.overflow = "hidden";
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") setIsExpanded(false);
      };
      window.addEventListener("keydown", handleKeyDown);
      return () => {
        document.body.style.overflow = "";
        window.removeEventListener("keydown", handleKeyDown);
      };
    } else {
      document.body.style.overflow = "";
    }
  }, [isExpanded]);

  // 1. Sanitize text: loại bỏ dấu chấm lửng rác '..' hoặc ký tự rác đầu câu
  const sanitizedAnalysis = useMemo(() => {
    if (!analysis) return "";
    return analysis
      .replace(/^(\s*(\.{2,}|…|:)\s*)+/, "")
      .trimStart();
  }, [analysis]);

  const handleCopy = async () => {
    if (!sanitizedAnalysis) return;
    try {
      await navigator.clipboard.writeText(sanitizedAnalysis);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  // 2. Custom Markdown Components làm đẹp giao diện, xóa bỏ tình trạng "Wall of text"
  const markdownComponents = useMemo(() => ({
    h1: ({ children }: { children?: React.ReactNode }) => (
      <div className="mt-4 mb-3 pb-2 border-b border-primary/20 flex items-center gap-2">
        <Sparkles className="w-5 h-5 text-primary shrink-0" />
        <h1 className="font-heading text-lg md:text-xl font-bold text-foreground tracking-tight m-0">
          {children}
        </h1>
      </div>
    ),
    h2: ({ children }: { children?: React.ReactNode }) => (
      <div className="mt-5 mb-3 pb-2 border-b border-white/10 flex items-center gap-2">
        <span className="w-1.5 h-4 rounded-full bg-primary inline-block shrink-0" />
        <h2 className="font-heading text-base md:text-lg font-bold text-foreground tracking-tight m-0">
          {children}
        </h2>
      </div>
    ),
    h3: ({ children }: { children?: React.ReactNode }) => {
      const text = String(children || "");
      let iconColor = "bg-primary text-primary";
      if (text.includes("1.") || text.includes("Đánh giá")) iconColor = "bg-sky-500/20 text-sky-400 border-sky-500/30";
      else if (text.includes("2.") || text.includes("trọng điểm")) iconColor = "bg-purple-500/20 text-purple-400 border-purple-500/30";
      else if (text.includes("3.") || text.includes("Thứ tự")) iconColor = "bg-amber-500/20 text-amber-400 border-amber-500/30";
      else if (text.includes("4.") || text.includes("dự phòng")) iconColor = "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
      else if (text.includes("5.") || text.includes("Lưu ý")) iconColor = "bg-rose-500/20 text-rose-400 border-rose-500/30";

      return (
        <div className="mt-6 mb-3 p-2.5 rounded-xl bg-white/[0.03] border border-white/5 flex items-center gap-2.5 shadow-xs">
          <span className={`px-2 py-0.5 rounded-md text-xs font-bold border ${iconColor}`}>
            Mục
          </span>
          <h3 className="font-heading text-sm md:text-base font-bold text-foreground tracking-tight m-0 flex-1">
            {children}
          </h3>
        </div>
      );
    },
    p: ({ children }: { children?: React.ReactNode }) => (
      <p className="text-sm md:text-[14.5px] leading-relaxed text-muted-foreground/95 mb-3 font-normal">
        {children}
      </p>
    ),
    ul: ({ children }: { children?: React.ReactNode }) => (
      <ul className="space-y-2 my-2.5 pl-1 list-none">
        {children}
      </ul>
    ),
    ol: ({ children }: { children?: React.ReactNode }) => (
      <ol className="space-y-2 my-2.5 pl-1 list-decimal list-inside text-sm text-muted-foreground/95">
        {children}
      </ol>
    ),
    li: ({ children }: { children?: React.ReactNode }) => (
      <li className="text-sm md:text-[14.5px] leading-relaxed text-muted-foreground/95 flex items-start gap-2.5">
        <span className="w-1.5 h-1.5 rounded-full bg-primary/80 shrink-0 mt-2" />
        <div className="flex-1 min-w-0">{children}</div>
      </li>
    ),
    strong: ({ children }: { children?: React.ReactNode }) => {
      const text = String(children || "").trim();

      // Badge An toàn (Xanh lá)
      if (text.includes("An toàn") || text === "[An toàn]") {
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 mx-0.5 rounded-md text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" /> {text.replace(/[[\]]/g, "")}
          </span>
        );
      }
      // Badge Vừa sức (Vàng hổ phách)
      if (text.includes("Vừa sức") || text === "[Vừa sức]") {
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 mx-0.5 rounded-md text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <Flame className="w-3 h-3" /> {text.replace(/[[\]]/g, "")}
          </span>
        );
      }
      // Badge Thử thách (Đỏ hồng)
      if (text.includes("Thử thách") || text === "[Thử thách]") {
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 mx-0.5 rounded-md text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <AlertTriangle className="w-3 h-3" /> {text.replace(/[[\]]/g, "")}
          </span>
        );
      }
      // Badge Tổ hợp môn (A00, A01, A07, D01, B02...)
      if (/^[A-Z][0-9]{2}$/.test(text)) {
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-xs font-mono font-bold bg-primary/20 text-primary border border-primary/30">
            {text}
          </span>
        );
      }
      // Badge Nguyện vọng (NV1, NV2, NV3...)
      if (/^NV\d+/.test(text)) {
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            {text}
          </span>
        );
      }

      return <strong className="font-semibold text-foreground text-white/95">{children}</strong>;
    },
    blockquote: ({ children }: { children?: React.ReactNode }) => (
      <div className="my-3.5 p-3.5 rounded-xl bg-amber-500/10 border-l-4 border-amber-500/80 text-amber-200/90 text-xs md:text-sm flex items-start gap-2.5">
        <HelpCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="flex-1">{children}</div>
      </div>
    ),
  }), []);

  return (
    <>
      <div className="space-y-4">
        {/* Cảnh báo quan trọng nếu có điểm liệt hoặc vi phạm ngưỡng */}
        {warnings && warnings.length > 0 && (
          <Card className="bg-destructive/10 border-destructive/20 text-destructive shadow-sm">
            <CardContent className="p-4 space-y-2">
              <div className="font-semibold flex items-center gap-2">
                <ShieldAlert className="w-4 h-4" /> Cảnh báo quan trọng
              </div>
              <ul className="list-disc pl-5 text-sm space-y-1">
                {warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Card AI Analysis chính */}
        <Card className="bg-background/50 border-white/10 backdrop-blur-3xl overflow-hidden relative shadow-2xl ring-1 ring-white/5">
          {/* Ambient Glows */}
          <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
          <div className="absolute top-0 right-0 -mr-16 -mt-16 w-40 h-40 bg-primary/20 rounded-full blur-[60px] pointer-events-none" />
          <div className="absolute bottom-0 left-0 -ml-16 -mb-16 w-40 h-40 bg-secondary/10 rounded-full blur-[60px] pointer-events-none" />
          
          <CardHeader className="p-5 pb-3 border-b border-white/5 relative z-10 flex flex-row items-center justify-between gap-2">
            <div>
              <CardTitle className="font-heading text-lg md:text-xl font-bold flex items-center gap-2 tracking-tight text-foreground">
                <Sparkles className="w-5 h-5 text-primary shrink-0 animate-pulse" />
                Nhận xét từ UniSearch AI
              </CardTitle>
              <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1 text-[11px] text-primary bg-primary/10 px-2 py-0.5 rounded-full border border-primary/20">
                  <Calendar className="w-3 h-3" /> Dữ liệu 2024 - 2025
                </span>
                {isAnalyzing && (
                  <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 animate-pulse">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" /> Đang phân tích...
                  </span>
                )}
              </div>
            </div>

            {/* Quick Actions (Copy, Expand, Re-run) */}
            {sanitizedAnalysis && (
              <div className="flex items-center gap-1">
                <Button 
                  variant="ghost" 
                  size="icon" 
                  onClick={handleCopy} 
                  title="Sao chép nhận xét" 
                  className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-white/10"
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </Button>
                <Button 
                  variant="ghost" 
                  size="icon" 
                  onClick={() => setIsExpanded(true)} 
                  title="Mở rộng toàn màn hình" 
                  className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-white/10"
                >
                  <Maximize2 className="w-4 h-4" />
                </Button>
              </div>
            )}
          </CardHeader>
          
          <CardContent className="p-5 max-h-[calc(100vh-250px)] lg:max-h-[820px] overflow-y-auto custom-scrollbar">
            {!analysisTriggered ? (
              <div className="flex flex-col items-center justify-center py-12 px-4 space-y-4 text-center">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-primary/20 to-secondary/20 border border-primary/30 flex items-center justify-center mb-1 shadow-[0_0_25px_rgba(242,55,161,0.2)]">
                  <Bot className="w-8 h-8 text-primary" />
                </div>
                <div className="space-y-1">
                  <p className="text-base font-semibold text-foreground">Bạn muốn AI đánh giá chiến lược nguyện vọng?</p>
                  <p className="text-xs text-muted-foreground max-w-sm">
                    UniSearch AI sẽ chỉ ra môn điểm nghẽn, tổ hợp lợi thế nhất và tư vấn thứ tự đặt nguyện vọng tối ưu theo dữ liệu 2024-2025.
                  </p>
                </div>
                <Button 
                  onClick={onStartAnalysis} 
                  disabled={isLoading}
                  className="bg-gradient-to-r from-primary to-secondary text-primary-foreground hover:opacity-90 shadow-[0_0_20px_rgba(242,55,161,0.3)] transition-all font-semibold px-6 py-2.5 rounded-xl"
                >
                  <Sparkles className="w-4 h-4 mr-2" /> Nhận phân tích chuyên sâu từ AI
                </Button>
              </div>
            ) : (!sanitizedAnalysis && isAnalyzing) ? (
              <div className="flex flex-col items-center justify-center py-16 space-y-4 text-muted-foreground/80">
                <div className="relative">
                  <div className="w-14 h-14 rounded-full border-2 border-primary/20" />
                  <div className="w-14 h-14 rounded-full border-2 border-primary border-t-transparent animate-spin absolute top-0 left-0" />
                  <Sparkles className="w-5 h-5 text-primary absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-pulse" />
                </div>
                <div className="text-center space-y-1">
                  <p className="text-sm font-semibold text-foreground animate-pulse">Đang rà soát dữ liệu điểm chuẩn & tính toán chiến lược...</p>
                  <p className="text-xs text-muted-foreground">Tối ưu hóa thứ tự nguyện vọng theo từng khối thi</p>
                </div>
              </div>
            ) : (
              <div className="analysis-markdown-content">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm, remarkBreaks]} 
                  components={markdownComponents}
                >
                  {sanitizedAnalysis}
                </ReactMarkdown>

                {isAnalyzing && (
                  <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse align-middle rounded-xs" />
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* MODAL MỞ RỘNG TOÀN MÀN HÌNH ĐỂ ĐỌC THOẢI MÁI (PORTAL TRỰC TIẾP LÊN BODY) */}
      {mounted && isExpanded && typeof document !== "undefined" && createPortal(
        <div 
          className="fixed inset-0 z-[99999] flex items-center justify-center p-3 sm:p-6 md:p-10 bg-black/95 backdrop-blur-3xl animate-in fade-in duration-200"
          onClick={() => setIsExpanded(false)}
        >
          <div 
            className="bg-[#0c0c12] border border-white/15 rounded-2xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-[0_0_80px_rgba(0,0,0,0.95)] overflow-hidden relative text-foreground ring-1 ring-white/10"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 md:p-6 border-b border-white/10 flex items-center justify-between bg-[#14141d]/90">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0">
                  <Sparkles className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-heading text-lg md:text-xl font-bold text-foreground">
                    Báo cáo Phân tích Chiến lược Tuyển sinh Toàn diện
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Hệ thống UniSearch AI • Tham chiếu điểm chuẩn 2024 - 2025
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleCopy}
                  className="bg-white/5 border-white/10 text-xs text-foreground hover:bg-white/10"
                >
                  {copied ? <Check className="w-3.5 h-3.5 mr-1.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 mr-1.5" />}
                  {copied ? "Đã sao chép" : "Sao chép"}
                </Button>
                <Button 
                  variant="ghost" 
                  size="icon" 
                  onClick={() => setIsExpanded(false)}
                  className="h-9 w-9 text-muted-foreground hover:text-foreground hover:bg-white/10 rounded-xl"
                >
                  <X className="w-5 h-5" />
                </Button>
              </div>
            </div>

            <div className="p-6 md:p-8 overflow-y-auto custom-scrollbar flex-1 bg-[#0c0c12]">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm, remarkBreaks]} 
                components={markdownComponents}
              >
                {sanitizedAnalysis}
              </ReactMarkdown>
            </div>

            <div className="p-4 border-t border-white/10 bg-[#14141d]/90 flex items-center justify-between text-xs text-muted-foreground">
              <span>* Khuyến nghị: Thí sinh cần tra cứu lại đề án tuyển sinh chính thức của các trường để nắm rõ điều kiện phụ.</span>
              <Button size="sm" onClick={() => setIsExpanded(false)} className="bg-primary text-primary-foreground font-semibold px-4">
                Đóng
              </Button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
