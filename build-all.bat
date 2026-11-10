@echo off
REM Audook - release complete en une commande (double-clic ou depuis un terminal) :
REM   1. cle de signature des mises a jour (creee seulement si absente)
REM   2. installeur Windows (.exe) + APK Android signe (build-release.ps1)
REM   3. manifeste signe release\latest.json + latest.json.sig
REM S'arrete a la premiere erreur. Ne publie RIEN : envoyez ensuite les fichiers de
REM release\ sur le depot de mises a jour (le manifeste en dernier).
REM Options : -SkipAndroid / -SkipWindows / -RunTests (logique dans scripts\build-all.ps1).
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build-all.ps1" %*
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% neq 0 (
    echo ECHEC ^(code %EXITCODE%^) : arret du processus, rien n'a ete publie. Voir les messages ci-dessus.
)
pause
exit /b %EXITCODE%
