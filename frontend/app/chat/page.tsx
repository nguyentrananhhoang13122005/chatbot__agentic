"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { fetchSSE } from "@/lib/sse-client";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { 
  Send, 
  Sparkles, 
  User, 
  GraduationCap, 
  Loader2, 
  MessageSquare, 
  Plus, 
  Trash2, 
  PanelLeftClose, 
  PanelLeft, 
  History, 
  X,
  Lock,
  ChevronRight
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { motion, AnimatePresence } from "framer-motion";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface ChatSession {
  id: string;
  title: string;
  bookmarked?: boolean;
  created_at: string;
  updated_at: string;
}

const WELCOME_MESSAGE: Message = {
  id: "welcome",
  role: "assistant",
  content: "Xin chào! Tôi là **Trợ lý AI tuyển sinh UniSearch**. Bạn muốn tra cứu điểm chuẩn trường nào, hay cần tư vấn chọn ngành gì? Hãy hỏi tôi nhé!"
};

const SUGGESTION_CHIPS = [
  { label: "Top 5 trường CNTT", query: "Top 5 trường đại học tốt nhất về Công nghệ thông tin?" },
  { label: "Điểm chuẩn Ngoại thương", query: "Điểm chuẩn Đại học Ngoại thương các ngành năm gần nhất?" },
  { label: "Học phí RMIT", query: "Học phí RMIT Việt Nam năm 2025 bao nhiêu?" },
  { label: "HUST vs KHTN", query: "So sánh Bách Khoa Hà Nội và ĐH Khoa học Tự nhiên HCM ngành CNTT?" },
];

