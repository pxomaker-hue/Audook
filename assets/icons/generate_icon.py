#!/usr/bin/env python3
"""
Génère audook.ico à partir du logo source audook.png.

Installation :
 pip install pillow

Exécution :
 python generate_icon.py
"""

from PIL import Image
from pathlib import Path

# Resolved relative to this script's own location, not the current working
# directory - otherwise this only worked when run from the project root
# (`python assets/icons/generate_icon.py`) and failed with a file-not-found
# when run from inside assets/icons/ itself (`python generate_icon.py`).
ICONS_DIR = Path(__file__).parent
SOURCE = ICONS_DIR / "audook 2.png"
ICO_PATH = ICONS_DIR / "audook.ico"
# Fraction of the square canvas the artwork occupies - leaves a small margin
# so the icon doesn't look cramped at small sizes (taskbar/tray). The new
# source is already a fully-composed icon (rounded square background, own
# internal padding, no transparent border) rather than bare artwork on a
# transparent canvas, so no extra shrink is needed here - 1.0 uses it as-is.
CONTENT_SCALE = 1.0

img = Image.open(SOURCE).convert("RGBA")

# Crop to the actual artwork (source has only a sliver of transparent border)
bbox = img.getbbox()
if bbox:
    img = img.crop(bbox)

# Pad to a square canvas, centered, with a small margin on all sides
side = max(img.width, img.height)
canvas_size = round(side / CONTENT_SCALE)
canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
offset = ((canvas_size - img.width) // 2, (canvas_size - img.height) // 2)
canvas.paste(img, offset, img)

icon_sizes = [16, 32, 48, 64, 128, 256]
resized_images = [canvas.resize((s, s), Image.LANCZOS) for s in icon_sizes]
resized_images[-1].save(ICO_PATH, format="ICO", sizes=[(s, s) for s in icon_sizes])

print(f"Icone generee : {ICO_PATH}")
