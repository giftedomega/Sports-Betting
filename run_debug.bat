@echo off
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate

echo Starting Football Betting Analysis (Debug Mode)...
echo Hot reload enabled - changes will restart server
echo.
python main.py --reload --debug

pause
