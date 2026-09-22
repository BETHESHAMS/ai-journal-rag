@echo off
set "PATH=C:\Program Files\nodejs;%PATH%"
echo Starting AI Journal Frontend (Vite + React)...
cd /d "%~dp0frontend"
call npm.cmd run dev
pause
