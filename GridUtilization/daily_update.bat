@echo off
REM ========================================================================
REM CAISO Daily Data Update - One-Click Launcher
REM ========================================================================
REM
REM This batch file runs the daily update script to:
REM   1. Download latest CAISO data (demand, supply, prices)
REM   2. Recalculate metrics with corrected methodology
REM   3. Regenerate all charts
REM   4. Push updates to GitHub
REM
REM Usage:
REM   - Double-click to run daily update
REM   - Run with --force flag to update even if data is current
REM   - Run with --full flag to include comprehensive CSV update
REM
REM ========================================================================

SETLOCAL EnableDelayedExpansion

REM Set window title
title CAISO Daily Data Update

REM Enable ANSI color codes (Windows 10+)
REM Note: This may not work in older Windows versions
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do (
  set "ESC=%%b"
)

REM Change to script directory
cd /d "%~dp0"

echo ========================================================================
echo                    CAISO DAILY DATA UPDATE
echo ========================================================================
echo.
echo This script will:
echo   [1] Check for missing dates
echo   [2] Download CAISO data (demand, supply, LMP, A/S)
echo   [3] Recalculate renewable penetration
echo   [4] Regenerate all charts
echo   [5] Push updates to GitHub
echo.
echo Working directory: %CD%
echo.
echo ========================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.7+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo [OK] Python found
python --version
echo.

REM Check if git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Git is not installed or not in PATH
    echo GitHub push will be skipped
    echo.
    set GIT_AVAILABLE=0
) else (
    echo [OK] Git found
    git --version
    echo.
    set GIT_AVAILABLE=1
)

REM Check if daily_update.py exists
if not exist "daily_update.py" (
    echo [ERROR] daily_update.py not found in current directory
    echo.
    echo Please make sure you're running this from the GridUtilization directory
    echo.
    pause
    exit /b 1
)

echo [OK] Update script found
echo.

REM Parse command line arguments
set FORCE_FLAG=
set FULL_FLAG=
if "%~1"=="--force" set FORCE_FLAG=--force
if "%~1"=="--full" set FULL_FLAG=--full
if "%~2"=="--force" set FORCE_FLAG=--force
if "%~2"=="--full" set FULL_FLAG=--full

REM Display flags if any
if defined FORCE_FLAG (
    echo [INFO] Force mode enabled - will update even if data is current
    echo.
)
if defined FULL_FLAG (
    echo [INFO] Full mode enabled - will update comprehensive CSV
    echo.
)

echo ========================================================================
echo Starting update process...
echo ========================================================================
echo.

REM Run the Python script
python daily_update.py %FORCE_FLAG% %FULL_FLAG%

REM Check exit code
if errorlevel 1 (
    echo.
    echo ========================================================================
    echo [ERROR] Update process completed with errors
    echo ========================================================================
    echo.
    echo Please review the output above for details
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ========================================================================
    echo [SUCCESS] Update process completed successfully!
    echo ========================================================================
    echo.
    echo Your website has been updated with the latest data
    echo Changes have been pushed to GitHub
    echo.
)

REM Optional: Open website in browser
REM Uncomment the line below to automatically open website after update
REM start https://eshan2803.github.io/eshan-website/

echo.
echo Update completed at %date% %time%
echo.

pause
