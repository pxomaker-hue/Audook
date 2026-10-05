"""Books endpoints."""

import re
import threading

from flask import Blueprint, jsonify, request

from app.api.context import services
from app.api.errors import internal_error
from app.api.helpers import format_chapter_title
from app.database import BookRepository, BookmarkRepository, ReadingProgressRepository, ServerRepository, get_session
from app.database.models import Book as DbBook
from app.sync import progress_sync
from app.utils import audio_loudness, logger, online_metadata

bp = Blueprint('books', __name__)


# Library endpoints
@bp.route('/api/books', methods=['GET'])
def get_books():
    try:
        books = services.library.get_all_books()
        session = get_session()
        progress_repo = ReadingProgressRepository(session)
        in_progress = progress_repo.get_in_progress_map()
        finished_ids = progress_repo.get_finished_book_ids()
        bookmarked_ids = BookmarkRepository(session).get_book_ids_with_bookmarks()

        # Books from a hidden server are excluded from library views - the
        # synced data itself is untouched, this is purely a display filter
        # (see POST /api/servers/<id>/hidden).
        hidden_server_ids = ServerRepository(session).get_hidden_server_ids()
        if hidden_server_ids:
            hidden_book_ids = {
                row[0] for row in session.query(DbBook.id)
                .filter(DbBook.server_id.in_(hidden_server_ids)).all()
            }
            books = [b for b in books if b.id not in hidden_book_ids]

        result = []
        for book in books:
            progress = in_progress.get(book.id)
            current_chapter_title = None
            if progress and book.chapters:
                chapter_index = progress.get('chapter_index') or 0
                if 0 <= chapter_index < len(book.chapters):
                    current_chapter_title = format_chapter_title(chapter_index, book.chapters[chapter_index].get('title'))

            result.append({
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'narrator': book.narrator,
                'cover_url': book.cover,
                'duration': book.duration,
                'description': book.description,
                'source': book.source,
                'series': book.metadata.get('series'),
                'series_sequence': book.metadata.get('series_sequence'),
                'genre': book.metadata.get('genre') or [],
                'progress_percent': progress.get('percent') if progress else 0,
                'current_chapter_title': current_chapter_title,
                'is_finished': book.id in finished_ids,
                'has_bookmark': book.id in bookmarked_ids,
                'author_bio': book.metadata.get('author_bio'),
                'author_photo': book.metadata.get('author_photo')
            })
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to get books: {e}")
        return internal_error()

@bp.route('/api/books/<book_id>', methods=['GET'])
def get_book_details(book_id):
    try:
        book = services.library.get_book_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        try:
            progress_sync.reconcile_progress(book_id)
        except Exception as e:
            logger.warning(f"Failed to reconcile progress before returning book details: {e}")

        session = get_session()
        progress_repo = ReadingProgressRepository(session)
        progress = progress_repo.get_or_create(book_id)
        bookmarks = BookmarkRepository(session).get_by_book(book_id)

        return jsonify({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'narrator': book.narrator,
            'cover_url': book.cover,
            'duration': book.duration,
            'description': book.description,
            'chapters': book.chapters,
            'series': book.metadata.get('series'),
            'series_sequence': book.metadata.get('series_sequence'),
            'genre': book.metadata.get('genre') or [],
            'author_bio': book.metadata.get('author_bio'),
            'author_photo': book.metadata.get('author_photo'),
            'manual_overrides': book.metadata.get('manual_overrides', []),
            'progress': {
                'position': progress.position_seconds,
                'percentage': progress.progress_percent,
                'chapter_index': progress.current_chapter_index
            },
            'is_finished': progress.is_finished,
            'noise_reduction_status': BookRepository(session).get_noise_reduction_status(book_id),
            'use_cleaned_audio': BookRepository(session).get_use_cleaned_audio(book_id),
            'bookmarks': [{
                'id': b.id,
                'chapter_index': b.chapter_index,
                'position_seconds': b.position_seconds,
                'title': b.title,
                'created_at': b.created_at.isoformat() if b.created_at else None
            } for b in bookmarks]
        })
    except Exception as e:
        logger.error(f"Failed to get book details: {e}")
        return internal_error()

@bp.route('/api/books/<book_id>/finished', methods=['POST'])
def set_book_finished(book_id):
    """Manually mark/unmark a book as finished. Also best-effort pushes the
    finished status to the book's source server (Plex/Audiobookshelf)."""
    try:
        data = request.json or {}
        finished = bool(data.get('finished', True))

        session = get_session()
        progress_repo = ReadingProgressRepository(session)
        progress = progress_repo.set_finished(book_id, finished)
        chapter_index = progress.current_chapter_index
        position = progress.position_seconds

        try:
            progress_sync.push_progress(book_id, chapter_index, position, finished)
        except Exception as e:
            logger.warning(f"Failed to push finished status to remote server: {e}")

        return jsonify({'status': 'ok', 'is_finished': finished})
    except Exception as e:
        logger.error(f"Failed to set finished status: {e}")
        return internal_error()

