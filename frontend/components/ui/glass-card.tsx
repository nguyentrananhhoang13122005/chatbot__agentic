import * as React from "react";
import { cn } from "@/lib/utils";
import { motion, HTMLMotionProps } from "framer-motion";

interface GlassCardProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  className?: string;
  glowColor?: "primary" | "secondary" | "none";
}

export const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  ({ children, className, glowColor = "none", ...props }, ref) => {
    const glowClasses = {
      primary: "hover:shadow-[0_0_30px_-5px_rgba(242,55,161,0.3)]",
      secondary: "hover:shadow-[0_0_30px_-5px_rgba(44,64,167,0.3)]",
      none: "",
    };

    return (
      <motion.div
        ref={ref}
        className={cn(
          "relative overflow-hidden rounded-2xl border border-white/20 dark:border-white/10",
          "bg-white/70 dark:bg-zinc-900/50 backdrop-blur-xl",
          "transition-all duration-300",
          glowClasses[glowColor],
          className
        )}
        {...props}
      >
        {/* Subtle inner highlight */}
        <div className="absolute inset-0 rounded-2xl ring-1 ring-inset ring-white/10 pointer-events-none" />
        {children}
      </motion.div>
    );
  }
);
GlassCard.displayName = "GlassCard";
