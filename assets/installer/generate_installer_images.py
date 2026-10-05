#!/usr/bin/env python3
"""
Génère les images de l'installeur Windows (NSIS) aux couleurs d'Audook.

  installerSidebar.bmp  164x314  page d'accueil / de fin (installeur et désinstalleur)
  installerHeader.bmp   150x57   bandeau des pages intermédiaires

Le logo vient de audook.ico (taille 256). Les polices sont celles de Windows
(Segoe UI) ; les BMP générés sont versionnés, ce script n'est à relancer que pour
changer le design :  python assets/installer/generate_installer_images.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
ICON = HERE.parent / "icons" / "audook.ico"

INK = (23, 22, 27)          # --accent-ink / --secondary
YELLOW = (255, 198, 41)     # --accent / --primary
SURFACE = (255, 255, 255)
MUTED = (170, 168, 176)
FONTS = Path("C:/Windows/Fonts")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for candidate in (FONTS / name, FONTS / "segoeui.ttf"):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def logo(size: int) -> Image.Image:
    ico = Image.open(ICON)
    ico.size = max(ico.info.get("sizes", {(256, 256)}))   # largest frame
    return ico.convert("RGBA").resize((size, size), Image.LANCZOS)


def paste_logo(canvas: Image.Image, size: int, xy):
    img = logo(size)
    canvas.paste(img, xy, img)


def sidebar() -> Image.Image:
    w, h = 164, 314
    im = Image.new("RGB", (w, h), INK)
    d = ImageDraw.Draw(im)
    # sound-wave bars along the bottom, fading from yellow to the background
    bars = [18, 34, 52, 28, 64, 40, 22, 58, 30, 46, 20, 36]
    bw, gap = 8, 5
    x0 = (w - (len(bars) * bw + (len(bars) - 1) * gap)) // 2
    base = 292
    for i, bh in enumerate(bars):
        x = x0 + i * (bw + gap)
        shade = tuple(int(INK[c] + (YELLOW[c] - INK[c]) * (0.35 + 0.65 * bh / 64)) for c in range(3))
        d.rounded_rectangle([x, base - bh, x + bw, base], radius=4, fill=shade)
    # logo, wordmark, tagline
    paste_logo(im, 92, ((w - 92) // 2, 34))
    title = "Audook"
    f = font("segoeuib.ttf", 28)
    tw = d.textlength(title, font=f)
    d.text(((w - tw) / 2, 140), title, font=f, fill=SURFACE)
    d.rounded_rectangle([(w - 36) // 2, 182, (w + 36) // 2, 185], radius=2, fill=YELLOW)
    f2 = font("segoeui.ttf", 12)
    for i, line in enumerate(("Votre bibliothèque", "d'audiolivres")):
        lw = d.textlength(line, font=f2)
        d.text(((w - lw) / 2, 198 + i * 18), line, font=f2, fill=MUTED)
    return im


def header() -> Image.Image:
    w, h = 150, 57
    im = Image.new("RGB", (w, h), SURFACE)
    d = ImageDraw.Draw(im)
    paste_logo(im, 40, (w - 40 - 8, (h - 40) // 2))
    d.rectangle([0, h - 3, w, h], fill=YELLOW)
    f = font("segoeuib.ttf", 17)
    d.text((10, 15), "Audook", font=f, fill=INK)
    return im


if __name__ == "__main__":
    sidebar().save(HERE / "installerSidebar.bmp", "BMP")
    header().save(HERE / "installerHeader.bmp", "BMP")
    print("ok:", ", ".join(p.name for p in sorted(HERE.glob("*.bmp"))))
