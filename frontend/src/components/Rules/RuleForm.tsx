import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createRule } from "../../api/client";

const CATEGORIES = [
  "completeness", "validity", "consistency", "uniqueness",
  "referential_integrity", "timeliness", "orphans", "business_rules",
];

export default function RuleForm() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [severity, setSeverity] = useState(3);
  const [sqlQuery, setSqlQuery] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const rule = await createRule({
        name,
        description: description || undefined,
        category,
        severity,
        sql_query: sqlQuery,
      });
      navigate(`/rules/${rule.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create rule");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 700 }}>
      <h1>Create New Rule</h1>
      {error && <p style={{ color: "#ef4444" }}>{error}</p>}
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #d1d5db" }}
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #d1d5db" }}
          />
        </div>

        <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #d1d5db" }}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>Severity</label>
            <select
              value={severity}
              onChange={(e) => setSeverity(Number(e.target.value))}
              style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #d1d5db" }}
            >
              <option value={1}>1 - Info</option>
              <option value={2}>2 - Warning</option>
              <option value={3}>3 - Error</option>
              <option value={4}>4 - Critical</option>
            </select>
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>SQL Query</label>
          <textarea
            value={sqlQuery}
            onChange={(e) => setSqlQuery(e.target.value)}
            required
            rows={8}
            placeholder="SELECT matnr, maktx FROM mara WHERE ..."
            style={{
              width: "100%",
              padding: 8,
              borderRadius: 6,
              border: "1px solid #d1d5db",
              fontFamily: "monospace",
            }}
          />
        </div>

        <button type="submit" disabled={saving}>
          {saving ? "Creating..." : "Create Rule"}
        </button>
      </form>
    </div>
  );
}
