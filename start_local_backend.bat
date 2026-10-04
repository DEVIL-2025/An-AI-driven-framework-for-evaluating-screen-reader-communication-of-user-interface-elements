@echo off
title Accessibility Auditor - Local Engine
echo ========================================================
echo Starting NVDA Accessibility Backend and Cloudflare Tunnel
echo ========================================================

:: Check if NVDA is running
tasklist /FI "IMAGENAME eq nvda.exe" 2>NUL | find /I /N "nvda.exe">NUL
if "%ERRORLEVEL%"=="1" (
    echo [WARNING] NVDA is not running! Please start NVDA and open Speech Viewer.
)

:: Start Backend in a new window
echo Starting FastAPI Backend on port 8000...
start "FastAPI Backend" cmd /k "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1"

:: Wait 3 seconds for backend to initialize
timeout /t 3 /nobreak >nul

:: Start Cloudflare Tunnel
echo Starting Cloudflare Tunnel...
echo Copy the https://xxxx.trycloudflare.com URL below into your Vercel VITE_API_BASE_URL setting:
echo.
cloudflared tunnel --url http://127.0.0.1:8000
