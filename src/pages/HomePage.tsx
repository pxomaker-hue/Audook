import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import axios from 'axios';

interface Book {
  id: string;
  title: string;
  author: string;
  narrator: string;
  cover_url: string;
}

const HomePage: React.FC = () => {
  const [books, setBooks] = useState<Book[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredBooks, setFilteredBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const apiBase = 'http://localhost:5000/api';

  useEffect(() => {
    const fetchBooks = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${apiBase}/books`);
        setBooks(response.data);
        setFilteredBooks(response.data);
      } catch (error) {
        console.error('Failed to fetch books:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchBooks();
  }, []);

  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredBooks(books);
    } else {
      setFilteredBooks(
        books.filter(book =>
          book.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          book.author.toLowerCase().includes(searchQuery.toLowerCase())
        )
      );
    }
  }, [searchQuery, books]);

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
        <h1 className="page-title">Bibliothèque</h1>
        <p className="page-subtitle">Vos audiolivres préférés</p>
      </div>

      <div className="search-bar">
        <Search size={20} />
        <input
          type="text"
          placeholder="Rechercher par titre ou auteur..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {loading ? (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Chargement des audiolivres...
        </div>
      ) : filteredBooks.length === 0 ? (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px' }}>
          Aucun audiolive trouvé
        </div>
      ) : (
        <div className="books-grid">
          {filteredBooks.map(book => (
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

export default HomePage;
