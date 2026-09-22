import React, { useState } from 'react';
import { api } from '../api/client';
import { JournalEntry } from '../types';

interface JournalEditorProps {
  onNoteCreated: (note: JournalEntry) => void;
}

export const JournalEditor: React.FC<JournalEditorProps> = ({ onNoteCreated }) => {
  const todayStr = new Date().toISOString().split('T')[0];
  const [content, setContent] = useState('');
  const [entryDate, setEntryDate] = useState(todayStr);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    setSaving(true);
    setError(null);

    try {
      const newNote = await api.createNote(content.trim(), entryDate);
      onNoteCreated(newNote);
      setContent('');
    } catch (err: any) {
      setError(err.message || 'Failed to save and embed entry.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="editor-section">
      <div className="editor-header">
        <h3>New Journal Entry</h3>
        <input
          type="date"
          value={entryDate}
          onChange={(e) => setEntryDate(e.target.value)}
          style={{ fontSize: '0.8rem', padding: '4px 8px' }}
        />
      </div>

      {error && <div className="alert-error" style={{ marginBottom: '8px' }}>{error}</div>}

      <form onSubmit={handleSubmit}>
        <textarea
          rows={4}
          style={{ width: '100%', resize: 'vertical', marginBottom: '10px' }}
          placeholder="Write your thoughts, daily events, meals, meetings, or reflections here... (e.g. 'On Tuesday I had oatmeal with blueberries for breakfast.')"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          required
        />

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button type="submit" className="btn-primary" disabled={saving || !content.trim()}>
            {saving ? 'Vectorizing & Saving...' : 'Save & Embed Note'}
          </button>
        </div>
      </form>
    </div>
  );
};
