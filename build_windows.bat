@echo off
REM Windows build script for Albion Trade Optimizer
REM Run this script on Windows to build the executable

echo Building Albion Trade Optimizer for Windows...
echo ================================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.11+ and add it to PATH.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

REM Install PyInstaller
echo Installing PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller.
    pause
    exit /b 1
)

REM Test the application
echo Testing application...
python main.py --test
if errorlevel 1 (
    echo WARNING: Application test failed. Continuing with build...
)

REM Run build script
echo Running build script...
python build.py
if errorlevel 1 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)

echo.
echo ================================================
echo Build completed successfully!
echo.
echo Outputs:
echo - Executable: dist\AlbionTradeOptimizer.exe
echo - Installer script: installer.iss
echo.
echo Next steps:
echo 1. Test the executable: dist\AlbionTradeOptimizer.exe
echo 2. Install Inno Setup to build installer
echo 3. Compile installer.iss to create setup.exe
echo.
pause

