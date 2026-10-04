"""Equalizer endpoints."""


from flask import Blueprint, jsonify, request

from app.api.context import services
from app.database import EqualizerPresetRepository, get_session
from app.utils import logger

bp = Blueprint('equalizer', __name__)


# Equalizer preset management (fine-tuning lives in Settings)
@bp.route('/api/equalizer/presets', methods=['GET'])
def get_equalizer_presets():
    try:
        session = get_session()
        presets = EqualizerPresetRepository(session).get_all()
        result = [{
            'id': p.id,
            'name': p.name,
            'bands': p.bands,
            'preamp': p.preamp,
            'is_builtin': p.is_builtin
        } for p in presets]
        session.close()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to get equalizer presets: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/equalizer/presets', methods=['POST'])
def create_equalizer_preset():
    try:
        data = request.json or {}
        name = (data.get('name') or '').strip()
        bands = data.get('bands')
        preamp = float(data.get('preamp', 0.0))

        if not name:
            return jsonify({'error': 'Le nom est requis'}), 400
        if not isinstance(bands, list) or len(bands) != 10:
            return jsonify({'error': 'bands doit contenir exactement 10 valeurs'}), 400

        session = get_session()
        preset = EqualizerPresetRepository(session).create(name, [float(b) for b in bands], preamp)
        result = {'id': preset.id, 'name': preset.name, 'bands': preset.bands,
                   'preamp': preset.preamp, 'is_builtin': preset.is_builtin}
        session.close()
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"Failed to create equalizer preset: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/equalizer/presets/<preset_id>', methods=['PUT'])
def update_equalizer_preset(preset_id):
    try:
        data = request.json or {}
        name = data.get('name')
        bands = data.get('bands')
        preamp = data.get('preamp')

        if bands is not None and (not isinstance(bands, list) or len(bands) != 10):
            return jsonify({'error': 'bands doit contenir exactement 10 valeurs'}), 400

        session = get_session()
        repo = EqualizerPresetRepository(session)
        preset = repo.update(
            preset_id,
            name=name.strip() if name else None,
            bands=[float(b) for b in bands] if bands is not None else None,
            preamp=float(preamp) if preamp is not None else None
        )

        if not preset:
            session.close()
            return jsonify({'error': 'Preset introuvable ou en lecture seule'}), 404

        # Read everything off the ORM object before closing the session -
        # commit() (inside repo.update()) expires its attributes, so touching
        # them after close() raises a DetachedInstanceError.
        result = {'id': preset.id, 'name': preset.name, 'bands': preset.bands,
                  'preamp': preset.preamp, 'is_builtin': preset.is_builtin}
        session.close()

        # If this preset is the one currently active, re-apply it so the
        # edit takes effect immediately instead of on the next switch.
        if services.player.equalizer_preset_id == result['id']:
            services.player.set_equalizer_preset(result['id'], result['bands'], result['preamp'])

        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to update equalizer preset: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/equalizer/presets/<preset_id>', methods=['DELETE'])
def delete_equalizer_preset(preset_id):
    try:
        session = get_session()
        deleted = EqualizerPresetRepository(session).delete(preset_id)
        session.close()

        if not deleted:
            return jsonify({'error': 'Preset introuvable ou en lecture seule'}), 404

        # Deleted preset was active - fall back to disabled rather than
        # keep driving the live player off a preset that no longer exists.
        if services.player.equalizer_preset_id == preset_id:
            services.player.set_equalizer_preset(None)

        return jsonify({'status': 'deleted'})
    except Exception as e:
        logger.error(f"Failed to delete equalizer preset: {e}")
        return jsonify({'error': str(e)}), 500
