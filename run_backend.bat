@echo off
echo Starting AI Journal Backend (FastAPI)...
cd /d "%~dp0backend"
call venv\Scripts\activate.bat
uvicorn app.main:app --reload --port 8000
pause
