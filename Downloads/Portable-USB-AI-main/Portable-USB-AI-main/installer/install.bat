@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0.."

title PortableAI Setup Wizard

REM Detect Python
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=py"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set "PY_CMD=python"
    ) else (
        echo.
        echo ERROR: Python 3 is required but not found.
        echo Please install Python 3 from https://python.org
        echo.
        pause
        exit /b 1
    )
)

echo.
echo ====================================
echo   PORTABLEAI SETUP WIZARD
echo ====================================
echo.
echo This script will set up PortableAI with:
echo  - Required directories
echo  - Configuration files
echo  - Optional: Model downloads
echo.
pause

REM Create necessary directories
if not exist "models" mkdir models
if not exist "data\chats" mkdir data\chats
if not exist "installer_data" mkdir installer_data

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo # PortableAI Configuration > .env
    echo CONTEXT_SIZE=4096 >> .env
    echo MAX_TOKENS=256 >> .env
    echo TEMPERATURE=0.1 >> .env
    echo PORT=9000 >> .env
    echo LLAMA_PORT=8080 >> .env
)

echo.
echo Configuration directory structure created.
echo.

REM Check for existing models
set "model_count=0"
for /f %%a in ('dir /b models\*.gguf 2^>nul') do (
    set /a model_count+=1
)

if %model_count% GTR 0 (
    echo Found %model_count% existing model(s).
    echo.
    dir models\*.gguf 2>nul
    echo.
)

REM Setup menu
:setup_menu
cls
echo ====================================
echo   PORTABLEAI SETUP
echo ====================================
echo.
echo 1) Start PortableAI (use existing models)
echo 2) Download Qwen 3 4B (recommended - lightweight)
echo 3) Enter custom HuggingFace model URL
echo 4) View installed models
echo 5) Exit setup
echo.
set /p "SETUP_CHOICE=Choose an option [1-5]: "

if "%SETUP_CHOICE%"=="1" goto :start_app
if "%SETUP_CHOICE%"=="2" goto :download_default
if "%SETUP_CHOICE%"=="3" goto :custom_model
if "%SETUP_CHOICE%"=="4" goto :list_models
if "%SETUP_CHOICE%"=="5" goto :exit_setup
echo Invalid option. Press any key to continue...
pause >nul
goto :setup_menu

:download_default
cls
echo.
echo Downloading Qwen 3 4B (Fast & Lightweight)...
echo This model is optimized for speed and efficiency.
echo.
set "MODEL_URL=https://huggingface.co/Qwen/Qwen3-4B-Instruct-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf"
set "MODEL_NAME=Qwen3-4B-Q4_K_M.gguf"
goto :download_model

:custom_model
cls
echo.
set /p "MODEL_URL=Paste HuggingFace model URL (e.g., https://huggingface.co/...): "
if "%MODEL_URL%"=="" (
    echo Cancelled.
    timeout /t 2 >nul
    goto :setup_menu
)

for %%A in ("%MODEL_URL:\=/%") do set "MODEL_NAME=%%~nxA"
if "%MODEL_NAME%"=="" set "MODEL_NAME=custom-model.gguf"

echo.
echo Model name: %MODEL_NAME%
echo.

:download_model
if exist "models\%MODEL_NAME%" (
    echo.
    echo Model already exists: models\%MODEL_NAME%
    echo.
    pause
    goto :setup_menu
)

echo Downloading %MODEL_NAME%...
echo.
echo Note: Large models can take 30+ minutes.
echo Do NOT close this window.
echo.

%PY_CMD% -c "
import urllib.request
import os
url = r'%MODEL_URL%'
file_path = os.path.join('models', r'%MODEL_NAME%')
try:
    print(f'Downloading from: {url}')
    print(f'Saving to: {file_path}')
    urllib.request.urlretrieve(url, file_path, reporthook=lambda a,b,c: print(f'\rProgress: {(100*a*b//c)}%%', end=''))
    print('\nDownload complete!')
except Exception as e:
    print(f'Error: {e}')
    exit(1)
"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Model downloaded successfully!
    echo.
    pause
    goto :setup_menu
) else (
    echo.
    echo Download failed. Check your internet connection.
    echo.
    pause
    goto :setup_menu
)

:list_models
cls
echo.
echo ====================================
echo   INSTALLED MODELS
echo ====================================
echo.
if exist models (
    dir models\*.gguf 2>nul || echo No models found.
) else (
    echo Models directory not found.
)
echo.
pause
goto :setup_menu

:start_app
cls
echo.
echo ====================================
echo   STARTING PORTABLEAI
echo ====================================
echo.
echo To access PortableAI:
echo   Web UI: http://127.0.0.1:9000
echo.
echo Keep this terminal open while using PortableAI.
echo Press Ctrl+C to stop the server.
echo.
timeout /t 3 >nul

call start.bat
goto :exit_setup

:exit_setup
echo.
echo Setup complete. Run start.bat to start PortableAI.
echo.
exit /b 0
