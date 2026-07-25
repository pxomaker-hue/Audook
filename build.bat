@echo off
:: Script de build pour Audook
:: Ce script crée un installateur Windows en utilisant PyInstaller

:: Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
 echo Erreur : Python n'est pas installé ou n'est pas dans le PATH
 pause
 exit /b 1
)

:: Vérifier si PyInstaller est installé
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
 echo Installation de PyInstaller...
 pip install pyinstaller
)

:: Créer le dossier dist
if not exist dist mkdir dist

:: Construire l'application
echo Construction d'Audook...
python build_spec.py

:: Vérifier si la construction a réussi
if errorlevel 1 (
 echo Erreur : La construction a échoué
 pause
 exit /b 1
)

:: Créer l'installateur en utilisant Inno Setup (si disponible)
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
 echo Création de l'installateur...
 "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /Qp installer.iss
 
 if errorlevel 1 (
 echo Avertissement : Inno Setup non disponible, création de l'installateur ignorée
 )
) else (
 echo Inno Setup introuvable, création de l'installateur ignorée
 echo Vous pouvez créer manuellement un installateur en utilisant le fichier dist/Audook.exe
)

echo Construction terminée !
echo L'exécutable se trouve dans le dossier dist/
pause
