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

title PortableAI Launcher

:menu
cls

echo ====================================
echo   PORTABLEAI LAUNCHER
echo ====================================
echo.
echo Current setup: local ^| auto-detect
echo.
echo 1) PortableAI Custom UI
echo 2) llama.cpp Built-in UI
echo 3) Start local GGUF model (shared llama-server)
echo 4) Start with OpenAI
echo 5) Start with Gemini
echo 6) Start with DeepSeek
echo 7) Start with OpenRouter
echo 8) Start with custom endpoint
echo 9) Exit
echo.
set /p "CHOICE=Choose an option [1-9]: "

if "%CHOICE%"=="1" echo Open PortableAI Custom UI: http://127.0.0.1:9000 & start "" http://127.0.0.1:9000 & timeout /t 2 >nul & goto :menu
if "%CHOICE%"=="2" echo Open llama.cpp Built-in UI: http://127.0.0.1:8080 & start "" http://127.0.0.1:8080 & timeout /t 2 >nul & goto :menu
if "%CHOICE%"=="3" goto :local
if "%CHOICE%"=="4" set "PROVIDER=openai" & goto :remote
if "%CHOICE%"=="5" set "PROVIDER=gemini" & goto :remote
if "%CHOICE%"=="6" set "PROVIDER=deepseek" & goto :remote
if "%CHOICE%"=="7" set "PROVIDER=openrouter" & goto :remote
if "%CHOICE%"=="8" set "PROVIDER=custom" & goto :remote
if "%CHOICE%"=="9" exit /b 0

echo.
echo Invalid option. Press any key to continue...
pause >nul
goto :menu

:local
cls
echo ====================================
echo   STARTING LOCAL MODEL
echo ====================================
echo.
for /f "delims=" %%a in ('dir /b models\*.gguf 2^>nul') do echo   - %%a
echo.
set /p "SELECTED_MODEL=Enter model filename or press Enter for auto-select: "
if "%SELECTED_MODEL%"=="" (
    %PY_CMD% app\server.py "" local
) else (
    if exist "models\%SELECTED_MODEL%" (
        %PY_CMD% app\server.py "%SELECTED_MODEL%" local
    ) else (
        echo Model not found: %SELECTED_MODEL%
        echo Falling back to the default local model.
        %PY_CMD% app\server.py "" local
    )
)

echo.
echo PortableAI is running in this terminal.
echo Press Ctrl+C to stop it.
echo.
pause
exit /b 0

:remote
cls
echo ====================================
echo   STARTING %PROVIDER%
echo ====================================
echo.
set /p "MODEL_NAME=Model name: "
if "%MODEL_NAME%"=="" set "MODEL_NAME=gpt-4o-mini"
set /p "API_KEY=API key: "
if "%PROVIDER%"=="openai" set "BASE_URL=https://api.openai.com/v1"
if "%PROVIDER%"=="gemini" set "BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai"
if "%PROVIDER%"=="deepseek" set "BASE_URL=https://api.deepseek.com/v1"
if "%PROVIDER%"=="openrouter" set "BASE_URL=https://openrouter.ai/api/v1"
if "%PROVIDER%"=="custom" set /p "BASE_URL=Base URL (example: https://your-endpoint/v1): "
if "%PROVIDER%"=="custom" if "%BASE_URL%"=="" set "BASE_URL=https://api.openai.com/v1"

echo.
echo Provider: %PROVIDER%
echo Model: %MODEL_NAME%
echo Base URL: %BASE_URL%
echo.
%PY_CMD% app\server.py "%MODEL_NAME%" "%PROVIDER%" "%API_KEY%" "%BASE_URL%"

echo.
echo PortableAI is running in this terminal.
echo Press Ctrl+C to stop it.
echo.
pause
exit /b 0