@bp.route('/api/books/<book_id>/clean-audio', methods=['POST'])
def clean_book_audio(book_id):
    """Kick off a one-time, opt-in noise-reduction pass over this book's
    chapters (see PlayerService.start_noise_reduction). Runs in the
    background - the caller polls GET /api/books/<id> for
    noise_reduction_status ('processing' -> 'done'/'error')."""
    try:
        book = services.library.get_book_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        started = services.player.start_noise_reduction(book_id)
        if not started:
            return jsonify({'status': 'already_processing'})
        return jsonify({'status': 'processing'})
    except Exception as e:
        logger.error(f"Failed to start noise reduction: {e}")
        return internal_error()

@bp.route('/api/books/<book_id>/use-cleaned-audio', methods=['POST'])
def set_book_use_cleaned_audio(book_id):
    """Switch a book back to its original audio, or back to the cleaned
    version - the cleaned files stay cached either way, so flipping this
    is instant and doesn't require re-running the noise reduction pass."""
    try:
        data = request.json or {}
        enabled = bool(data.get('enabled', True))
        session = get_session()
        BookRepository(session).set_use_cleaned_audio(book_id, enabled)
        return jsonify({'status': 'ok', 'use_cleaned_audio': enabled})
    except Exception as e:
        logger.error(f"Failed to set use_cleaned_audio: {e}")
        return internal_error()

@bp.route('/api/books/<book_id>', methods=['PATCH'])
def update_book(book_id):
    """Manually edit a book's metadata. Edited fields are locked against
    being overwritten by a future scan."""
    try:
        data = request.json or {}
        allowed_fields = ('title', 'author', 'narrator', 'description', 'cover_url', 'series', 'genre')
        fields = {k: v for k, v in data.items() if k in allowed_fields}
        if not fields:
            return jsonify({'error': 'Aucun champ valide à mettre à jour'}), 400

        session = get_session()
        book_repo = BookRepository(session)
        book = book_repo.update_fields(book_id, fields, lock=True)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        return jsonify({'status': 'updated'})
    except Exception as e:
        logger.error(f"Failed to update book: {e}")
        return internal_error()

@bp.route('/api/books/<book_id>/lock', methods=['POST'])
def lock_book_fields(book_id):
    """Lock fields against being overwritten by a future scan or online
    match/replace, without changing their value - lets the user freely lock
    a field, not just get it locked as a side effect of editing it."""
    try:
        data = request.json or {}
        fields = data.get('fields')
        if not fields or not isinstance(fields, list):
            return jsonify({'error': 'fields (liste) requis'}), 400

        session = get_session()
        book_repo = BookRepository(session)
        book = book_repo.lock_fields(book_id, fields)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        return jsonify({'status': 'locked', 'fields': fields})
    except Exception as e:
        logger.error(f"Failed to lock book fields: {e}")
        return internal_error()

@bp.route('/api/books/<book_id>/unlock', methods=['POST'])
def unlock_book_fields(book_id):
    """Unlock previously-manually-edited fields so the next scan or online
    match/replace can overwrite them again."""
    try:
        data = request.json or {}
        fields = data.get('fields')
        if not fields or not isinstance(fields, list):
            return jsonify({'error': 'fields (liste) requis'}), 400

        session = get_session()
        book_repo = BookRepository(session)
        book = book_repo.unlock_fields(book_id, fields)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        return jsonify({'status': 'unlocked', 'fields': fields})
    except Exception as e:
        logger.error(f"Failed to unlock book fields: {e}")
        return internal_error()

@bp.route('/api/books/<book_id>/match-candidates', methods=['GET'])
def get_book_match_candidates(book_id):
    """Search Open Library for candidate matches for a book (like Plex's
    'Fix Match'). Defaults to the book's own title/author but accepts an
    override query for a manual search."""
    try:
        book = services.library.get_book_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        query = request.args.get('query', '').strip()
        # Local-folder scans sometimes fall back to the raw filename/folder
        # name as the title (e.g. "Harry_Potter_a_L_Ecole_des_sorciers"),
        # which searches poorly - clean it up before using it as a query.
        title = query or re.sub(r'[_\s]+', ' ', book.title).strip()
        author = None if query else book.author

        # Fetch more than the usual default so the frontend has enough
        # Open Library/Google Books results in reserve for its "Voir plus"
        # button (Audible results are shown first/by default, these are
        # extra/optional since audiobooks rarely need them).
        candidates = online_metadata.search_book_candidates(title, author, limit=12)
        return jsonify(candidates)
    except Exception as e:
        logger.error(f"Failed to get match candidates: {e}")
        return internal_error()

