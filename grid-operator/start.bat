@echo off
echo ====================================
echo   Grid Operator Game - Quick Start
echo ====================================
echo.
echo Starting Backend Server (Port 3000)...
start "Backend Server" cmd /k "node server.js"
timeout /t 2 /nobreak >nul
echo.
echo Starting Frontend Server (Port 8000)...
start "Frontend Server" cmd /k "python -m http.server 8000"
timeout /t 2 /nobreak >nul
echo.
echo ====================================
echo   Both servers are running!
echo ====================================
echo.
echo Backend:  http://localhost:3000
echo Frontend: http://localhost:8000
echo.
echo Open your browser to http://localhost:8000
echo.
echo Press any key to open the game in your browser...
pause >nul
start http://localhost:8000
