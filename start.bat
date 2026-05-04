@echo off
title Media Extractor Pro Runner
echo Starting Environment Check...
echo ------------------------------------------
echo [1/2] Installing required libraries...
python -m pip install fastapi uvicorn jinja2 python-multipart websockets httpx
echo.
echo [2/2] Launching server...
echo ------------------------------------------
echo Access the site at: http://127.0.0.1:8888
echo (Keep this window open while using the app)
echo.
python app.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start server.
    pause
)
pause
