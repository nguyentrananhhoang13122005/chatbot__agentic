"use client";

import { useState, useCallback } from "react";
import { toast } from "sonner";

export function useApi<T, P extends unknown[]>(
  apiFunc: (...args: P) => Promise<T>,
  options: {
    showSuccessToast?: boolean | string;
    showErrorToast?: boolean;
    onSuccess?: (data: T) => void;
    onError?: (error: Error) => void;
  } = {}
) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(
    async (...args: P): Promise<T | null> => {
      setIsLoading(true);
      setError(null);
      
      try {
        const result = await apiFunc(...args);
        setData(result);
        
        if (options.showSuccessToast) {
          toast.success(typeof options.showSuccessToast === "string" ? options.showSuccessToast : "Operation successful");
        }
        
        if (options.onSuccess) {
          options.onSuccess(result);
        }
        
        return result;
      } catch (err) {
        const errorObj = err instanceof Error ? err : new Error("Unknown error");
        setError(errorObj);
        
        if (options.showErrorToast !== false) {
          toast.error(errorObj.message || "An error occurred");
        }
        
        if (options.onError) {
          options.onError(errorObj);
        }
        
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [apiFunc, options]
  );

  return { data, isLoading, error, execute, setData };
}
