export interface User {
  id: string;
  email: string;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface JournalEntry {
  id: string;
  user_id: string;
  content: string;
  entry_date: string;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  entry_id: string;
  entry_date: string;
  snippet: string;
  similarity: number;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  citations?: Citation[];
  provider?: string;
  model?: string;
  isStreaming?: boolean;
}

export interface HealthStatus {
  status: string;
  version: string;
  llm_provider: string;
  llm_model: string;
  database_configured: boolean;
}
