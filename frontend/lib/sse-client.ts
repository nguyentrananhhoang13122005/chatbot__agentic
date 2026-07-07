export type SSECallback = {
  onMeta?: (meta: Record<string, unknown>) => void;
  onChunk?: (chunk: string) => void;
  onDone?: () => void;
  onError?: (err: unknown) => void;
};

export async function fetchSSE(
  url: string,
  body: Record<string, unknown>,
  callbacks: SSECallback,
  signal?: AbortSignal,
) {
  try {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    const fullUrl = url.startsWith("http") ? url : `${API_BASE_URL}${url}`;

    const res = await fetch(fullUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
      },
      body: JSON.stringify(body),
      signal,
      credentials: "include",
    });

    if (!res.ok) {
      throw new Error(`HTTP Error: ${res.status}`);
    }

    if (!res.body) throw new Error("ReadableStream not supported in this environment");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        callbacks.onDone?.();
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep the last incomplete line in buffer

      for (const line of lines) {
        if (line.trim() === "") continue;
        if (line.startsWith("data: ")) {
          const dataStr = line.substring(6).trim();
          if (dataStr === "[DONE]") {
            callbacks.onDone?.();
            // In SSE, usually [DONE] implies stream closure, but we'll let the reader end naturally
            continue;
          }
          
          try {
            const data = JSON.parse(dataStr);
            if (data.type === "meta") {
              callbacks.onMeta?.(data);
            } else if (data.type === "chunk" && data.content) {
              callbacks.onChunk?.(data.content);
            } else if (!data.type && data.content) {
              // Support for /recommend endpoint which doesn't send "type"
              callbacks.onChunk?.(data.content);
            }
          } catch {
            console.error("Failed to parse SSE JSON data:", dataStr);
          }
        }
      }
    }
  } catch (err) {
    // Silent abort — user navigated away or triggered re-run
    if (err instanceof DOMException && err.name === "AbortError") return;
    callbacks.onError?.(err);
  }
}
