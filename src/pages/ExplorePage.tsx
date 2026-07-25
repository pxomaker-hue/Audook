import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface Book {
  id: string;
  title: string;
  author: string;
  narrator: string;
  cover_url: string;
}

const ExplorePage: React.FC = () => {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const apiBase = 'http://localhost:5000/api';

  useEffect(() => {
    const fetchBooks = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${apiBase}/books`);
        setBooks(response.data);
      } catch (error) {
        console.error('Failed to fetch books:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchBooks();
  }, []);

  const handleBookClick = (bookId: string) => {
    navigate(`/book/${bookId}`);
  };

  const handlePlayBook = async (e: React.MouseEvent, bookId: string) => {
    e.stopPropagation();
    try {
      await axios.post(`${apiBase}/player/play`, { book_id: bookId });
    } catch (error) {
      console.error('Failed to play book:', error);
    }
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Découvrir</h1>
        <p className="page-subtitle">Explorez notre collection d'audiolivres</p>
      </div>

      <h2 style={{ marginTop: '30px', marginBottom: '15px', color: 'var(--primary)' }}>
        En vedette
      </h2>

      {loading ? (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Chargement des audiolivres...
        </div>
      ) : books.length === 0 ? (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Aucun audiolive disponible
        </div>
      ) : (
        <div className="books-grid">
          {books.map(book => (
            <div
              key={book.id}
              className="book-card"
              onClick={() => handleBookClick(book.id)}
            >
              <div className="book-card-cover">
                {book.cover_url ? (
                  <img src={book.cover_url} alt={book.title} />
                ) : (
                  <span>📚</span>
                )}
                <div className="book-card-overlay">
                  <button
                    className="play-button"
                    onClick={(e) => handlePlayBook(e, book.id)}
                    title="Lire"
                  >
                    ▶
                  </button>
                </div>
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
  );
};

export default ExplorePage;
