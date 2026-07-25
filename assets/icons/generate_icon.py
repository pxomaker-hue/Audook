#!/usr/bin/env python3
"""
Script pour générer une icône basique pour Audook
Utilise Pillow pour créer un fichier .ico

Installation :
 pip install pillow

Exécution :
 python generate_icon.py
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Créer un dossier pour l'icône si nécessaire
os.makedirs("assets/icons", exist_ok=True)

# Créer une image carrée (256x256 pour une bonne qualité)
size = 256
img = Image.new('RGBA', (size, size), (22, 33, 62, 255))  # Fond bleu foncé (#1a1a2e)

# Dessiner un livre ouvert (icône basique)
draw = ImageDraw.Draw(img)

# Couleurs
book_color = (233, 69, 96, 255)  # Rose (#e94560)
page_color = (248, 249, 250, 255)  # Blanc cassé
text_color = (22, 33, 62, 255)  # Bleu foncé

# Dessiner le livre (rectangle avec une couverture)
# Couverture du livre
cover_width = 120
cover_height = 160
cover_x = (size - cover_width) // 2
cover_y = (size - cover_height) // 2

# Dessiner la couverture
draw.rectangle([cover_x, cover_y, cover_x + cover_width, cover_y + cover_height], fill=book_color, outline=(0, 0, 0, 255), width=4)

# Dessiner les pages (à droite de la couverture)
page_width = 80
page_x = cover_x + cover_width - 10
draw.rectangle([page_x, cover_y, page_x + page_width, cover_y + cover_height], fill=page_color, outline=(200, 200, 200, 255), width=2)

# Dessiner une ligne pour séparer les pages
draw.line([(page_x + 5, cover_y), (page_x + 5, cover_y + cover_height)], fill=(150, 150, 150, 255), width=1)

# Ajouter un petit logo "A" au centre de la couverture
center_x = cover_x + cover_width // 2
center_y = cover_y + cover_height // 2

# Dessiner un "A" stylisé
try:
 # Essayer avec une police par défaut
 font = ImageFont.truetype("arial.ttf", 60)
except:
 font = ImageFont.load_default()

draw.text((center_x - 25, center_y - 30), "A", fill=page_color, font=font)

# Sauvegarder en .ico (plusieurs tailles)
icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
resized_images = []

for icon_size in icon_sizes:
 resized = img.resize(icon_size, Image.LANCZOS)
 resized_images.append(resized)

# Sauvegarder le fichier .ico
ico_path = "assets/icons/audook.ico"
resized_images[0].save(ico_path, format='ICO', sizes=[s for s in icon_sizes])

print(f"✅ Icône générée avec succès : {ico_path}")
print("\nPour l'utiliser avec PyInstaller, ajoutez :")
print("  --icon=assets/icons/audook.ico")
