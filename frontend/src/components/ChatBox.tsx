import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User as UserIcon, Sparkles, BookOpen } from 'lucide-react';
import { api } from '../api/client';
import { ChatMessage, Citation } from '../types';

export const ChatBox: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: "Hello! I'm your private AI Journal assistant. Ask me anything about your past entries, routines, thoughts, or events you've logged.",
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = inputQuery.trim();
    if (!query || isGenerating) return;

    const userMessageId = `u-${Date.now()}`;
    const assistantMessageId = `a-${Date.now()}`;

    // 1. Append user query
    setMessages((prev) => [
      ...prev,
      { id: userMessageId, sender: 'user', text: query },
      {
        id: assistantMessageId,
        sender: 'assistant',
        text: '',
        isStreaming: true,
        citations: [],
      },
    ]);

    setInputQuery('');
    setIsGenerating(true);

    // 2. Stream response from backend
    await api.streamChat(
      query,
      // onChunk (token)
      (token: string) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, text: msg.text + token }
              : msg
          )
        );
      },
      // onMetadata (citations & provider)
      (meta: { provider: string; model: string; citations: Citation[] }) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  provider: meta.provider,
                  model: meta.model,
                  citations: meta.citations,
                }
              : msg
          )
        );
      },
      // onDone
      () => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId ? { ...msg, isStreaming: false } : msg
          )
        );
        setIsGenerating(false);
      },
      // onError
      (err: Error) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  text: msg.text + `\n\n[Error: ${err.message}]`,
                  isStreaming: false,
                }
              : msg
          )
        );
        setIsGenerating(false);
      }
    );
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={18} color="#6366f1" />
          <h2>Journal Intelligence Assistant</h2>
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          Scoped Strictly to Authenticated User
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-row ${msg.sender}`}>
            <div className="message-avatar">
              {msg.sender === 'user' ? <UserIcon size={16} /> : <Bot size={16} />}
            </div>
            <div className="message-bubble">
              <div>{msg.text || (msg.isStreaming ? 'Searching notes & thinking...' : '')}</div>

              {/* Source Citations Pill Badges (Stretch Goal) */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="citations-container">
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <BookOpen size={12} /> Sources:
                  </span>
                  {msg.citations.map((c, i) => (
                    <span
                      key={i}
                      className="citation-pill"
                      title={`Snippet: "${c.snippet}" (Cosine Match: ${(c.similarity * 100).toFixed(1)}%)`}
                    >
                      {c.entry_date} ({c.similarity.toFixed(2)})
                    </span>
                  ))}
                </div>
              )}

              {/* Provider & Model signature */}
              {msg.provider && (
                <div style={{ fontSize: '0.7rem', color: 'var(--text-faint)', marginTop: '6px' }}>
                  Generated via {msg.provider.toUpperCase()} ({msg.model})
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-area" onSubmit={handleSend}>
        <input
          type="text"
          placeholder="Ask a question about your past entries (e.g. 'What did I eat for breakfast on Tuesday?')..."
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          disabled={isGenerating}
        />
        <button type="submit" className="btn-primary" disabled={isGenerating || !inputQuery.trim()}>
          <Send size={16} />
        </button>
      </form>
    </div>
  );
};
