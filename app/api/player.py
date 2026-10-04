"""Player endpoints."""

from flask import Blueprint, jsonify, request

from app.api.context import services
from app.api.helpers import format_chapter_title
from app.database import EqualizerPresetRepository, get_session
from app.utils import logger

bp = Blueprint('player', __name__)


# Player endpoints
@bp.route('/api/player/play', methods=['POST'])
def play_book():
    try:
        data = request.json
        book_id = data.get('book_id')
        chapter_index = data.get('chapter_index')
        audiobook = services.library.get_book_by_id(book_id)
        if not audiobook:
            return jsonify({'error': 'Book not found'}), 404
        if not services.player.start_playbook(audiobook, chapter_index=chapter_index):
            return jsonify({'error': 'La lecture a échoué (voir les logs du serveur)'}), 500
        return jsonify({'status': 'playing'})
    except Exception as e:
        logger.error(f"Failed to play book: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/pause', methods=['POST'])
def pause_playback():
    try:
        services.player.pause()
        return jsonify({'status': 'paused'})
    except Exception as e:
        logger.error(f"Failed to pause: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/resume', methods=['POST'])
def resume_playback():
    try:
        services.player.resume()
        return jsonify({'status': 'playing'})
    except Exception as e:
        logger.error(f"Failed to resume: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/stop', methods=['POST'])
def stop_playback():
    try:
        services.player.stop()
        return jsonify({'status': 'stopped'})
    except Exception as e:
        logger.error(f"Failed to stop: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/next-chapter', methods=['POST'])
def next_chapter():
    try:
        if not services.player.next_chapter():
            return jsonify({'error': 'Pas de chapitre suivant'}), 400
        return jsonify({'status': 'playing'})
    except Exception as e:
        logger.error(f"Failed to go to next chapter: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/previous-chapter', methods=['POST'])
def previous_chapter():
    try:
        if not services.player.previous_chapter():
            return jsonify({'error': 'Pas de chapitre précédent'}), 400
        return jsonify({'status': 'playing'})
    except Exception as e:
        logger.error(f"Failed to go to previous chapter: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/seek', methods=['POST'])
def seek():
    try:
        data = request.json
        position = data.get('position')
        services.player.seek(position)
        return jsonify({'status': 'seeking'})
    except Exception as e:
        logger.error(f"Failed to seek: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/volume', methods=['POST'])
def set_volume():
    try:
        data = request.json
        volume = data.get('volume')
        services.player.set_volume(volume)
        return jsonify({'status': 'volume_set'})
    except Exception as e:
        logger.error(f"Failed to set volume: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/speed', methods=['POST'])
def set_speed():
    try:
        data = request.json
        speed = data.get('speed')
        services.player.set_speed(speed)
        return jsonify({'status': 'speed_set'})
    except Exception as e:
        logger.error(f"Failed to set speed: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/equalizer', methods=['POST'])
def set_player_equalizer():
    try:
        data = request.json or {}
        preset_id = data.get('preset_id')
        if preset_id is None:
            services.player.set_equalizer_preset(None)
            return jsonify({'status': 'equalizer_set', 'preset_id': None})

        session = get_session()
        preset = EqualizerPresetRepository(session).get_by_id(preset_id)
        session.close()
        if not preset:
            return jsonify({'error': 'Preset introuvable'}), 404

        services.player.set_equalizer_preset(preset.id, preset.bands, preset.preamp)
        return jsonify({'status': 'equalizer_set', 'preset_id': preset.id})
    except Exception as e:
        logger.error(f"Failed to set equalizer: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/equalizer/cycle', methods=['POST'])
def cycle_player_equalizer():
    try:
        new_preset_id = services.player.cycle_equalizer_preset()
        return jsonify({'status': 'equalizer_cycled', 'preset_id': new_preset_id})
    except Exception as e:
        logger.error(f"Failed to cycle equalizer: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/compression/cycle', methods=['POST'])
def cycle_player_compression():
    """Cycle dynamic range compression: off -> léger -> modéré -> fort ->
    off (see VLCPlayer.COMPRESSOR_PRESETS)."""
    try:
        new_preset = services.player.cycle_compression()
        return jsonify({'status': 'compression_cycled', 'preset': new_preset})
    except Exception as e:
        logger.error(f"Failed to cycle compression: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/loudness-normalization', methods=['POST'])
def set_player_loudness_normalization():
    """Toggle per-book EBU-style loudness matching (see
    app/utils/audio_loudness.py) - distinct from the real-time
    'Normalisation' filter above."""
    try:
        data = request.json or {}
        enabled = bool(data.get('enabled'))
        services.player.set_loudness_normalization(enabled)
        return jsonify({'status': 'loudness_normalization_set', 'enabled': enabled})
    except Exception as e:
        logger.error(f"Failed to set loudness normalization: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/sleep-timer', methods=['POST'])
def set_player_sleep_timer():
    """Set (or cancel, with minutes null/0) the sleep timer. Fades the
    volume out and pauses playback once it elapses - see
    PlayerService.set_sleep_timer."""
    try:
        data = request.json or {}
        minutes = data.get('minutes')
        services.player.set_sleep_timer(minutes)
        return jsonify({
            'status': 'ok',
            'sleep_timer_remaining_seconds': services.player.get_sleep_timer_remaining_seconds()
        })
    except Exception as e:
        logger.error(f"Failed to set sleep timer: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/player/state', methods=['GET'])
def get_player_state():
    try:
        book = services.player.current_audiobook
        chapter_index = services.player.current_chapter_index
        chapter_title = None
        if book and book.chapters and 0 <= chapter_index < len(book.chapters):
            chapter_title = format_chapter_title(chapter_index, book.chapters[chapter_index].get('title'))

        state = {
            'is_playing': services.player.is_playing(),
            'is_paused': services.player.is_paused(),
            'position': services.player.get_current_position(),
            'duration': services.player.get_current_duration(),
            'volume': services.player.get_volume(),
            'speed': services.player.get_speed(),
            'equalizer_preset_id': services.player.equalizer_preset_id,
            'loudness_normalization_enabled': services.player.loudness_normalization_enabled,
            'compression_preset': services.player.compression_preset,
            'sleep_timer_remaining_seconds': services.player.get_sleep_timer_remaining_seconds(),
            'is_casting': services.player.is_casting(),
            'cast_device_name': services.player.get_cast_device_name(),
            'currentChapterIndex': chapter_index,
            'currentChapterTitle': chapter_title,
            'currentBook': {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'narrator': book.narrator,
                'cover_url': book.cover,
                'description': book.description
            } if book else None
        }
        return jsonify(state)
    except Exception as e:
        logger.error(f"Failed to get player state: {e}")
        return jsonify({'error': str(e)}), 500
