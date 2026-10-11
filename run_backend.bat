@echo off
title OpsPilot Backend Service
cd /d "%~dp0backend"
echo ===================================================
echo   Starting OpsPilot Core Backend (FastAPI)
echo   URL: http://127.0.0.1:8000
echo   API Docs: http://127.0.0.1:8000/api/v1/docs
echo ===================================================
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause
