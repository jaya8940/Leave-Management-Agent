@echo off
title Stopping Leave Management Agent
echo.
echo  ============================================
echo   Stopping AI-Powered Leave Management Agent
echo  ============================================
echo.

:: Kill Python (Flask backend on port 5000)
echo [1/2] Stopping backend server (Python/Flask)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo       Done!

:: Kill Node (Vite frontend on port 5173)
echo [2/2] Stopping frontend server (Node/Vite)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo       Done!

echo.
echo  All servers stopped.
echo  ============================================
echo.
pause
