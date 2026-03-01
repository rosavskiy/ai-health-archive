"use client";
import { useState, useRef, useEffect } from "react";
import AppLayout from "@/components/AppLayout";
import { chatApi } from "@/lib/api";
import { clsx } from "clsx";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTIONS = [
  "Есть ли у меня отклонения в анализах?",
  "Покажи динамику холестерина",
  "Что означает повышенный TSH?",
  "Когда последний раз были сданы анализы?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Привет! Я ваш AI-консультант по здоровью 🩺\n\nЗадайте вопрос о ваших анализах. Все данные анонимизированы — ваши персональные данные не передаются." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text?: string) => {
    const content = text || input.trim();
    if (!content || loading) return;
    setInput("");

    const newMessages: Message[] = [...messages, { role: "user", content }];
    setMessages(newMessages);
    setLoading(true);

    try {
      const res = await chatApi.send(newMessages.slice(-20));
      setMessages((prev) => [...prev, { role: "assistant", content: res.data.reply }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Произошла ошибка. Попробуйте ещё раз." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      <div className="flex flex-col h-[calc(100vh-10rem)]">
        <h1 className="text-2xl font-bold mb-4">AI-Консультант</h1>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-3 pr-1">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={clsx(
                "max-w-[85%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed",
                msg.role === "user"
                  ? "ml-auto bg-brand-500 text-white rounded-br-sm"
                  : "mr-auto bg-white text-gray-800 border border-gray-100 rounded-bl-sm shadow-sm"
              )}
            >
              {msg.content}
            </div>
          ))}

          {loading && (
            <div className="max-w-[85%] mr-auto bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Suggestions (only initially) */}
        {messages.length <= 1 && (
          <div className="flex flex-wrap gap-2 my-3">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => sendMessage(s)}
                className="text-xs bg-brand-50 text-brand-700 border border-brand-200 rounded-full px-3 py-1.5 hover:bg-brand-100 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <form
          onSubmit={(e) => { e.preventDefault(); sendMessage(); }}
          className="flex gap-2 pt-2"
        >
          <input
            className="input flex-1"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Спросите об анализах..."
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="btn-primary px-3"
          >
            ➤
          </button>
        </form>

        <p className="text-center text-xs text-gray-400 mt-2">
          🔒 Ваши ФИО не передаются в AI. Только анонимизированные показатели.
        </p>
      </div>
    </AppLayout>
  );
}
