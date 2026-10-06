import React, { useState } from 'react';
import { Loader2, Lock, Unlock } from 'lucide-react';
import axios from 'axios';
import { getApiBase } from '../../config';
import { BookDetail } from './types';

interface EditFormProps {
  book: BookDetail;
  onSaved: () => Promise<void> | void;
  onChanged: () => Promise<void> | void;
}

type FieldKey = 'title' | 'author' | 'series' | 'genre' | 'narrator' | 'description' | 'cover_url';

const FIELDS: Array<{ key: FieldKey; placeholder: string; multiline?: boolean }> = [
  { key: 'title', placeholder: 'Titre' },
  { key: 'author', placeholder: 'Auteur' },
  { key: 'series', placeholder: 'Série' },
  { key: 'genre', placeholder: 'Genre(s), séparés par des virgules' },
  { key: 'narrator', placeholder: 'Narrateur' },
  { key: 'description', placeholder: 'Description', multiline: true },
  { key: 'cover_url', placeholder: 'URL de couverture' }
];

const LOCK_HINT_LOCKED =
  'Champ verrouillé - cliquer pour déverrouiller (autorise une future synchronisation ou un remplacement à le modifier)';
const LOCK_HINT_UNLOCKED =
  'Champ déverrouillé - cliquer pour verrouiller (protège sa valeur actuelle des prochaines synchronisations/remplacements)';

// Manual metadata editor. Mounted only while open, so the fields start from
// the book's current values each time. `onChanged` refreshes the book after a
// lock toggle without closing the form; `onSaved` closes it.
const EditForm: React.FC<EditFormProps> = ({ book, onSaved, onChanged }) => {
  const apiBase = getApiBase();
  const [values, setValues] = useState<Record<FieldKey, string>>({
    title: book.title,
    author: book.author,
    series: book.series || '',
    genre: (book.genre || []).join(', '),
    narrator: book.narrator || '',
    description: book.description || '',
    cover_url: book.cover_url || ''
  });
  const [saving, setSaving] = useState(false);
  const [lockBusyField, setLockBusyField] = useState<FieldKey | null>(null);

  const setValue = (key: FieldKey, value: string) => setValues((prev) => ({ ...prev, [key]: value }));

  const save = async () => {
    try {
      setSaving(true);
      // Only send fields the user actually changed - the backend locks
      // every field it receives, so resending the whole form unconditionally
      // would silently re-lock a field the user had just unlocked (even
      // without touching it) the moment "Enregistrer" is clicked.
      const payload: Record<string, string | string[] | null> = {};
      const next = {
        title: values.title.trim(),
        author: values.author.trim(),
        narrator: values.narrator.trim() || null,
        description: values.description.trim() || null,
        cover_url: values.cover_url.trim() || null,
        series: values.series.trim() || null,
        genre: values.genre.split(',').map((g) => g.trim()).filter(Boolean)
      };

      if (next.title !== book.title) payload.title = next.title;
      if (next.author !== book.author) payload.author = next.author;
      if (next.narrator !== (book.narrator || null)) payload.narrator = next.narrator;
      if (next.description !== (book.description || null)) payload.description = next.description;
      if (next.cover_url !== (book.cover_url || null)) payload.cover_url = next.cover_url;
      if (next.series !== (book.series || null)) payload.series = next.series;
      if (JSON.stringify(next.genre) !== JSON.stringify(book.genre || [])) payload.genre = next.genre;

      if (Object.keys(payload).length > 0) {
        await axios.patch(`${apiBase}/books/${book.id}`, payload);
      }
      await onSaved();
    } catch (error) {
      console.error('Failed to save edit:', error);
    } finally {
      setSaving(false);
    }
  };

  const toggleLock = async (field: FieldKey, currentlyLocked: boolean) => {
    const action = currentlyLocked ? 'unlock' : 'lock';
    try {
      setLockBusyField(field);
      await axios.post(`${apiBase}/books/${book.id}/${action}`, { fields: [field] });
      await onChanged();
    } catch (error) {
      console.error(`Failed to ${action} field:`, error);
    } finally {
      setLockBusyField(null);
    }
  };

  return (
    <div className="bd-panel bd-panel-form">
      {FIELDS.map(({ key, placeholder, multiline }) => {
        const isLocked = Boolean(book.manual_overrides?.includes(key));
        const isBusy = lockBusyField === key;
        const common = {
          value: values[key],
          placeholder,
          'aria-label': placeholder,
          onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setValue(key, e.target.value)
        };
        return (
          <div key={key} className="bd-row bd-row-start">
            <div className="bd-grow">
              {multiline ? (
                <textarea {...common} rows={4} className="bd-input bd-input-multiline" />
              ) : (
                <input {...common} type="text" className="bd-input" />
              )}
            </div>
            <button
              type="button"
              className={`bd-lock-button ${isLocked ? 'locked' : ''}`}
              onClick={() => toggleLock(key, isLocked)}
              disabled={isBusy}
              aria-pressed={isLocked}
              aria-label={`${placeholder} : ${isLocked ? 'verrouillé' : 'déverrouillé'}`}
              title={isLocked ? LOCK_HINT_LOCKED : LOCK_HINT_UNLOCKED}
            >
              {isBusy ? <Loader2 size={14} className="spin" /> : isLocked ? <Lock size={14} /> : <Unlock size={14} />}
            </button>
          </div>
        );
      })}
      <div>
        <button type="button" className="cta-button bd-button" disabled={saving} onClick={save}>
          {saving ? <Loader2 size={14} className="spin" /> : 'Enregistrer'}
        </button>
      </div>
    </div>
  );
};

export default EditForm;
