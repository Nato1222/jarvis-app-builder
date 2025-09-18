@echo off
echo Starting Jarvis App Builder System...

echo.
echo [1/3] Starting Generator Service...
start "Generator Service" cmd /k "cd generator && npm install && npm run dev"

echo.
echo [2/3] Starting Dashboard...
start "Dashboard" cmd /k "cd dashboard && npm install && npm run dev"

echo.
echo [3/3] Starting Backend API...
start "Backend API" cmd /k "cd JarvisOne && python -m uvicorn main:app --reload --port 8000"

echo.
echo All services starting...
echo - Generator Service: http://localhost:3001
echo - Dashboard: http://localhost:3000
echo - Backend API: http://localhost:8000
echo.
echo Press any key to exit...
pause > nul
