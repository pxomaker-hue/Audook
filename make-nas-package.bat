@echo off
REM Cree release\Audook-NAS-<version>.zip, a copier sur le NAS (voir LISEZMOI-NAS.txt dans le zip).
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\make-nas-package.ps1"
if errorlevel 1 ( echo ECHEC. & pause & exit /b 1 )
pause
