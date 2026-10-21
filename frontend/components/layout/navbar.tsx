"use client";

import Link from "next/link";
import { GraduationCap, Menu, X } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/contexts/auth-context";
import { AuthDialog } from "@/components/auth/auth-dialog";
import { LogOut, User } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Navbar() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isAuthDialogOpen, setIsAuthDialogOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const { user, logout, isLoading } = useAuth();

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };
    if (isUserMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isUserMenuOpen]);

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
          {/* User Section */}
          {!isLoading && (
            <>
              {user ? (
                <div className="relative" ref={userMenuRef}>
                  <button
                    type="button"
                    onClick={() => setIsUserMenuOpen((prev) => !prev)}
                    className="relative flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-primary/20 text-primary font-semibold text-sm transition-transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background cursor-pointer"
                    aria-label="User profile menu"
                    aria-expanded={isUserMenuOpen}
                  >
                    {user.avatar_url ? (
                      <img
                        src={user.avatar_url}
                        alt={user.display_name}
                        className="h-8 w-8 rounded-full object-cover"
                      />
                    ) : (
                      <span>{user.display_name ? user.display_name.charAt(0).toUpperCase() : "U"}</span>
                    )}
                  </button>

                  {isUserMenuOpen && (
                    <div className="absolute right-0 mt-2 w-60 rounded-xl border border-white/10 bg-popover/95 p-1.5 text-popover-foreground shadow-2xl backdrop-blur-xl animate-in fade-in-0 zoom-in-95 z-50">
                      <div className="px-3 py-2 border-b border-border/40">
                        <p className="text-sm font-semibold text-foreground truncate">{user.display_name}</p>
                        <p className="text-xs text-muted-foreground truncate mt-0.5">{user.email}</p>
                      </div>
                      <div className="pt-1">
                        <button
                          type="button"
                          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-500 hover:bg-red-500/10 transition-colors font-medium cursor-pointer"
                          onClick={async () => {
                            setIsUserMenuOpen(false);
                            await logout();
                          }}
                        >
                          <LogOut className="h-4 w-4" />
                          <span>Đăng xuất</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <Button
                  variant="outline" 
                  size="sm" 
                  className="hidden md:flex bg-white/5 border-white/10 hover:bg-white/10 hover:text-primary transition-all"
                  onClick={() => setIsAuthDialogOpen(true)}
                >
                  <User className="mr-2 h-4 w-4" />
                  Đăng nhập
                </Button>
              )}
            </>
          )}

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

            {!user && !isLoading && (
              <button
                className="px-2 py-1.5 text-left text-primary transition-colors hover:text-primary/80"
                onClick={() => {
                  setIsMobileMenuOpen(false);
                  setIsAuthDialogOpen(true);
                }}
              >
                Đăng nhập / Đăng ký
              </button>
            )}

            {user && (
              <button
                className="px-2 py-1.5 text-left text-red-500 transition-colors hover:text-red-400 flex items-center"
                onClick={() => {
                  setIsMobileMenuOpen(false);
                  logout();
                }}
              >
                <LogOut className="mr-2 h-4 w-4" />
                Đăng xuất
              </button>
            )}
          </nav>
        </div>
      )}

      <AuthDialog
        isOpen={isAuthDialogOpen} 
        onOpenChange={setIsAuthDialogOpen} 
      />
    </header>
  );
}
