@echo off
cd /d "%~dp0"

echo ==============================================
echo CAISO Demand Forecast Fetcher
echo ==============================================
echo.

REM Pass all command-line arguments to the Python script
REM Usage:
REM   fetch_demand.bat                        (fetches today)
REM   fetch_demand.bat 2026-02-10             (fetches single date)
REM   fetch_demand.bat 2026-02-01 2026-02-11  (fetches date range)

python fetch_demand.py %*
set PYERR=%ERRORLEVEL%

if %PYERR% NEQ 0 (
    echo.
    echo [ERROR] Script failed with exit code %PYERR%.
)

echo.
echo Press any key to close this window...
pause >nul
