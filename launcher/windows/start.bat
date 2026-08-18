@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

REM ========================================================
REM AUTO-CACHE CLEARING FOR PORTABILITY
REM ========================================================
REM Clear old path caches so the app works on different PCs

if exist "app\__pycache__" (
    echo Clearing Python cache...
    rmdir /s /q "app\__pycache__" 2>nul
)

REM ========================================================
REM PYTHON DETECTION
REM ========================================================

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=py"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set "PY_CMD=python"
    ) else (
        echo Python was not found on PATH.
        echo Install Python 3 or ensure "py" is available.
        echo.
        pause
        exit /b 1
    )
)

title PortableAI - Llama Server

REM ========================================================
REM START LLAMA.CPP WITH BUILT-IN UI
REM ========================================================

cls
echo ====================================
echo   PORTABLE LOCAL AI
echo ====================================
echo.
echo Starting llama.cpp server with built-in UI...
echo.

%PY_CMD% app\server.py

REM If we get here, the server exited
echo.
echo Server stopped.
pause
exit /b 0
