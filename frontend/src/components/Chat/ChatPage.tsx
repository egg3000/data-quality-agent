import React, { useCallback, useEffect, useState } from "react";
import { getConversations } from "../../api/client";
import type { Conversation } from "../../types/chat";
import ChatWindow from "./ChatWindow";

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [sessionId, setSessionId] = useState(() => `session-${Date.now()}`);
  const [isNewSession, setIsNewSession] = useState(true);

  const refreshSessions = useCallback(() => {
    getConversations().then(setConversations).catch(() => {});
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  const handleNewSession = () => {
    setSessionId(`session-${Date.now()}`);
    setIsNewSession(true);
  };

  const handleSelectSession = (id: string) => {
    setSessionId(id);
    setIsNewSession(false);
  };

  // Called by ChatWindow after the first message is sent, so we can refresh the sidebar
  const handleFirstMessage = () => {
    setIsNewSession(false);
    refreshSessions();
  };

  return (
    <div style={{ display: "flex", height: "calc(100vh - 60px)" }}>
      <div style={{ width: 250, borderRight: "1px solid #e5e7eb", padding: 16, overflowY: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3>Sessions</h3>
          <button onClick={handleNewSession} style={{ fontSize: 12 }}>+ New</button>
        </div>
        {isNewSession && (
          <div
            style={{
              padding: 8,
              borderRadius: 6,
              background: "#eff6ff",
              marginBottom: 8,
              cursor: "default",
              fontSize: 13,
              fontStyle: "italic",
              color: "#6b7280",
            }}
          >
            New conversation
          </div>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            onClick={() => handleSelectSession(c.session_id)}
            style={{
              padding: 8,
              borderRadius: 6,
              cursor: "pointer",
              marginBottom: 4,
              background: c.session_id === sessionId ? "#eff6ff" : "transparent",
              fontSize: 13,
            }}
          >
            {c.session_id}
            <div style={{ fontSize: 11, color: "#9ca3af" }}>
              {new Date(c.last_active_at).toLocaleDateString()}
            </div>
          </div>
        ))}
      </div>
      <div style={{ flex: 1 }}>
        <ChatWindow
          sessionId={sessionId}
          onFirstMessage={handleFirstMessage}
        />
      </div>
    </div>
  );
}
