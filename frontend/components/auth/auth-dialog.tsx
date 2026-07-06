"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";
import { apiClient } from "@/lib/api-client";
import { Loader2 } from "lucide-react";

export function AuthDialog({
  isOpen,
  onOpenChange,
}: {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { login, register } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // Form states
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPass, setLoginPass] = useState("");

  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPass, setRegPass] = useState("");
  const [regPass2, setRegPass2] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    try {
      await login({ email: loginEmail, password: loginPass });
      onOpenChange(false);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Đăng nhập thất bại";
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (regPass !== regPass2) {
      setError("Mật khẩu xác nhận không khớp.");
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      await register({
        email: regEmail,
        display_name: regName,
        password: regPass,
      });
      onOpenChange(false);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Đăng ký thất bại";
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleAuth = async () => {
    setIsLoading(true);
    setError("");
    try {
      const { url } = await apiClient.getGoogleUrl();
      if (url) {
        window.location.href = url;
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Không thể khởi tạo Google Auth";
      setError(errorMessage);
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px] bg-background/80 backdrop-blur-xl border border-white/10 shadow-[0_0_40px_rgba(242,55,161,0.1)]">
        <DialogHeader>
          <DialogTitle className="text-2xl font-heading font-bold text-center">
            Tham gia UniSearch AI
          </DialogTitle>
          <DialogDescription className="text-center">
            Đăng nhập để lưu trữ kết quả phân tích
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-2">
          <Button
            type="button"
            variant="outline"
            className="w-full flex items-center justify-center gap-2 border-white/10 hover:bg-white/5 transition-all"
            onClick={handleGoogleAuth}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
            )}
            Tiếp tục với Google
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-white/10" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background/80 px-2 text-muted-foreground backdrop-blur-sm">
                Hoặc
              </span>
            </div>
          </div>

          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2 bg-white/5">
              <TabsTrigger value="login">Đăng nhập</TabsTrigger>
              <TabsTrigger value="register">Đăng ký</TabsTrigger>
            </TabsList>
            
            {error && (
              <div className="mt-4 p-2 bg-red-500/10 border border-red-500/20 rounded text-red-500 text-sm text-center animate-in fade-in zoom-in-95">
                {error}
              </div>
            )}

            <TabsContent value="login">
              <form onSubmit={handleLogin} className="space-y-4 mt-4">
                <div className="space-y-2">
                  <input
                    type="email"
                    required
                    placeholder="Email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <input
                    type="password"
                    required
                    placeholder="Mật khẩu"
                    value={loginPass}
                    onChange={(e) => setLoginPass(e.target.value)}
                    className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  />
                </div>
                <Button 
                  type="submit" 
                  className="w-full bg-gradient-to-r from-primary to-primary/80 hover:to-primary/90 shadow-[0_0_15px_rgba(242,55,161,0.3)] transition-all"
                  disabled={isLoading}
                >
                  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Đăng nhập
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="register">
              <form onSubmit={handleRegister} className="space-y-4 mt-4">
                <div className="space-y-2">
                  <input
                    type="text"
                    required
                    placeholder="Họ và tên"
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                    className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <input
                    type="email"
                    required
                    placeholder="Email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <input
                    type="password"
                    required
                    placeholder="Mật khẩu (tối thiểu 8 ký tự)"
                    value={regPass}
                    onChange={(e) => setRegPass(e.target.value)}
                    className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <input
                    type="password"
                    required
                    placeholder="Xác nhận mật khẩu"
                    value={regPass2}
                    onChange={(e) => setRegPass2(e.target.value)}
                    className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  />
                </div>
                <Button 
                  type="submit" 
                  className="w-full bg-gradient-to-r from-primary to-primary/80 hover:to-primary/90 shadow-[0_0_15px_rgba(242,55,161,0.3)] transition-all"
                  disabled={isLoading}
                >
                  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Đăng ký
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  );
}
