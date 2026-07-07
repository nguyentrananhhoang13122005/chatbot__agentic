export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export class ApiError extends Error {
  public status: number;
  public data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = "ApiError";
  }
}

async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
      credentials: "include", // Use HttpOnly Cookies
    });

    const isJson = response.headers.get("content-type")?.includes("application/json");
    const data = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      const errorMessage = data?.detail || response.statusText || "Something went wrong";
      throw new ApiError(response.status, typeof errorMessage === "string" ? errorMessage : JSON.stringify(errorMessage), data);
    }

    return data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new Error(error instanceof Error ? error.message : "Network error");
  }
}

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestInit) => apiFetch<T>(endpoint, { ...options, method: "GET" }),
  post: <T>(endpoint: string, body?: any, options?: RequestInit) => apiFetch<T>(endpoint, { ...options, method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(endpoint: string, body?: any, options?: RequestInit) => apiFetch<T>(endpoint, { ...options, method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(endpoint: string, options?: RequestInit) => apiFetch<T>(endpoint, { ...options, method: "DELETE" }),
};
