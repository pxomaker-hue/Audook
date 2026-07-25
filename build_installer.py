#!/usr/bin/env python3
"""
Script tout-en-un pour construire Audook et créer un installateur

Utilisation :
 python build_installer.py

Ce script va :
1. Générer l'icône si elle n'existe pas
2. Construire l'exécutable avec PyInstaller
3. Créer un installateur avec Inno Setup (si disponible)

Options :
 --no-icon    : Ne pas générer l'icône
 --no-installer : Ne pas créer l'installateur
 --test       : Tester la construction sans créer de fichiers finaux
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(cmd, cwd=None, capture_output=True):
 """Exécuter une commande et retourner le résultat"""
 print(f"➡ {cmd}")
 try:
 result = subprocess.run(
 cmd, 
 shell=True, 
 cwd=cwd, 
 capture_output=capture_output,
 text=True
 )
 if result.returncode != 0:
 print(f"❌ Erreur : {result.stderr}")
 return False
 return True
 except Exception as e:
 print(f"❌ Exception : {e}")
 return False


def generate_icon():
 """Générer l'icône Audook"""
 icon_path = Path("assets/icons/audook.ico")
 
 if icon_path.exists():
 print(f"✅ Icône existante : {icon_path}")
 return True
 
 print("🎨 Génération de l'icône...")
 
 # Vérifier si Pillow est installé
 try:
 from PIL import Image, ImageDraw
 except ImportError:
 print("📦 Installation de Pillow...")
 if not run_command("pip install pillow -q"):
 print("❌ Échec de l'installation de Pillow")
 return False
 
 # Créer l'icône
 try:
 from PIL import Image, ImageDraw
 
 size = 256
 img = Image.new('RGBA', (size, size), (22, 33, 62, 255))
 draw = ImageDraw.Draw(img)
 
 # Dessiner un livre
 cover_width, cover_height = 120, 160
 cover_x, cover_y = (size - cover_width) // 2, (size - cover_height) // 2
 
 # Couverture rose (#e94560)
 cover_color = (233, 69, 96, 255)
 draw.rectangle([cover_x, cover_y, cover_x + cover_width, cover_y + cover_height], 
 fill=cover_color, outline=(0, 0, 0, 255), width=4)
 
 # Pages blanches
 page_color = (248, 249, 250, 255)
 page_x = cover_x + cover_width - 10
 draw.rectangle([page_x, cover_y, page_x + 80, cover_y + cover_height], 
 fill=page_color, outline=(200, 200, 200, 255), width=2)
 
 # Ligne de séparation
 draw.line([(page_x + 5, cover_y), (page_x + 5, cover_y + cover_height)], 
 fill=(150, 150, 150, 255), width=1)
 
 # Sauvegarder en .ico
 icon_path.parent.mkdir(parents=True, exist_ok=True)
 img.save(str(icon_path), format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
 
 print(f"✅ Icône générée : {icon_path}")
 return True
 
 except Exception as e:
 print(f"❌ Échec de la génération de l'icône : {e}")
 return False


def build_executable():
 """Construire l'exécutable avec PyInstaller"""
 print("\n🏗️ Construction de l'exécutable...")
 
 # Vérifier si PyInstaller est installé
 try:
 import PyInstaller
 except ImportError:
 print("📦 Installation de PyInstaller...")
 if not run_command("pip install pyinstaller"):
 print("❌ Échec de l'installation de PyInstaller")
 return False
 
 # Exécuter PyInstaller
 if not run_command("python build_spec.py"):
 print("❌ Échec de la construction")
 return False
 
 # Vérifier si l'exécutable a été créé
 exe_path = Path("dist/Audook.exe")
 if not exe_path.exists():
 print("❌ Exécutable non trouvé : dist/Audook.exe")
 return False
 
 print(f"✅ Exécutable créé : {exe_path}")
 return True


def build_installer():
 """Créer l'installateur avec Inno Setup"""
 print("\n📦 Création de l'installateur...")
 
 # Vérifier si Inno Setup est installé
 inno_setup_path = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
 if not Path(inno_setup_path).exists():
 print("⚠️ Inno Setup non trouvé à : " + inno_setup_path)
 print("   Téléchargez-le ici : https://jrsoftware.org/isinfo.php")
 print("   Ou installez-le et réessayez.")
 return False
 
 # Vérifier si l'exécutable existe
 exe_path = Path("dist/Audook.exe")
 if not exe_path.exists():
 print("❌ Exécutable manquant : dist/Audook.exe")
 return False
 
 # Exécuter Inno Setup
 if not run_command(f'"{inno_setup_path}" /Qp installer.iss'):
 print("❌ Échec de la création de l'installateur")
 return False
 
 # Vérifier si l'installateur a été créé
 installer_path = Path("dist/Audook_Setup.exe")
 if not installer_path.exists():
 print("❌ Installateur non trouvé : dist/Audook_Setup.exe")
 return False
 
 print(f"✅ Installateur créé : {installer_path}")
 return True


def main():
 """Fonction principale"""
 print("=" * 60)
 print("Audook - Script de build et d'installation")
 print("=" * 60)
 print()
 
 # Analyser les arguments
 no_icon = "--no-icon" in sys.argv
 no_installer = "--no-installer" in sys.argv
 test_mode = "--test" in sys.argv
 
 # Étape 1 : Générer l'icône
 if not no_icon:
 if not generate_icon():
 if not test_mode:
 print("\n❌ Arrêt en raison d'une erreur")
 sys.exit(1)
 else:
 print("⚠️ Mode test : continuation sans icône")
 
 # Étape 2 : Construire l'exécutable
 if not build_executable():
 if not test_mode:
 print("\n❌ Arrêt en raison d'une erreur")
 sys.exit(1)
 else:
 print("⚠️ Mode test : continuation sans exécutable")
 
 # Étape 3 : Créer l'installateur
 if not no_installer:
 if not build_installer():
 print("⚠️ Impossible de créer l'installateur (Inno Setup non installé)")
 
 # Résumé
 print("\n" + "=" * 60)
 print("Résumé du build")
 print("=" * 60)
 
 exe_path = Path("dist/Audook.exe")
 installer_path = Path("dist/Audook_Setup.exe")
 
 if exe_path.exists():
 print(f"✅ Exécutable : {exe_path}")
 else:
 print("❌ Exécutable : Non créé")
 
 if installer_path.exists():
 print(f"✅ Installateur : {installer_path}")
 else:
 print("⚠️ Installateur : Non créé (Inno Setup requis)")
 
 print("\n🎉 Build terminé !")
 
 if not installer_path.exists():
 print("\nPour créer l'installateur :")
 print("1. Téléchargez Inno Setup : https://jrsoftware.org/isinfo.php")
 print("2. Installez-le")
 print("3. Exécutez : python build_installer.py")
 
 if not test_mode:
 print("\nAppuyez sur Entrée pour quitter...")
 input()


if __name__ == "__main__":
 main()
