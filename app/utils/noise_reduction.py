"""
On-demand noise/hiss reduction for a single book, run once and cached -
never live during playback. Uses ffmpeg's built-in `afftdn` (FFT denoiser),
which needs no external model file (unlike RNNoise), so it works with just
the bundled/PATH ffmpeg already required for loudness normalization.

Deliberately NOT applied automatically to every book: most sources (ABS/Plex
professional narrations) are already clean, and a full-book denoise pass
takes real time proportional to the book's length. This is opt-in, per book,
triggered by the user for a specifically noisy recording - see
POST /api/books/<id>/clean-audio in audook_backend.py.
"""

import subprocess
from pathlib import Path
from typing import Optional

from app.utils import logger, get_ffmpeg_path

# Noise floor estimate in dB - how aggressively afftdn treats low-level
# broadband noise (tape hiss, room hum, mic self-noise) as noise to remove.
# Conservative default: prioritizes not degrading the voice over removing
# every trace of hiss.
NOISE_FLOOR_DB = -25

FFMPEG_TIMEOUT_SECONDS = 3600  # a long book can take a while to encode


def clean_audio_file(source: str, output_path: Path) -> bool:
    """Run source (a local path or streamable URL) through ffmpeg's noise
    reduction filter and write the result to output_path. Returns False (and
    leaves no partial file behind) if ffmpeg is missing or the pass fails -
    this must never be treated as fatal by callers."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".part")

    try:
        result = subprocess.run(
            [
                get_ffmpeg_path(), "-y", "-hide_banner", "-loglevel", "error",
                "-i", source,
                "-af", f"afftdn=nf={NOISE_FLOOR_DB}",
                "-c:a", "libmp3lame", "-q:a", "4",
                # Force the container format explicitly - the temp file's
                # ".mp3.part" extension (used so a half-written file is never
                # mistaken for a finished one) breaks ffmpeg's extension-based
                # muxer autodetection, since it only looks at the last
                # extension ("part", not "mp3.part").
                "-f", "mp3",
                str(tmp_path)
            ],
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT_SECONDS
        )
    except FileNotFoundError:
        logger.warning("ffmpeg not found (bundled path missing and none on PATH) - noise reduction disabled")
        return False
    except subprocess.TimeoutExpired:
        logger.warning(f"Noise reduction timed out for '{source}'")
        tmp_path.unlink(missing_ok=True)
        return False
    except Exception as e:
        logger.warning(f"Noise reduction failed to run for '{source}': {e}")
        tmp_path.unlink(missing_ok=True)
        return False

    if result.returncode != 0 or not tmp_path.exists():
        logger.warning(f"Noise reduction failed for '{source}': {result.stderr.strip()[:500]}")
        tmp_path.unlink(missing_ok=True)
        return False

    tmp_path.replace(output_path)
    return True
