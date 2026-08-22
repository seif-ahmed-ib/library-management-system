@echo off
title LibraDesk FastAPI Server
cd /d "%~dp0backend"

echo ========================================
echo        Starting LibraDesk API
echo ========================================
echo.
echo Frontend:   http://127.0.0.1:8000/app
echo Swagger:    http://127.0.0.1:8000/docs
echo Health:     http://127.0.0.1:8000/health
echo Monitoring: http://127.0.0.1:8000/monitoring
echo.
echo Press Ctrl+C to stop the server.
echo ========================================
echo.

"%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --reload

echo.
echo Server stopped.
pause