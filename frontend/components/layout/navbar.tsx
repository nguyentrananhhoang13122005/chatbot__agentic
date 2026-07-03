"use client";

import Link from "next/link";
import { GraduationCap, Menu, X } from "lucide-react";
import { useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";

export function Navbar() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4 flex h-16 max-w-screen-2xl items-center justify-between">
        <div className="flex items-center gap-2">
          <Link href="/" className="flex items-center space-x-2">
            <GraduationCap className="h-7 w-7 text-primary" />
            <span className="hidden font-heading font-bold text-xl sm:inline-block">
              UniSearch AI
            </span>
          </Link>
        </div>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
          <Link href="/" className="transition-colors hover:text-primary">Trang chủ</Link>
          <Link href="/score" className="transition-colors hover:text-primary">Phân tích điểm</Link>
          <Link href="/chat" className="transition-colors hover:text-primary">Chat AI</Link>
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          
          {/* Mobile Menu Toggle */}
          <button 
            className="md:hidden p-2 text-foreground"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Nav */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-b border-border/40 bg-background px-4 py-4 space-y-4 shadow-lg">
          <nav className="flex flex-col space-y-4 text-sm font-medium">
            <Link 
              href="/" 
              className="px-2 py-1.5 transition-colors hover:text-primary"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              Trang chủ
            </Link>
            <Link 
              href="/score" 
              className="px-2 py-1.5 transition-colors hover:text-primary"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              Phân tích điểm
            </Link>
            <Link 
              href="/chat" 
              className="px-2 py-1.5 transition-colors hover:text-primary"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              Chat AI
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
