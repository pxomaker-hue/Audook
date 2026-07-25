"""
Generate cover images for audiobooks
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib


def generate_cover(title: str, author: str, output_path: Path, size: int = 300) -> Path:
    """Generate a simple cover image for an audiobook"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate color based on title hash
    hash_obj = hashlib.md5(title.encode())
    hash_hex = hash_obj.hexdigest()
    r = int(hash_hex[0:2], 16)
    g = int(hash_hex[2:4], 16)
    b = int(hash_hex[4:6], 16)

    # Create image
    img = Image.new('RGB', (size, size), (r, g, b))
    draw = ImageDraw.Draw(img)

    # Add title and author text
    try:
        # Try to use a decent font, fall back to default
        font_size = int(size * 0.08)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Draw semi-transparent overlay
    overlay = Image.new('RGBA', (size, size), (0, 0, 0, 100))
    img.paste(overlay, (0, 0), overlay)

    # Text color
    text_color = (255, 255, 255)

    # Draw title (centered)
    title_text = title[:20] + "..." if len(title) > 20 else title
    bbox = draw.textbbox((0, 0), title_text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (size - text_width) // 2
    y = size // 3

    draw.text((x, y), title_text, fill=text_color, font=font)

    # Draw author (smaller, lower)
    author_text = author[:20] + "..." if len(author) > 20 else author
    try:
        small_font = ImageFont.truetype("arial.ttf", int(font_size * 0.7))
    except:
        small_font = font

    bbox = draw.textbbox((0, 0), author_text, font=small_font)
    text_width = bbox[2] - bbox[0]
    x = (size - text_width) // 2
    y = size * 2 // 3

    draw.text((x, y), author_text, fill=text_color, font=small_font)

    # Save
    img.save(str(output_path), 'PNG')
    return output_path


def get_or_create_cover(audiobook_id: str, title: str, author: str, covers_dir: Path) -> Path:
    """Get existing cover or create a new one"""
    cover_path = covers_dir / f"{audiobook_id}.png"

    if not cover_path.exists():
        generate_cover(title, author, cover_path)

    return cover_path
