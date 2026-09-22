import React from 'react';
import { Trash2, Calendar, FileText } from 'lucide-react';
import { JournalEntry } from '../types';

interface JournalListProps {
  notes: JournalEntry[];
  loading: boolean;
  onDeleteNote: (id: string) => void;
}

export const JournalList: React.FC<JournalListProps> = ({ notes, loading, onDeleteNote }) => {
  return (
    <div className="notes-list-section">
      <div className="notes-list-header">
        <h3>Past Entries ({notes.length})</h3>
      </div>

      <div className="notes-scroll">
        {loading && <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading entries...</div>}

        {!loading && notes.length === 0 && (
          <div
            style={{
              padding: '24px 16px',
              textAlign: 'center',
              color: 'var(--text-faint)',
              fontSize: '0.85rem',
              border: '1px dashed var(--border)',
              borderRadius: '8px',
            }}
          >
            <FileText size={32} style={{ margin: '0 auto 8px', opacity: 0.5 }} />
            <p>No journal entries logged yet.</p>
            <p style={{ fontSize: '0.75rem', marginTop: '4px' }}>
              Create an entry above to start building your personal memory bank.
            </p>
          </div>
        )}

        {notes.map((note) => (
          <div key={note.id} className="note-card">
            <div className="note-card-meta">
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Calendar size={13} />
                {note.entry_date}
              </span>
              <button
                className="btn-danger"
                title="Delete note and remove vectors"
                onClick={() => {
                  if (confirm('Delete this note and its associated vector embeddings?')) {
                    onDeleteNote(note.id);
                  }
                }}
              >
                <Trash2 size={14} />
              </button>
            </div>
            <div className="note-card-content">{note.content}</div>
          </div>
        ))}
      </div>
    </div>
  );
};
