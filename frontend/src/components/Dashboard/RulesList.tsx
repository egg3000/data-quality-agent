import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getRules, triggerRun } from "../../api/client";
import type { Rule, RunBatchResponse } from "../../types/rules";

const SEVERITY_LABELS: Record<number, string> = {
  1: "Info",
  2: "Warning",
  3: "Error",
  4: "Critical",
};

const SEVERITY_COLORS: Record<number, string> = {
  1: "#6b7280",
  2: "#f59e0b",
  3: "#ef4444",
  4: "#991b1b",
};

export default function RulesList() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [lastRun, setLastRun] = useState<RunBatchResponse | null>(null);

  useEffect(() => {
    getRules().then(setRules).finally(() => setLoading(false));
  }, []);

  const handleRunAll = async () => {
    setRunning(true);
    try {
      const result = await triggerRun();
      setLastRun(result);
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <p>Loading rules...</p>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2>Rules ({rules.length})</h2>
        <div>
          <Link to="/rules/new" style={{ marginRight: 12 }}>+ New Rule</Link>
          <button onClick={handleRunAll} disabled={running}>
            {running ? "Running..." : "Run All Rules"}
          </button>
        </div>
      </div>

      {lastRun && (
        <div style={{ padding: 12, background: "#f0fdf4", borderRadius: 6, marginBottom: 16 }}>
          Executed {lastRun.total_rules} rules: {lastRun.completed} completed, {lastRun.failed} failed, {lastRun.total_errors} total errors
        </div>
      )}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
            <th style={{ padding: 8 }}>Name</th>
            <th style={{ padding: 8 }}>Category</th>
            <th style={{ padding: 8 }}>Severity</th>
            <th style={{ padding: 8 }}>Active</th>
          </tr>
        </thead>
        <tbody>
          {rules.map((rule) => (
            <tr key={rule.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
              <td style={{ padding: 8 }}>
                <Link to={`/rules/${rule.id}`}>{rule.name}</Link>
              </td>
              <td style={{ padding: 8 }}>
                <span style={{ background: "#e5e7eb", padding: "2px 8px", borderRadius: 12, fontSize: 13 }}>
                  {rule.category}
                </span>
              </td>
              <td style={{ padding: 8 }}>
                <span style={{ color: SEVERITY_COLORS[rule.severity], fontWeight: 600 }}>
                  {SEVERITY_LABELS[rule.severity]}
                </span>
              </td>
              <td style={{ padding: 8 }}>{rule.is_active ? "Yes" : "No"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
