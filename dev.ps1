# Audook Development Launcher for Windows PowerShell
# Usage: .\dev.ps1

Write-Host "Starting Audook Development Environment..." -ForegroundColor Green
Write-Host ""

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing Node.js dependencies..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install npm dependencies" -ForegroundColor Red
        exit 1
    }
}

# Start Flask backend in a new window
Write-Host "Starting Flask backend on http://127.0.0.1:5000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python audook_backend.py" -WindowStyle Normal

# Wait for Flask to start
Write-Host "Waiting for backend to start..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# Start React dev server
Write-Host "Starting React dev server on http://localhost:3000..." -ForegroundColor Yellow
npm run react-start
