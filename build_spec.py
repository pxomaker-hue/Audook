#!/usr/bin/env python3
"""
Spécification de build PyInstaller pour Audook

Utilisation :
 python build_spec.py
 
Cela créera un exécutable Windows autonome dans le dossier dist/
"""

from PyInstaller.__main__ import run

if __name__ == '__main__':
    from pathlib import Path

    # Chemin du répertoire courant
    project_dir = Path(__file__).parent.absolute()

    opts = [
        str(project_dir / 'main.py'),
        '--name=Audook',
        '--windowed',
        '--onefile',
        f'--icon={project_dir / "assets/icons/audook.ico"}',
        '--clean',
        '--noconfirm',
        f'--distpath={project_dir / "dist"}',
        f'--workpath={project_dir / "build"}',
        f'--specpath={project_dir / "build"}',
        f'--add-data={project_dir / "assets"}{chr(59)}assets',
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
