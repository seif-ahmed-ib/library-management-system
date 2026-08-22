@echo off
title LibraDesk API Tests
cd /d "%~dp0backend"

echo ========================================
echo        LibraDesk API Test Suite
echo ========================================
echo.

"%~dp0.venv\Scripts\python.exe" -m pytest -q

echo.
echo ========================================
echo Test execution finished.
echo ========================================
pause