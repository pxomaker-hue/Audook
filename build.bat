@echo off
:: Script de build pour Audook
:: Ce script crée un exécutable Windows et un installateur

:: Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
 echo Erreur : Python n'est pas installé ou n'est pas dans le PATH
 pause
 exit /b 1
)

:: Installer Pillow si nécessaire (pour générer l'icône)
python -c "import PIL" >nul 2>&1
if errorlevel 1 (
 echo Installation de Pillow pour générer l'icône...
 pip install pillow -q
)

:: Générer l'icône si elle n'existe pas
if not exist assets\icons\audook.ico (
 echo Génération de l'icône...
 python assets\icons\generate_icon.py
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
echo Construction de l'exécutable Audook...
python build_spec.py

:: Vérifier si la construction a réussi
if errorlevel 1 (
 echo Erreur : La construction a échoué
 pause
 exit /b 1
)

echo Exécutable créé : dist\Audook.exe

:: Créer l'installateur avec Inno Setup (si disponible)
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
 echo Création de l'installateur...
 "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /Qp installer.iss
 
 if exist dist\Audook_Setup.exe (
 echo Installateur créé : dist\Audook_Setup.exe
 ) else (
 echo Avertissement : Inno Setup non disponible ou erreur lors de la création
 )
) else (
 echo Inno Setup introuvable, création de l'installateur ignorée
 echo Vous pouvez créer manuellement un installateur en utilisant le fichier dist/Audook.exe
)

echo ============================================
echo Build terminé avec succès !
echo ============================================
echo.
echo Fichiers générés :
echo - Exécutable : dist\Audook.exe
echo.
if exist dist\Audook_Setup.exe (
 echo - Installateur : dist\Audook_Setup.exe
)
echo.
pause
