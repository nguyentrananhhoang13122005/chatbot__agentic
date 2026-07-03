import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Phân tích điểm số | UniSearch AI",
  description: "Nhập điểm thi THPT hoặc điểm học bạ để phân tích tổ hợp môn và gợi ý trường đại học phù hợp nhất.",
};

export default function ScoreLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
