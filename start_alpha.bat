@echo off
title Alpha Omega System - Starting...
color 0A

echo ============================================================
echo           ALPHA OMEGA SYSTEM v2.0.0
echo     Voice-Activated PC Control System
echo ============================================================
echo.

echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.9+
    pause
    exit /b 1
)
echo [OK] Python found

echo.
echo [2/4] Checking directories...
if not exist "logs" mkdir logs
if not exist "data" mkdir data
echo [OK] Directories ready

echo.
echo [3/4] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [WARNING] Some dependencies may have failed to install
) else (
    echo [OK] Dependencies installed
)

echo.
echo [4/4] Starting system...
echo ============================================================
echo.
echo Starting Alpha Omega...
echo API Server: http://localhost:8000
echo WebSocket: ws://localhost:8000/ws
echo.
echo Press Ctrl+C to stop
echo ============================================================
echo.

python run_alpha.py

pause
