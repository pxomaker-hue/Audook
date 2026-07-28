import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2 } from 'lucide-react';
import axios from 'axios';
import { getApiBase } from '../config';

interface HistoryEntry {
  session_id: number;
  book_id: string;
  title: string;
  author: string;
  cover_url: string | null;
  session_start: string | null;
  duration_seconds: number | null;
}

const formatDuration = (seconds: number | null) => {
  if (!seconds) return null;
  const minutes = Math.round(seconds / 60);
  if (minutes < 1) return "moins d'une minute";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h${(minutes % 60).toString().padStart(2, '0')}`;
};

const HistoryPage: React.FC = () => {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);
  const navigate = useNavigate();

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${getApiBase()}/history`);
      setHistory(response.data);
    } catch (error) {
      console.error('Failed to fetch history:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDeleteEntry = async (e: React.MouseEvent, sessionId: number) => {
    e.stopPropagation();
    setHistory(prev => prev.filter(h => h.session_id !== sessionId));
    try {
      await axios.delete(`${getApiBase()}/history/${sessionId}`);
    } catch (error) {
      console.error('Failed to delete history entry:', error);
      fetchHistory();
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm("Effacer tout l'historique d'écoute ?")) return;
    try {
      setClearing(true);
      await axios.delete(`${getApiBase()}/history`);
      setHistory([]);
    } catch (error) {
      console.error('Failed to clear history:', error);
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="page-content">
      <div className="top-bar" style={{ marginBottom: '20px' }}>
        <div style={{ flex: 1 }}>
          <h1 className="page-title" style={{ marginBottom: '4px' }}>Historique</h1>
          <p className="page-subtitle">Vos sessions d'écoute récentes</p>
        </div>
        {history.length > 0 && (
          <button
            className="cta-button"
            onClick={handleClearAll}
            disabled={clearing}
            style={{
              background: 'var(--surface-muted)',
              color: 'var(--text-primary)',
              border: 'none',
              padding: '10px 18px',
              borderRadius: '999px',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              opacity: clearing ? 0.6 : 1
            }}
          >
            <Trash2 size={14} /> Effacer tout
          </button>
        )}
      </div>

      {loading ? (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Chargement...
        </div>
      ) : history.length === 0 ? (
        <div
          style={{
            backgroundColor: 'var(--surface)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-pop)',
            padding: '40px',
            textAlign: 'center',
            color: 'var(--text-secondary)'
          }}
        >
          <p style={{ fontSize: '16px', marginBottom: '10px' }}>Aucune session d'écoute pour l'instant</p>
          <p style={{ fontSize: '14px' }}>Vos sessions d'écoute s'afficheront ici au fur et à mesure</p>
        </div>
      ) : (
        <div
          style={{
            backgroundColor: 'var(--surface)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-pop)',
            overflow: 'hidden'
          }}
        >
          {history.map((entry, index) => (
            <div
              key={entry.session_id}
              onClick={() => navigate(`/book/${entry.book_id}`)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '14px',
                padding: '14px 18px',
                cursor: 'pointer',
                borderBottom: index < history.length - 1 ? '1px solid var(--border)' : 'none'
              }}
            >
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '10px',
                  overflow: 'hidden',
                  flexShrink: 0,
                  backgroundColor: 'var(--surface-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '18px'
                }}
              >
                {entry.cover_url ? (
                  <img src={entry.cover_url} alt={entry.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  '📚'
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text-primary)' }}>{entry.title}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{entry.author}</div>
              </div>
              <div style={{ textAlign: 'right', fontSize: '12px', color: 'var(--text-tertiary)', flexShrink: 0 }}>
                {entry.session_start && (
                  <div>{new Date(entry.session_start).toLocaleString('fr-FR')}</div>
                )}
                {formatDuration(entry.duration_seconds) && <div>{formatDuration(entry.duration_seconds)}</div>}
              </div>
              <button
                onClick={(e) => handleDeleteEntry(e, entry.session_id)}
                title="Supprimer cette session"
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-tertiary)',
                  cursor: 'pointer',
                  flexShrink: 0,
                  padding: '6px',
                  display: 'flex',
                  transition: 'color 0.15s'
                }}
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default HistoryPage;
