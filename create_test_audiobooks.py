#!/usr/bin/env python3
"""
Create test audiobook files for local library testing
Generates simple MP3 files using a tone generator
"""

import wave
import math
import sys
from pathlib import Path

# Set UTF-8 encoding for console output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def create_test_audio(output_path: Path, duration: int = 60, frequency: float = 440.0):
    """Create a simple WAV file with a sine wave tone"""
    sample_rate = 44100
    num_samples = sample_rate * duration

    # Generate sine wave
    frames = []
    for i in range(num_samples):
        # Simple sine wave
        sample = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
        frames.append(sample.to_bytes(2, byteorder='little', signed=True))

    # Write WAV file
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(output_path), 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(frames))

    print(f"[OK] Created: {output_path}")


def create_test_library():
    """Create a test audiobook library"""
    test_lib_path = Path("test_audiobooks")

    # Create some test audiobooks
    audiobooks = [
        {
            "title": "Les Misérables",
            "chapters": [
                ("Book 1 - Fantine", 60),
                ("Book 2 - Cosette", 60),
                ("Book 3 - Marius", 60),
            ]
        },
        {
            "title": "The Great Gatsby",
            "chapters": [
                ("Chapter 1", 60),
                ("Chapter 2", 60),
            ]
        },
        {
            "title": "Pride and Prejudice",
            "chapters": [
                ("Volume 1", 60),
                ("Volume 2", 60),
                ("Volume 3", 60),
            ]
        }
    ]

    for book in audiobooks:
        book_path = test_lib_path / book["title"]
        book_path.mkdir(parents=True, exist_ok=True)

        for chapter_name, duration in book["chapters"]:
            audio_file = book_path / f"{chapter_name}.wav"
            create_test_audio(audio_file, duration=duration)

    print(f"\n[OK] Test library created at: {test_lib_path}")
    print(f"   You can now open this folder in Audook!")
    print(f"   Path: {test_lib_path.absolute()}")


if __name__ == "__main__":
    create_test_library()