export default function ChatPage() {
  const { user } = useAuth();
  
  // Chat state
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [dataAsOf, setDataAsOf] = useState("");
  
  // Session & Sidebar state
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const idCounterRef = useRef(0);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load session list (từ backend nếu đã đăng nhập, hoặc localStorage nếu là khách)
  const loadSessions = useCallback(async () => {
    setIsLoadingSessions(true);
    try {
      if (user) {
        const data = await apiClient.get<ChatSession[]>("/chat/sessions");
        setSessions(Array.isArray(data) ? data : []);
      } else {
        const local = localStorage.getItem("unisearch_guest_sessions");
        if (local) {
          try {
            setSessions(JSON.parse(local));
          } catch {
            setSessions([]);
          }
        } else {
          setSessions([]);
        }
      }
    } catch (err) {
      console.error("Lỗi tải danh sách session:", err);
    } finally {
      setIsLoadingSessions(false);
    }
  }, [user]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Bắt đầu một đoạn chat mới (+ New Chat)
  const startNewChat = () => {
    setCurrentSessionId(null);
    setMessages([WELCOME_MESSAGE]);
    setShowSuggestions(true);
    setDataAsOf("");
    setInput("");
    setIsMobileSidebarOpen(false);
  };

  // Chọn một phiên chat từ danh sách
  const selectSession = async (sessionId: string) => {
    if (sessionId === currentSessionId) {
      setIsMobileSidebarOpen(false);
      return;
    }
    
    setCurrentSessionId(sessionId);
    setIsMobileSidebarOpen(false);
    setShowSuggestions(false);
    
    try {
      if (user) {
        const data = await apiClient.get<{ id: string; messages: Array<{ role: "user" | "assistant"; content: string }> }>(
          `/chat/sessions/${sessionId}`
        );
        if (data && Array.isArray(data.messages) && data.messages.length > 0) {
          setMessages(
            data.messages.map((m, idx) => ({
              id: `hist-${idx}`,
              role: m.role as "user" | "assistant",
              content: m.content,
            }))
          );
        } else {
          setMessages([WELCOME_MESSAGE]);
        }
      } else {
        const local = localStorage.getItem(`unisearch_guest_msgs_${sessionId}`);
        if (local) {
          try {
            setMessages(JSON.parse(local));
          } catch {
            setMessages([WELCOME_MESSAGE]);
          }
        } else {
          setMessages([WELCOME_MESSAGE]);
        }
      }
    } catch (err) {
      console.error("Lỗi tải tin nhắn phiên chat:", err);
    }
  };

  // Xóa một phiên chat
  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      if (user) {
        await apiClient.delete(`/chat/sessions/${sessionId}`);
      } else {
        const updated = sessions.filter(s => s.id !== sessionId);
        localStorage.setItem("unisearch_guest_sessions", JSON.stringify(updated));
        localStorage.removeItem(`unisearch_guest_msgs_${sessionId}`);
      }
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        startNewChat();
      }
    } catch (err) {
      console.error("Lỗi xóa phiên chat:", err);
    }
  };

  // Gửi tin nhắn
  const sendMessage = async (userMessage: string) => {
    if (!userMessage.trim() || isLoading) return;

    setInput("");
    setShowSuggestions(false);

    // Xác định sessionId (nếu là chat mới -> sinh UUID)
    let activeSessionId = currentSessionId;
    if (!activeSessionId) {
      activeSessionId = typeof crypto !== "undefined" && crypto.randomUUID 
        ? crypto.randomUUID() 
        : `sess-${Date.now()}`;
      setCurrentSessionId(activeSessionId);
    }

    const userMsgId = `msg-${++idCounterRef.current}`;
    const newMessages = [...messages, { id: userMsgId, role: "user" as const, content: userMessage }];
    setMessages(newMessages);
    setIsLoading(true);

    const assistantMsgId = `msg-${++idCounterRef.current}`;
    setMessages([...newMessages, { id: assistantMsgId, role: "assistant", content: "" }]);

    // Chuẩn bị history cho server (tối đa 8 tin gần nhất)
    const history = messages
      .filter(m => m.id !== "welcome" && m.content.trim() !== "")
      .slice(-8)
      .map(m => ({ role: m.role, content: m.content }));

    let assistantFullResponse = "";

    await fetchSSE("/schools/chat", {
      user_query: userMessage,
      history,
      stream: true,
      session_id: activeSessionId,
    }, {
      onMeta: (meta) => {
        const label = typeof meta.data_as_of === "string" ? meta.data_as_of : "";
        if (label) setDataAsOf(label);
      },
      onChunk: (chunk) => {
        assistantFullResponse += chunk;
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMsgId 
            ? { ...msg, content: msg.content + chunk }
            : msg
        ));
      },
      onDone: () => {
        setIsLoading(false);
        // Lưu cho khách nếu chưa đăng nhập
        if (!user && activeSessionId) {
          const finalMessages = [
            ...newMessages,
            { id: assistantMsgId, role: "assistant" as const, content: assistantFullResponse }
          ];
          localStorage.setItem(`unisearch_guest_msgs_${activeSessionId}`, JSON.stringify(finalMessages));
          
          // Cập nhật session list khách
          const title = userMessage.length > 35 ? userMessage.substring(0, 35) + "..." : userMessage;
          const existing = sessions.find(s => s.id === activeSessionId);
          let newSessionsList: ChatSession[];
          if (!existing) {
            newSessionsList = [{
              id: activeSessionId,
              title,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            }, ...sessions];
          } else {
            newSessionsList = sessions.map(s => s.id === activeSessionId ? { ...s, updated_at: new Date().toISOString() } : s);
          }
          setSessions(newSessionsList);
          localStorage.setItem("unisearch_guest_sessions", JSON.stringify(newSessionsList));
        } else {
          // Người dùng đã đăng nhập: server tự động lưu vào SQLite DB qua API, chỉ cần reload list để hiện title mới
          loadSessions();
        }
      },
      onError: (err) => {
        console.error("Chat error:", err);
        const tooMany = err instanceof Error && err.message.includes("429");
        const note = tooMany
          ? "\n\n*(Bạn gửi câu hỏi hơi nhanh. Vui lòng thử lại sau ít giây)*"
          : "\n\n*(Lỗi kết nối. Xin vui lòng thử lại sau)*";
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMsgId 
            ? { ...msg, content: msg.content + note }
            : msg
        ));
        setIsLoading(false);
      }
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await sendMessage(input.trim());
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden bg-background">
      {/* ========================================================================= */}
      {/* SIDEBAR: DESKTOP & MOBILE DRAWER */}
      {/* ========================================================================= */}
      
      {/* Mobile Backdrop */}
      {isMobileSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setIsMobileSidebarOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-72 bg-card/95 border-r border-border/40 backdrop-blur-xl flex flex-col transition-all duration-300 md:static md:z-0
        ${isSidebarOpen ? "md:w-72" : "md:w-0 md:opacity-0 md:pointer-events-none"}
        ${isMobileSidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
      `}>
        {/* Top Header of Sidebar: New Chat Button */}
        <div className="p-3 border-b border-border/40 flex items-center justify-between gap-2">
          <Button
            onClick={startNewChat}
            className="flex-1 justify-start gap-2 bg-primary/10 border border-primary/20 text-primary hover:bg-primary/20 font-medium rounded-xl h-10 shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Đoạn chat mới</span>
          </Button>

          {/* Mobile Close Button */}
          <button
            onClick={() => setIsMobileSidebarOpen(false)}
            className="md:hidden p-2 text-muted-foreground hover:text-foreground rounded-lg"
            aria-label="Đóng menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
          <div className="px-2 py-1.5 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
            Lịch sử trò chuyện
          </div>

          {isLoadingSessions ? (
            <div className="flex items-center justify-center p-6 text-muted-foreground text-sm gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              <span>Đang tải lịch sử...</span>
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-4 text-center text-xs text-muted-foreground/80 space-y-2">
              <MessageSquare className="w-8 h-8 mx-auto text-muted-foreground/40" />
              <p>Chưa có đoạn chat nào.</p>
              <p className="text-[11px]">Hãy đặt câu hỏi để bắt đầu cuộc trò chuyện!</p>
            </div>
          ) : (
            sessions.map((sess) => {
              const isActive = sess.id === currentSessionId;
              return (
                <div
                  key={sess.id}
                  onClick={() => selectSession(sess.id)}
                  className={`
                    group relative flex items-center justify-between w-full px-3 py-2.5 rounded-xl text-sm transition-all cursor-pointer
                    ${isActive 
                      ? "bg-primary/15 text-primary font-medium border border-primary/25 shadow-sm" 
                      : "text-muted-foreground hover:bg-white/5 hover:text-foreground border border-transparent"}
                  `}
                >
                  <div className="flex items-center gap-2.5 min-w-0 flex-1 pr-2">
                    <MessageSquare className={`w-4 h-4 shrink-0 ${isActive ? "text-primary" : "text-muted-foreground/60"}`} />
                    <span className="truncate text-xs md:text-sm">{sess.title || "Cuộc trò chuyện mới"}</span>
                  </div>

                  {/* Delete Action */}
                  <button
                    onClick={(e) => handleDeleteSession(sess.id, e)}
                    className="opacity-0 group-hover:opacity-100 hover:text-red-400 p-1 text-muted-foreground/60 hover:bg-red-500/10 rounded transition-all shrink-0"
                    title="Xóa đoạn chat này"
                    aria-label="Xóa đoạn chat"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Bottom User/Sync Indicator */}
        <div className="p-3 border-t border-border/40 bg-card/40 text-xs">
          {user ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="truncate">Đã đồng bộ tài khoản: <strong>{user.display_name}</strong></span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-amber-500/90">
              <Lock className="w-3.5 h-3.5 shrink-0" />
              <span className="text-[11px] leading-tight">Đăng nhập để lưu lịch sử vĩnh viễn trên đám mây</span>
            </div>
          )}
        </div>
      </aside>

      {/* ========================================================================= */}
      {/* MAIN CHAT AREA */}
      {/* ========================================================================= */}
      <main className="flex-1 flex flex-col h-full min-w-0 relative">
        {/* Top Control Bar */}
        <div className="h-12 border-b border-border/40 px-4 flex items-center justify-between shrink-0 bg-background/80 backdrop-blur-md">
          <div className="flex items-center gap-2">
            {/* Desktop Toggle Button */}
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="hidden md:flex p-1.5 text-muted-foreground hover:text-foreground hover:bg-white/5 rounded-lg transition-colors"
              title={isSidebarOpen ? "Đóng danh sách lịch sử" : "Mở danh sách lịch sử"}
            >
              {isSidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeft className="w-4 h-4" />}
            </button>

            {/* Mobile Toggle Button */}
            <button
              onClick={() => setIsMobileSidebarOpen(true)}
              className="md:hidden p-1.5 text-muted-foreground hover:text-foreground hover:bg-white/5 rounded-lg transition-colors flex items-center gap-1.5 text-xs font-medium"
            >
              <History className="w-4 h-4 text-primary" />
              <span>Lịch sử ({sessions.length})</span>
            </button>

            <span className="text-xs md:text-sm font-semibold text-foreground truncate max-w-xs md:max-w-md ml-1">
              {currentSessionId 
                ? (sessions.find(s => s.id === currentSessionId)?.title || "Cuộc trò chuyện") 
                : "Đoạn chat mới"}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={startNewChat}
              className="h-8 text-xs gap-1 rounded-lg border-white/10 bg-white/5 hover:bg-white/10 hover:text-primary transition-all"
            >
              <Plus className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Đoạn chat mới</span>
            </Button>
          </div>
        </div>

        {/* Message Scroll Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 max-w-4xl w-full mx-auto">
          <AnimatePresence mode="popLayout">
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
                className={`flex gap-3 md:gap-4 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-sm ${
                  msg.role === "user" 
                    ? "bg-secondary text-white" 
                    : "bg-primary text-white"
                }`}>
                  {msg.role === "user" ? <User className="w-4 h-4" /> : <GraduationCap className="w-4 h-4" />}
                </div>
                
                <div className={`max-w-[85%] md:max-w-[80%] rounded-2xl px-4 py-3 ${
                  msg.role === "user" 
                    ? "bg-secondary text-white rounded-tr-none shadow-md" 
                    : "bg-card/70 border border-border/50 backdrop-blur-md rounded-tl-none shadow-sm"
                }`}>
                  {msg.content === "" && isLoading && msg.role === "assistant" ? (
                    <div className="flex items-center gap-2 h-6">
                      <span className="w-2 h-2 rounded-full bg-primary animate-bounce" />
                      <span className="w-2 h-2 rounded-full bg-primary animate-bounce [animation-delay:75ms]" />
                      <span className="w-2 h-2 rounded-full bg-primary animate-bounce [animation-delay:150ms]" />
                    </div>
                  ) : (
                    <div className="prose prose-sm dark:prose-invert max-w-none break-words text-foreground">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm, remarkBreaks]}
                        components={{
                          table: ({ node, ...props }) => (
                            <div className="my-3 overflow-x-auto rounded-xl border border-white/10 bg-white/[0.02] shadow-sm">
                              <table className="min-w-full text-xs md:text-sm text-left border-collapse" {...props} />
                            </div>
                          ),
                          thead: ({ node, ...props }) => (
                            <thead className="bg-white/10 text-foreground font-semibold border-b border-white/10" {...props} />
                          ),
                          tbody: ({ node, ...props }) => (
                            <tbody className="divide-y divide-white/5" {...props} />
                          ),
                          tr: ({ node, ...props }) => (
                            <tr className="hover:bg-white/[0.04] transition-colors" {...props} />
                          ),
                          th: ({ node, ...props }) => (
                            <th className="px-3 py-2.5 font-semibold text-foreground whitespace-nowrap" {...props} />
                          ),
                          td: ({ node, ...props }) => (
                            <td className="px-3 py-2 text-muted-foreground align-top" {...props} />
                          ),
                          ul: ({ node, ...props }) => (
                            <ul className="my-2 list-disc pl-5 space-y-1" {...props} />
                          ),
                          ol: ({ node, ...props }) => (
                            <ol className="my-2 list-decimal pl-5 space-y-1" {...props} />
                          ),
                          p: ({ node, ...props }) => (
                            <p className="my-1.5 leading-relaxed" {...props} />
                          ),
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Suggestion Chips */}
          {showSuggestions && messages.length <= 1 && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ delay: 0.2 }}
              className="flex flex-col items-center gap-3 pt-6"
            >
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Sparkles className="w-4 h-4 text-primary" />
                <span>Gợi ý câu hỏi phổ biến:</span>
              </div>
              <div className="flex flex-wrap justify-center gap-2 max-w-xl">
                {SUGGESTION_CHIPS.map((chip) => (
                  <Button
                    key={chip.label}
                    variant="outline"
                    size="sm"
                    className="rounded-full bg-white/5 border-white/10 hover:bg-primary/10 hover:border-primary/30 hover:text-primary transition-all text-xs"
                    onClick={() => sendMessage(chip.query)}
                  >
                    {chip.label}
                  </Button>
                ))}
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-3 md:p-4 border-t border-border/40 bg-card/60 backdrop-blur-xl shrink-0">
          <div className="max-w-4xl mx-auto">
            <form onSubmit={handleSubmit} className="relative flex items-center">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Nhập câu hỏi của bạn (VD: Điểm chuẩn IT Bách Khoa...)"
                className="pr-12 bg-background/80 h-12 rounded-full border-white/10 focus-visible:ring-primary shadow-inner"
                disabled={isLoading}
              />
              <Button 
                type="submit" 
                size="icon" 
                disabled={!input.trim() || isLoading}
                className="absolute right-1 w-10 h-10 rounded-full bg-primary hover:bg-primary/90 text-primary-foreground transition-all shadow"
                aria-label="Gửi tin nhắn"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </Button>
            </form>
            <div className="text-center mt-2">
              <span className="text-[10px] text-muted-foreground">AI có thể đưa ra thông tin không chính xác. Hãy đối chiếu với công bố chính thức của trường.</span>
              {dataAsOf && (
                <span className="block text-[10px] text-muted-foreground/80 mt-0.5">{dataAsOf}</span>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
