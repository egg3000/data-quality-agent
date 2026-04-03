import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getRule, getErrors, getRuns, triggerRun } from "../../api/client";
import type { Rule, RuleError, RuleRun } from "../../types/rules";

export default function RuleDetail() {
  const { ruleId } = useParams<{ ruleId: string }>();
  const [rule, setRule] = useState<Rule | null>(null);
  const [errors, setErrors] = useState<RuleError[]>([]);
  const [runs, setRuns] = useState<RuleRun[]>([]);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!ruleId) return;
    getRule(ruleId).then(setRule);
    getErrors({ rule_id: ruleId, limit: 20 }).then(setErrors);
    getRuns({ rule_id: ruleId, limit: 10 }).then(setRuns);
  }, [ruleId]);

  const handleRun = async () => {
    if (!ruleId) return;
    setRunning(true);
    try {
      await triggerRun(ruleId);
      const [newErrors, newRuns] = await Promise.all([
        getErrors({ rule_id: ruleId, limit: 20 }),
        getRuns({ rule_id: ruleId, limit: 10 }),
      ]);
      setErrors(newErrors);
      setRuns(newRuns);
    } finally {
      setRunning(false);
    }
  };

  if (!rule) return <p>Loading...</p>;

  return (
    <div style={{ padding: 24 }}>
      <Link to="/">&larr; Back to Dashboard</Link>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16 }}>
        <h1>{rule.name}</h1>
        <button onClick={handleRun} disabled={running}>
          {running ? "Running..." : "Run This Rule"}
        </button>
      </div>

      <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
        <span style={{ background: "#e5e7eb", padding: "2px 8px", borderRadius: 12 }}>
          {rule.category}
        </span>
        <span>Severity: {rule.severity}</span>
        <span>{rule.is_active ? "Active" : "Inactive"}</span>
      </div>

      {rule.description && <p>{rule.description}</p>}

      <h3>SQL Query</h3>
      <pre style={{ background: "#1e293b", color: "#e2e8f0", padding: 16, borderRadius: 8, overflow: "auto" }}>
        {rule.sql_query}
      </pre>

      <h3>Run History ({runs.length})</h3>
      {runs.length === 0 ? (
        <p>No runs yet.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 24 }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
              <th style={{ padding: 8 }}>Status</th>
              <th style={{ padding: 8 }}>Errors</th>
              <th style={{ padding: 8 }}>Triggered By</th>
              <th style={{ padding: 8 }}>Started</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={{ padding: 8, color: run.status === "completed" ? "#22c55e" : "#ef4444" }}>
                  {run.status}
                </td>
                <td style={{ padding: 8 }}>{run.error_count}</td>
                <td style={{ padding: 8 }}>{run.triggered_by}</td>
                <td style={{ padding: 8 }}>{new Date(run.started_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Recent Errors ({errors.length})</h3>
      {errors.length === 0 ? (
        <p>No errors found.</p>
      ) : (
        <div>
          {errors.map((err) => (
            <div
              key={err.id}
              style={{
                padding: 12,
                marginBottom: 8,
                background: err.is_resolved ? "#f0fdf4" : "#fef2f2",
                borderRadius: 6,
              }}
            >
              <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 4 }}>
                {err.is_resolved ? "Resolved" : "Open"} | {new Date(err.detected_at).toLocaleString()}
              </div>
              <pre style={{ margin: 0, fontSize: 13 }}>{JSON.stringify(err.error_data, null, 2)}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
