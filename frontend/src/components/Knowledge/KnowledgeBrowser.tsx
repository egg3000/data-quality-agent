import React, { useEffect, useState } from "react";
import { listKnowledge, searchKnowledge } from "../../api/client";
import type { KnowledgeEntry, KnowledgeSearchResult } from "../../types/knowledge";

export default function KnowledgeBrowser() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResult[] | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    listKnowledge().then(setEntries).finally(() => setLoading(false));
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) {
      setSearchResults(null);
      return;
    }
    setLoading(true);
    try {
      const results = await searchKnowledge(query.trim());
      setSearchResults(results);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const displayEntries = searchResults
    ? searchResults.map((r) => ({ ...r.entry, similarity: r.similarity }))
    : entries.map((e) => ({ ...e, similarity: undefined }));

  return (
    <div style={{ padding: 24 }}>
      <h1>Knowledge Base</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Semantic search..."
          style={{ flex: 1, padding: 10, borderRadius: 6, border: "1px solid #d1d5db" }}
        />
        <button onClick={handleSearch}>Search</button>
        {searchResults && (
          <button onClick={() => { setSearchResults(null); setQuery(""); }}>Clear</button>
        )}
      </div>

      {loading ? (
        <p>Loading...</p>
      ) : displayEntries.length === 0 ? (
        <p>No knowledge entries found.{searchResults ? " Try a different query." : ""}</p>
      ) : (
        <div>
          {displayEntries.map((entry) => (
            <div
              key={entry.id}
              onClick={() => toggleExpand(entry.id)}
              style={{
                padding: 16,
                marginBottom: 8,
                background: "#f9fafb",
                borderRadius: 8,
                cursor: "pointer",
                border: "1px solid #e5e7eb",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>{entry.title}</strong>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  {"similarity" in entry && entry.similarity !== undefined && (
                    <span style={{ fontSize: 12, color: "#6b7280" }}>
                      {(entry.similarity * 100).toFixed(0)}% match
                    </span>
                  )}
                  <span style={{ fontSize: 12, background: "#e5e7eb", padding: "2px 6px", borderRadius: 8 }}>
                    {entry.source_type}
                  </span>
                </div>
              </div>
              {entry.tags && entry.tags.length > 0 && (
                <div style={{ marginTop: 4 }}>
                  {entry.tags.map((tag) => (
                    <span key={tag} style={{ fontSize: 11, background: "#dbeafe", padding: "1px 6px", borderRadius: 8, marginRight: 4 }}>
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              {expanded.has(entry.id) && (
                <div style={{ marginTop: 12, whiteSpace: "pre-wrap", fontSize: 14 }}>
                  {entry.content}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
