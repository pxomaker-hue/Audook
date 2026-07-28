import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Plus, X, Pencil, Trash2, Loader2, FolderOpen } from 'lucide-react';
import axios from 'axios';
import { getApiBase } from '../config';

interface Book {
  id: string;
  title: string;
  author: string;
  cover_url: string;
  duration: number;
}

interface CollectionEntry {
  id: string;
  name: string;
  book_ids: string[];
}

const inputStyle: React.CSSProperties = {
  padding: '10px 16px',
  backgroundColor: 'var(--surface-muted)',
  color: 'var(--text-primary)',
  border: 'none',
  borderRadius: '999px',
  fontFamily: 'inherit',
  fontSize: '13px'
};

const smallButtonStyle: React.CSSProperties = {
  background: 'var(--primary)',
  color: 'var(--secondary)',
  border: 'none',
  padding: '10px 20px',
  borderRadius: '999px',
  cursor: 'pointer',
  fontSize: '13px',
  fontWeight: 600,
  display: 'flex',
  alignItems: 'center',
  gap: '8px'
};

const iconButtonStyle: React.CSSProperties = {
  background: 'var(--surface-muted)',
  color: 'var(--text-primary)',
  border: 'none',
  width: '34px',
  height: '34px',
  borderRadius: '50%',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
};

const formatDuration = (seconds: number) => {
  if (!seconds) return '--';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours > 0 ? `${hours}h${minutes.toString().padStart(2, '0')}` : `${minutes}min`;
};

