@echo off
echo ========================================================
echo Launching Personalized AI Journal (Backend + Frontend)
echo ========================================================

start "AI Journal - Backend (FastAPI)" cmd /c "%~dp0run_backend.bat"
timeout /t 2 >nul
start "AI Journal - Frontend (Vite)" cmd /c "%~dp0run_frontend.bat"

echo.
echo Both servers are launching:
echo   - Backend:  http://localhost:8000 (Docs at /docs)
echo   - Frontend: http://localhost:3000
echo.
