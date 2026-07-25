@echo off
REM Audook Development Launcher for Windows
REM This script starts both the React dev server and Python backend

echo Starting Audook Development Environment...
echo.

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing Node.js dependencies...
    call npm install
    if errorlevel 1 (
        echo Failed to install npm dependencies
        pause
        exit /b 1
    )
)

REM Start Flask backend in a new window
echo Starting Flask backend on http://127.0.0.1:5000...
start "Audook Backend" cmd /k python audook_backend.py

REM Wait a moment for Flask to start
timeout /t 3 /nobreak

REM Start React dev server
echo Starting React dev server on http://localhost:3000...
call npm run react-start

REM If we get here, React stopped
pause
