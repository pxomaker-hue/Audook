"""
EBU R128 loudness measurement, used to compute a per-book gain so different
audiobooks (often mastered at wildly different levels) end up at a
consistent perceived volume - distinct from the real-time "Normalisation"
VLC filter, which reacts to short-term level changes rather than matching a
long-term loudness target.

Requires ffmpeg (bundled with the app, or on PATH - see get_ffmpeg_path).
Degrades gracefully (returns None) if it's missing or the measurement fails
for any reason - this must never block playback.
"""

import json
import re
import subprocess
from typing import Optional

from app.utils import logger, get_ffmpeg_path

# ACX/Audible-style spoken-word target. Real EBU R128 broadcast target is
# -23 LUFS, but that's tuned for TV/radio, not deliberately quieter
# audiobook masters - -18 LUFS reads as a comfortable, consistent level for
# narration without needing extreme gain swings on well-mastered sources.
TARGET_LUFS = -18.0

# Only analyze the first N seconds of the (often very long) source file -
# fast approximate measurement instead of decoding an entire 10+ hour book.
# A narrator's mastering level is consistent throughout a chapter, so a
# representative sample is enough.
SAMPLE_SECONDS = 600

# Clamp the computed gain so a bad/atypical measurement can't produce an
# extreme, jarring volume jump.
MAX_GAIN_DB = 12.0

FFMPEG_TIMEOUT_SECONDS = 60


def measure_loudness_gain(source: str) -> Optional[float]:
    """Measure the integrated loudness (LUFS) of `source` (a local path or a
    streamable URL - ffmpeg reads both) and return the gain in dB needed to
    reach TARGET_LUFS, clamped to +/-MAX_GAIN_DB. Returns None if ffmpeg
    isn't available or the measurement fails."""
    try:
        result = subprocess.run(
            [
                get_ffmpeg_path(), "-hide_banner",
                "-t", str(SAMPLE_SECONDS),
                "-i", source,
                "-af", f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:print_format=json",
                "-f", "null", "-"
            ],
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT_SECONDS
        )
    except FileNotFoundError:
        logger.warning("ffmpeg not found (bundled path missing and none on PATH) - loudness normalization disabled")
        return None
    except Exception as e:
        logger.warning(f"Loudness measurement failed to run for '{source}': {e}")
        return None

    # loudnorm prints its JSON block to stderr, mixed in with ffmpeg's own logs
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", result.stderr)
    if not match:
        logger.warning(f"Loudness measurement produced no readable output for '{source}'")
        return None

    try:
        stats = json.loads(match.group(0))
        measured_lufs = float(stats["input_i"])
    except (ValueError, KeyError) as e:
        logger.warning(f"Failed to parse loudness measurement for '{source}': {e}")
        return None

    # ffmpeg reports -inf for near-silent samples (e.g. a long intro/silence
    # at the very start) - not a usable measurement.
    if measured_lufs < -70:
        logger.warning(f"Loudness measurement for '{source}' looks invalid ({measured_lufs} LUFS)")
        return None

    gain_db = TARGET_LUFS - measured_lufs
    return max(-MAX_GAIN_DB, min(MAX_GAIN_DB, gain_db))
