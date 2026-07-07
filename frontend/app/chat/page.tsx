"use client";

import { useState, useRef, useEffect } from "react";
import { fetchSSE } from "@/lib/sse-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Send, Sparkles, User, GraduationCap, Loader2, MessageSquare } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { motion, AnimatePresence } from "framer-motion";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

const SUGGESTION_CHIPS = [
  { label: "Top 5 trường CNTT", query: "Top 5 trường đại học tốt nhất về Công nghệ thông tin?" },
  { label: "Điểm chuẩn Ngoại thương", query: "Điểm chuẩn Đại học Ngoại thương các ngành năm gần nhất?" },
  { label: "Học phí RMIT", query: "Học phí RMIT Việt Nam năm 2025 bao nhiêu?" },
  { label: "HUST vs KHTN", query: "So sánh Bách Khoa Hà Nội và ĐH Khoa học Tự nhiên HCM ngành CNTT?" },
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Xin chào! Tôi là **Trợ lý AI tuyển sinh UniSearch**. Bạn muốn tra cứu điểm chuẩn trường nào, hay cần tư vấn chọn ngành gì? Hãy hỏi tôi nhé!"
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const idCounterRef = useRef(0);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (userMessage: string) => {
    if (!userMessage.trim() || isLoading) return;

    setInput("");
    setShowSuggestions(false);

    const userMsgId = `msg-${++idCounterRef.current}`;
    const newMessages = [...messages, { id: userMsgId, role: "user" as const, content: userMessage }];
    setMessages(newMessages);
    setIsLoading(true);

    const assistantMsgId = `msg-${++idCounterRef.current}`;
    setMessages([...newMessages, { id: assistantMsgId, role: "assistant", content: "" }]);

    await fetchSSE("/schools/recommend", {
      user_query: userMessage,
      stream: true,
      pre_extracted_school: "ALL",
      pre_extracted_location: "ALL",
      pre_extracted_keyword: "ALL",
      pre_extracted_year: 0
    }, {
      onChunk: (chunk) => {
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMsgId 
            ? { ...msg, content: msg.content + chunk }
            : msg
        ));
      },
      onDone: () => {
        setIsLoading(false);
      },
      onError: (err) => {
        console.error("Chat error:", err);
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMsgId 
            ? { ...msg, content: msg.content + "\n\n*(Lỗi kết nối. Xin vui lòng thử lại sau)*" }
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
    <div className="container mx-auto px-4 py-8 h-[calc(100vh-4rem-5rem)] max-w-4xl flex flex-col">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="font-heading text-2xl font-bold">UniSearch AI Chat</h1>
          <p className="text-sm text-muted-foreground">Tư vấn tuyển sinh & Tra cứu điểm chuẩn</p>
        </div>
      </div>

      <Card className="flex-1 overflow-hidden flex flex-col bg-white/5 border-white/10 backdrop-blur-md">
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
          <AnimatePresence mode="popLayout">
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
                className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                  msg.role === "user" ? "bg-secondary text-white" : "bg-primary text-white"
                }`}>
                  {msg.role === "user" ? <User className="w-4 h-4" /> : <GraduationCap className="w-4 h-4" />}
                </div>
                
                <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  msg.role === "user" 
                    ? "bg-secondary text-white rounded-tr-none" 
                    : "bg-muted/50 border border-border rounded-tl-none"
                }`}>
                  {msg.content === "" && isLoading && msg.role === "assistant" ? (
                    <div className="flex items-center gap-2 h-6">
                      <span className="w-2 h-2 rounded-full bg-primary animate-bounce" />
                      <span className="w-2 h-2 rounded-full bg-primary animate-bounce [animation-delay:75ms]" />
                      <span className="w-2 h-2 rounded-full bg-primary animate-bounce [animation-delay:150ms]" />
                    </div>
                  ) : (
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
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
              transition={{ delay: 0.3 }}
              className="flex flex-col items-center gap-3 pt-4"
            >
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <MessageSquare className="w-4 h-4" />
                <span>Hoặc thử các câu hỏi gợi ý:</span>
              </div>
              <div className="flex flex-wrap justify-center gap-2">
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

        <div className="p-4 border-t border-border/50 bg-background/50">
          <form onSubmit={handleSubmit} className="relative flex items-center">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Nhập câu hỏi của bạn (VD: Điểm chuẩn IT Bách Khoa...)"
              className="pr-12 bg-background h-12 rounded-full"
              disabled={isLoading}
            />
            <Button 
              type="submit" 
              size="icon" 
              disabled={!input.trim() || isLoading}
              className="absolute right-1 w-10 h-10 rounded-full"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </form>
          <div className="text-center mt-2">
            <span className="text-[10px] text-muted-foreground">AI có thể đưa ra thông tin không chính xác. Hãy đối chiếu với công bố chính thức của trường.</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
