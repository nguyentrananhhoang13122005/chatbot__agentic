"use client";

import Link from "next/link";
import { ArrowRight, BarChart3, Compass, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { AnimatedCounter } from "@/components/ui/animated-counter";
import { GlassCard } from "@/components/ui/glass-card";

export default function Home() {
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 },
    },
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } },
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center relative overflow-hidden">
      {/* Background decorations */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-[128px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/20 rounded-full blur-[128px] pointer-events-none" />

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="container px-4 py-16 md:py-24 lg:py-32 flex flex-col items-center text-center relative z-10"
      >
        <motion.div variants={item} className="mb-6">
          <span className="inline-flex items-center rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-sm font-medium text-primary">
            <Sparkles className="mr-2 h-4 w-4" />
            Trợ lý tuyển sinh AI
          </span>
        </motion.div>

        <motion.h1
          variants={item}
          className="font-heading text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-6 max-w-4xl"
        >
          Tìm trường <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary">mơ ước</span> của bạn, ngay hôm nay.
        </motion.h1>

        <motion.p
          variants={item}
          className="text-lg md:text-xl text-muted-foreground mb-10 max-w-2xl"
        >
          UniSearch phân tích điểm số của bạn bằng AI để gợi ý lộ trình xét tuyển tối ưu nhất vào các trường Đại học tại Việt Nam.
        </motion.p>

        <motion.div variants={item} className="flex flex-col sm:flex-row gap-4 mb-20">
          <Link href="/score">
            <Button size="lg" className="h-12 px-8 text-base bg-gradient-to-r from-primary to-primary/80 hover:to-primary shadow-[0_0_20px_rgba(242,55,161,0.4)]">
              Bắt đầu phân tích
              <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
          </Link>
          <Link href="/chat">
            <Button size="lg" variant="outline" className="h-12 px-8 text-base bg-background/50 backdrop-blur-sm">
              Trò chuyện với AI
            </Button>
          </Link>
        </motion.div>

        {/* Stats Section */}
        <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-3 gap-8 w-full max-w-3xl mb-24 border-y border-border/50 py-8">
          <div className="flex flex-col items-center justify-center">
            <span className="text-4xl font-bold text-foreground">
              <AnimatedCounter value={200} suffix="+" />
            </span>
            <span className="text-sm text-muted-foreground mt-1">Trường Đại học</span>
          </div>
          <div className="flex flex-col items-center justify-center">
            <span className="text-4xl font-bold text-foreground">
              <AnimatedCounter value={5000} suffix="+" />
            </span>
            <span className="text-sm text-muted-foreground mt-1">Ngành học</span>
          </div>
          <div className="flex flex-col items-center justify-center col-span-2 md:col-span-1">
            <span className="text-4xl font-bold text-foreground">∞</span>
            <span className="text-sm text-muted-foreground mt-1">Câu hỏi giải đáp</span>
          </div>
        </motion.div>

        {/* Features Section */}
        <motion.div variants={item} className="grid md:grid-cols-3 gap-6 w-full max-w-5xl">
          <GlassCard glowColor="primary" className="p-6 text-left">
            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
              <Compass className="w-6 h-6 text-primary" />
            </div>
            <h3 className="font-heading text-xl font-bold mb-2">Định hướng ngành</h3>
            <p className="text-muted-foreground">Khám phá các ngành học phù hợp với điểm số và sở thích cá nhân của bạn.</p>
          </GlassCard>

          <GlassCard glowColor="secondary" className="p-6 text-left">
            <div className="w-12 h-12 rounded-lg bg-secondary/10 flex items-center justify-center mb-4">
              <BarChart3 className="w-6 h-6 text-secondary" />
            </div>
            <h3 className="font-heading text-xl font-bold mb-2">Phân tích điểm chuẩn</h3>
            <p className="text-muted-foreground">So sánh điểm của bạn với điểm chuẩn các năm trước để đưa ra lựa chọn an toàn.</p>
          </GlassCard>

          <GlassCard glowColor="primary" className="p-6 text-left md:col-span-1 sm:col-span-2">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center mb-4">
              <Sparkles className="w-6 h-6 text-foreground" />
            </div>
            <h3 className="font-heading text-xl font-bold mb-2">Tư vấn bằng AI</h3>
            <p className="text-muted-foreground">Trợ lý ảo 24/7 giải đáp mọi thắc mắc về quy chế, học phí và lộ trình xét tuyển.</p>
          </GlassCard>
        </motion.div>
      </motion.div>
    </div>
  );
}
