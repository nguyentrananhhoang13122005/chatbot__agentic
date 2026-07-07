"use client";

import { useEffect, useState, Suspense, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { apiClient } from "@/lib/api";
import { Loader2 } from "lucide-react";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refreshMe } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const isProcessed = useRef(false);

  useEffect(() => {
    const handleCallback = async () => {
      if (isProcessed.current) return;
      isProcessed.current = true;

      const code = searchParams.get("code");
      const state = searchParams.get("state");
      const err = searchParams.get("error");

      if (err) {
        setError(`Google Auth Error: ${err}`);
        setTimeout(() => router.push("/"), 3000);
        return;
      }

      if (!code || !state) {
        setError("Không tìm thấy mã xác thực từ Google.");
        setTimeout(() => router.push("/"), 3000);
        return;
      }

      try {
        const response = await apiClient.post<{ status: string, user: unknown }>("/auth/google/callback", {
          code,
          state,
        });

        if (response.status === "success") {
          await refreshMe();
          router.push("/");
        }
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : "Xác thực Google thất bại.";
        setError(errorMessage);
        setTimeout(() => router.push("/"), 3000);
      }
    };

    handleCallback();
  }, [searchParams, refreshMe, router]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      {error ? (
        <div className="text-red-500 bg-red-500/10 border border-red-500/20 p-4 rounded-md">
          {error}
          <p className="text-sm mt-2 text-muted-foreground">Đang quay lại trang chủ...</p>
        </div>
      ) : (
        <>
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <p className="text-lg font-medium animate-pulse text-muted-foreground">
            Đang hoàn tất đăng nhập...
          </p>
        </>
      )}
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense 
      fallback={
        <div className="flex justify-center items-center min-h-[60vh]">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      }
    >
      <AuthCallbackContent />
    </Suspense>
  );
}
