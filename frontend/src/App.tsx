import React from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import DashboardPage from "./components/Dashboard/DashboardPage";
import ChatPage from "./components/Chat/ChatPage";
import RuleDetail from "./components/Rules/RuleDetail";
import RuleForm from "./components/Rules/RuleForm";
import KnowledgeBrowser from "./components/Knowledge/KnowledgeBrowser";

function Nav() {
  return (
    <nav style={{
      display: "flex",
      gap: 24,
      padding: "12px 24px",
      borderBottom: "1px solid #e5e7eb",
      background: "#1e293b",
      color: "#fff",
      alignItems: "center",
    }}>
      <strong style={{ marginRight: 16 }}>DQA</strong>
      <Link to="/" style={{ color: "#94a3b8", textDecoration: "none" }}>Dashboard</Link>
      <Link to="/chat" style={{ color: "#94a3b8", textDecoration: "none" }}>Chat</Link>
      <Link to="/knowledge" style={{ color: "#94a3b8", textDecoration: "none" }}>Knowledge</Link>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Nav />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/rules/new" element={<RuleForm />} />
        <Route path="/rules/:ruleId" element={<RuleDetail />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/knowledge" element={<KnowledgeBrowser />} />
      </Routes>
    </BrowserRouter>
  );
}
