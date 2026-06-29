@echo off
echo ================================
echo  World Cup 2026 Prediction App
echo ================================
echo.

echo [1/2] Starting Backend...
cd /d "%~dp0backend"
start "WC26-Backend" cmd /c "C:\Users\MECHREUO\.workbuddy\binaries\python\versions\3.13.12\python.exe run.py"
echo    Backend starting on http://localhost:8001

echo [2/2] Starting Frontend...
cd /d "%~dp0frontend"
start "WC26-Frontend" cmd /c "npx vite --host --port 5173"
echo    Frontend starting on http://localhost:5173

echo.
echo ================================
echo  Both services are starting!
echo  Frontend: http://localhost:5173
echo  Backend:  http://localhost:8001
echo  API Docs:  http://localhost:8001/docs
echo ================================
echo.
echo Press any key to stop all services...
pause >nul

taskkill /FI "WINDOWTITLE eq WC26-Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq WC26-Frontend*" /F >nul 2>&1
echo Services stopped.
