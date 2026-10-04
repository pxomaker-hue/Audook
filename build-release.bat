@echo off
REM Audook - build des releases (installeur Windows NSIS + APK Android signe)
REM Double-clic, ou depuis un terminal :
REM   build-release.bat                 installeur Windows + APK
REM   build-release.bat -SkipAndroid    seulement l'installeur Windows
REM   build-release.bat -SkipWindows    seulement l'APK
REM   build-release.bat -RunTests       lance les tests avant de construire
REM Resultat dans le dossier release\ (la logique est dans build-release.ps1).
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-release.ps1" %*
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% neq 0 (
    echo ECHEC du build ^(code %EXITCODE%^). Voir les messages ci-dessus.
) else (
    echo Build termine : voir le dossier release\
)
pause
exit /b %EXITCODE%
