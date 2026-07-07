"use client";

import Link from "next/link";
import { ArrowRight, BarChart3, Compass, Sparkles, GraduationCap, Search, Target } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function Home() {
  const reduce = useReducedMotion();
  
  // Clean stagger reveal
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.08, delayChildren: 0.1 },
    },
  };

  const item = {
    hidden: { opacity: 0, y: 16 },
    show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } },
  };

  return (
    <div className="flex flex-col w-full pb-24 overflow-hidden relative min-h-screen">
      {/* Dynamic Animated Mesh Gradient */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none z-0 opacity-80">
        <motion.div 
          animate={{ 
            x: ["0vw", "-20vw", "10vw", "0vw"],
            y: ["0vh", "15vh", "-10vh", "0vh"],
            scale: [1, 1.2, 0.9, 1],
            rotate: [0, 90, 180, 360]
          }}
          transition={{ duration: 12, repeat: Infinity, ease: "linear" }}
          className="absolute top-[0%] right-[5%] w-[400px] h-[400px] sm:w-[500px] sm:h-[500px] rounded-full bg-primary/40 blur-[80px] mix-blend-screen dark:mix-blend-lighten"
        />
        <motion.div 
          animate={{ 
            x: ["0vw", "15vw", "-15vw", "0vw"],
            y: ["0vh", "-15vh", "15vh", "0vh"],
            scale: [0.9, 1.3, 1, 0.9],
            rotate: [360, 180, 90, 0]
          }}
          transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
          className="absolute top-[20%] right-[15%] w-[450px] h-[450px] sm:w-[600px] sm:h-[600px] rounded-full bg-secondary/40 blur-[90px] mix-blend-screen dark:mix-blend-lighten"
        />
        <motion.div 
          animate={{ 
            x: ["0vw", "20vw", "-5vw", "0vw"],
            y: ["0vh", "5vh", "-20vh", "0vh"],
            scale: [1.1, 0.8, 1.2, 1.1],
          }}
          transition={{ duration: 18, repeat: Infinity, ease: "linear" }}
          className="absolute top-[10%] right-[25%] w-[300px] h-[300px] sm:w-[400px] sm:h-[400px] rounded-full bg-blue-500/30 blur-[80px] mix-blend-screen dark:mix-blend-lighten"
        />
      </div>

      {/* Hero Section */}
      <section className="relative z-10 pt-20 md:pt-32 pb-16 md:pb-24 px-6 max-w-[1400px] mx-auto w-full">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-8 items-center">
          
          {/* Left: Typography */}
          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="max-w-3xl z-10"
          >
            <motion.h1
              variants={item}
              className="font-heading text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tighter leading-[1.05] text-balance mb-6 md:mb-8"
            >
              Tìm trường <br className="hidden sm:block" /> mơ ước của bạn.
            </motion.h1>

            <motion.p
              variants={item}
              className="text-base sm:text-lg md:text-xl text-muted-foreground max-w-[50ch] leading-relaxed mb-8 md:mb-10 text-pretty"
            >
              UniSearch phân tích điểm số bằng AI để gợi ý lộ trình xét tuyển tối ưu nhất vào các trường Đại học tại Việt Nam. Không còn mơ hồ.
            </motion.p>

            <motion.div variants={item} className="flex flex-col sm:flex-row items-stretch sm:items-start gap-4">
              <Link 
                href="/score"
                className={cn(buttonVariants({ size: "lg" }), "h-14 sm:h-12 px-8 text-base rounded-full shadow-lg shadow-primary/20 hover:-translate-y-0.5 transition-all active:translate-y-0 w-full sm:w-auto")}
              >
                Bắt đầu phân tích
                <ArrowRight className="ml-2 w-4 h-4" />
              </Link>
              <Link 
                href="/chat"
                className={cn(buttonVariants({ size: "lg", variant: "secondary" }), "h-14 sm:h-12 px-8 text-base rounded-full bg-secondary/10 hover:bg-secondary/20 text-foreground border-0 shadow-none hover:-translate-y-0.5 transition-all active:translate-y-0 w-full sm:w-auto")}
              >
                Trò chuyện với AI
              </Link>
            </motion.div>
          </motion.div>

          {/* Right: Abstract Animated Visual - CLUSTERED */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.3, ease: "easeOut" }}
            className="relative w-full h-[400px] sm:h-[500px] lg:h-[600px] flex items-center justify-center mt-12 lg:mt-0 z-10"
          >
            {/* Main AI Card */}
            <motion.div
              animate={{ y: [0, -20, 0] }}
              transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }}
              className="absolute z-20 w-[280px] sm:w-[340px] p-6 rounded-3xl bg-background/80 backdrop-blur-xl border border-white/10 shadow-[0_20px_40px_-15px_rgba(0,0,0,0.3)] dark:shadow-[0_20px_40px_-15px_rgba(0,0,0,0.8)]"
            >
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 rounded-2xl bg-primary/20 flex items-center justify-center">
                  <Sparkles className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <div className="text-base font-semibold text-foreground">AI Prediction</div>
                  <div className="text-sm text-muted-foreground">98% Match Rate</div>
                </div>
              </div>
              <div className="space-y-4">
                <div className="w-full h-2.5 rounded-full bg-muted overflow-hidden">
                  <motion.div 
                    initial={{ width: "0%" }}
                    animate={{ width: "85%" }}
                    transition={{ delay: 1, duration: 1.5, ease: "easeOut" }}
                    className="h-full bg-primary rounded-full shadow-[0_0_10px_rgba(242,55,161,0.5)]" 
                  />
                </div>
                <div className="w-full h-2.5 rounded-full bg-muted overflow-hidden">
                  <motion.div 
                    initial={{ width: "0%" }}
                    animate={{ width: "65%" }}
                    transition={{ delay: 1.2, duration: 1.5, ease: "easeOut" }}
                    className="h-full bg-secondary rounded-full shadow-[0_0_10px_rgba(44,64,167,0.5)]" 
                  />
                </div>
              </div>
            </motion.div>

            {/* Small Uni Badge (Overlapping Bottom Right) */}
            <motion.div
              animate={{ y: [0, 15, 0] }}
              transition={{ repeat: Infinity, duration: 4.5, ease: "easeInOut", delay: 0.5 }}
              className="absolute z-30 w-[200px] sm:w-[240px] p-5 rounded-2xl bg-secondary/90 backdrop-blur-md border border-white/10 shadow-2xl translate-x-[40%] translate-y-[80%]"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-background/20 flex items-center justify-center">
                  <GraduationCap className="w-6 h-6 text-white" />
                </div>
                <div>
                  <div className="text-base font-bold text-white">Top 10</div>
                  <div className="text-sm text-white/80">Đại học QG</div>
                </div>
              </div>
            </motion.div>

            {/* Search Pill (Overlapping Top Left) */}
            <motion.div
              animate={{ y: [0, -15, 0], rotate: [0, -2, 0] }}
              transition={{ repeat: Infinity, duration: 6, ease: "easeInOut", delay: 1 }}
              className="absolute z-10 p-4 px-6 rounded-full bg-background border border-border/50 shadow-xl -translate-x-[40%] -translate-y-[120%] flex items-center gap-3"
            >
              <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                <Search className="w-4 h-4 text-foreground" />
              </div>
              <span className="text-base font-medium text-foreground">Khối A00, 27.5 điểm</span>
            </motion.div>

          </motion.div>
        </div>
      </section>

      {/* Trust Metrics - Responsive Grid */}
      <section className="relative z-10 px-6 max-w-[1400px] mx-auto w-full mb-20 md:mb-32">
        <motion.div 
          initial={reduce ? { opacity: 0 } : { opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="grid grid-cols-1 sm:grid-cols-3 gap-8 sm:gap-12 pt-10 sm:pt-12 border-t border-border/40"
        >
          <div className="text-center sm:text-left">
            <div className="font-heading text-4xl sm:text-5xl font-bold tracking-tight mb-2">200+</div>
            <div className="text-xs sm:text-sm font-medium text-muted-foreground uppercase tracking-wider">Trường Đại học</div>
          </div>
          <div className="text-center sm:text-left">
            <div className="font-heading text-4xl sm:text-5xl font-bold tracking-tight mb-2">5k+</div>
            <div className="text-xs sm:text-sm font-medium text-muted-foreground uppercase tracking-wider">Ngành học</div>
          </div>
          <div className="text-center sm:text-left">
            <div className="font-heading text-4xl sm:text-5xl font-bold tracking-tight mb-2">∞</div>
            <div className="text-xs sm:text-sm font-medium text-muted-foreground uppercase tracking-wider">Câu hỏi được giải đáp</div>
          </div>
        </motion.div>
      </section>

      {/* Features - Asymmetric Bento Grid */}
      <section className="relative z-10 px-6 max-w-[1400px] mx-auto w-full">
        <motion.div 
          initial={reduce ? { opacity: 0 } : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.1 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="grid grid-cols-1 md:grid-cols-12 gap-4 md:gap-6 auto-rows-auto md:auto-rows-[400px]"
        >
          {/* Feature 1 - Wide card */}
          <div className="md:col-span-7 rounded-3xl bg-primary/5 border border-primary/10 p-8 sm:p-10 md:p-12 flex flex-col justify-between overflow-hidden relative group min-h-[300px]">
            <div className="absolute top-0 right-0 w-[300px] sm:w-[500px] h-[300px] sm:h-[500px] bg-primary/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3 group-hover:translate-x-1/4 transition-transform duration-1000 ease-out" />
            <div className="w-12 h-12 rounded-full bg-background flex items-center justify-center shadow-sm relative z-10 mb-8">
              <Sparkles className="w-5 h-5 text-primary" />
            </div>
            <div className="relative z-10">
              <h3 className="font-heading text-2xl md:text-3xl font-bold tracking-tight mb-3">Tư vấn bằng AI</h3>
              <p className="text-muted-foreground max-w-md text-base sm:text-lg">Trợ lý ảo 24/7 giải đáp mọi thắc mắc về quy chế, học phí và lộ trình xét tuyển. Hỏi mọi thứ bạn cần.</p>
            </div>
          </div>

          {/* Feature 2 - Narrow card */}
          <div className="md:col-span-5 rounded-3xl bg-secondary/5 border border-border p-8 sm:p-10 md:p-12 flex flex-col justify-between min-h-[300px]">
            <div className="w-12 h-12 rounded-full bg-background flex items-center justify-center shadow-sm mb-8">
              <Compass className="w-5 h-5 text-secondary" />
            </div>
            <div>
              <h3 className="font-heading text-2xl md:text-3xl font-bold tracking-tight mb-3">Định hướng ngành</h3>
              <p className="text-muted-foreground text-base sm:text-lg">Khám phá các ngành học phù hợp với điểm số và sở thích cá nhân.</p>
            </div>
          </div>

          {/* Feature 3 - Full width panoramic card */}
          <div className="md:col-span-12 rounded-3xl bg-muted/40 border border-border p-8 sm:p-10 md:p-12 flex flex-col md:flex-row items-start md:items-center justify-between gap-8 sm:gap-12">
            <div className="max-w-xl">
              <div className="w-12 h-12 rounded-full bg-background flex items-center justify-center shadow-sm mb-8">
                <Target className="w-5 h-5 text-foreground" />
              </div>
              <h3 className="font-heading text-2xl md:text-3xl font-bold tracking-tight mb-3">Phân tích điểm chuẩn</h3>
              <p className="text-muted-foreground text-base sm:text-lg">So sánh điểm của bạn với điểm chuẩn các năm trước để đưa ra lựa chọn an toàn và chính xác nhất.</p>
            </div>
            
            {/* Animated Data Visualization */}
            <div className="w-full md:w-[400px] h-[200px] md:h-[240px] rounded-2xl bg-background border border-border flex items-center justify-center shadow-sm relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-tr from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <div className="flex items-end gap-2 sm:gap-3 h-32 px-6 w-full">
                <motion.div initial={{ height: "10%" }} whileInView={{ height: "40%" }} transition={{ duration: 1, delay: 0.1 }} className="flex-1 bg-primary/20 rounded-t-sm" />
                <motion.div initial={{ height: "10%" }} whileInView={{ height: "60%" }} transition={{ duration: 1, delay: 0.2 }} className="flex-1 bg-primary/40 rounded-t-sm" />
                <motion.div initial={{ height: "10%" }} whileInView={{ height: "75%" }} transition={{ duration: 1, delay: 0.3 }} className="flex-1 bg-primary/60 rounded-t-sm" />
                <motion.div initial={{ height: "10%" }} whileInView={{ height: "95%" }} transition={{ duration: 1, delay: 0.4 }} className="flex-1 bg-primary rounded-t-sm" />
              </div>
            </div>
          </div>
        </motion.div>
      </section>
    </div>
  );
}
