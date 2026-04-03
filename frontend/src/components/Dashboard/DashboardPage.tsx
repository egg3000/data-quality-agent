import React from "react";
import ErrorTrends from "./ErrorTrends";
import RulesList from "./RulesList";

export default function DashboardPage() {
  return (
    <div style={{ padding: 24 }}>
      <h1>Data Quality Dashboard</h1>
      <ErrorTrends />
      <div style={{ marginTop: 32 }}>
        <RulesList />
      </div>
    </div>
  );
}
