# Run OpsPilot FastAPI Backend with Uvicorn
$ErrorActionPreference = "Stop"
Write-Host "Starting OpsPilot Enterprise Backend..." -ForegroundColor Cyan

$env:PYTHONPATH = "backend;."
& ".\.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend
