import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatScore(score: number | string | undefined | null): string {
  if (score === undefined || score === null) return "-";
  const num = typeof score === "string" ? parseFloat(score) : score;
  if (isNaN(num)) return "-";
  return num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatTier(tier: string | undefined): { label: string, colorClass: string, icon: string } {
  if (!tier) return { label: "N/A", colorClass: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300", icon: "⚪" };
  
  const normalized = tier.toUpperCase();
  if (normalized.includes("AN TOÀN")) {
    return { label: "AN TOÀN", colorClass: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 border-green-200 dark:border-green-800", icon: "🟢" };
  }
  if (normalized.includes("VỪA SỨC")) {
    return { label: "VỪA SỨC", colorClass: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800", icon: "🟡" };
  }
  if (normalized.includes("THỬ THÁCH")) {
    return { label: "THỬ THÁCH", colorClass: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border-red-200 dark:border-red-800", icon: "🔴" };
  }
  
  return { label: tier, colorClass: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-700", icon: "⚪" };
}