@bp.route('/api/books/<book_id>/match', methods=['POST'])
def apply_book_match(book_id):
    """Apply a chosen Open Library candidate to a book. mode='replace'
    overwrites description/cover unconditionally, mode='fill' (default)
    only fills fields that are currently empty."""
    try:
        data = request.json or {}
        work_key = data.get('work_key')
        mode = data.get('mode', 'fill')
        # The candidate's title/author come from the search result itself
        # (search_book_candidates), not from get_book_work_details below -
        # that only fetches description/cover/genre, so without these the
        # title/author shown in the search list never actually got applied.
        candidate_title = (data.get('title') or '').strip()
        candidate_author = (data.get('author') or '').strip()
        if not work_key:
            return jsonify({'error': 'work_key requis'}), 400

        session = get_session()
        book_repo = BookRepository(session)
        book = book_repo.get_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        details = online_metadata.get_book_work_details(work_key)
        existing_metadata = book.extra_metadata or {}
        existing_genre = existing_metadata.get('genre') or []
        locked_fields = set(existing_metadata.get('manual_overrides') or [])

        def should_apply(field_name, existing_value, candidate_value):
            """Compléter (fill): only touches fields that are currently
            empty, and never touches a locked field even if it's empty (a
            locked-but-empty field means the user deliberately wants it left
            blank). Remplacer (replace): overwrites regardless of whether
            it's already filled, but a locked field is still protected -
            that's the whole point of locking it."""
            if not candidate_value or field_name in locked_fields:
                return False
            return mode == 'replace' or not existing_value

        fields = {}
        if should_apply('title', book.title, candidate_title):
            fields['title'] = candidate_title
        if should_apply('author', book.author, candidate_author):
            fields['author'] = candidate_author
        if should_apply('description', book.description, details.get('description')):
            fields['description'] = details['description']
        if should_apply('cover_url', book.cover_url, details.get('cover_url')):
            fields['cover_url'] = details['cover_url']
        if should_apply('genre', existing_genre, details.get('genre')):
            fields['genre'] = [details['genre']]
        # Audible-only fields: narrator/series/series_sequence - Open
        # Library/Google Books candidates never populate these (they're
        # book-catalog databases, not audiobook ones), so this is a no-op
        # for any match that didn't come from Audible.
        if should_apply('narrator', book.narrator, details.get('narrator')):
            fields['narrator'] = details['narrator']
        if should_apply('series', existing_metadata.get('series'), details.get('series')):
            fields['series'] = details['series']
        if should_apply('series_sequence', existing_metadata.get('series_sequence'), details.get('series_sequence')):
            fields['series_sequence'] = details['series_sequence']

        applied = []
        if fields:
            book_repo.update_fields(book_id, fields, lock=True)
            applied.extend(fields.keys())

        # Real per-chapter titles - only from Audible (the only source with
        # actual chapter data), and only applied when the chapter count
        # matches exactly (see update_chapter_titles). Not part of the
        # fill/replace/lock field system above since there's nothing to lock
        # a chapter title against - a matching chapter count is itself the
        # safety check.
        if work_key.startswith('audible:'):
            chapters = online_metadata.get_audible_chapters(work_key[len('audible:'):])
            if chapters:
                titles = [c['title'] for c in chapters if c.get('title')]
                if len(titles) == len(book.chapters or []) and book_repo.update_chapter_titles(book_id, titles):
                    applied.append('chapters')

        if not applied:
            return jsonify({'status': 'no_change'})

        return jsonify({'status': 'matched', 'applied': applied})
    except Exception as e:
        logger.error(f"Failed to apply match: {e}")
        return internal_error()

@bp.route('/api/books/search', methods=['GET'])
def search_books():
    try:
        query = request.args.get('q', '')
        books = services.library.search_books(query)
        return jsonify([{
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'narrator': book.narrator,
            'cover_url': book.cover
        } for book in books])
    except Exception as e:
        logger.error(f"Failed to search books: {e}")
        return internal_error()

@bp.route('/api/books/<book_id>/loudness-gain', methods=['GET'])
def get_book_loudness_gain(book_id):
    """Per-book EBU-style loudness gain (see app/utils/audio_loudness.py) -
    used by the mobile app to apply the same normalization desktop does via
    VLC's equalizer preamp, through Android's LoudnessEnhancer/volume
    instead. Returns the cached value immediately if there is one;
    otherwise kicks off the (slow, ffmpeg-based) measurement in the
    background - same as the desktop player does on first play of a book -
    and returns null so the caller can poll again shortly after."""
    try:
        session = get_session()
        book = BookRepository(session).get_by_id(book_id)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        cached_gain = BookRepository(session).get_loudness_gain(book_id)
        if cached_gain is not None:
            return jsonify({'gain_db': cached_gain})

        chapters = book.chapters or []
        source = chapters[0].get('audio_file') if chapters else None
        if not source:
            return jsonify({'gain_db': None})

        def measure_and_cache():
            gain = audio_loudness.measure_loudness_gain(source)
            if gain is None:
                return
            measure_session = get_session()
            try:
                BookRepository(measure_session).set_loudness_gain(book_id, gain)
            finally:
                measure_session.close()

        threading.Thread(target=measure_and_cache, daemon=True).start()
        return jsonify({'gain_db': None})
    except Exception as e:
        logger.error(f"Failed to get loudness gain for {book_id}: {e}")
        return internal_error()
