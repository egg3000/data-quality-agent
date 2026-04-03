export interface Rule {
  id: string;
  name: string;
  description: string | null;
  category: string;
  severity: number;
  sql_query: string;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface RuleCreate {
  name: string;
  description?: string;
  category: string;
  severity: number;
  sql_query: string;
  is_active?: boolean;
  created_by?: string;
}

export interface RuleUpdate {
  name?: string;
  description?: string;
  category?: string;
  severity?: number;
  sql_query?: string;
  is_active?: boolean;
}

export interface RuleRun {
  id: string;
  rule_id: string;
  rule_name: string | null;
  triggered_by: string;
  status: string;
  error_count: number;
  started_at: string;
  completed_at: string | null;
}

export interface RunBatchResponse {
  total_rules: number;
  completed: number;
  failed: number;
  total_errors: number;
  runs: RuleRun[];
}

export interface RuleError {
  id: string;
  rule_id: string;
  rule_run_id: string;
  rule_name: string | null;
  error_data: Record<string, unknown>;
  is_resolved: boolean;
  detected_at: string;
  resolved_at: string | null;
}

export interface ErrorSummaryItem {
  rule_id: string;
  rule_name: string | null;
  summary_date: string;
  total_errors: number;
  new_errors: number;
  resolved_errors: number;
}
