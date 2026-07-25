@echo off
:: Build script for Audook
:: This script creates a Windows installer using PyInstaller

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
 echo Error: Python is not installed or not in PATH
 pause
 exit /b 1
)

:: Check if PyInstaller is installed
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
 echo Installing PyInstaller...
 pip install pyinstaller
)

:: Create dist directory
if not exist dist mkdir dist

:: Build the application
echo Building Audook...
python build_spec.py

:: Check if build succeeded
if errorlevel 1 (
 echo Error: Build failed
 pause
 exit /b 1
)

:: Create installer using Inno Setup (if available)
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
 echo Creating installer...
 "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /Qp installer.iss
 
 if errorlevel 1 (
 echo Warning: Inno Setup not available, skipping installer creation
 )
) else (
 echo Inno Setup not found, skipping installer creation
 echo You can manually create an installer using the dist/Audook.exe file
)

echo Build complete!
echo The executable is in the dist/ folder
pause
