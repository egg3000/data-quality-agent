import React, { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { getErrorSummary } from "../../api/client";
import type { ErrorSummaryItem } from "../../types/rules";

export default function ErrorTrends() {
  const [summaries, setSummaries] = useState<ErrorSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getErrorSummary().then(setSummaries).finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading trends...</p>;
  if (summaries.length === 0) return <p>No error summary data yet. Run rules to generate trends.</p>;

  // Aggregate by date
  const byDate = new Map<string, { date: string; total: number; newErrors: number; resolved: number }>();
  for (const s of summaries) {
    const existing = byDate.get(s.summary_date) || { date: s.summary_date, total: 0, newErrors: 0, resolved: 0 };
    existing.total += s.total_errors;
    existing.newErrors += s.new_errors;
    existing.resolved += s.resolved_errors;
    byDate.set(s.summary_date, existing);
  }
  const chartData = Array.from(byDate.values()).sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div>
      <h2>Error Trends</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="total" stroke="#ef4444" name="Total Errors" />
          <Line type="monotone" dataKey="newErrors" stroke="#f59e0b" name="New Errors" />
          <Line type="monotone" dataKey="resolved" stroke="#22c55e" name="Resolved" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
