#!/usr/bin/env python3
"""
Build script for Audook Electron application.
Compiles Python backend with PyInstaller for production use.

Usage:
  python build_electron.py
"""

import subprocess
import sys
from pathlib import Path

def main():
    project_dir = Path(__file__).parent.absolute()

    print("=" * 60)
    print("Audook Electron Build")
    print("=" * 60)

    # Step 1: Compile Python backend
    print("\n[1/2] Compiling Python backend with PyInstaller...")
    backend_opts = [
        str(project_dir / 'audook_backend.py'),
        '--name=audook_backend',
        '--onefile',
        '--console',
        f'--icon={project_dir / "assets/icons/audook.ico"}',
        '--clean',
        '--noconfirm',
        f'--distpath={project_dir / "dist/audook_backend"}',
        f'--workpath={project_dir / "build"}',
        f'--specpath={project_dir / "build"}',
        f'--add-data={project_dir / "assets"}{chr(59)}assets',
        '--hidden-import=flask',
        '--hidden-import=flask_cors',
        '--hidden-import=sqlalchemy',
        '--hidden-import=sqlalchemy.orm',
        '--hidden-import=vlc',
        '--hidden-import=requests',
    ]

    try:
        from PyInstaller.__main__ import run
        run(backend_opts)
        print("✓ Python backend compiled successfully")
    except Exception as e:
        print(f"✗ Failed to compile Python backend: {e}")
        return False

    # Step 2: Build Electron app with electron-builder
    print("\n[2/2] Building Electron application...")
    try:
        result = subprocess.run(
            ['npm', 'run', 'electron-build'],
            cwd=str(project_dir),
            check=True,
            capture_output=False
        )
        print("✓ Electron application built successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to build Electron application: {e}")
        return False

    print("\n" + "=" * 60)
    print("Build complete!")
    print("=" * 60)
    print(f"\nOutput files in: {project_dir / 'dist'}")
    print("  - dist/Audook.exe (Portable)")
    print("  - dist/Audook Setup.exe (Installer)")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
