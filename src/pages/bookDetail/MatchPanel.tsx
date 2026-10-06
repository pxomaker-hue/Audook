import React, { useCallback, useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import axios from 'axios';
import { getApiBase } from '../../config';
import { BookDetail, MatchCandidate } from './types';

interface MatchPanelProps {
  book: BookDetail;
  onApplied: () => Promise<void> | void;
}

const isAudible = (c: MatchCandidate) => c.work_key.startsWith('audible:');

// "Associer": look the book up online and copy the chosen result's
// metadata onto it. Mounted only while open, so it searches once on open.
const MatchPanel: React.FC<MatchPanelProps> = ({ book, onApplied }) => {
  const apiBase = getApiBase();
  const [query, setQuery] = useState('');
  const [candidates, setCandidates] = useState<MatchCandidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<'fill' | 'replace'>('fill');
  const [applyingKey, setApplyingKey] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  const search = useCallback(async (q: string) => {
    try {
      setLoading(true);
      setShowAll(false);
      const response = await axios.get(`${apiBase}/books/${book.id}/match-candidates`, {
        params: q ? { query: q } : {}
      });
      setCandidates(response.data);
    } catch (error) {
      console.error('Failed to search candidates:', error);
    } finally {
      setLoading(false);
    }
  }, [apiBase, book.id]);

  useEffect(() => {
    search('');
  }, [search]);

  const apply = async (candidate: MatchCandidate) => {
    try {
      setApplyingKey(candidate.work_key);
      // Title/author come straight from the search result -
      // get_book_work_details only fetches description/cover/genre, so
      // without sending these along, picking a match never actually
      // corrected the title/author shown in the search list.
      await axios.post(`${apiBase}/books/${book.id}/match`, {
        work_key: candidate.work_key,
        mode,
        title: candidate.title,
        author: candidate.author
      });
      await onApplied();
    } catch (error) {
      console.error('Failed to apply match:', error);
      setApplyingKey(null);
    }
  };

  const hasAudible = candidates.some(isAudible);
  const hasOthers = candidates.some((c) => !isAudible(c));
  const visible = !showAll && hasAudible ? candidates.filter(isAudible) : candidates;

  return (
    <div className="bd-panel">
      <div className="bd-row bd-row-spaced">
        <input
          type="text"
          className="bd-input bd-grow"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search(query)}
          placeholder={`${book.title} ${book.author}`}
          aria-label="Rechercher une correspondance"
        />
        <button type="button" className="cta-button bd-button bd-button-muted" onClick={() => search(query)}>
          Chercher
        </button>
      </div>

      <div className="bd-row bd-row-spaced bd-radios">
        <label>
          <input type="radio" name="match-mode" checked={mode === 'fill'} onChange={() => setMode('fill')} />
          Compléter (garde ce qui existe)
        </label>
        <label>
          <input type="radio" name="match-mode" checked={mode === 'replace'} onChange={() => setMode('replace')} />
          Remplacer
        </label>
      </div>

      {loading ? (
        <p className="bd-muted">Recherche...</p>
      ) : candidates.length === 0 ? (
        <p className="bd-muted">Aucun résultat</p>
      ) : (
        <div className="bd-candidates">
          {visible.map((c) => (
            <div key={c.work_key} className="bd-candidate">
              <div className="bd-candidate-cover">
                {c.cover_url && <img src={c.cover_url} alt="" />}
              </div>
              <div className="bd-candidate-info">
                <div className="bd-candidate-title">
                  {c.title}
                  {isAudible(c) && (
                    <span className="bd-badge" title="Résultat Audible - inclut narrateur/série/genre réels">
                      Audible
                    </span>
                  )}
                  {c.is_french && <span className="bd-badge">FR</span>}
                </div>
                <div className="bd-candidate-meta">
                  {c.author} {c.year ? `· ${c.year}` : ''}
                </div>
              </div>
              <button
                type="button"
                className="cta-button bd-button bd-button-muted"
                disabled={applyingKey === c.work_key}
                onClick={() => apply(c)}
              >
                {applyingKey === c.work_key ? <Loader2 size={14} className="spin" /> : 'Choisir'}
              </button>
            </div>
          ))}
          {!showAll && hasAudible && hasOthers && (
            <button type="button" className="bd-link-button" onClick={() => setShowAll(true)}>
              Voir plus (Open Library, Google Books)
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default MatchPanel;
