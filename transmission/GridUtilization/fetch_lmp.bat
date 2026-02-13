@echo off
REM Fetch CAISO Real-Time Market LMP data for 2020-2025

cd /d "%~dp0"

echo ===================================
echo Fetching CAISO LMP Data
echo ===================================
echo.
echo This will fetch hourly LMP data from CAISO OASIS API
echo for 2020-2025 (2,192 days).
echo.
echo Data source: Real-Time Market (RTM)
echo Location: SP15 Trading Hub (Southern California)
echo.
echo Note: This will take approximately 2-3 hours due to
echo API rate limiting (1 request per 2 seconds).
echo.

pause

python fetch_lmp.py

echo.
echo ===================================
echo Done!
echo ===================================
pause
