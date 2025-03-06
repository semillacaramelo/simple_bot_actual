@echo off
@REM Ensure that batch script is executed with color support enabled
@IF NOT DEFINED __COLORS_DEFINED  powershell -Command "& {$env:__COLORS_DEFINED=1 ; cmd /V:on /E:on /C \"%~f0\"}"; & exit /b %errorlevel%
@SETLOCAL

echo Setting up Trading Bot environment...

REM --- Color definitions ---
SET COLOR_RESET=[0m
SET COLOR_CYAN=[36m
SET COLOR_GREEN=[32m
SET COLOR_YELLOW=[33m
SET COLOR_RED=[31m

REM --- Icon definitions ---
SET ICON_ROCKET=🚀
SET ICON_CHECK_MARK=✅
SET ICON_WAIT=⏳
SET ICON_ERROR=❌

REM Function to display colored messages
:color_echo
    echo %~2 %~1%~3%COLOR_RESET%
    exit /b 0


REM Check if Python is installed and version >= 3.9
python --version 2>NUL
if errorlevel 1 (
    call :color_echo %COLOR_RED% %ICON_ERROR% "Error: Python is not installed"
    echo Please install Python 3.9 or higher from https://www.python.org/downloads/
    exit /b 1
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"
if errorlevel 1 (
    call :color_echo %COLOR_RED% %ICON_ERROR% "Error: Python 3.9 or higher is required"
    echo Current Python version:
    python --version
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "TradingENV_virtualenv" (
    call :color_echo %COLOR_CYAN% %ICON_ROCKET% "Creating virtual environment..."
    python -m venv TradingENV_virtualenv
) else (
    call :color_echo %COLOR_WAIT% %ICON_WAIT% "Virtual environment exists, checking for updates..."
)

REM Activate virtual environment
call TradingENV_virtualenv\Scripts\activate.bat

REM Upgrade pip to latest version
call :color_echo %COLOR_CYAN% %ICON_ROCKET% "Upgrading pip..."
python -m pip install --upgrade pip

REM Install/upgrade required packages including colorama
call :color_echo %COLOR_CYAN% %ICON_ROCKET% "Installing dependencies (including colorama)..."
pip install --upgrade -r requirements.txt
if errorlevel 1 (
    call :color_echo %COLOR_RED% %ICON_ERROR% "Failed to install dependencies. Check requirements.txt"
    exit /b 1
)

REM Verify colorama installation
python -c "import colorama" 2>NUL
if errorlevel 1 (
    call :color_echo %COLOR_RED% %ICON_ERROR% "Error: colorama installation failed."
    echo Please check pip and virtual environment setup.
    exit /b 1
)

call :color_echo %COLOR_GREEN% %ICON_CHECK_MARK% "colorama package verified."


REM Create .env file from template if it doesn't exist
if not exist ".env" (
    call :color_echo %COLOR_CYAN% %ICON_ROCKET% "Creating .env file from template..."
    copy .env.example .env
    echo Please edit .env file with your API credentials.
)

REM Create logs directory
if not exist "logs" (
    call :color_echo %COLOR_CYAN% %ICON_ROCKET% "Creating logs directory..."
    mkdir logs
)

REM Create utils directory
if not exist "src\utils" (
    call :color_echo %COLOR_CYAN% %ICON_ROCKET% "Creating utils directory..."
    mkdir src\utils
)

REM Set environment variables
SET PYTHONPATH=%~dp0
SET PYTHONUNBUFFERED=1

echo.
call :color_echo %COLOR_GREEN% %ICON_CHECK_MARK% "Setup complete! Environment is ready."
echo.
echo Important steps before running:
echo 1. Edit .env file with your Deriv.com API credentials
echo 2. Configure your trading parameters in .env file
echo 3. Run the bot using: start.bat
echo.
echo Type 'deactivate' to exit the virtual environment
