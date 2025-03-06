@echo off
@REM Ensure that batch script is executed with color support enabled
@IF NOT DEFINED __COLORS_DEFINED  powershell -Command "& {$env:__COLORS_DEFINED=1 ; cmd /V:on /E:on /C \"%~f0\"}"; & exit /b %errorlevel%
@SETLOCAL

echo Starting Trading Bot...

REM --- Color definitions ---
SET COLOR_RESET= [0m
SET COLOR_CYAN= [36m
SET COLOR_GREEN= [32m
SET COLOR_YELLOW= [33m
SET COLOR_RED= [31m

REM --- Icon definitions ---
SET ICON_ROCKET=🚀
SET ICON_CHECK_MARK=✅
SET ICON_WAIT=⏳
SET ICON_ERROR=❌

REM Function to display colored messages
:color_echo
    echo %~2 %~1%~3%COLOR_RESET%
    exit /b 0

REM Check if virtual environment exists
if not exist "TradingENV_virtualenv" (
    call :color_echo %COLOR_WAIT% %ICON_WAIT% "Virtual environment not found"
    echo Running setup...
    call "%~dp0setup_env.bat"
    if errorlevel 1 (
        call :color_echo %COLOR_RED% %ICON_ERROR% "Failed to setup environment"
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call TradingENV_virtualenv\Scripts\activate.bat
if errorlevel 1 (
    call :color_echo %COLOR_RED% %ICON_ERROR% "Failed to activate virtual environment"
    pause
    exit /b 1
)

REM Verify Python packages
python -c "import deriv_api" 2>NUL
if errorlevel 1 (
    call :color_echo %COLOR_WAIT% %ICON_WAIT% "Required packages not found"
    call :color_echo %COLOR_CYAN% %ICON_ROCKET% "Installing dependencies..."
    pip install -r requirements.txt
    if errorlevel 1 (
        call :color_echo %COLOR_RED% %ICON_ERROR% "Failed to install dependencies"
        pause
        exit /b 1
    )
)

REM Check if .env file exists
if not exist ".env" (
    call :color_echo %COLOR_RED% %ICON_ERROR% "Error: .env file not found"
    call :color_echo %COLOR_CYAN% %ICON_ROCKET% "Creating from template..."
    copy .env.example .env
    echo Please edit .env file with your API credentials
    notepad .env
    exit /b 1
)

REM Create logs directory if needed
if not exist "logs" mkdir logs

REM Set environment variables
SET PYTHONPATH=%~dp0
SET PYTHONUNBUFFERED=1

REM Start the bot
call :color_echo %COLOR_CYAN% %ICON_ROCKET% "Starting bot in %ENVIRONMENT% mode..."
python main.py
if errorlevel 1 (
    call :color_echo %COLOR_RED% %ICON_ERROR% "Bot exited with error code %errorlevel%"
    echo Check logs/trading_bot.log for details
    pause
    exit /b 1
)

pause
