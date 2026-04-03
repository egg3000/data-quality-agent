export interface ChatRequest {
  session_id: string;
  message: string;
}

export interface ChatResponse {
  session_id: string;
  response: string;
}

export interface Conversation {
  id: string;
  session_id: string;
  analyst_id: string | null;
  started_at: string;
  last_active_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string | null;
  created_at: string;
}
