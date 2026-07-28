import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import axios from 'axios';
import { getApiBase } from '../config';

interface Book {
  id: string;
  author: string;
  author_photo: string | null;
}

const AVATAR_COLORS = ['#ffc629', '#17161b', '#c3c2c9', '#f4f4f2'];

const initials = (name: string) =>
  name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(p => p[0]?.toUpperCase())
    .join('');

const ExplorePage: React.FC = () => {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchBooks = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${getApiBase()}/books`);
        setBooks(response.data);
      } catch (error) {
        console.error('Failed to fetch books:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchBooks();
  }, []);

  const authors = useMemo(() => {
    const counts = new Map<string, number>();
    const photos = new Map<string, string>();
    books.forEach(b => {
      counts.set(b.author, (counts.get(b.author) || 0) + 1);
      if (b.author_photo && !photos.has(b.author)) {
        photos.set(b.author, b.author_photo);
      }
    });
    let list = Array.from(counts.entries()).map(([author, count]) => ({
      author,
      count,
      photo: photos.get(author) || null
    }));

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(a => a.author.toLowerCase().includes(q));
    }

    return list.sort((a, b) => a.author.localeCompare(b.author));
  }, [books, searchQuery]);

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Découvrir</h1>
        <p className="page-subtitle">Parcourez votre bibliothèque par auteur</p>
      </div>

      <div className="search-bar">
        <Search size={16} />
        <input
          type="text"
          placeholder="Rechercher un auteur..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {loading ? (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Chargement...
        </div>
      ) : authors.length === 0 ? (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Aucun auteur trouvé
        </div>
      ) : (
        <div className="authors-grid" style={{ marginTop: '20px' }}>
          {authors.map(({ author, count, photo }, i) => (
            <div
              key={author}
              className="author-row"
              onClick={() => navigate(`/author/${encodeURIComponent(author)}`)}
            >
              <div
                className="author-avatar"
                style={{ backgroundColor: photo ? undefined : AVATAR_COLORS[i % AVATAR_COLORS.length] }}
              >
                {photo ? <img src={photo} alt={author} /> : (initials(author) || '?')}
              </div>
              <div className="author-name">{author}</div>
              <div className="author-count">{count}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ExplorePage;
