"use client";

import Link from "next/link";
import { GraduationCap, Menu, X } from "lucide-react";
import { useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/contexts/auth-context";
import { AuthDialog } from "@/components/auth/auth-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { LogOut, User } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Navbar() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isAuthDialogOpen, setIsAuthDialogOpen] = useState(false);
  const { user, logout, isLoading } = useAuth();

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
                <DropdownMenu>
                  <DropdownMenuTrigger className="relative h-8 w-8 rounded-full focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background">
                    <Avatar className="h-8 w-8 border border-white/10">
                      <AvatarImage src={user.avatar_url || ""} alt={user.display_name} />
                      <AvatarFallback className="bg-primary/20 text-primary">
                        {user.display_name ? user.display_name.charAt(0).toUpperCase() : "U"}
                      </AvatarFallback>
                    </Avatar>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="w-56" align="end">
                    <DropdownMenuLabel className="font-normal">
                      <div className="flex flex-col space-y-1">
                        <p className="text-sm font-medium leading-none">{user.display_name}</p>
                        <p className="text-xs leading-none text-muted-foreground">
                          {user.email}
                        </p>
                      </div>
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="text-red-500 focus:text-red-500 focus:bg-red-500/10 cursor-pointer"
                      onClick={() => logout()}
                    >
                      <LogOut className="mr-2 h-4 w-4" />
                      <span>Đăng xuất</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
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
