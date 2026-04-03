export interface KnowledgeEntry {
  id: string;
  title: string;
  content: string;
  source_type: string;
  source_id: string | null;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeCreate {
  title: string;
  content: string;
  source_type: string;
  source_id?: string;
  tags?: string[];
}

export interface KnowledgeSearchResult {
  entry: KnowledgeEntry;
  similarity: number;
}
