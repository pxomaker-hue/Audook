@echo off
REM Audook - release complete en une commande (double-clic ou depuis un terminal) :
REM   1. cle de signature des mises a jour (creee seulement si absente)
REM   2. installeur Windows (.exe) + APK Android signe (build-release.ps1)
REM   3. manifeste signe release\latest.json + latest.json.sig
REM S'arrete a la premiere erreur. Ne publie RIEN : envoyez ensuite les 4 fichiers
REM de release\ sur le depot de mises a jour (le manifeste en dernier).
REM Options : -SkipAndroid / -SkipWindows / -RunTests sont transmises a build-release.ps1.
setlocal
cd /d "%~dp0"

set PY=python
where python >nul 2>nul || set PY=py -3
%PY% --version >nul 2>nul || ( echo ERREUR : Python 3 introuvable dans le PATH. & goto :fail )

if exist release-signing.key (
    echo [1/3] Cle de signature deja presente.
) else (
    echo [1/3] Creation de la cle de signature...
    %PY% scripts\release_update.py keygen || goto :fail
    echo.
    echo IMPORTANT : sauvegardez release-signing.key ^(jamais dans git^) et committez app\update_key.py
    echo avant de distribuer : la cle publique doit etre dans l'application construite ci-dessous.
)

echo.
echo [2/3] Build Windows + Android...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-release.ps1" %* || goto :fail

echo.
echo [3/3] Manifeste signe...
if exist CHANGELOG-notes.txt (
    %PY% scripts\release_update.py manifest --notes-file CHANGELOG-notes.txt || goto :fail
) else (
    %PY% scripts\release_update.py manifest || goto :fail
)

echo.
echo TERMINE. Fichiers a envoyer sur le depot de mises a jour ^(dossier release\^) :
dir /b release\Audook-Setup-*.exe release\Audook-*.apk release\latest.json release\latest.json.sig 2>nul
echo Rien n'a ete publie. Envoyez latest.json et latest.json.sig en dernier.
pause
exit /b 0

:fail
echo.
echo ECHEC : arret du processus, rien n'a ete publie. Voir les messages ci-dessus.
pause
exit /b 1
