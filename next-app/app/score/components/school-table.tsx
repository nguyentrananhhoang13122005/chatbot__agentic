import { formatScore, formatTier } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Building2, BookOpen, GraduationCap, Info } from "lucide-react";

interface SchoolTableProps {
  schools: any[];
}

export function SchoolTable({ schools }: SchoolTableProps) {
  if (!schools || schools.length === 0) {
    return (
      <Card className="bg-white/5 border-white/10 backdrop-blur-md">
        <CardContent className="p-8 text-center text-muted-foreground">
          Không tìm thấy trường nào phù hợp với tiêu chí hiện tại. Vui lòng mở rộng bộ lọc.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Mobile & Desktop hybrid using CSS classes */}
      
      {/* Desktop Table View */}
      <div className="hidden md:block rounded-xl border border-white/10 bg-white/5 backdrop-blur-md overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-muted/30 text-muted-foreground uppercase text-xs border-b border-white/10">
            <tr>
              <th className="px-4 py-3 font-medium">Trường ĐH</th>
              <th className="px-4 py-3 font-medium">Ngành học</th>
              <th className="px-4 py-3 font-medium text-center">Tổ hợp môn</th>
              <th className="px-4 py-3 font-medium text-center">Điểm của bạn</th>
              <th className="px-4 py-3 font-medium text-center">Điểm chuẩn (Năm)</th>
              <th className="px-4 py-3 font-medium text-center">Đánh giá</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {schools.map((school, i) => {
              const tier = formatTier(school.tier);
              return (
                <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                  <td className="px-4 py-4 font-semibold text-foreground">
                    <div className="flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-muted-foreground" />
                      {school.school_name}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="font-medium">{school.major_name}</div>
                    <div className="text-xs text-muted-foreground">Mã: {school.major_code}</div>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <div className="flex gap-1 flex-wrap justify-center max-w-[120px] mx-auto">
                      {school.combo?.split(",").map((c: string) => (
                        <Badge key={c} variant="outline" className="text-[10px] px-1 py-0 h-4 border-white/20">
                          {c.trim()}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-4 text-center font-bold text-primary">
                    {formatScore(school.score)}
                  </td>
                  <td className="px-4 py-4 text-center">
                    <div className="font-medium">{school.year_score || "-"}</div>
                    <div className="text-xs text-muted-foreground">Năm {school.year}</div>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <Badge variant="outline" className={`px-2 py-1 text-xs whitespace-nowrap ${tier.colorClass} border-current`}>
                      {tier.icon} {tier.label}
                    </Badge>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View */}
      <div className="md:hidden space-y-4">
        {schools.map((school, i) => {
          const tier = formatTier(school.tier);
          return (
            <Card key={i} className="bg-white/5 border-white/10 backdrop-blur-md overflow-hidden">
              <CardHeader className="p-4 pb-3 bg-muted/20 border-b border-border/50">
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <CardTitle className="text-base font-bold text-foreground line-clamp-2">
                      {school.school_name}
                    </CardTitle>
                    <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground">
                      <BookOpen className="w-3.5 h-3.5 shrink-0" />
                      <span className="line-clamp-1">{school.major_name} ({school.major_code})</span>
                    </div>
                  </div>
                  <Badge variant="outline" className={`px-2 py-1 text-[10px] whitespace-nowrap shrink-0 ${tier.colorClass} border-current`}>
                    {tier.icon} {tier.label}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-4">
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div className="space-y-1 bg-black/10 dark:bg-black/20 p-2 rounded-lg">
                    <div className="text-[10px] text-muted-foreground uppercase font-medium">Điểm chuẩn {school.year}</div>
                    <div className="text-lg font-bold font-heading">{school.year_score || "-"}</div>
                  </div>
                  <div className="space-y-1 bg-primary/10 p-2 rounded-lg">
                    <div className="text-[10px] text-primary uppercase font-medium">Điểm của bạn</div>
                    <div className="text-lg font-bold font-heading text-primary">{formatScore(school.score)}</div>
                  </div>
                </div>
                
                <div className="space-y-2 mb-3">
                  <div className="text-[10px] text-muted-foreground uppercase font-medium">Tổ hợp môn xét tuyển</div>
                  <div className="flex gap-1 flex-wrap">
                    {school.combo?.split(",").map((c: string) => (
                      <Badge key={c} variant="secondary" className="bg-white/5 border-white/10 text-xs py-0 h-5">
                        {c.trim()}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="pt-3 border-t border-border/50 flex flex-wrap gap-2 text-[10px] text-muted-foreground">
                  <span className="flex items-center gap-1 bg-muted/50 px-2 py-1 rounded">
                    <GraduationCap className="w-3 h-3" /> {school.method}
                  </span>
                  {school.notes && (
                    <span className="flex items-center gap-1 bg-muted/50 px-2 py-1 rounded">
                      <Info className="w-3 h-3" /> {school.notes}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
      
      <div className="text-center text-sm text-muted-foreground pt-2">
        Hiển thị {schools.length} kết quả phù hợp nhất
      </div>
    </div>
  );
}
