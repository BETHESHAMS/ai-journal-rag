import React, { useState, useEffect } from 'react';
import { BookMarked, LogOut, Cpu } from 'lucide-react';
import { api, tokenStorage } from './api/client';
import { User, JournalEntry, HealthStatus } from './types';
import { AuthModal } from './components/AuthModal';
import { JournalEditor } from './components/JournalEditor';
import { JournalList } from './components/JournalList';
import { ChatBox } from './components/ChatBox';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [notes, setNotes] = useState<JournalEntry[]>([]);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  // Check health and session on startup
  useEffect(() => {
    api.getHealth()
      .then(setHealth)
      .catch((err) => console.error('Health check error:', err));

    const token = tokenStorage.get();
    if (token) {
      api.getMe()
        .then((user) => setCurrentUser(user))
        .catch(() => {
          tokenStorage.clear();
          setCurrentUser(null);
        });
    }
  }, []);

  // Fetch notes when user is authenticated
  useEffect(() => {
    if (currentUser) {
      fetchNotes();
    } else {
      setNotes([]);
    }
  }, [currentUser]);

  const fetchNotes = async () => {
    setLoadingNotes(true);
    try {
      const data = await api.getNotes();
      setNotes(data);
    } catch (err) {
      console.error('Failed to load notes:', err);
    } finally {
      setLoadingNotes(false);
    }
  };

  const handleNoteCreated = (newNote: JournalEntry) => {
    setNotes((prev) => [newNote, ...prev]);
  };

  const handleDeleteNote = async (id: string) => {
    try {
      await api.deleteNote(id);
      setNotes((prev) => prev.filter((n) => n.id !== id));
    } catch (err) {
      alert('Failed to delete journal entry.');
    }
  };

  const handleLogout = () => {
    tokenStorage.clear();
    setCurrentUser(null);
  };

  return (
    <div className="app-container">
      {/* Top Navigation Bar */}
      <header className="app-header">
        <div className="header-brand">
          <BookMarked size={22} color="#6366f1" />
          <h1>Personalized AI Journal</h1>
          {health && (
            <span className="provider-badge">
              <Cpu size={12} />
              {health.llm_provider.toUpperCase()}: {health.llm_model}
            </span>
          )}
        </div>

        <div className="header-actions">
          {currentUser ? (
            <>
              <span className="user-tag">{currentUser.email}</span>
              <button className="btn-secondary" onClick={handleLogout} title="Log Out">
                <LogOut size={14} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} />
                Sign Out
              </button>
            </>
          ) : (
            <span className="user-tag">Not Authenticated</span>
          )}
        </div>
      </header>

      {/* Main Two-Panel Layout */}
      <main className="main-layout">
        {/* Left Column: Notes Composer & Past Notes */}
        <div className="sidebar-panel">
          <JournalEditor onNoteCreated={handleNoteCreated} />
          <JournalList
            notes={notes}
            loading={loadingNotes}
            onDeleteNote={handleDeleteNote}
          />
        </div>

        {/* Right Column: RAG Chat Assistant */}
        <ChatBox />
      </main>

      {/* Authentication Modal if not logged in */}
      {!currentUser && <AuthModal onSuccess={(user) => setCurrentUser(user)} />}
    </div>
  );
};

export default App;
