@echo off
REM Start local backend + static hosting for Slide Voice Maker
REM Access: http://127.0.0.1:8000/index.html

cd /d "%~dp0"

echo ===============================================
echo  Slide Voice Maker - Local Backend Preview
echo ===============================================
echo.
echo Starting FastAPI server (src/server.py)...
echo.
echo Access URL: http://127.0.0.1:8000/index.html
echo Press Ctrl+C to stop the server.
echo.

py -3.10 -m uvicorn src.server:app --host 127.0.0.1 --port 8000
