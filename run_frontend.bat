@echo off
title OpsPilot SRE Frontend Console
cd /d "%~dp0frontend"
echo ===================================================
echo   Starting OpsPilot SRE Web Console (Vite + React)
echo   URL: http://localhost:5173
echo ===================================================
npm run dev
pause
