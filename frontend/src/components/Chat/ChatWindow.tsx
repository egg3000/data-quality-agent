import React, { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getConversationHistory, sendChatMessage } from "../../api/client";
import type { ChatMessage } from "../../types/chat";

function ensureTableNewlines(text: string): string {
  // Ensure blank lines before and after markdown tables so remark parses them as blocks.
  // A table line starts with optional whitespace then a pipe character.
  const lines = text.split("\n");
  const result: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    const isTableLine = /^\s*\|/.test(lines[i]);
    const prevIsTableLine = i > 0 && /^\s*\|/.test(lines[i - 1]);
    // Insert blank line before the first table row if previous line is non-empty non-table
    if (isTableLine && !prevIsTableLine && i > 0 && lines[i - 1].trim() !== "") {
      result.push("");
    }
    result.push(lines[i]);
    // Insert blank line after the last table row if next line is non-empty non-table
    if (isTableLine && i + 1 < lines.length && !/^\s*\|/.test(lines[i + 1]) && lines[i + 1].trim() !== "") {
      result.push("");
    }
  }
  return result.join("\n");
}

interface Props {
  sessionId: string;
  onFirstMessage?: () => void;
}

export default function ChatWindow({ sessionId, onFirstMessage }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const hasNotified = useRef(false);

  useEffect(() => {
    hasNotified.current = false;
    getConversationHistory(sessionId)
      .then(setMessages)
      .catch(() => setMessages([]));
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    const userMessage = input.trim();
    setInput("");
    setSending(true);

    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await sendChatMessage(sessionId, userMessage);
      const assistantMsg: ChatMessage = {
        id: `temp-${Date.now()}-resp`,
        role: "assistant",
        content: response.response,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      if (!hasNotified.current && onFirstMessage) {
        hasNotified.current = true;
        onFirstMessage();
      }
    } catch (err) {
      const errorMsg: ChatMessage = {
        id: `temp-${Date.now()}-err`,
        role: "assistant",
        content: `Error: ${err instanceof Error ? err.message : "Something went wrong"}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              marginBottom: 12,
              padding: 12,
              borderRadius: 8,
              background: msg.role === "user" ? "#eff6ff" : "#f9fafb",
              maxWidth: "80%",
              marginLeft: msg.role === "user" ? "auto" : 0,
            }}
          >
            <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 4 }}>
              {msg.role === "user" ? "You" : "Agent"}
            </div>
            {msg.role === "assistant" ? (
              <div className="markdown-body">
                <Markdown remarkPlugins={[remarkGfm]}>{ensureTableNewlines(msg.content ?? "")}</Markdown>
              </div>
            ) : (
              <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
            )}
          </div>
        ))}
        {sending && (
          <div style={{ padding: 12, color: "#6b7280" }}>Agent is thinking...</div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={{ display: "flex", padding: 16, borderTop: "1px solid #e5e7eb" }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask the Data Quality Agent..."
          disabled={sending}
          style={{ flex: 1, padding: 10, borderRadius: 6, border: "1px solid #d1d5db", marginRight: 8 }}
        />
        <button onClick={handleSend} disabled={sending || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
