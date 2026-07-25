#!/usr/bin/env python3
"""
Spécification de build PyInstaller pour Audook

Utilisation :
 python build_spec.py
 
Cela créera un exécutable Windows autonome dans le dossier dist/
"""

from PyInstaller.__main__ import run

if __name__ == '__main__':
 opts = [
 'main.py',
 '--name=Audook',
 '--windowed',
 '--onefile',
 '--icon=assets/icon.ico',
 '--clean',
 '--noconfirm',
 '--distpath=dist',
 '--workpath=build',
 '--specpath=build',
 '--add-data=assets;assets',
 '--add-data=app;app',
 '--hidden-import=PyQt6.QtCore',
 '--hidden-import=PyQt6.QtGui',
 '--hidden-import=PyQt6.QtWidgets',
 '--hidden-import=pygame',
 '--hidden-import=pygame.mixer',
 '--hidden-import=pydantic',
 '--hidden-import=httpx',
 '--hidden-import=requests',
 ]
 
 run(opts)