const CollectionsPage: React.FC = () => {
  const [collections, setCollections] = useState<CollectionEntry[]>([]);
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [creating, setCreating] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [addBookQuery, setAddBookQuery] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchAll = async () => {
    try {
      const [collectionsRes, booksRes] = await Promise.all([
        axios.get(`${getApiBase()}/collections`),
        axios.get(`${getApiBase()}/books`)
      ]);
      setCollections(collectionsRes.data);
      setBooks(booksRes.data);
    } catch (error) {
      console.error('Failed to fetch collections:', error);
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchAll().finally(() => setLoading(false));
  }, []);

  const booksById = useMemo(() => {
    const map = new Map<string, Book>();
    books.forEach(b => map.set(b.id, b));
    return map;
  }, [books]);

  const selectedCollection = useMemo(
    () => collections.find(c => c.id === selectedId) || null,
    [collections, selectedId]
  );

  const selectedBooks = useMemo(() => {
    if (!selectedCollection) return [];
    return selectedCollection.book_ids
      .map(id => booksById.get(id))
      .filter((b): b is Book => Boolean(b));
  }, [selectedCollection, booksById]);

  const addBookCandidates = useMemo(() => {
    if (!selectedCollection || !addBookQuery.trim()) return [];
    const q = addBookQuery.toLowerCase();
    const existing = new Set(selectedCollection.book_ids);
    return books
      .filter(b => !existing.has(b.id))
      .filter(b => b.title.toLowerCase().includes(q) || b.author.toLowerCase().includes(q))
      .slice(0, 8);
  }, [books, selectedCollection, addBookQuery]);

  const handleCreateCollection = async () => {
    const name = newCollectionName.trim();
    if (!name) return;
    try {
      setCreating(true);
      const response = await axios.post(`${getApiBase()}/collections`, { name });
      setCollections(prev => [...prev, response.data]);
      setNewCollectionName('');
      setSelectedId(response.data.id);
    } catch (error) {
      console.error('Failed to create collection:', error);
    } finally {
      setCreating(false);
    }
  };

  const handleStartRename = (e: React.MouseEvent, collection: CollectionEntry) => {
    e.stopPropagation();
    setRenamingId(collection.id);
    setRenameValue(collection.name);
  };

  const handleSaveRename = async (collectionId: string) => {
    const name = renameValue.trim();
    setRenamingId(null);
    if (!name) return;
    try {
      await axios.patch(`${getApiBase()}/collections/${collectionId}`, { name });
      setCollections(prev => prev.map(c => (c.id === collectionId ? { ...c, name } : c)));
    } catch (error) {
      console.error('Failed to rename collection:', error);
    }
  };

  const handleDeleteCollection = async (e: React.MouseEvent, collectionId: string) => {
    e.stopPropagation();
    try {
      setDeletingId(collectionId);
      await axios.delete(`${getApiBase()}/collections/${collectionId}`);
      setCollections(prev => prev.filter(c => c.id !== collectionId));
      if (selectedId === collectionId) setSelectedId(null);
    } catch (error) {
      console.error('Failed to delete collection:', error);
    } finally {
      setDeletingId(null);
    }
  };

  const handleAddBook = async (bookId: string) => {
    if (!selectedCollection) return;
    try {
      const response = await axios.post(`${getApiBase()}/collections/${selectedCollection.id}/books`, { book_id: bookId });
      setCollections(prev =>
        prev.map(c => (c.id === selectedCollection.id ? { ...c, book_ids: response.data.book_ids } : c))
      );
    } catch (error) {
      console.error('Failed to add book to collection:', error);
    }
  };

  const handleRemoveBook = async (e: React.MouseEvent, bookId: string) => {
    e.stopPropagation();
    if (!selectedCollection) return;
    try {
      const response = await axios.delete(`${getApiBase()}/collections/${selectedCollection.id}/books/${bookId}`);
      setCollections(prev =>
        prev.map(c => (c.id === selectedCollection.id ? { ...c, book_ids: response.data.book_ids } : c))
      );
    } catch (error) {
      console.error('Failed to remove book from collection:', error);
    }
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Collections</h1>
        <p className="page-subtitle">Créez et organisez vos propres regroupements de livres</p>
      </div>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '30px' }}>
        <input
          type="text"
          value={newCollectionName}
          onChange={(e) => setNewCollectionName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleCreateCollection()}
          placeholder="Nom de la nouvelle collection..."
          style={{ ...inputStyle, width: '320px' }}
        />
        <button
          style={{ ...smallButtonStyle, opacity: creating || !newCollectionName.trim() ? 0.6 : 1 }}
          disabled={creating || !newCollectionName.trim()}
          onClick={handleCreateCollection}
        >
          {creating ? <Loader2 size={14} className="spin" /> : <Plus size={14} />}
          Créer
        </button>
      </div>

      {loading ? (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Chargement...
        </div>
      ) : collections.length === 0 ? (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Aucune collection pour le moment - créez-en une ci-dessus.
        </div>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', marginBottom: '30px' }}>
          {collections.map(collection => {
            const covers = collection.book_ids
              .map(id => booksById.get(id)?.cover_url)
              .filter(Boolean)
              .slice(0, 4) as string[];
            const isSelected = selectedId === collection.id;
            return (
              <div
                key={collection.id}
                onClick={() => setSelectedId(isSelected ? null : collection.id)}
                style={{
                  width: '210px',
                  backgroundColor: 'var(--surface)',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: isSelected ? '0 0 0 2px var(--primary)' : 'var(--shadow-pop)',
                  padding: '14px',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px'
                }}
              >
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '3px',
                    aspectRatio: '1 / 1',
                    borderRadius: 'var(--radius-sm)',
                    overflow: 'hidden',
                    backgroundColor: 'var(--surface-muted)'
                  }}
                >
                  {covers.length > 0 ? (
                    covers.map((url, i) => (
                      <img key={i} src={url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ))
                  ) : (
                    <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)' }}>
                      <FolderOpen size={28} />
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px' }}>
                  {renamingId === collection.id ? (
                    <input
                      autoFocus
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => e.key === 'Enter' && handleSaveRename(collection.id)}
                      onBlur={() => handleSaveRename(collection.id)}
                      style={{ ...inputStyle, flex: 1, padding: '6px 10px' }}
                    />
                  ) : (
                    <div style={{ fontWeight: 700, fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {collection.name}
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
                    <button
                      title="Renommer"
                      onClick={(e) => handleStartRename(e, collection)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', display: 'flex' }}
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      title="Supprimer"
                      disabled={deletingId === collection.id}
                      onClick={(e) => handleDeleteCollection(e, collection.id)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', display: 'flex' }}
                    >
                      {deletingId === collection.id ? <Loader2 size={14} className="spin" /> : <Trash2 size={14} />}
                    </button>
                  </div>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {collection.book_ids.length} livre{collection.book_ids.length !== 1 ? 's' : ''}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selectedCollection && (
        <div>
          <h2 className="section-title">{selectedCollection.name}</h2>

          <div className="search-bar">
            <Search size={16} />
            <input
              type="text"
              placeholder="Rechercher un livre à ajouter..."
              value={addBookQuery}
              onChange={(e) => setAddBookQuery(e.target.value)}
            />
          </div>

          {addBookCandidates.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '20px', maxWidth: '500px' }}>
              {addBookCandidates.map(book => (
                <div
                  key={book.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '10px',
                    padding: '8px 14px',
                    backgroundColor: 'var(--surface)',
                    borderRadius: 'var(--radius-sm)'
                  }}
                >
                  <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <strong>{book.title}</strong>
                    <span style={{ color: 'var(--text-secondary)' }}> · {book.author}</span>
                  </div>
                  <button
                    onClick={() => handleAddBook(book.id)}
                    style={{ ...iconButtonStyle, flexShrink: 0 }}
                    title="Ajouter à la collection"
                  >
                    <Plus size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {selectedBooks.length === 0 ? (
            <div style={{ color: 'var(--text-secondary)', padding: '20px 0' }}>
              Cette collection est vide - utilisez la recherche ci-dessus pour y ajouter des livres.
            </div>
          ) : (
            <div className="books-grid">
              {selectedBooks.map(book => (
                <div key={book.id} className="book-card" onClick={() => navigate(`/book/${book.id}`)}>
                  <div className="book-card-cover">
                    {book.cover_url ? <img src={book.cover_url} alt={book.title} /> : <span>📚</span>}
                    <span className="book-card-badge">{formatDuration(book.duration)}</span>
                    <button
                      onClick={(e) => handleRemoveBook(e, book.id)}
                      className="book-card-dismiss"
                      title="Retirer de la collection"
                    >
                      <X size={12} />
                    </button>
                  </div>
                  <div className="book-card-info">
                    <div className="book-card-title">{book.title}</div>
                    <div className="book-card-author">{book.author}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CollectionsPage;
