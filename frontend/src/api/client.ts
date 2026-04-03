import type { ChatMessage, ChatResponse, Conversation } from "../types/chat";
import type { KnowledgeCreate, KnowledgeEntry, KnowledgeSearchResult } from "../types/knowledge";
import type {
  ErrorSummaryItem,
  Rule,
  RuleCreate,
  RuleError,
  RuleRun,
  RuleUpdate,
  RunBatchResponse,
} from "../types/rules";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Rules ---
export const getRules = (params?: {
  category?: string;
  severity?: number;
  is_active?: boolean;
}): Promise<Rule[]> => {
  const search = new URLSearchParams();
  if (params?.category) search.set("category", params.category);
  if (params?.severity !== undefined) search.set("severity", String(params.severity));
  if (params?.is_active !== undefined) search.set("is_active", String(params.is_active));
  const qs = search.toString();
  return request(`/rules/${qs ? `?${qs}` : ""}`);
};

export const getRule = (id: string): Promise<Rule> =>
  request(`/rules/${id}`);

export const createRule = (data: RuleCreate): Promise<Rule> =>
  request("/rules/", { method: "POST", body: JSON.stringify(data) });

export const updateRule = (id: string, data: RuleUpdate): Promise<Rule> =>
  request(`/rules/${id}`, { method: "PUT", body: JSON.stringify(data) });

export const deleteRule = (id: string): Promise<void> =>
  request(`/rules/${id}`, { method: "DELETE" });

// --- Runs ---
export const triggerRun = (ruleId?: string): Promise<RunBatchResponse> =>
  request("/runs/", {
    method: "POST",
    body: JSON.stringify(ruleId ? { rule_id: ruleId } : {}),
  });

export const getRuns = (params?: {
  rule_id?: string;
  status?: string;
  limit?: number;
}): Promise<RuleRun[]> => {
  const search = new URLSearchParams();
  if (params?.rule_id) search.set("rule_id", params.rule_id);
  if (params?.status) search.set("status", params.status);
  if (params?.limit) search.set("limit", String(params.limit));
  const qs = search.toString();
  return request(`/runs/${qs ? `?${qs}` : ""}`);
};

// --- Errors ---
export const getErrors = (params?: {
  rule_id?: string;
  run_id?: string;
  is_resolved?: boolean;
  limit?: number;
}): Promise<RuleError[]> => {
  const search = new URLSearchParams();
  if (params?.rule_id) search.set("rule_id", params.rule_id);
  if (params?.run_id) search.set("run_id", params.run_id);
  if (params?.is_resolved !== undefined) search.set("is_resolved", String(params.is_resolved));
  if (params?.limit) search.set("limit", String(params.limit));
  const qs = search.toString();
  return request(`/errors/${qs ? `?${qs}` : ""}`);
};

export const resolveError = (id: string, isResolved: boolean): Promise<RuleError> =>
  request(`/errors/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ is_resolved: isResolved }),
  });

export const getErrorSummary = (params?: {
  rule_id?: string;
  start_date?: string;
  end_date?: string;
}): Promise<ErrorSummaryItem[]> => {
  const search = new URLSearchParams();
  if (params?.rule_id) search.set("rule_id", params.rule_id);
  if (params?.start_date) search.set("start_date", params.start_date);
  if (params?.end_date) search.set("end_date", params.end_date);
  const qs = search.toString();
  return request(`/errors/summary${qs ? `?${qs}` : ""}`);
};

// --- Knowledge ---
export const listKnowledge = (params?: {
  source_type?: string;
  tag?: string;
}): Promise<KnowledgeEntry[]> => {
  const search = new URLSearchParams();
  if (params?.source_type) search.set("source_type", params.source_type);
  if (params?.tag) search.set("tag", params.tag);
  const qs = search.toString();
  return request(`/knowledge/${qs ? `?${qs}` : ""}`);
};

export const searchKnowledge = (q: string, limit = 5): Promise<KnowledgeSearchResult[]> =>
  request(`/knowledge/search?q=${encodeURIComponent(q)}&limit=${limit}`);

export const createKnowledge = (data: KnowledgeCreate): Promise<KnowledgeEntry> =>
  request("/knowledge/", { method: "POST", body: JSON.stringify(data) });

export const deleteKnowledge = (id: string): Promise<void> =>
  request(`/knowledge/${id}`, { method: "DELETE" });

// --- Chat ---
export const sendChatMessage = (sessionId: string, message: string): Promise<ChatResponse> =>
  request("/chat/", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message }),
  });

export const getConversations = (): Promise<Conversation[]> =>
  request("/chat/sessions");

export const getConversationHistory = (sessionId: string): Promise<ChatMessage[]> =>
  request(`/chat/sessions/${sessionId}`);
