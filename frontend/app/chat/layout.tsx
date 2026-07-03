import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Chat AI Tuyển sinh | UniSearch AI",
  description: "Hỏi đáp với trợ lý AI về điểm chuẩn, học phí, quy chế tuyển sinh và so sánh trường đại học tại Việt Nam.",
};

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
