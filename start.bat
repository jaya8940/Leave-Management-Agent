@echo off
title AI-Powered Leave Management Agent
echo.
echo  ============================================
echo   AI-Powered Leave Management Agent
echo   Starting backend and frontend servers...
echo  ============================================
echo.

:: Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

:: Check for Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)

:: Install Python dependencies
echo [1/3] Installing Python dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)
echo       Done!

:: Install frontend dependencies (if needed)
echo [2/3] Checking frontend dependencies...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo       Installing npm packages...
    call npm install --silent
)
echo       Done!

:: Start backend server
echo [3/3] Starting servers...
echo.
echo  Backend:  http://localhost:5000
echo  Frontend: http://localhost:5173
echo.
echo  Press Ctrl+C to stop both servers.
echo  ============================================
echo.

cd /d "%~dp0backend"
start "Leave Agent Backend" cmd /c "python app.py"

:: Give the backend a moment to start
timeout /t 2 /nobreak >nul

:: Start frontend dev server
cd /d "%~dp0frontend"
call npm run dev
