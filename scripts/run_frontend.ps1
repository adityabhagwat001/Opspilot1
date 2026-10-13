# Run OpsPilot React Vite Frontend
$ErrorActionPreference = "Stop"
Write-Host "Starting OpsPilot Enterprise Frontend..." -ForegroundColor Cyan

Set-Location -Path "frontend"
npm run dev
