@echo off
echo Starting Discord Log Dashboard...
echo.

echo [1/2] Starting Flask API on port 5000...
start "Flask API" cmd /k "python api.py"

timeout /t 3 /nobreak > nul

echo [2/2] Starting React development server...
start "React App" cmd /k "npm start"

echo.
echo Dashboard is starting!
echo API: http://localhost:5000
echo Web: http://localhost:3000
echo.
