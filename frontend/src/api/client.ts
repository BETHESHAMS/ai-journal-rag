import { AuthResponse, JournalEntry, User, HealthStatus, Citation } from '../types';

const metaEnv = (import.meta as any).env;
const API_BASE = metaEnv && metaEnv.VITE_API_URL
  ? `${metaEnv.VITE_API_URL}/api`
  : '/api';

export const tokenStorage = {
  get: (): string | null => localStorage.getItem('ai_journal_token'),
  set: (token: string): void => localStorage.setItem('ai_journal_token', token),
  clear: (): void => localStorage.removeItem('ai_journal_token'),
};

function authHeaders(): Record<string, string> {
  const token = tokenStorage.get();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export const api = {
  async register(email: string, password: string): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(err.detail || 'Registration failed');
    }
    const data: AuthResponse = await res.json();
    tokenStorage.set(data.access_token);
    return data;
  },

  async login(email: string, password: string): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || 'Incorrect credentials');
    }
    const data: AuthResponse = await res.json();
    tokenStorage.set(data.access_token);
    return data;
  },

  async getMe(): Promise<User> {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error('Unauthorized');
    return res.json();
  },

  async getHealth(): Promise<HealthStatus> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  },

  async getNotes(): Promise<JournalEntry[]> {
    const res = await fetch(`${API_BASE}/notes`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch journal entries');
    return res.json();
  },

  async createNote(content: string, entry_date: string): Promise<JournalEntry> {
    const res = await fetch(`${API_BASE}/notes`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ content, entry_date }),
    });
    if (!res.ok) throw new Error('Failed to save journal entry');
    return res.json();
  },

  async deleteNote(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/notes/${id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete journal entry');
  },

  async streamChat(
    query: string,
    onChunk: (token: string) => void,
    onMetadata: (metadata: { provider: string; model: string; citations: Citation[] }) => void,
    onDone: () => void,
    onError: (err: Error) => void
  ): Promise<void> {
    const token = tokenStorage.get();
    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ query, top_k: 5 }),
      });

      if (!res.ok) {
        const errorJson = await res.json().catch(() => ({ detail: 'Chat request failed' }));
        throw new Error(errorJson.detail || 'Chat query failed');
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error('No readable stream available');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            const rawJson = trimmed.slice(6);
            try {
              const event = JSON.parse(rawJson);
              if (event.type === 'metadata') {
                onMetadata({
                  provider: event.provider,
                  model: event.model,
                  citations: event.citations || [],
                });
              } else if (event.type === 'token') {
                onChunk(event.content);
              } else if (event.type === 'done') {
                onDone();
                return;
              }
            } catch (e) {
              console.error('SSE JSON parse error:', e, rawJson);
            }
          }
        }
      }
      onDone();
    } catch (err: any) {
      onError(err);
    }
  },
};
