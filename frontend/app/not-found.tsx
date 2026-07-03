import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Home, ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center py-20 px-4 text-center">
      <div className="relative mb-8">
        <span className="text-[120px] md:text-[180px] font-heading font-black text-foreground/5 select-none leading-none">
          404
        </span>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-6xl md:text-8xl font-heading font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary">
            404
          </span>
        </div>
      </div>

      <h1 className="font-heading text-2xl md:text-3xl font-bold mb-3">
        Trang không tìm thấy
      </h1>
      <p className="text-muted-foreground max-w-md mb-8">
        Xin lỗi, trang bạn đang tìm kiếm không tồn tại hoặc đã được di chuyển.
      </p>

      <div className="flex gap-4">
        <Link href="/">
          <Button className="bg-gradient-to-r from-primary to-primary/80 shadow-[0_0_20px_rgba(242,55,161,0.3)]">
            <Home className="w-4 h-4 mr-2" />
            Trang chủ
          </Button>
        </Link>
        <Link href="/score">
          <Button variant="outline" className="bg-background/50 backdrop-blur-sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Phân tích điểm
          </Button>
        </Link>
      </div>
    </div>
  );
}
